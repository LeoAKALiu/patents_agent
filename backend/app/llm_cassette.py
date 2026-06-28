from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from backend.app.llm import ConfigError, LLMClient


class LLMCassetteError(ConfigError):
    pass


_LOCKS_GUARD = Lock()
_CASSETTE_LOCKS: dict[Path, Lock] = {}


def maybe_wrap_with_cassette(
    delegate: LLMClient,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> LLMClient:
    mode = os.environ.get("PATENTAGENT_LLM_MODE", "live").strip().lower() or "live"
    if mode == "live":
        return delegate
    if mode not in {"record", "replay"}:
        raise LLMCassetteError(
            "PATENTAGENT_LLM_MODE must be one of: live, record, replay."
        )
    return CassetteLLMClient(
        delegate=delegate,
        mode=mode,
        provider=provider or _provider_name(delegate),
        model=model or str(getattr(delegate, "model", "") or _provider_name(delegate)),
        cassette_path=_cassette_path(),
    )


@dataclass
class CassetteLLMClient:
    delegate: LLMClient
    mode: str
    provider: str
    model: str
    cassette_path: Path

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        key = cassette_key(
            provider=self.provider,
            model=self.model,
            stage=stage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if self.mode == "replay":
            return self._replay(key, stage)

        response = self.delegate.complete_stage(stage, system_prompt, user_prompt)
        self._record(
            key=key,
            stage=stage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
        return response

    def _replay(self, key: str, stage: str) -> str:
        payload = _read_cassette(self.cassette_path)
        entry = payload.get("entries", {}).get(key)
        if not entry:
            raise LLMCassetteError(
                f"missing cassette entry for stage {stage!r} in {self.cassette_path}"
            )
        return str(entry["response"])

    def _record(
        self,
        *,
        key: str,
        stage: str,
        system_prompt: str,
        user_prompt: str,
        response: str,
    ) -> None:
        with _cassette_lock(self.cassette_path):
            payload = _read_cassette(self.cassette_path)
            entries = payload.setdefault("entries", {})
            entries[key] = {
                "key": key,
                "provider": self.provider,
                "model": self.model,
                "stage": stage,
                "messages": _messages(system_prompt, user_prompt),
                "response": response,
            }
            _write_cassette(self.cassette_path, payload)


def cassette_key(
    *,
    provider: str,
    model: str,
    stage: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    payload = {
        "provider": provider,
        "model": model,
        "messages": _messages(system_prompt, user_prompt),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _normalize_text(system_prompt)},
        {"role": "user", "content": _normalize_text(user_prompt)},
    ]


def _normalize_text(value: str) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n")


def _cassette_path() -> Path:
    base = Path(os.environ.get("PATENTAGENT_LLM_CASSETTE_DIR", "tests/cassettes"))
    suite = _safe_path_part(os.environ.get("PATENTAGENT_LLM_CASSETTE_SUITE", "default"))
    case = _safe_path_part(os.environ.get("PATENTAGENT_LLM_CASSETTE_CASE", "default"))
    return base / suite / f"{case}.json"


def _safe_path_part(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "default"


def _provider_name(delegate: LLMClient) -> str:
    return delegate.__class__.__name__


def _cassette_lock(path: Path) -> Lock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        lock = _CASSETTE_LOCKS.get(resolved)
        if lock is None:
            lock = Lock()
            _CASSETTE_LOCKS[resolved] = lock
        return lock


def _read_cassette(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "entries": {}}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise LLMCassetteError(f"Invalid cassette payload in {path}")
    payload.setdefault("version", 1)
    payload.setdefault("entries", {})
    return payload


def _write_cassette(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp_path.replace(path)
