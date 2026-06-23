"""Desktop configuration helpers extracted from the application module.

These helpers are consumed by the ``desktop_config`` API router and by
Tauri bridge commands that need to enforce origin checks without importing
the FastAPI application.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request

from backend.app.desktop_config import (
    DesktopConfig,
    DesktopConfigError,
    apply_update as dc_apply_update,
    effective_settings,
    redacted_view,
    save_desktop_config,
)
from backend.app.settings import Settings

LOCAL_RENDERER_ORIGINS: frozenset[str] = frozenset(
    {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    }
)


def enforce_desktop_config_origin(request: Request) -> None:
    """Reject browser-originated config writes from non-renderer origins.

    Tauri command invocations and backend tests do not send Origin, so
    absence is allowed.  Browser requests from arbitrary sites send Origin
    and must not be able to read or mutate the local desktop LLM
    configuration.
    """
    origin = request.headers.get("origin")
    if origin and origin not in LOCAL_RENDERER_ORIGINS:
        raise HTTPException(
            status_code=403, detail="Forbidden desktop config origin."
        )


def desktop_config_view(
    settings: Settings, desktop_config: DesktopConfig
) -> dict[str, Any]:
    """Return the redacted view the renderer is allowed to see."""
    view = redacted_view(desktop_config)
    effective = effective_settings(settings, desktop_config)
    view["provider"] = effective["provider"]
    view["base_url"] = effective["base_url"]
    view["model"] = effective["model"]
    view["api_key_source"] = effective["api_key_source"]
    return view


def desktop_config_update(
    settings: Settings,
    desktop_config: DesktopConfig,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    clear_api_key: bool = False,
) -> tuple[dict[str, Any], DesktopConfig]:
    """Apply an update payload to *desktop_config* and persist it.

    Returns ``(redacted_view, saved_config)``.  Raises ``DesktopConfigError``
    (subclass of ``ValueError``) when validation fails.
    """
    updated = dc_apply_update(
        desktop_config,
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
        clear_api_key=clear_api_key,
    )
    saved = save_desktop_config(settings.data_dir, updated)
    view = desktop_config_view(settings, saved)
    return view, saved


def desktop_config_health_check(
    settings: Settings, desktop_config: DesktopConfig
) -> dict[str, Any]:
    """Probe the configured LLM with a tiny request.

    The raw API key is never echoed in the result or in error messages.
    """
    from backend.app.services.llm_factory import redact_error_message

    effective = effective_settings(settings, desktop_config)
    api_key = effective["api_key"]
    model = effective["model"]
    base_url = effective["base_url"]
    result: dict[str, Any] = {
        "ok": False,
        "model": model,
        "api_key_source": effective["api_key_source"],
        "latency_ms": 0,
        "status_code": 0,
        "error": "",
    }
    if not api_key:
        result["error"] = "no_api_key"
        return result

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    started = time.monotonic()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "ping"},
                {"role": "user", "content": "ping"},
            ],
            max_tokens=1,
            temperature=0,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        result["ok"] = bool(completion.choices)
        result["latency_ms"] = latency_ms
        result["status_code"] = 200
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        latency_ms = int((time.monotonic() - started) * 1000)
        result["latency_ms"] = latency_ms
        result["error"] = redact_error_message(exc)
        status = getattr(exc, "status_code", None) or 0
        result["status_code"] = int(status) if isinstance(status, int) else 0
    return result
