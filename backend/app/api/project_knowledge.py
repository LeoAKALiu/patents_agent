from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.deps import get_project_repository, require_project
from backend.app.schemas import (
    BuildProjectCorpusRequest,
    CandidateBulkDecision,
    CandidateDecisionPatch,
)
from backend.app.services.project_knowledge_service import (
    ProjectKnowledgeConflictError,
    create_project_corpus_from_included_candidates,
    knowledge_overview,
    regenerate_project_knowledge,
    run_agent_search_plan,
)

router = APIRouter(tags=["project-knowledge"])


@router.get("/api/projects/{project_id}/knowledge")
def get_project_knowledge(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return knowledge_overview(request.app.state.store, project_id).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-intent")
def create_project_search_intent(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    project = require_project(project_id, repo)
    patent_points = repo.list_patent_points(project_id)
    return regenerate_project_knowledge(request.app.state.store, project, patent_points).model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/search-plans/{plan_id}/run")
def run_project_search_plan(project_id: str, plan_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    try:
        overview = run_agent_search_plan(request.app.state.store, project_id, plan_id)
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return overview.model_dump(mode="json")


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
    candidate = request.app.state.store.update_prior_art_candidate_decision(
        project_id,
        candidate_id,
        payload.user_decision,
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Prior-art candidate not found.")
    return candidate.model_dump(mode="json")


@router.post("/api/projects/{project_id}/knowledge/candidates/bulk-decision")
def update_project_candidate_decisions(
    project_id: str,
    payload: CandidateBulkDecision,
    request: Request,
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    store = request.app.state.store
    known_candidates = {
        candidate.id: candidate
        for candidate in store.list_prior_art_candidates(project_id)
    }
    missing_ids = [candidate_id for candidate_id in payload.candidate_ids if candidate_id not in known_candidates]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Prior-art candidate not found: {missing_ids[0]}",
        )
    updated = []
    for candidate_id in payload.candidate_ids:
        candidate = store.update_prior_art_candidate_decision(
            project_id,
            candidate_id,
            payload.user_decision,
        )
        if candidate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Prior-art candidate not found: {candidate_id}",
            )
        updated.append(candidate.model_dump(mode="json"))
    return {"candidates": updated}


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
    return overview.model_dump(mode="json")
