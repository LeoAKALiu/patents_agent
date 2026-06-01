from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


class ConfigError(RuntimeError):
    pass


class LLMClient(Protocol):
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass
class LLMCall:
    stage: str
    system_prompt: str
    user_prompt: str


class MissingLLMClient:
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        raise ConfigError("LLM is not configured. Set DEEPSEEK_API_KEY before generating drafts.")


class FakeLLMClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[LLMCall] = []

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(LLMCall(stage=stage, system_prompt=system_prompt, user_prompt=user_prompt))
        return self.responses[stage]


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
