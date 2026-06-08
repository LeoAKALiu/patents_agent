from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


class ConfigError(RuntimeError):
    pass


class StructuredOutputError(RuntimeError):
    """Raised when an LLM stage cannot produce a valid JSON object after a repair retry.

    Callers must treat this as a hard failure (return 503) and never persist raw text.
    """

    def __init__(self, stage: str, message: str, *, raw: str = "") -> None:
        super().__init__(message)
        self.stage = stage
        self.raw = raw


class LLMClient(Protocol):
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        ...

    def complete_stage_json(self, stage: str, system_prompt: str, user_prompt: str) -> dict:
        ...


@dataclass
class LLMCall:
    stage: str
    system_prompt: str
    user_prompt: str


class MissingLLMClient:
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        raise ConfigError("LLM is not configured. Set DEEPSEEK_API_KEY before generating drafts.")

    def complete_stage_json(self, stage: str, system_prompt: str, user_prompt: str) -> dict:
        raise ConfigError("LLM is not configured. Set DEEPSEEK_API_KEY before generating drafts.")


class FakeLLMClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[LLMCall] = []

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(LLMCall(stage=stage, system_prompt=system_prompt, user_prompt=user_prompt))
        return self.responses[stage]

    def complete_stage_json(self, stage: str, system_prompt: str, user_prompt: str) -> dict:
        self.calls.append(LLMCall(stage=stage, system_prompt=system_prompt, user_prompt=user_prompt))
        raw = self.responses[stage]
        payload = _parse_json_object(raw)
        if payload is None:
            raise StructuredOutputError(stage, f"Fake response for stage {stage} is not a JSON object.", raw=raw)
        return payload


class DeepSeekLLMClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        if not api_key:
            raise ConfigError("DEEPSEEK_API_KEY is required.")
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(f"LLM returned empty content for stage {stage}.")
        return content

    def complete_stage_json(self, stage: str, system_prompt: str, user_prompt: str) -> dict:
        system = (
            f"{system_prompt}\n"
            "只输出符合要求的单个 JSON 对象，不要输出任何解释、开场白、Markdown 代码块或多余文本。"
        )
        last_raw = ""
        for attempt in range(2):
            prompt = user_prompt
            if attempt == 1:
                prompt = (
                    f"{user_prompt}\n\n上一次输出无法解析为合法 JSON 对象，请仅返回一个合法 JSON 对象。"
                    f"上次输出片段：{last_raw[:500]}"
                )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            last_raw = response.choices[0].message.content or ""
            payload = _parse_json_object(last_raw)
            if payload is not None:
                return payload
        raise StructuredOutputError(
            stage, f"LLM did not return a valid JSON object for stage {stage} after retry.", raw=last_raw
        )


def _parse_json_object(text: str) -> dict | None:
    """Best-effort extraction of a single JSON object from model output (handles code fences)."""
    stripped = (text or "").strip()
    if not stripped:
        return None
    candidates = [stripped]
    if "```" in stripped:
        candidates.extend(part.replace("json", "", 1).strip() for part in stripped.split("```") if "{" in part)
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None
