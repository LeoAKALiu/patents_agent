"""System health and agent diagnostics router.

Endpoints moved from ``backend/app/main.py``:
  * GET /api/health
  * GET /api/agents/doctor
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.llm import MissingLLMClient

router = APIRouter(tags=["system"])


@router.get("/api/health")
def health(request: Request) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    return {
        "ok": True,
        "llm_configured": not isinstance(llm, MissingLLMClient),
        "data_dir": str(settings.data_dir),
        "model": settings.llm_model,
        "embedding_model": settings.embedding_model,
    }


@router.get("/api/agents/doctor")
def agent_doctor() -> dict:
    return inspect_agent_environment().model_dump(mode="json")
