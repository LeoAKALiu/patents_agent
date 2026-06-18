"""Stage-level LLM cache helpers.

This module keeps cache behavior outside the LLM client protocol. Callers pass
a fallback callable, so FakeLLMClient and existing tests keep the same surface.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from collections.abc import Callable

from backend.app.llm import LLMClient
from backend.app.storage import SQLiteStore


def stage_cache_key(
    *,
    project_id: str,
    stage: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    source_hash: str,
    prompt_pack_version: str = "",
) -> str:
    prompt_hash = _hash_json({"system_prompt": system_prompt, "user_prompt": user_prompt})
    input_hash = _hash_text(source_hash)
    payload = {
        "project_id": project_id,
        "stage": stage,
        "model": model,
        "prompt_hash": prompt_hash,
        "input_hash": input_hash,
        "prompt_pack_version": prompt_pack_version,
    }
    return "llm-stage:" + _hash_json(payload)


def complete_stage_cached(
    *,
    store: SQLiteStore,
    project_id: str,
    stage: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    source_hash: str,
    fallback: Callable[[], str],
    prompt_pack_version: str = "",
    response_json: str | None = None,
    timeout_s: float | None = None,
    retries: int = 0,
    expires_at: str | None = None,
) -> str:
    prompt_hash = _hash_json({"system_prompt": system_prompt, "user_prompt": user_prompt})
    input_hash = _hash_text(source_hash)
    cache_key = stage_cache_key(
        project_id=project_id,
        stage=stage,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        source_hash=source_hash,
        prompt_pack_version=prompt_pack_version,
    )
    cached = store.get_llm_stage_cache(cache_key)
    if cached and cached.get("status") == "completed":
        return str(cached["response_text"])

    response_text = _call_with_retry(fallback, retries=retries, timeout_s=timeout_s)
    store.put_llm_stage_cache(
        cache_key=cache_key,
        project_id=project_id,
        stage=stage,
        model=model,
        prompt_hash=prompt_hash,
        input_hash=input_hash,
        prompt_pack_version=prompt_pack_version,
        response_text=response_text,
        response_json=response_json,
        status="completed",
        expires_at=expires_at,
    )
    return response_text


def clear_project_llm_cache(store: SQLiteStore, project_id: str) -> int:
    return store.clear_project_llm_cache(project_id)


class CachedStageLLMClient:
    """LLMClient wrapper that caches individual stage completions."""

    def __init__(
        self,
        *,
        store: SQLiteStore,
        project_id: str,
        source_hash: str,
        delegate: LLMClient,
        model: str = "",
        prompt_pack_version: str = "",
        timeout_s: float | None = None,
        retries: int = 0,
    ) -> None:
        self.store = store
        self.project_id = project_id
        self.source_hash = source_hash
        self.delegate = delegate
        delegate_model = getattr(delegate, "model", "")
        self.model = model or delegate_model or f"{delegate.__class__.__name__}:{id(delegate)}"
        self.prompt_pack_version = prompt_pack_version
        self.timeout_s = timeout_s
        self.retries = retries

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        return complete_stage_cached(
            store=self.store,
            project_id=self.project_id,
            stage=stage,
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            source_hash=self.source_hash,
            prompt_pack_version=self.prompt_pack_version,
            timeout_s=self.timeout_s,
            retries=self.retries,
            fallback=lambda: self.delegate.complete_stage(stage, system_prompt, user_prompt),
        )


def _call_with_retry(fallback: Callable[[], str], *, retries: int, timeout_s: float | None) -> str:
    attempts = max(0, retries) + 1
    last_error: BaseException | None = None
    for _attempt in range(attempts):
        try:
            if timeout_s is None:
                return fallback()
            return _call_with_timeout(fallback, timeout_s)
        except BaseException as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("LLM fallback did not run.")


def _call_with_timeout(fallback: Callable[[], str], timeout_s: float) -> str:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fallback)
        return future.result(timeout=timeout_s)


def _hash_json(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_text(canonical)


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
