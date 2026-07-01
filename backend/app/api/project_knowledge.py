from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi import File, Form, UploadFile

from backend.app.api.deps import get_project_repository, require_project
from backend.app.evidence_sources import evidence_source_views
from backend.app.knowledge.patent_sources import list_patent_source_capabilities
from backend.app.schemas import (
    BuildProjectCorpusRequest,
    CandidateBulkDecision,
    CandidateDecisionPatch,
)
from backend.app.services.project_knowledge_service import (
    ProjectKnowledgeConflictError,
    bulk_update_project_candidate_decisions,
    create_project_corpus_from_included_candidates,
    get_cnipa_query_pack,
    import_cnipa_official_export,
    knowledge_overview,
    regenerate_project_knowledge,
    run_agent_search_plan,
    update_project_candidate_decision as update_project_candidate_decision_in_store,
)

router = APIRouter(tags=["project-knowledge"])
CNIPA_EXPORT_UPLOAD_SUFFIXES = frozenset({".csv", ".xlsx", ".zip"})
MAX_CNIPA_EXPORT_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


def _resolve_patent_search_providers(request: Request, project_id: str, plan_id: str):
    providers = getattr(request.app.state, "project_patent_search_providers", None)
    if callable(providers):
        return providers(project_id=project_id, plan_id=plan_id)
    return providers


def _overview_with_source_statuses(request: Request, overview):
    return overview.model_copy(
        update={"source_statuses": evidence_source_views(request.app.state.settings.data_dir)}
    )


async def _stream_cnipa_export_upload(file: UploadFile, destination: Path) -> None:
    try:
        suffix = destination.suffix.lower()
        if suffix not in CNIPA_EXPORT_UPLOAD_SUFFIXES:
            raise ValueError(f"Unsupported CNIPA export file type: {suffix or '(none)'}")
        total_bytes = 0
        with destination.open("wb") as handle:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_CNIPA_EXPORT_UPLOAD_BYTES:
                    raise ValueError(
                        f"CNIPA export upload exceeds the upload limit of {MAX_CNIPA_EXPORT_UPLOAD_BYTES} bytes."
                    )
                handle.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.get("/api/patent-sources")
def list_patent_sources() -> dict:
    return {"sources": [source.model_dump(mode="json") for source in list_patent_source_capabilities()]}


@router.get("/api/projects/{project_id}/knowledge")
def get_project_knowledge(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    source_statuses = evidence_source_views(request.app.state.settings.data_dir)
    return knowledge_overview(request.app.state.store, project_id, source_statuses=source_statuses).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-intent")
def create_project_search_intent(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    project = require_project(project_id, repo)
    patent_points = repo.list_patent_points(project_id)
    overview = regenerate_project_knowledge(request.app.state.store, project, patent_points)
    return _overview_with_source_statuses(request, overview).model_dump(mode="json")


@router.get("/api/projects/{project_id}/knowledge/cnipa-query-pack")
def get_project_cnipa_query_pack(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return get_cnipa_query_pack(request.app.state.store, project_id).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-plans/{plan_id}/run")
def run_project_search_plan(project_id: str, plan_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        overview = run_agent_search_plan(
            request.app.state.store,
            project_id,
            plan_id,
            providers=_resolve_patent_search_providers(request, project_id, plan_id),
            data_dir=request.app.state.settings.data_dir,
        )
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _overview_with_source_statuses(request, overview).model_dump(mode="json")


@router.get("/api/projects/{project_id}/knowledge/search-ledger/{ledger_id}")
def get_project_search_ledger(project_id: str, ledger_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    ledger = request.app.state.store.get_project_search_ledger(project_id, ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Project search ledger not found.")
    return ledger.model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/cnipa-export-imports")
async def import_project_cnipa_export(
    project_id: str,
    request: Request,
    plan_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    settings = request.app.state.settings
    upload_dir = settings.data_dir / "project-knowledge" / project_id / "cnipa-imports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "cnipa-export").name
    stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
    try:
        await _stream_cnipa_export_upload(file, stored_path)
        overview = import_cnipa_official_export(
            request.app.state.store,
            project_id,
            plan_id,
            stored_path,
            source_file_name=safe_name,
        )
    except ProjectKnowledgeConflictError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Failed to import CNIPA export.") from exc
    ledgers = request.app.state.store.list_project_knowledge_import_ledgers(project_id, plan_id)
    return {"overview": _overview_with_source_statuses(request, overview).model_dump(mode="json"), "ledger": ledgers[0].model_dump(mode="json")}


@router.get("/api/projects/{project_id}/knowledge/import-ledgers")
def list_project_knowledge_import_ledgers(project_id: str, request: Request, plan_id: str | None = None) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    ledgers = request.app.state.store.list_project_knowledge_import_ledgers(project_id, plan_id)
    return {"ledgers": [ledger.model_dump(mode="json") for ledger in ledgers]}


@router.get("/api/projects/{project_id}/knowledge/candidates")
def list_project_candidates(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    store = request.app.state.store
    plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, plan.id if plan else None)
    return {"candidates": [candidate.model_dump(mode="json") for candidate in candidates]}


@router.patch("/api/projects/{project_id}/knowledge/candidates/{candidate_id}")
def update_project_candidate_decision(
    project_id: str,
    candidate_id: str,
    payload: CandidateDecisionPatch,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        candidate = update_project_candidate_decision_in_store(
            request.app.state.store,
            project_id,
            candidate_id,
            payload.user_decision,
        )
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return candidate.model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/candidates/bulk-decision")
def update_project_candidate_decisions(
    project_id: str,
    payload: CandidateBulkDecision,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        updated = bulk_update_project_candidate_decisions(
            request.app.state.store,
            project_id,
            payload.candidate_ids,
            payload.user_decision,
        )
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"candidates": [candidate.model_dump(mode="json") for candidate in updated]}


@router.post("/api/projects/{project_id}/knowledge/corpus-versions")
def create_project_corpus_version(
    project_id: str,
    payload: BuildProjectCorpusRequest,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        overview = create_project_corpus_from_included_candidates(
            request.app.state.store,
            project_id,
            payload.plan_id,
        )
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _overview_with_source_statuses(request, overview).model_dump(mode="json")
