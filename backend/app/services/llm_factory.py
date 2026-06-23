"""Build the LLM client from environment settings and desktop config.

Extracted from backend/app/main.py so routers and tests can reuse the
construction logic without importing the FastAPI application module.
"""

from __future__ import annotations

import re

from backend.app.desktop_config import DesktopConfig, effective_settings
from backend.app.llm import ConfigError, DeepSeekLLMClient, LLMClient, MissingLLMClient
from backend.app.settings import Settings

_API_KEY_REDACT_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]{6,})")


def build_llm(
    settings: Settings, desktop_config: DesktopConfig | None = None
) -> LLMClient:
    """Return an LLM client from *settings* merged with *desktop_config*.

    Desktop config values take precedence over env/``.env`` values.
    When no API key is available a ``MissingLLMClient`` is returned so
    callers can still boot and serve health checks.
    """
    effective = effective_settings(
        settings, desktop_config or DesktopConfig()
    )
    api_key = effective["api_key"]
    if not api_key:
        return MissingLLMClient()
    return DeepSeekLLMClient(
        api_key=api_key,
        base_url=effective["base_url"] or None,
        model=effective["model"],
    )


def redact_error_message(exc: BaseException) -> str:
    """Return a short, key-free description of *exc* for the health endpoint."""
    text = f"{type(exc).__name__}: {exc}"
    return _API_KEY_REDACT_PATTERN.sub("sk-...", text)[:512]
