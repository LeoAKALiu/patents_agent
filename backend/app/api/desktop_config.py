"""Desktop LLM configuration router.

Endpoints moved from ``backend/app/main.py``:
  * GET  /api/desktop-config     - redacted view (no raw API key)
  * PATCH /api/desktop-config    - persist local LLM settings
  * POST /api/desktop-config/health - probe the configured LLM

Delegates business logic to ``backend.app.services.desktop_config_service``
so the router module stays thin and the service is testable in isolation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.desktop_config import DesktopConfigError
from backend.app.schemas import (
    DesktopConfigHealthResult,
    DesktopConfigUpdate,
    DesktopConfigView,
)
from backend.app.services.desktop_config_service import (
    desktop_config_health_check,
    desktop_config_update,
    desktop_config_view,
    enforce_desktop_config_origin,
)
from backend.app.services.llm_factory import build_llm

router = APIRouter(tags=["desktop-config"])


@router.get("/api/desktop-config", response_model=DesktopConfigView)
def get_desktop_config(request: Request) -> dict:
    """Return the redacted desktop LLM configuration (no raw key)."""
    enforce_desktop_config_origin(request)
    return desktop_config_view(
        request.app.state.settings,
        request.app.state.desktop_config,
    )


@router.patch("/api/desktop-config", response_model=DesktopConfigView)
def patch_desktop_config(payload: DesktopConfigUpdate, request: Request) -> dict:
    """Persist a desktop LLM configuration update on the local machine.

    The raw API key is dropped from the response and from any log lines.
    The ``.env`` file is never touched.
    """
    enforce_desktop_config_origin(request)
    try:
        view, saved = desktop_config_update(
            request.app.state.settings,
            request.app.state.desktop_config,
            provider=payload.provider,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
            clear_api_key=payload.clear_api_key,
        )
    except DesktopConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    request.app.state.desktop_config = saved
    # Rebuild the LLM so subsequent generation calls pick up the new key.
    if not request.app.state.llm_client_override:
        request.app.state.llm = build_llm(
            request.app.state.settings, saved
        )
    return view


@router.post(
    "/api/desktop-config/health",
    response_model=DesktopConfigHealthResult,
)
def desktop_config_health(request: Request) -> dict:
    """Probe the configured LLM with a tiny request without echoing the key."""
    enforce_desktop_config_origin(request)
    return desktop_config_health_check(
        request.app.state.settings,
        request.app.state.desktop_config,
    )
