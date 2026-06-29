"""Projects API router - project CRUD, materials, and patent point endpoints.

Endpoints moved from ``backend/app/main.py``:
  * GET    /api/projects                                      - list projects
  * POST   /api/projects                                      - create project
  * GET    /api/projects/{project_id}                          - get project
  * PUT    /api/projects/{project_id}                          - update project
  * DELETE /api/projects/{project_id}                          - delete project
  * POST   /api/projects/{project_id}/materials                - upload material
  * GET    /api/projects/{project_id}/materials                - list materials
  * GET    /api/projects/{project_id}/patent-points            - list patent points
  * POST   /api/projects/{project_id}/patent-points            - create patent point
  * PATCH  /api/projects/{project_id}/patent-points/{point_id} - update point
  * DELETE /api/projects/{project_id}/patent-points/{point_id} - delete point
  * POST   /api/projects/{project_id}/patent-points/{point_id}/evaluate-moat - moat
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from backend.app.api.deps import get_project_repository, require_project
from backend.app.schemas import (
    PatentPointCreate,
    PatentPointUpdate,
    ProjectCreate,
    ProjectUpdate,
)
from backend.app.services.project_service import (
    apply_project_update,
    build_patent_point_candidate,
    build_project_record,
    evaluate_point_moat,
    import_project_material,
    merge_patent_point_update,
    project_material_upload_error,
)
from backend.app.services.project_knowledge_service import ensure_project_knowledge_initialized

router = APIRouter(tags=["projects"])


@router.get("/api/projects")
def list_projects(request: Request) -> dict:
    repo = get_project_repository(request)
    return {
        "projects": [
            project.model_dump(mode="json") for project in repo.list_all()
        ]
    }


@router.post("/api/projects")
def create_project(payload: ProjectCreate, request: Request) -> dict:
    repo = get_project_repository(request)
    project = build_project_record(payload)
    stored = repo.create(project)
    ensure_project_knowledge_initialized(request.app.state.store, stored)
    return stored.model_dump(mode="json")


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    project = require_project(project_id, repo)
    return project.model_dump(mode="json")


@router.put("/api/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    updated = apply_project_update(project_id, payload, repo)
    if updated is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return updated.model_dump(mode="json")


@router.delete("/api/projects/{project_id}")
def delete_project(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    deleted = repo.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"ok": True}


@router.post("/api/projects/{project_id}/materials")
async def upload_project_material(
    request: Request, project_id: str, file: UploadFile = File(...)
) -> dict:
    repo = get_project_repository(request)
    settings = request.app.state.settings
    require_project(project_id, repo)
    upload_dir = settings.data_dir / "project-materials" / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "material.txt").name
    stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
    with stored_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    try:
        material = import_project_material(
            project_id=project_id,
            file_name=safe_name,
            stored_path=stored_path,
            repo=repo,
        )
    except ValueError as exc:
        try:
            stored_path.unlink()
        except OSError:
            pass
        status_code, detail = project_material_upload_error(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return material.model_dump(mode="json")


@router.get("/api/projects/{project_id}/materials")
def list_project_materials(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return {
        "materials": [
            material.model_dump(mode="json")
            for material in repo.list_materials(project_id)
        ]
    }


@router.get("/api/projects/{project_id}/patent-points")
def list_project_patent_points(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return {
        "points": [
            point.model_dump(mode="json")
            for point in repo.list_patent_points(project_id)
        ]
    }


@router.post("/api/projects/{project_id}/patent-points")
def create_project_patent_point(
    project_id: str, payload: PatentPointCreate, request: Request
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    point = build_patent_point_candidate(payload)
    stored = repo.add_patent_point(project_id, point)
    return stored.model_dump(mode="json")


@router.patch("/api/projects/{project_id}/patent-points/{point_id}")
def update_project_patent_point(
    project_id: str, point_id: str, payload: PatentPointUpdate, request: Request
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    existing = repo.get_patent_point(project_id, point_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patent point not found.")
    try:
        updated = merge_patent_point_update(existing, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = repo.add_patent_point(project_id, updated)
    return stored.model_dump(mode="json")


@router.delete("/api/projects/{project_id}/patent-points/{point_id}")
def delete_project_patent_point(
    project_id: str, point_id: str, request: Request
) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    deleted = repo.delete_patent_point(project_id, point_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patent point not found.")
    return {"ok": True}


@router.post("/api/projects/{project_id}/patent-points/{point_id}/evaluate-moat")
def evaluate_patent_point_moat(
    project_id: str, point_id: str, request: Request
) -> dict:
    repo = get_project_repository(request)
    llm = request.app.state.llm
    project = require_project(project_id, repo)
    existing = repo.get_patent_point(project_id, point_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patent point not found.")
    try:
        updated = evaluate_point_moat(project=project, point=existing, llm=llm)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    stored = repo.add_patent_point(project_id, updated)
    return stored.model_dump(mode="json")
