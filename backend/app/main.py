from __future__ import annotations

import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import ValidationError

from backend.app.corpus.pipeline import CorpusImportService
from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.core_formula import assess_formula_need, formula_package_to_markdown, generate_formula_run
from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.deliberation.providers import repair_suggestion_for_failure
from backend.app.disclosure.exporter import disclosure_to_markdown, export_disclosure_docx, write_disclosure_artifacts
from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.material_parser import read_project_material_text
from backend.app.disclosure.prior_art import PublicPriorArtProvider
from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
from backend.app.external_drafts import (
    create_external_draft_source,
    external_draft_review_bundle_to_markdown,
    extract_docx_text,
    file_content_hash,
    parse_external_draft_source,
    review_bundle_hash,
    seal_external_draft_file,
    working_draft_hash,
)
from backend.app.exporter import export_docx, package_to_markdown
from backend.app.filing_readiness import (
    assess_filing_readiness,
    readiness_report_to_markdown,
)
from backend.app.generator import PatentDraftGenerator
from backend.app.desktop_config import (
    DesktopConfig,
    DesktopConfigError,
    apply_update as apply_desktop_config_update,
    effective_settings as effective_desktop_settings,
    load_desktop_config,
    redacted_view as desktop_config_redacted_view,
    save_desktop_config,
)
from backend.app.llm import ConfigError, DeepSeekLLMClient, LLMClient, MissingLLMClient
from backend.app.official_compile import (
    OfficialDraftCompiler,
    export_official_package_docx,
    official_compile_run_to_markdown,
    official_package_to_markdown,
    source_draft_hash,
)
from backend.app.patent_mode import is_utility_model_project
from backend.app.patent_parser import chunk_document, make_patent_document, read_document_text
from backend.app.post_draft_review import (
    post_draft_review_to_markdown,
    run_post_draft_review,
)
from backend.app.rag import LocalVectorIndex, create_vector_index
from backend.app.research.deep_researcher import (
    DeepResearchSearchProvider,
    PatentDeepResearcher,
    PriorArtProviderAdapter,
)
from backend.app.research.ledger import (
    ProviderDiagnostic,
    SourceLedger,
)
from backend.app.research.providers import ChainedResearchProvider, build_provider_chain
from backend.app.schemas import (
    AgentFailure,
    DeepResearchPacket,
    DeliberationRun,
    DeliberationLogEntry,
    DeliberationRunCreate,
    DesktopConfigHealthResult,
    DesktopConfigUpdate,
    DesktopConfigView,
    DisclosurePackage,
    DisclosureRun,
    DisclosureRunCreate,
    DraftCompletionRun,
    ExternalDraftIntakeConfirmRequest,
    ExternalDraftReviewBundle,
    ExternalDraftSourceCreate,
    DraftPackage,
    FormulaRun,
    FormulaRunCreate,
    GenerateRequest,
    InventionBrief,
    OfficialCompileRunCreate,
    OfficialCompileRun,
    PatentChunk,
    PatentPointCandidate,
    PatentPointCreate,
    PatentPointUpdate,
    PostDraftReviewRunCreate,
    ProposedPatch,
    CorpusImportJobCreate,
    ProjectMaterial,
    ProjectCreate,
    ProjectRecord,
    SectionType,
    ScoreImprovementRequest,
    ScoreImprovementResult,
)
from backend.app.settings import Settings, build_settings
from backend.app.storage import SQLiteStore


STRICT_DELIBERATION_PROVIDERS = ("codex", "gemini", "claude")
APP_VERSION = "1.0.0"
LOCAL_RENDERER_ORIGINS = frozenset(
    {
        "null",  # Electron/file:// renderer fetches report Origin: null.
        "file://",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    }
)


def _enforce_desktop_config_origin(request: Request) -> None:
    """Reject browser-originated config writes from non-renderer origins.

    Electron main-process requests and tests do not send Origin, so absence is
    allowed. Browser requests from arbitrary sites send Origin and must not be
    able to read or mutate the local desktop LLM configuration.
    """

    origin = request.headers.get("origin")
    if origin and origin not in LOCAL_RENDERER_ORIGINS:
        raise HTTPException(status_code=403, detail="Forbidden desktop config origin.")


