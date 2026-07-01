from __future__ import annotations

import json
from typing import Any

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


def _unprocessable_entity(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _parse_config_patch(payload: Any) -> EvidenceSourceConfigPatch:
    if not isinstance(payload, dict):
        raise _unprocessable_entity("Request body must be a JSON object.")

    api_key = payload.get("api_key")
    if api_key is not None and not isinstance(api_key, str):
        raise _unprocessable_entity("api_key must be a string")

    clear_api_key = payload.get("clear_api_key", False)
    if not isinstance(clear_api_key, bool):
        raise _unprocessable_entity("clear_api_key must be a boolean")

    base_url = payload.get("base_url")
    if base_url is not None and not isinstance(base_url, str):
        raise _unprocessable_entity("base_url must be a string or null")

    enabled = payload.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        raise _unprocessable_entity("enabled must be a boolean")

    return EvidenceSourceConfigPatch(
        api_key=api_key,
        clear_api_key=clear_api_key,
        base_url=base_url,
        enabled=enabled,
    )


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
async def put_evidence_source_config(
    source_id: str,
    request: Request,
) -> dict:
    enforce_desktop_config_origin(request)
    try:
        try:
            raw_payload = json.loads(await request.body())
        except json.JSONDecodeError as exc:
            raise _unprocessable_entity("Malformed JSON body.") from exc
        payload = _parse_config_patch(raw_payload)
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
