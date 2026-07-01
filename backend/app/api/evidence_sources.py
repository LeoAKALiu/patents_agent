from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.evidence_sources import (
    check_evidence_source_config,
    evidence_source_views,
    update_evidence_source_config,
)
from backend.app.schemas import EvidenceSourceConfigPatch
from backend.app.services.desktop_config_service import enforce_desktop_config_origin

router = APIRouter(tags=["evidence-sources"])


def _http_exception_from_value_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    status_code = 404 if "Unknown evidence source" in detail else 422
    return HTTPException(status_code=status_code, detail=detail)


@router.get("/api/evidence-sources")
def list_evidence_sources(request: Request) -> dict:
    enforce_desktop_config_origin(request)
    return {
        "sources": [
            source.model_dump(mode="json")
            for source in evidence_source_views(request.app.state.settings.data_dir)
        ]
    }


@router.put("/api/evidence-sources/{source_id}/config")
def put_evidence_source_config(
    source_id: str,
    payload: EvidenceSourceConfigPatch,
    request: Request,
) -> dict:
    enforce_desktop_config_origin(request)
    try:
        view = update_evidence_source_config(
            request.app.state.settings.data_dir,
            source_id,
            payload,
        )
    except ValueError as exc:
        raise _http_exception_from_value_error(exc) from exc
    return view.model_dump(mode="json")


@router.post("/api/evidence-sources/{source_id}/check")
def post_evidence_source_check(source_id: str, request: Request) -> dict:
    enforce_desktop_config_origin(request)
    try:
        result = check_evidence_source_config(request.app.state.settings.data_dir, source_id)
    except ValueError as exc:
        raise _http_exception_from_value_error(exc) from exc
    return result.model_dump(mode="json")