def create_app(
    data_dir: Path | None = None,
    llm_client: LLMClient | None = None,
    provider_runner: object | None = None,
    prior_art_provider: object | None = None,
    research_search_provider: DeepResearchSearchProvider | None = None,
    load_env_file: bool = True,
) -> FastAPI:
    settings = build_settings(load_env_file=load_env_file)
    if data_dir is not None:
        settings.data_dir = Path(data_dir)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore(settings.data_dir / "patents_agent.sqlite3")
    index = create_vector_index(settings.data_dir / "chroma")
    existing_chunks = store.list_chunks()
    if existing_chunks:
        index.add(existing_chunks)
    desktop_config = load_desktop_config(settings.data_dir)
    llm = llm_client or _build_llm(settings, desktop_config)

    app = FastAPI(title="Patents Agent", version=APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(LOCAL_RENDERER_ORIGINS),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.store = store
    app.state.index = index
    app.state.llm = llm
    app.state.llm_client_override = llm_client is not None
    app.state.desktop_config = desktop_config
    app.state.provider_runner = provider_runner
    app.state.prior_art_provider = prior_art_provider or PublicPriorArtProvider()
    app.state.research_search_provider = research_search_provider
    app.state.disclosure_inline = prior_art_provider is not None
    app.state.corpus_service = CorpusImportService(store=store, index=index, data_dir=settings.data_dir)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "ok": True,
            "llm_configured": not isinstance(app.state.llm, MissingLLMClient),
            "data_dir": str(settings.data_dir),
            "model": settings.llm_model,
            "embedding_model": settings.embedding_model,
        }

    @app.get("/api/desktop-config", response_model=DesktopConfigView)
    def get_desktop_config(request: Request) -> dict:
        """Return the redacted desktop LLM configuration (no raw key)."""
        _enforce_desktop_config_origin(request)
        view = desktop_config_redacted_view(app.state.desktop_config)
        effective = effective_desktop_settings(settings, app.state.desktop_config)
        view["provider"] = effective["provider"]
        view["base_url"] = effective["base_url"]
        view["model"] = effective["model"]
        view["api_key_source"] = effective["api_key_source"]
        return view

    @app.patch("/api/desktop-config", response_model=DesktopConfigView)
    def patch_desktop_config(payload: DesktopConfigUpdate, request: Request) -> dict:
        """Persist a desktop LLM configuration update on the local machine.

        The raw API key is dropped from the response and from any log lines.
        The ``.env`` file is never touched.
        """
        _enforce_desktop_config_origin(request)
        try:
            updated = apply_desktop_config_update(
                app.state.desktop_config,
                provider=payload.provider,
                base_url=payload.base_url,
                model=payload.model,
                api_key=payload.api_key,
                clear_api_key=payload.clear_api_key,
            )
        except DesktopConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        saved = save_desktop_config(settings.data_dir, updated)
        app.state.desktop_config = saved
        # Rebuild the LLM so subsequent generation calls pick up the new key.
        if not app.state.llm_client_override:
            app.state.llm = _build_llm(settings, saved)
        view = desktop_config_redacted_view(saved)
        effective = effective_desktop_settings(settings, saved)
        view["provider"] = effective["provider"]
        view["base_url"] = effective["base_url"]
        view["model"] = effective["model"]
        view["api_key_source"] = effective["api_key_source"]
        return view

    @app.post("/api/desktop-config/health", response_model=DesktopConfigHealthResult)
    def desktop_config_health(request: Request) -> dict:
        """Probe the configured LLM with a tiny request without echoing the key."""
        _enforce_desktop_config_origin(request)
        effective = effective_desktop_settings(settings, app.state.desktop_config)
        api_key = effective["api_key"]
        model = effective["model"]
        base_url = effective["base_url"]
        result: dict = {
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
        # Lazy import: keep the module import order predictable.
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
            result["error"] = _redact_error(exc)
            status = getattr(exc, "status_code", None) or 0
            result["status_code"] = int(status) if isinstance(status, int) else 0
        return result

    @app.get("/api/agents/doctor")
    def agent_doctor() -> dict:
        return inspect_agent_environment().model_dump(mode="json")

    @app.get("/api/corpus")
    def list_corpus() -> dict:
        documents = store.list_documents()
        return {"documents": [document.model_dump(mode="json") for document in documents]}

    @app.post("/api/corpus/jobs")
    def create_corpus_job(payload: CorpusImportJobCreate) -> dict:
        job = app.state.corpus_service.create_job(
            source_type=payload.source_type,
            source_name=payload.source_name,
            query=payload.query,
            domain=payload.domain,
            version_name=payload.version_name,
        )
        return job.model_dump(mode="json")

    @app.post("/api/corpus/jobs/{job_id}/files")
    async def upload_corpus_job_file(job_id: str, file: UploadFile = File(...)) -> dict:
        if not store.get_corpus_job(job_id):
            raise HTTPException(status_code=404, detail="Corpus import job not found.")
        upload_dir = settings.data_dir / "corpus-jobs" / job_id / "uploaded"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "corpus-upload").name
        stored_path = upload_dir / safe_name
        with stored_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        job = app.state.corpus_service.add_input(job_id, stored_path)
        return {"job": job.model_dump(mode="json"), "file_count": len(job.input_paths)}

    @app.post("/api/corpus/jobs/{job_id}/run")
    def run_corpus_job(job_id: str) -> dict:
        if not store.get_corpus_job(job_id):
            raise HTTPException(status_code=404, detail="Corpus import job not found.")
        job = app.state.corpus_service.run_job(job_id)
        if job.status == "failed" and not job.imported_documents:
            return job.model_dump(mode="json")
        return job.model_dump(mode="json")

    @app.get("/api/corpus/jobs/{job_id}")
    def get_corpus_job(job_id: str) -> dict:
        job = store.get_corpus_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Corpus import job not found.")
        return job.model_dump(mode="json")

    @app.get("/api/corpus/versions")
    def list_corpus_versions() -> dict:
        return {"versions": [version.model_dump(mode="json") for version in store.list_corpus_versions()]}

    @app.get("/api/corpus/stats")
    def corpus_stats(version: str | None = None) -> dict:
        return store.get_corpus_stats(version_name=version)

    @app.get("/api/corpus/documents/{document_id}")
    def get_corpus_document(document_id: str) -> dict:
        document = store.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Corpus document not found.")
        return document.model_dump(mode="json")

    @app.post("/api/corpus/import")
    async def import_corpus(file: UploadFile = File(...)) -> dict:
        upload_dir = settings.data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "patent.txt").name
        stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
        with stored_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)

        try:
            text = read_document_text(stored_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        document = make_patent_document(uuid.uuid4().hex, safe_name, text)
        chunks = [PatentChunk(**chunk) for chunk in chunk_document(document)]
        store.add_document(document, chunks)
        index.add(chunks)
        return {
            "document": document.model_dump(mode="json"),
            "chunks_count": len(chunks),
            "warnings": [],
        }

    @app.get("/api/corpus/search")
    def search_corpus(
        q: str = Query(min_length=1),
        section_type: SectionType | None = None,
        limit: int = Query(default=5, ge=1, le=20),
        version: str | None = None,
    ) -> dict:
        results = index.search(q, section_type=section_type, limit=limit, version_name=version)
        return {"results": [result.model_dump(mode="json") for result in results]}

    @app.get("/api/projects")
    def list_projects() -> dict:
        return {"projects": [project.model_dump(mode="json") for project in store.list_projects()]}

    @app.post("/api/projects")
    def create_project(payload: ProjectCreate) -> dict:
        project = ProjectRecord(
            id=uuid.uuid4().hex,
            name=payload.name,
            draft_text=payload.draft_text,
            patent_type=payload.patent_type,
        )
        stored = store.create_project(project)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = _require_project(store, project_id)
        return project.model_dump(mode="json")

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str) -> dict:
        deleted = store.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found.")
        return {"ok": True}

    @app.post("/api/projects/{project_id}/materials")
    async def upload_project_material(project_id: str, file: UploadFile = File(...)) -> dict:
        _require_project(store, project_id)
        upload_dir = settings.data_dir / "project-materials" / project_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "material.txt").name
        stored_path = upload_dir / f"{uuid.uuid4().hex}-{safe_name}"
        with stored_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        warnings: list[str] = []
        text = ""
        status = "processed"
        try:
            text, warnings = read_project_material_text(stored_path)
        except ValueError as exc:
            status = "failed"
            warnings = [str(exc)]
        material = ProjectMaterial(
            id=uuid.uuid4().hex,
            project_id=project_id,
            file_name=safe_name,
            path=str(stored_path),
            file_type=stored_path.suffix.lower().lstrip("."),
            text=text,
            status=status,
            warnings=warnings,
        )
        store.add_project_material(material)
        return material.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/materials")
    def list_project_materials(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"materials": [material.model_dump(mode="json") for material in store.list_project_materials(project_id)]}

    @app.post("/api/projects/{project_id}/external-drafts")
    def create_external_draft(project_id: str, payload: ExternalDraftSourceCreate) -> dict:
        _require_project(store, project_id)
        text = payload.text
        if payload.source_type in {"markdown_file", "docx_file"} and payload.file_content.strip():
            text = payload.file_content
        if not text.strip():
            raise HTTPException(status_code=422, detail="External draft text is required.")
        source = create_external_draft_source(
            project_id=project_id,
            source_type=payload.source_type,
            text=text,
            file_name=payload.file_name or "external-draft.txt",
            metadata={"source_type": payload.source_type},
        )
        stored = store.create_external_draft_source(source)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/external-drafts")
    def list_external_drafts(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"sources": [source.model_dump(mode="json") for source in store.list_external_draft_sources(project_id)]}

    @app.post("/api/projects/{project_id}/external-drafts/upload")
    async def upload_external_draft(project_id: str, file: UploadFile = File(...)) -> dict:
        _require_project(store, project_id)
        safe_name = Path(file.filename or "external-draft.txt").name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in {".docx", ".markdown", ".md", ".txt"}:
            raise HTTPException(status_code=415, detail="Unsupported external draft file type.")
        source_type = "docx_file" if suffix == ".docx" else "markdown_file"
        raw_path = settings.data_dir / "external-drafts" / project_id / f"{uuid.uuid4().hex}{suffix or '.txt'}"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_path.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        if suffix == ".docx":
            try:
                text = extract_docx_text(raw_path)
            except ValueError as exc:
                raw_path.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        else:
            text = raw_path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            raise HTTPException(status_code=422, detail="External draft text is required.")
        raw_content_hash = file_content_hash(raw_path) if raw_path.exists() else ""
        try:
            source = create_external_draft_source(
                project_id=project_id,
                source_type=source_type,
                text=text,
                file_name=safe_name,
                raw_path=str(raw_path),
                raw_content_hash=raw_content_hash,
                metadata={"uploaded": True, "content_type": file.content_type or ""},
            )
        except Exception:
            # Make sure the on-disk raw file is cleaned up if the in-memory model
            # cannot be built; nothing should leak onto disk for a failed import.
            raw_path.unlink(missing_ok=True)
            raise
        if raw_path.exists():
            seal_external_draft_file(raw_path)
        stored = store.create_external_draft_source(source)
        return stored.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/external-drafts/{source_id}/intake-runs")
    def create_external_draft_intake_run(project_id: str, source_id: str) -> dict:
        _require_project(store, project_id)
        source = store.get_external_draft_source(project_id, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="External draft source not found.")
        run = parse_external_draft_source(project_id=project_id, source=source)
        stored = store.create_external_draft_intake_run(run)
        if stored.status == "completed" and stored.parsed_package:
            store.update_project_package(project_id, stored.parsed_package)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/external-drafts/{source_id}/intake-runs")
    def list_external_draft_intake_runs(project_id: str, source_id: str) -> dict:
        _require_project(store, project_id)
        source = store.get_external_draft_source(project_id, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="External draft source not found.")
        return {
            "runs": [
                run.model_dump(mode="json")
                for run in store.list_external_draft_intake_runs(project_id, source_id)
            ]
        }

    @app.get("/api/projects/{project_id}/external-draft-intake-runs/{run_id}")
    def get_external_draft_intake_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_external_draft_intake_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="External draft intake run not found.")
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/external-draft-intake-runs/{run_id}/confirm")
    def confirm_external_draft_intake_run(
        project_id: str,
        run_id: str,
        payload: ExternalDraftIntakeConfirmRequest,
    ) -> dict:
        _require_project(store, project_id)
        run = store.get_external_draft_intake_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="External draft intake run not found.")
        claims = payload.claims.strip()
        description = payload.description.strip()
        if not claims or not description:
            raise HTTPException(status_code=422, detail="Confirmed external draft requires non-empty claims and description.")
        package = DraftPackage(
            title=payload.title.strip(),
            abstract=payload.abstract.strip(),
            claims=claims,
            description=description,
            drawing_description=payload.drawing_description.strip(),
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=[f"external_draft_intake: confirmed from run {run.id}"],
        )
        updated = run.model_copy(
            update={
                "status": "completed",
                "parsed_package": package,
                "working_draft_hash": working_draft_hash(package),
            }
        )
        persisted = store.update_external_draft_intake_run(updated)
        if not persisted:
            raise HTTPException(status_code=409, detail="External draft intake run update conflicted.")
        store.update_project_package(project_id, package)
        return persisted.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/external-draft-review-bundle/report.md")
    def export_external_draft_review_bundle(project_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        sources = store.list_external_draft_sources(project_id)
        intake_runs = store.list_external_draft_intake_runs(project_id)
        completion_runs = store.list_draft_completion_runs(project_id)
        official_runs = store.list_official_compile_runs(project_id)
        review_runs = store.list_post_draft_review_runs(project_id)
        latest_intake = intake_runs[0] if intake_runs else None
        initial_score = completion_runs[-1].scorecard.overall if completion_runs else None
        latest_score = completion_runs[0].scorecard.overall if completion_runs else None
        latest_official = official_runs[0] if official_runs else None
        latest_review = review_runs[0] if review_runs else None
        accepted_patch_ids = [
            patch.id
            for run in completion_runs
            for patch in run.patches
            if patch.status == "accepted"
        ]
        bundle = ExternalDraftReviewBundle(
            project_id=project_id,
            source_id=latest_intake.source_id if latest_intake else sources[0].id if sources else "",
            intake_run_id=latest_intake.id if latest_intake else "",
            initial_score=initial_score,
            latest_score=latest_score,
            accepted_patch_ids=accepted_patch_ids,
            completion_run_ids=[run.id for run in completion_runs],
            official_compile_run_id=latest_official.id if latest_official else "",
            post_draft_review_run_id=latest_review.id if latest_review else "",
            export_allowed=bool(latest_review and latest_review.export_allowed),
        )
        bundle = bundle.model_copy(update={"report_hash": review_bundle_hash(bundle)})
        return PlainTextResponse(
            external_draft_review_bundle_to_markdown(bundle),
            media_type="text/markdown; charset=utf-8",
        )

    @app.get("/api/projects/{project_id}/patent-points")
    def list_project_patent_points(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"points": [point.model_dump(mode="json") for point in store.list_project_patent_points(project_id)]}

    @app.post("/api/projects/{project_id}/patent-points")
    def create_project_patent_point(project_id: str, payload: PatentPointCreate) -> dict:
        _require_project(store, project_id)
        point: PatentPointCandidate = payload.to_candidate(payload.source_candidate_id or f"user-{uuid.uuid4().hex}")
        stored = store.add_project_patent_point(project_id, point)
        return stored.model_dump(mode="json")

    @app.patch("/api/projects/{project_id}/patent-points/{point_id}")
    def update_project_patent_point(project_id: str, point_id: str, payload: PatentPointUpdate) -> dict:
        _require_project(store, project_id)
        existing = store.get_project_patent_point(project_id, point_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Patent point not found.")
        patch = payload.model_dump(exclude_unset=True)
        null_fields = [field for field, value in patch.items() if value is None]
        if null_fields:
            raise HTTPException(status_code=422, detail=f"Null fields are not allowed in patent point patches: {', '.join(null_fields)}")
        if "moat_scores" in patch:
            patch["moat_scores"] = {
                **existing.moat_scores.model_dump(mode="json"),
                **patch["moat_scores"],
            }
        if patch.get("evidence_status") in {"feasible_unverified", "needs_experiment"} and not patch.get("support_gaps") and not existing.support_gaps:
            patch["support_gaps"] = ["提交前需补充实验或工程样例。"]
        try:
            updated = PatentPointCandidate.model_validate({**existing.model_dump(mode="json"), **patch})
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        stored = store.add_project_patent_point(project_id, updated)
        return stored.model_dump(mode="json")

    @app.delete("/api/projects/{project_id}/patent-points/{point_id}")
    def delete_project_patent_point(project_id: str, point_id: str) -> dict:
        _require_project(store, project_id)
        deleted = store.delete_project_patent_point(project_id, point_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Patent point not found.")
        return {"ok": True}

    @app.post("/api/projects/{project_id}/disclosures")
    def create_disclosure(
        project_id: str,
        payload: DisclosureRunCreate,
        background_tasks: BackgroundTasks,
    ) -> dict:
        project = _require_project(store, project_id)
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured. Set DEEPSEEK_API_KEY before generating disclosures.")
        run_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "disclosures" / project_id / run_id
        run = DisclosureRun(
            id=run_id,
            project_id=project_id,
            status="queued",
            trace=payload.trace,
            max_prior_art_results=payload.max_prior_art_results,
            research_mode=payload.research_mode,
            run_dir=str(run_dir),
        )
        store.create_disclosure_run(run)
        if app.state.disclosure_inline:
            completed = _execute_disclosure(
                store=store,
                index=index,
                llm=app.state.llm,
                prior_art_provider=app.state.prior_art_provider,
                research_search_provider=app.state.research_search_provider,
                project=project,
                run=run,
            )
            return completed.model_dump(mode="json")
        background_tasks.add_task(
            _execute_disclosure,
            store,
            index,
            app.state.llm,
            app.state.prior_art_provider,
            app.state.research_search_provider,
            project,
            run,
        )
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/disclosures")
    def list_disclosures(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"runs": [run.model_dump(mode="json") for run in store.list_disclosure_runs(project_id)]}

    @app.get("/api/projects/{project_id}/disclosures/{run_id}")
    def get_disclosure(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_disclosure_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Disclosure run not found.")
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/deliberations")
    def create_deliberation(
        project_id: str,
        payload: DeliberationRunCreate,
        background_tasks: BackgroundTasks,
    ) -> dict:
        project = _require_project(store, project_id)
        doctor = inspect_agent_environment()
        requested = payload.providers or list(STRICT_DELIBERATION_PROVIDERS)
        available = set(doctor.active_provider_ids)
        selectable = set(doctor.active_provider_ids) | set(doctor.unknown_required)
        active_requested_count = len(requested) if app.state.provider_runner is not None else len([provider for provider in requested if provider in available])
        run_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "deliberation-runs" / project_id / run_id
        if app.state.provider_runner is None:
            missing_providers = [provider for provider in requested if provider not in selectable]
            if missing_providers:
                failures = [
                    AgentFailure(
                        provider_id=provider,
                        phase="doctor",
                        reason="provider_missing",
                        message=f"{provider} provider is not available.",
                    )
                    for provider in missing_providers
                ]
                logs = [
                    DeliberationLogEntry(
                        level="error",
                        phase="doctor",
                        provider_id=provider,
                        message="provider missing",
                        detail=f"{provider} CLI is not available in PATH or is not usable by the backend process.",
                        repair_suggestion=repair_suggestion_for_failure("provider_missing", provider),
                    )
                    for provider in missing_providers
                ]
                failed_run = DeliberationRun(
                    id=run_id,
                    project_id=project_id,
                    status="failed",
                    providers=requested,
                    run_mode=_run_mode(active_requested_count),
                    round_depth=payload.round_depth,
                    trace=payload.trace,
                    run_dir=str(run_dir),
                    failures=failures,
                    events=[f"provider missing: {provider}" for provider in missing_providers],
                    logs=logs,
                )
                store.create_deliberation_run(failed_run)
                return failed_run.model_dump(mode="json")
        run = DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="queued",
            providers=requested,
            run_mode=_run_mode(active_requested_count),
            round_depth=payload.round_depth,
            trace=payload.trace,
            run_dir=str(run_dir),
        )
        store.create_deliberation_run(run)
        if app.state.provider_runner is not None:
            completed = _execute_deliberation(
                store=store,
                index=index,
                provider_runner=app.state.provider_runner,
                project=project,
                run=run,
                trace=payload.trace,
                task_timeout_ms=payload.task_timeout_ms or 180_000,
            )
            return completed.model_dump(mode="json")
        background_tasks.add_task(
            _execute_deliberation,
            store,
            index,
            app.state.provider_runner,
            project,
            run,
            payload.trace,
            payload.task_timeout_ms or 180_000,
        )
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/deliberations")
    def list_deliberations(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"runs": [run.model_dump(mode="json") for run in store.list_deliberation_runs(project_id)]}

    @app.get("/api/projects/{project_id}/deliberations/{run_id}")
    def get_deliberation(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_deliberation_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Deliberation run not found.")
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/formula-requirement")
    def get_formula_requirement(project_id: str) -> dict:
        project = _require_project(store, project_id)
        disclosure = store.get_latest_completed_disclosure_run(project_id)
        deliberation = _resolve_deliberation(store, project_id, None)
        assessment = assess_formula_need(
            project=project,
            patent_points=store.list_project_patent_points(project_id),
            disclosure=disclosure.package if disclosure else None,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
        )
        return assessment.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/formula-runs")
    def create_formula_run(project_id: str, payload: FormulaRunCreate | None = None) -> dict:
        project = _require_project(store, project_id)
        disclosure = store.get_latest_completed_disclosure_run(project_id)
        deliberation = _resolve_deliberation(store, project_id, None)
        patent_points = store.list_project_patent_points(project_id)
        providers = payload.providers if payload and payload.providers else list(STRICT_DELIBERATION_PROVIDERS)
        assessment = assess_formula_need(
            project=project,
            patent_points=patent_points,
            disclosure=disclosure.package if disclosure else None,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
        )
        if assessment.required and isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured. Set DEEPSEEK_API_KEY before generating core formulas.")
        run = generate_formula_run(
            project_id=project_id,
            project=project,
            patent_points=patent_points,
            disclosure=disclosure.package if disclosure else None,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
            llm=app.state.llm,
            providers=providers,
        )
        return store.create_formula_run(run).model_dump(mode="json")

    @app.get("/api/projects/{project_id}/formula-runs")
    def list_formula_runs(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"runs": [run.model_dump(mode="json") for run in store.list_formula_runs(project_id)]}

    @app.get("/api/projects/{project_id}/formula-runs/{run_id}/latex.md")
    def export_formula_markdown(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = store.get_formula_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Formula run not found.")
        if not run.package:
            raise HTTPException(status_code=409, detail="Formula run has no generated package.")
        return PlainTextResponse(formula_package_to_markdown(run.package), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/generate")
    def generate_project(project_id: str, payload: GenerateRequest | None = None) -> dict:
        project = _require_project(store, project_id)
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured. Set DEEPSEEK_API_KEY before generating drafts.")
        deliberation = _resolve_deliberation(store, project_id, payload.deliberation_run_id if payload else None)
        if deliberation is None and not is_utility_model_project(project):
            raise HTTPException(status_code=409, detail="Multi-agent deliberation is required before generating a patent draft.")
        disclosure = store.get_latest_completed_disclosure_run(project_id)
        disclosure_package = disclosure.package if disclosure else None
        user_candidates = store.list_project_patent_points(project_id)
        selected_user_candidates = [candidate for candidate in user_candidates if candidate.selected]
        if not disclosure_package and selected_user_candidates:
            selected_candidate = selected_user_candidates[0]
            disclosure_package = DisclosurePackage(
                title=selected_candidate.title,
                summary=f"用户指定护城河专利点：{selected_candidate.title}",
                materials_summary=selected_candidate.feasibility_basis,
                candidates=selected_user_candidates,
                selected_candidate_id=selected_candidate.id,
                prior_art_hits=[],
                prior_art_differences="尚未完成公开现有技术差异分析。",
                body_markdown=selected_candidate.technical_solution,
                mermaid=(
                    "flowchart TD\nA[用户指定结构方案] --> B[部件连接关系待补充]"
                    if is_utility_model_project(project)
                    else "flowchart TD\nA[用户指定技术方案] --> B[待补充验证]"
                ),
                image_prompt=(
                    "黑白线稿，展示用户指定结构方案的部件组成、连接关系和安装位置。"
                    if is_utility_model_project(project)
                    else "黑白线稿，展示用户指定技术方案的数据流和模块关系。"
                ),
                self_check_findings=[],
                generation_logs=["disclosure: synthesized from selected user patent point"],
            )
        formula_run = _resolve_formula_run(
            store=store,
            project=project,
            project_id=project_id,
            formula_run_id=payload.formula_run_id if payload else None,
            patent_points=user_candidates,
            disclosure_package=disclosure_package,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
        )
        brief = _brief_from_draft(project, disclosure_package)
        context = _retrieve_generation_context(index, brief)
        generator = PatentDraftGenerator(app.state.llm)
        try:
            package = generator.generate(
                brief,
                context,
                strategy_brief=deliberation.strategy_brief if deliberation else None,
                disclosure=disclosure_package,
                formula_package=formula_run.package if formula_run else None,
            )
        except ConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if deliberation:
            package.deliberation_run_id = deliberation.id
            package.strategy_brief = deliberation.strategy_brief
            package.agent_consensus = deliberation.strategy_brief.agent_consensus if deliberation.strategy_brief else None
            package.generation_logs.append(f"deliberation: injected strategy brief from run {deliberation.id}")
        else:
            package.generation_logs.append("deliberation: no completed multi-agent deliberation injected")
        if disclosure and disclosure_package:
            package.disclosure_run_id = disclosure.id
            package.disclosure_summary = disclosure_package.summary
            selected = disclosure_package.selected_candidate
            package.patent_point_summary = selected.title if selected else None
            package.generation_logs.append(f"disclosure: injected pre-filing materials from run {disclosure.id}")
        elif disclosure_package:
            package.disclosure_summary = disclosure_package.summary
            selected = disclosure_package.selected_candidate
            package.patent_point_summary = selected.title if selected else None
            package.generation_logs.append("disclosure: injected selected user patent point without completed disclosure")
        else:
            package.generation_logs.append("disclosure: no completed pre-filing disclosure injected")
        if formula_run and formula_run.package:
            package.formula_run_id = formula_run.id
            package.core_formula_summary = formula_run.package.summary
            package.generation_logs.append(f"formula: injected core formula package from run {formula_run.id}")
        else:
            package.generation_logs.append("formula: no core formula package required")
        store.update_project_package(project_id, package)
        return package.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/review")
    def review_project(project_id: str) -> dict:
        project = _require_project(store, project_id)
        if not project.package:
            raise HTTPException(status_code=409, detail="Generate a draft before review.")
        generator = PatentDraftGenerator(app.state.llm)
        try:
            findings = generator.review(project.package)
        except ConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        package = project.package.model_copy(update={"review_findings": findings})
        store.update_project_package(project_id, package)
        return package.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/filing-readiness")
    def create_filing_readiness_report(project_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        verified_effects = any(
            point.evidence_status == "verified"
            for point in store.list_project_patent_points(project_id)
        )
        report = assess_filing_readiness(project_id, package, verified_effects=verified_effects)
        stored = store.create_filing_readiness_report(report)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/filing-readiness")
    def list_filing_readiness_reports(project_id: str) -> dict:
        _require_project(store, project_id)
        return {
            "reports": [
                report.model_dump(mode="json")
                for report in store.list_filing_readiness_reports(project_id)
            ]
        }

    @app.get("/api/projects/{project_id}/filing-readiness/{report_id}/export.md")
    def export_filing_readiness_report(project_id: str, report_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        report = store.get_filing_readiness_report(project_id, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Filing readiness report not found.")
        return PlainTextResponse(readiness_report_to_markdown(report), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/claim-defense-worksheets")
    def create_claim_defense_worksheet(project_id: str) -> dict:
        project = _require_project(store, project_id)
        worksheet = generate_claim_defense_worksheet(
            project_id=project_id,
            package=project.package,
            disclosures=store.list_disclosure_runs(project_id),
            patent_points=store.list_project_patent_points(project_id),
            llm=app.state.llm,
        )
        stored = store.create_claim_defense_worksheet(worksheet)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/claim-defense-worksheets")
    def list_claim_defense_worksheets(project_id: str) -> dict:
        _require_project(store, project_id)
        return {
            "worksheets": [
                worksheet.model_dump(mode="json")
                for worksheet in store.list_claim_defense_worksheets(project_id)
            ]
        }

    @app.get("/api/projects/{project_id}/claim-defense-worksheets/{worksheet_id}")
    def get_claim_defense_worksheet(project_id: str, worksheet_id: str) -> dict:
        _require_project(store, project_id)
        worksheet = store.get_claim_defense_worksheet(project_id, worksheet_id)
        if not worksheet:
            raise HTTPException(status_code=404, detail="Claim defense worksheet not found.")
        return worksheet.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/completion-runs")
    def create_draft_completion_run(project_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = run_draft_completion(
            project_id=project_id,
            package=package,
            filing_reports=store.list_filing_readiness_reports(project_id),
            worksheets=store.list_claim_defense_worksheets(project_id),
            patent_points=store.list_project_patent_points(project_id),
            disclosures=store.list_disclosure_runs(project_id),
            materials=store.list_project_materials(project_id),
        )
        stored = store.create_draft_completion_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/completion-runs")
    def list_draft_completion_runs(project_id: str) -> dict:
        _require_project(store, project_id)
        return {
            "runs": [
                run.model_dump(mode="json")
                for run in store.list_draft_completion_runs(project_id)
            ]
        }

    @app.get("/api/projects/{project_id}/completion-runs/{run_id}")
    def get_draft_completion_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_draft_completion_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/completion-runs/{run_id}/report.md")
    def export_draft_completion_report(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = store.get_draft_completion_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        return PlainTextResponse(completion_run_to_markdown(run), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/accept")
    def accept_completion_patch(project_id: str, run_id: str, patch_id: str) -> dict:
        _require_project(store, project_id)
        run = store.update_completion_patch_status(project_id, run_id, patch_id, "accepted")
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion patch not found.")
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/reject")
    def reject_completion_patch(project_id: str, run_id: str, patch_id: str) -> dict:
        _require_project(store, project_id)
        run = store.update_completion_patch_status(project_id, run_id, patch_id, "rejected")
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion patch not found.")
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/score-improvement")
    def improve_project_score(project_id: str, payload: ScoreImprovementRequest) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        logs = ["score-improvement: 启动通用专利审查视角评分闭环"]
        before_run = _run_quality_cycle(app, store, project_id)
        current_run = before_run
        current_package = package
        accepted_patch_ids: list[str] = []
        logs.append(f"score-improvement: 初始评分 {before_run.scorecard.overall}/100")

        for round_index in range(1, payload.max_rounds + 1):
            safe_patches = [
                patch
                for patch in current_run.patches
                if patch.status == "proposed" and patch.can_enter_official_draft and patch.after_text.strip()
            ]
            if not safe_patches:
                logs.append("score-improvement: 未发现可自动进入正式稿的补强补丁")
                break
            for patch in safe_patches:
                current_package = _apply_completion_patch(current_package, patch)
                store.update_completion_patch_status(project_id, current_run.id, patch.id, "accepted")
                accepted_patch_ids.append(patch.id)
                logs.append(f"score-improvement: 已应用补丁 {patch.id} -> {patch.target_section}")
            store.update_project_package(project_id, current_package)
            current_run = _run_quality_cycle(app, store, project_id)
            logs.append(f"score-improvement: 第 {round_index} 轮重新评分 {current_run.scorecard.overall}/100")
            if current_run.scorecard.overall >= payload.target_score:
                logs.append(f"score-improvement: 已达到目标分 {payload.target_score}/100")
                break
            if current_run.scorecard.overall <= before_run.scorecard.overall and round_index == payload.max_rounds:
                logs.append("score-improvement: 当前补强未继续提高分数，等待人工补充证据或实施例")

        result = ScoreImprovementResult(
            project_id=project_id,
            before_score=before_run.scorecard.overall,
            after_score=current_run.scorecard.overall,
            accepted_patch_ids=accepted_patch_ids,
            before_run=before_run,
            after_run=current_run,
            logs=logs,
        )
        return result.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/post-draft-reviews")
    def create_post_draft_review(project_id: str, payload: PostDraftReviewRunCreate | None = None) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_latest_completed_official_compile(store, project_id, package)
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured for post-draft multi-agent review.")
        providers = list(payload.providers if payload and payload.providers else STRICT_DELIBERATION_PROVIDERS)
        run = run_post_draft_review(
            project_id=project_id,
            package=compile_run.official_package,
            llm=app.state.llm,
            providers=providers,
            official_compile_run_id=compile_run.id,
        )
        stored = store.create_post_draft_review_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/post-draft-reviews")
    def list_post_draft_reviews(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "runs": [run.model_dump(mode="json") for run in store.list_post_draft_review_runs(project_id)],
            "current_draft_hash": current_hash,
        }

    @app.get("/api/projects/{project_id}/post-draft-reviews/{run_id}")
    def get_post_draft_review(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_post_draft_review_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Post-draft review run not found.")
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/post-draft-reviews/{run_id}/report.md")
    def export_post_draft_review_report(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = store.get_post_draft_review_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Post-draft review run not found.")
        return PlainTextResponse(post_draft_review_to_markdown(run), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/official-compile-runs")
    def create_official_compile_run(
        project_id: str, payload: OfficialCompileRunCreate | None = None
    ) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = OfficialDraftCompiler().compile(project_id=project_id, package=package)
        stored = store.create_official_compile_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/official-compile-runs")
    def list_official_compile_runs(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "runs": [run.model_dump(mode="json") for run in store.list_official_compile_runs(project_id)],
            "current_source_draft_hash": current_hash,
        }

    @app.get("/api/projects/{project_id}/official-compile-runs/{run_id}")
    def get_official_compile_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_official_compile_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/official-compile-runs/{run_id}/report.md")
    def export_official_compile_report(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = store.get_official_compile_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        return PlainTextResponse(official_compile_run_to_markdown(run), media_type="text/markdown; charset=utf-8")

    @app.get("/api/projects/{project_id}/official-export.docx")
    def export_project_official_docx(project_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, package)
        output_path = export_official_package_docx(
            compile_run.official_package,
            settings.data_dir / "exports" / f"{project.id}-official.docx",
        )
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}-正式提交稿.docx",
        )

    @app.get("/api/projects/{project_id}/official-export.md")
    def export_project_official_markdown(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, package)
        return PlainTextResponse(official_package_to_markdown(compile_run.official_package), media_type="text/markdown; charset=utf-8")

    @app.get("/api/projects/{project_id}/export.docx")
    def export_project_docx(project_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        output_path = export_docx(package, settings.data_dir / "exports" / f"{project.id}.docx")
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}.docx",
        )

    @app.get("/api/projects/{project_id}/export.md")
    def export_project_markdown(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(package_to_markdown(package), media_type="text/markdown; charset=utf-8")

    @app.get("/api/projects/{project_id}/diagram.mmd")
    def export_project_mermaid(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(package.mermaid, media_type="text/plain; charset=utf-8")

    @app.get("/api/projects/{project_id}/image-prompt.md")
    def export_project_image_prompt(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(package.image_prompt, media_type="text/markdown; charset=utf-8")

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/export.docx")
    def export_disclosure_run_docx(project_id: str, run_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        output_path = export_disclosure_docx(package, Path(run.run_dir) / "disclosure.docx", Path(run.run_dir))
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}-技术交底书.docx",
        )

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/export.md")
    def export_disclosure_run_markdown(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        return PlainTextResponse(disclosure_to_markdown(package), media_type="text/markdown; charset=utf-8")

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/diagram.mmd")
    def export_disclosure_run_mermaid(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        return PlainTextResponse(package.mermaid, media_type="text/plain; charset=utf-8")

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/image-prompt.md")
    def export_disclosure_run_image_prompt(project_id: str, run_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        return PlainTextResponse(package.image_prompt, media_type="text/markdown; charset=utf-8")

    return app


def _execute_disclosure(
    store: SQLiteStore,
    index: LocalVectorIndex,
    llm: LLMClient,
    prior_art_provider: object,
    research_search_provider: DeepResearchSearchProvider | None,
    project: ProjectRecord,
    run: DisclosureRun,
) -> DisclosureRun:
    running = run.model_copy(update={"status": "running", "events": [*run.events, "run started"]})
    store.update_disclosure_run(running)
    materials = store.list_project_materials(project.id)
    brief = _brief_from_draft(project)
    context = _retrieve_generation_context(index, brief)

    # ---- V1.1: pre-flight provider diagnostics ----
    pre_diagnostics = _collect_provider_diagnostics(
        prior_art_provider=prior_art_provider,
        research_search_provider=research_search_provider,
    )

    try:
        generator = DisclosureGenerator(llm, prior_art_provider)
        user_candidates = store.list_project_patent_points(project.id)
        package, stage_results, warnings = generator.generate(
            project=project,
            materials=materials,
            context_chunks=context,
            max_prior_art_results=run.max_prior_art_results,
            user_candidates=user_candidates,
            pre_diagnostics=[d.model_dump(mode="json") for d in pre_diagnostics],
        )
        events: list[str] = [
            *running.events,
            "project scan completed",
            "patent points generated",
            "prior art search completed",
            "disclosure package generated",
        ]
        # Optional supplement: free deep research mode runs AFTER the standard
        # disclosure pipeline, appends its stages, and decorates the package
        # supporting fields (never the canonical/official draft surface).
        if run.research_mode == "free_deep_research":
            package, deep_stages, deep_warnings = _apply_free_deep_research(
                llm=llm,
                prior_art_provider=prior_art_provider,
                research_search_provider=research_search_provider,
                project=project,
                package=package,
            )
            stage_results.extend(deep_stages)
            warnings.extend(deep_warnings)
            events.append("free deep research supplement completed")

        # ---- V1.1: post-flight provider diagnostics ----
        post_diagnostics = _collect_provider_diagnostics(
            prior_art_provider=prior_art_provider,
            research_search_provider=research_search_provider,
            ledger=package.research_ledger,
        )
        package_with_diagnostics = package.model_copy(
            update={
                "provider_diagnostics": [
                    d.model_dump(mode="json") for d in [*pre_diagnostics, *post_diagnostics]
                ],
            }
        )
        completed = running.model_copy(
            update={
                "status": "completed",
                "stage_results": stage_results,
                "package": package_with_diagnostics,
                "events": [
                    *events,
                    *[f"warning: {warning}" for warning in warnings],
                ],
            }
        )
        run_dir = Path(run.run_dir)
        write_disclosure_artifacts(package_with_diagnostics, run_dir)
        store.update_disclosure_run(completed)
        return completed
    except ConfigError:
        raise
    except Exception as exc:
        failed = running.model_copy(update={"status": "failed", "failures": [str(exc)], "events": [*running.events, f"run failed: {exc}"]})
        store.update_disclosure_run(failed)
        return failed


def _collect_provider_diagnostics(
    *,
    prior_art_provider: object,
    research_search_provider: DeepResearchSearchProvider | None = None,
    ledger: dict[str, Any] | None = None,
) -> list[ProviderDiagnostic]:
    """Collect pre/post-flight diagnostics about the provider chain.

    Pre-flight (ledger=None): check which prior_art and deep research providers
    are configured and available.

    Post-flight (ledger populated): summarize what actually happened during search.
    """
    diagnostics: list[ProviderDiagnostic] = []

    if ledger is None:
        # ---- Pre-flight: what is configured ----
        available: list[str] = []
        skipped: list[dict[str, str]] = []

        # Check CNIPA EPUB helper
        cnipa_script = getattr(prior_art_provider, "cnipa_script", None)
        if cnipa_script is not None and hasattr(cnipa_script, "exists") and cnipa_script.exists():
            available.append("cnipa")
        else:
            skipped.append(
                {"provider": "cnipa", "reason": "CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search."}
            )

        # Google Patents is always available (stdlib fetch)
        available.append("google_patents")

        # Deep research providers
        if research_search_provider is not None:
            provider_names = list(getattr(research_search_provider, "provider_names", []))
            available.extend(provider_names)
        else:
            # Without a configured chain, only the patent provider is used
            available.append("patent")

        diagnostics.append(
            ProviderDiagnostic(
                phase="pre_flight",
                available_providers=available,
                skipped_providers=skipped,
                active_chain=available,
                warnings=[],
            )
        )
    else:
        # ---- Post-flight: what actually happened ----
        ledger_entries: list[dict] = ledger.get("entries", [])
        available: list[str] = []
        skipped: list[dict[str, str]] = []
        warnings: list[str] = []

        for entry in ledger_entries:
            provider = entry.get("provider", "")
            status = entry.get("status", "running")
            if status == "skipped":
                skipped.append({"provider": provider, "reason": entry.get("failure_reason", "unknown")})
            elif status == "failed":
                warnings.append(f"{provider} failed: {entry.get('failure_reason', 'unknown')}")
            elif status == "timeout":
                warnings.append(f"{provider} timed out: {entry.get('failure_reason', 'unknown')}")
            elif status == "ok":
                available.append(provider)

        total_hits = ledger.get("total_hits", 0)
        provider_warnings_list = ledger.get("provider_warnings", [])
        warnings.extend(provider_warnings_list)
        if total_hits == 0 and available:
            warnings.append("0 references collected from active providers; disclosure should not imply high patentability confidence.")

        diagnostics.append(
            ProviderDiagnostic(
                phase="post_flight",
                available_providers=available,
                skipped_providers=skipped,
                active_chain=available,
                warnings=warnings,
            )
        )

    return diagnostics


def _apply_free_deep_research(
    *,
    llm: LLMClient,
    prior_art_provider: object,
    research_search_provider: DeepResearchSearchProvider | None = None,
    project: ProjectRecord,
    package: DisclosurePackage,
) -> tuple[DisclosurePackage, list[dict[str, object]], list[str]]:
    """Run the patent deep researcher and merge supporting outputs into the
    disclosure package.

    Boundaries (enforced here):
      * Never mutates ``body_markdown`` (the canonical disclosure body).
      * Never touches OfficialDraftCompiler or any export-gate state.
      * Web content / prompts / wrapper JSON stay INSIDE ``stage_results``;
        only short, human-readable summaries are surfaced on the package.
    """

    provider_names: list[str] = []
    provider_warnings: list[str] = []
    if research_search_provider is not None:
        search_provider = research_search_provider
        provider_names = list(getattr(research_search_provider, "provider_names", []))
    else:
        try:
            providers, provider_warnings = build_provider_chain(
                patent_provider=prior_art_provider,
            )
            search_provider = ChainedResearchProvider(providers, provider_warnings)
            provider_names = list(search_provider.provider_names)
        except Exception as exc:  # pragma: no cover - defensive fallback
            provider_warnings = [f"research provider chain failed; fell back to patent provider: {exc}"]
            search_provider = PriorArtProviderAdapter(prior_art_provider)  # type: ignore[arg-type]
            provider_names = ["patent"]

    researcher = PatentDeepResearcher(
        llm=llm,
        search_provider=search_provider,
        provider_names=provider_names,
    )
    try:
        packet, deep_stages = researcher.research(
            project=project,
            candidates=list(package.candidates),
            selected_candidate_id=package.selected_candidate_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        warning = f"free_deep_research failed: {exc}"
        deep_stages = [
            {
                "phase": "deep_research_failed",
                "payload": {"error": str(exc)},
            }
        ]
        packet = DeepResearchPacket(
            status="failed",
            project_id=project.id,
            warnings=[warning],
            generation_logs=[warning],
        )

    augmented_logs = list(package.generation_logs)
    augmented_logs.append(
        "free_deep_research: internal supporting research packet generated; "
        "does not replace deliberation or official export gate."
    )
    augmented_logs.extend(
        f"deep_research: {line}" for line in packet.generation_logs
    )

    augmented_diffs = package.prior_art_differences or ""
    summary_parts: list[str] = []
    if packet.differentiators:
        summary_parts.append("差异要点：" + "；".join(packet.differentiators[:5]))
    if packet.novelty_opportunities:
        summary_parts.append("新颖性方向：" + "；".join(packet.novelty_opportunities[:5]))
    if packet.claim_drafting_constraints:
        summary_parts.append("撰写约束：" + "；".join(packet.claim_drafting_constraints[:5]))
    if summary_parts:
        # prior_art_differences is later used as draft-generation context, so
        # keep it to neutral technical distinctions only. Internal process
        # labels stay in generation_logs and stage_results.
        suffix = "\n\n补充现有技术差异分析：\n" + "\n".join(summary_parts)
        augmented_diffs = (augmented_diffs + suffix).strip()

    candidate_completion_tasks = packet.suggested_completion_tasks[:5]
    updated_candidates = []
    for candidate in package.candidates:
        if candidate.id == package.selected_candidate_id and candidate_completion_tasks:
            merged_experiments = list(candidate.experiment_needed) + [
                task for task in candidate_completion_tasks if task not in candidate.experiment_needed
            ]
            merged_gaps = list(candidate.support_gaps)
            for diff in packet.claim_drafting_constraints[:3]:
                if diff and diff not in merged_gaps:
                    merged_gaps.append(diff)
            updated_candidates.append(
                candidate.model_copy(
                    update={
                        "experiment_needed": merged_experiments,
                        "support_gaps": merged_gaps,
                    }
                )
            )
        else:
            updated_candidates.append(candidate)

    augmented_package = package.model_copy(
        update={
            "candidates": updated_candidates,
            "prior_art_differences": augmented_diffs,
            "generation_logs": augmented_logs,
        }
    )
    warnings_out = list(packet.warnings)
    if packet.status == "failed":
        warnings_out.append("free_deep_research: packet status=failed; standard disclosure preserved.")
    elif packet.status == "partial":
        warnings_out.append(
            "free_deep_research: packet status=partial; consider expanding materials or search terms."
        )
    return augmented_package, deep_stages, warnings_out


def _execute_deliberation(
    store: SQLiteStore,
    index: LocalVectorIndex,
    provider_runner: object | None,
    project: ProjectRecord,
    run: DeliberationRun,
    trace: bool,
    task_timeout_ms: int,
) -> DeliberationRun:
    running = run.model_copy(update={"status": "running", "events": [*run.events, "run started"]})
    store.update_deliberation_run(running)
    disclosure = store.get_latest_completed_disclosure_run(project.id)
    brief = _brief_from_draft(project, disclosure.package if disclosure else None)
    context = _retrieve_generation_context(index, brief)
    try:
        orchestrator = DeliberationOrchestrator(provider_runner=provider_runner)
        completed = __import__("asyncio").run(
            orchestrator.run(
                run_id=run.id,
                project_id=run.project_id,
                brief=brief,
                context_chunks=context,
                providers=run.providers,
                run_dir=Path(run.run_dir),
                trace=trace,
                task_timeout_ms=task_timeout_ms,
                on_update=store.update_deliberation_run,
            )
        )
        store.update_deliberation_run(completed)
        return completed
    except Exception as exc:
        failed = running.model_copy(update={"status": "failed", "events": [*running.events, f"run failed: {exc}"]})
        store.update_deliberation_run(failed)
        return failed


def _run_quality_cycle(app: FastAPI, store: SQLiteStore, project_id: str) -> DraftCompletionRun:
    project = _require_project(store, project_id)
    package = _require_package(project)
    verified_effects = any(point.evidence_status == "verified" for point in store.list_project_patent_points(project_id))
    report = assess_filing_readiness(project_id, package, verified_effects=verified_effects)
    store.create_filing_readiness_report(report)
    worksheet = generate_claim_defense_worksheet(
        project_id=project_id,
        package=package,
        disclosures=store.list_disclosure_runs(project_id),
        patent_points=store.list_project_patent_points(project_id),
        llm=app.state.llm,
    )
    store.create_claim_defense_worksheet(worksheet)
    run = run_draft_completion(
        project_id=project_id,
        package=package,
        filing_reports=store.list_filing_readiness_reports(project_id),
        worksheets=store.list_claim_defense_worksheets(project_id),
        patent_points=store.list_project_patent_points(project_id),
        disclosures=store.list_disclosure_runs(project_id),
        materials=store.list_project_materials(project_id),
    )
    return store.create_draft_completion_run(run)


def _apply_completion_patch(package: DraftPackage, patch: ProposedPatch) -> DraftPackage:
    if not patch.can_enter_official_draft or not patch.after_text.strip():
        return package
    text = patch.after_text.strip()
    if patch.target_section in {"description", "embodiment", "term"}:
        return package.model_copy(update={"description": _append_once(package.description, "补充实施方式", text)})
    if patch.target_section == "claim":
        return package.model_copy(update={"claims": _append_once(package.claims, "补充权利要求", text)})
    if patch.target_section == "drawing":
        return package.model_copy(update={"drawing_description": _append_once(package.drawing_description, "补充附图说明", text)})
    return package


def _append_once(original: str, heading: str, addition: str) -> str:
    if addition in original:
        return original
    return f"{original.rstrip()}\n\n{heading}：\n{addition}\n"


def _build_llm(settings: Settings, desktop_config: DesktopConfig | None = None) -> LLMClient:
    effective = effective_desktop_settings(settings, desktop_config or DesktopConfig())
    api_key = effective["api_key"]
    if not api_key:
        return MissingLLMClient()
    return DeepSeekLLMClient(
        api_key=api_key,
        base_url=effective["base_url"] or None,
        model=effective["model"],
    )


_API_KEY_REDACT_PATTERN = re.compile(r"(sk-[A-Za-z0-9_-]{6,})")


def _redact_error(exc: BaseException) -> str:
    """Return a short, key-free description of ``exc`` for the health endpoint."""
    text = f"{type(exc).__name__}: {exc}"
    return _API_KEY_REDACT_PATTERN.sub("sk-…", text)[:512]


def _require_project(store: SQLiteStore, project_id: str) -> ProjectRecord:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _require_package(project: ProjectRecord) -> DraftPackage:
    if not project.package:
        raise HTTPException(status_code=409, detail="Generate a draft before export.")
    return project.package


def _require_latest_completed_official_compile(
    store: SQLiteStore, project_id: str, package: DraftPackage
) -> OfficialCompileRun:
    run = store.get_latest_completed_official_compile_run_for_hash(project_id, source_draft_hash(package))
    if not run or not run.official_package:
        raise HTTPException(status_code=409, detail="Official draft compile is required before post-draft review.")
    return run


def _require_official_export_gate(store: SQLiteStore, project_id: str, package: DraftPackage) -> OfficialCompileRun:
    current_source_hash = source_draft_hash(package)
    compile_run = store.get_latest_completed_official_compile_run(project_id)
    if not compile_run or not compile_run.official_package or compile_run.source_draft_hash != current_source_hash:
        raise HTTPException(
            status_code=409,
            detail="Official draft compile is required for the current draft before official export.",
        )
    latest_matching_review = next(
        (
            run
            for run in store.list_post_draft_review_runs(project_id)
            if run.status == "completed"
            and run.draft_package_hash == current_source_hash
            and run.official_compile_run_id == compile_run.id
            and run.official_package_hash == compile_run.official_package_hash
        ),
        None,
    )
    if not latest_matching_review or not latest_matching_review.export_allowed:
        raise HTTPException(
            status_code=409,
            detail="Post-draft multi-agent review is required for the current official draft before official export.",
        )
    return compile_run


def _require_disclosure_run(store: SQLiteStore, project_id: str, run_id: str) -> DisclosureRun:
    run = store.get_disclosure_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Disclosure run not found.")
    return run


def _require_disclosure_package(run: DisclosureRun) -> DisclosurePackage:
    if not run.package:
        raise HTTPException(status_code=409, detail="Disclosure run has no generated package.")
    return run.package


def _resolve_deliberation(store: SQLiteStore, project_id: str, run_id: str | None) -> DeliberationRun | None:
    if run_id:
        run = store.get_deliberation_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Deliberation run not found.")
        if not _is_strict_completed_deliberation(run):
            raise HTTPException(status_code=409, detail="A strict multi-agent deliberation is required before generating a patent draft.")
        return run
    for run in store.list_deliberation_runs(project_id):
        if _is_strict_completed_deliberation(run):
            return run
    return None


def _is_strict_completed_deliberation(run: DeliberationRun) -> bool:
    if run.status != "completed" or run.strategy_brief is None or run.failures:
        return False
    required = set(STRICT_DELIBERATION_PROVIDERS)
    if not required.issubset(set(run.providers)):
        return False
    completed = {(stage.phase, stage.provider_id, stage.label) for stage in run.stage_results if stage.status == "completed"}
    if not all(("opening", provider, f"opening {provider}") in completed for provider in required):
        return False
    pair_labels = {
        "pair codex-vs-gemini",
        "pair codex-vs-claude",
        "pair gemini-vs-claude",
    }
    if not pair_labels.issubset({label for phase, _provider, label in completed if phase == "pair"}):
        return False
    return any(phase == "chair" and label == "chair synthesis" for phase, _provider, label in completed)


def _resolve_formula_run(
    *,
    store: SQLiteStore,
    project: ProjectRecord,
    project_id: str,
    formula_run_id: str | None,
    patent_points: list[PatentPointCandidate],
    disclosure_package: DisclosurePackage | None,
    strategy_brief: object | None,
) -> FormulaRun | None:
    assessment = assess_formula_need(
        project=project,
        patent_points=patent_points,
        disclosure=disclosure_package,
        strategy_brief=strategy_brief,  # type: ignore[arg-type]
    )
    if formula_run_id:
        run = store.get_formula_run(project_id, formula_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Formula run not found.")
        if run.status != "completed" or run.package is None:
            raise HTTPException(status_code=409, detail="Formula run is not completed.")
        return run
    if not assessment.required:
        return None
    run = store.get_latest_completed_formula_run(project_id)
    if not run or not run.package:
        raise HTTPException(status_code=409, detail="Core formula package is required before generating a patent draft.")
    return run


def _brief_from_draft(project: ProjectRecord, disclosure: DisclosurePackage | None = None) -> InventionBrief:
    draft = project.draft_text.strip()
    first_sentence = draft.split("。", 1)[0]
    title = project.name if project.name else first_sentence[:40]
    selected = disclosure.selected_candidate if disclosure else None
    utility_model = is_utility_model_project(project)
    normalized_title = title if title.startswith("一种") else f"一种{title}{'结构' if utility_model else '方法'}"
    return InventionBrief(
        title=normalized_title,
        technical_field="实用新型产品结构" if utility_model else "人工智能软件方法",
        technical_problem=selected.technical_problem if selected else _infer_problem(draft),
        technical_solution=selected.technical_solution if selected else draft,
        beneficial_effects=selected.beneficial_effects if selected else (
            ["提高结构稳定性", "降低装配和维护难度"]
            if utility_model
            else ["提升申请文本结构完整性", "降低专利初稿撰写遗漏风险"]
        ),
        key_steps=selected.protection_focus if selected and selected.protection_focus else (
            _infer_structure_features(draft) if utility_model else _infer_steps(draft)
        ),
        raw_draft=draft,
        disclosure_summary=disclosure.summary if disclosure else None,
        patent_point_summary=selected.title if selected else None,
        prior_art_differences=disclosure.prior_art_differences if disclosure else None,
        supporting_materials_summary=disclosure.materials_summary if disclosure else None,
        patent_type=project.patent_type,
    )


def _infer_problem(draft: str) -> str:
    for marker in ["解决", "用于", "针对"]:
        if marker in draft:
            return draft[draft.index(marker) :][:80]
    return "现有技术中存在专利初稿结构不完整、权利要求支撑不足的问题。"


def _infer_steps(draft: str) -> list[str]:
    candidates = []
    for keyword in ["采集", "获取", "解析", "训练", "检索", "生成", "输出", "审核", "导出"]:
        if keyword in draft:
            candidates.append(keyword)
    return candidates or ["获取输入数据", "生成专利文本", "输出审查建议"]


def _infer_structure_features(draft: str) -> list[str]:
    candidates = []
    for keyword in ["支架", "壳体", "连接", "固定", "安装", "限位", "导向", "密封", "传感器", "模块", "组件", "结构"]:
        if keyword in draft:
            candidates.append(keyword)
    return candidates or ["部件组成", "连接关系", "安装位置"]


def _retrieve_generation_context(index: LocalVectorIndex, brief: InventionBrief) -> list[PatentChunk]:
    query = " ".join([brief.title, brief.technical_field, brief.technical_problem, brief.technical_solution])
    selected: list[PatentChunk] = []
    seen: set[str] = set()
    for section_type in [SectionType.CLAIMS, SectionType.SUMMARY, SectionType.EMBODIMENTS, SectionType.ABSTRACT]:
        for result in index.search(query, section_type=section_type, limit=3):
            if result.chunk.id not in seen:
                selected.append(result.chunk)
                seen.add(result.chunk.id)
    return selected[:8]


def _run_mode(active_count: int) -> str:
    if active_count >= 3:
        return "full"
    if active_count == 2:
        return "partial"
    if active_count == 1:
        return "minimal"
    return "blocked"


app = create_app()
