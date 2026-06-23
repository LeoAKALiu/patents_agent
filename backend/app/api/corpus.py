"""Corpus API router - corpus document, job, version, search, and stats endpoints.

Endpoints moved from ``backend/app/main.py``:
  * GET    /api/corpus                     - list all documents
  * POST   /api/corpus/jobs                - create import job
  * POST   /api/corpus/jobs/{job_id}/files - upload file for job
  * POST   /api/corpus/jobs/{job_id}/run   - run import job
  * GET    /api/corpus/jobs/{job_id}       - get job status
  * GET    /api/corpus/versions            - list corpus versions
  * GET    /api/corpus/stats               - corpus statistics
  * GET    /api/corpus/documents/{document_id} - get one document
  * POST   /api/corpus/import              - import a patent document
  * GET    /api/corpus/search              - semantic search
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

from backend.app.schemas import (
    CorpusImportJobCreate,
    SectionType,
)
from backend.app.services.corpus_service import import_corpus_document

router = APIRouter(tags=["corpus"])


@router.get("/api/corpus")
def list_corpus(request: Request) -> dict:
    store = request.app.state.store
    documents = store.list_documents()
    return {"documents": [document.model_dump(mode="json") for document in documents]}


@router.post("/api/corpus/jobs")
def create_corpus_job(payload: CorpusImportJobCreate, request: Request) -> dict:
    corpus_service = request.app.state.corpus_service
    job = corpus_service.create_job(
        source_type=payload.source_type,
        source_name=payload.source_name,
        query=payload.query,
        domain=payload.domain,
        version_name=payload.version_name,
    )
    return job.model_dump(mode="json")


@router.post("/api/corpus/jobs/{job_id}/files")
async def upload_corpus_job_file(
    request: Request, job_id: str, file: UploadFile = File(...)
) -> dict:
    store = request.app.state.store
    settings = request.app.state.settings
    corpus_service = request.app.state.corpus_service
    if not store.get_corpus_job(job_id):
        raise HTTPException(status_code=404, detail="Corpus import job not found.")
    upload_dir = settings.data_dir / "corpus-jobs" / job_id / "uploaded"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "corpus-upload").name
    stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
    with stored_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    job = corpus_service.add_input(job_id, stored_path)
    return {"job": job.model_dump(mode="json"), "file_count": len(job.input_paths)}


@router.post("/api/corpus/jobs/{job_id}/run")
def run_corpus_job(job_id: str, request: Request) -> dict:
    store = request.app.state.store
    corpus_service = request.app.state.corpus_service
    if not store.get_corpus_job(job_id):
        raise HTTPException(status_code=404, detail="Corpus import job not found.")
    job = corpus_service.run_job(job_id)
    return job.model_dump(mode="json")


@router.get("/api/corpus/jobs/{job_id}")
def get_corpus_job(job_id: str, request: Request) -> dict:
    store = request.app.state.store
    job = store.get_corpus_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Corpus import job not found.")
    return job.model_dump(mode="json")


@router.get("/api/corpus/versions")
def list_corpus_versions(request: Request) -> dict:
    store = request.app.state.store
    return {
        "versions": [
            version.model_dump(mode="json") for version in store.list_corpus_versions()
        ]
    }


@router.get("/api/corpus/stats")
def corpus_stats(request: Request, version: str | None = None) -> dict:
    store = request.app.state.store
    return store.get_corpus_stats(version_name=version)


@router.get("/api/corpus/documents/{document_id}")
def get_corpus_document(document_id: str, request: Request) -> dict:
    store = request.app.state.store
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Corpus document not found.")
    return document.model_dump(mode="json")


@router.post("/api/corpus/import")
async def import_corpus(request: Request, file: UploadFile = File(...)) -> dict:
    settings = request.app.state.settings
    store = request.app.state.store
    index = request.app.state.index
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "patent.txt").name
    stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
    with stored_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    try:
        return import_corpus_document(stored_path=stored_path, store=store, index=index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/corpus/search")
def search_corpus(
    request: Request,
    q: str = Query(min_length=1),
    section_type: SectionType | None = None,
    limit: int = Query(default=5, ge=1, le=20),
    version: str | None = None,
) -> dict:
    index = request.app.state.index
    results = index.search(
        q, section_type=section_type, limit=limit, version_name=version
    )
    return {
        "results": [result.model_dump(mode="json") for result in results]
    }
