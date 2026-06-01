from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import ValidationError

from backend.app.corpus.pipeline import CorpusImportService
from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.disclosure.exporter import disclosure_to_markdown, export_disclosure_docx, write_disclosure_artifacts
from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.material_parser import read_project_material_text
from backend.app.disclosure.prior_art import PublicPriorArtProvider
from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
from backend.app.exporter import export_docx, package_to_markdown
from backend.app.filing_readiness import (
    assess_filing_readiness,
    export_official_docx,
    official_package_to_markdown,
    readiness_report_to_markdown,
)
from backend.app.generator import PatentDraftGenerator
from backend.app.llm import ConfigError, DeepSeekLLMClient, LLMClient, MissingLLMClient
from backend.app.patent_parser import chunk_document, make_patent_document, read_document_text
from backend.app.rag import LocalVectorIndex, create_vector_index
from backend.app.schemas import (
    DeliberationRun,
    DeliberationRunCreate,
    DisclosurePackage,
    DisclosureRun,
    DisclosureRunCreate,
    DraftPackage,
    GenerateRequest,
    InventionBrief,
    PatentChunk,
    PatentPointCandidate,
    PatentPointCreate,
    PatentPointUpdate,
    CorpusImportJobCreate,
    ProjectMaterial,
    ProjectCreate,
    ProjectRecord,
    SectionType,
)
from backend.app.settings import Settings, build_settings
from backend.app.storage import SQLiteStore


def create_app(
    data_dir: Path | None = None,
    llm_client: LLMClient | None = None,
    provider_runner: object | None = None,
    prior_art_provider: object | None = None,
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
    llm = llm_client or _build_llm(settings)

    app = FastAPI(title="Patents Agent", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.store = store
    app.state.index = index
    app.state.llm = llm
    app.state.provider_runner = provider_runner
    app.state.prior_art_provider = prior_art_provider or PublicPriorArtProvider()
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
        project = ProjectRecord(id=uuid.uuid4().hex, name=payload.name, draft_text=payload.draft_text)
        store.create_project(project)
        return project.model_dump(mode="json")

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = _require_project(store, project_id)
        return project.model_dump(mode="json")

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

    @app.get("/api/projects/{project_id}/patent-points")
    def list_project_patent_points(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"points": [point.model_dump(mode="json") for point in store.list_project_patent_points(project_id)]}

    @app.post("/api/projects/{project_id}/patent-points")
    def create_project_patent_point(project_id: str, payload: PatentPointCreate) -> dict:
        _require_project(store, project_id)
        point: PatentPointCandidate = payload.to_candidate(f"user-{uuid.uuid4().hex}")
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
            run_dir=str(run_dir),
        )
        store.create_disclosure_run(run)
        if app.state.disclosure_inline:
            completed = _execute_disclosure(
                store=store,
                index=index,
                llm=app.state.llm,
                prior_art_provider=app.state.prior_art_provider,
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
        if doctor.status == "blocked" and app.state.provider_runner is None:
            raise HTTPException(status_code=503, detail=f"Agent doctor blocked: {doctor.missing_required}")
        requested = payload.providers or ["codex", "gemini", "claude"]
        available = set(doctor.active_provider_ids)
        providers = requested if app.state.provider_runner is not None else [provider for provider in requested if provider in available]
        if "codex" not in providers and app.state.provider_runner is None:
            raise HTTPException(status_code=503, detail="Codex provider is required for deliberation.")
        run_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "deliberation-runs" / project_id / run_id
        run = DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="queued",
            providers=providers,
            run_mode=_run_mode(len(providers)),
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

    @app.post("/api/projects/{project_id}/generate")
    def generate_project(project_id: str, payload: GenerateRequest | None = None) -> dict:
        project = _require_project(store, project_id)
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
                mermaid="flowchart TD\nA[用户指定技术方案] --> B[待补充验证]",
                image_prompt="黑白线稿，展示用户指定技术方案的数据流和模块关系。",
                self_check_findings=[],
                generation_logs=["disclosure: synthesized from selected user patent point"],
            )
        brief = _brief_from_draft(project, disclosure_package)
        context = _retrieve_generation_context(index, brief)
        deliberation = _resolve_deliberation(store, project_id, payload.deliberation_run_id if payload else None)
        generator = PatentDraftGenerator(app.state.llm)
        try:
            package = generator.generate(
                brief,
                context,
                strategy_brief=deliberation.strategy_brief if deliberation else None,
                disclosure=disclosure_package,
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

    @app.get("/api/projects/{project_id}/official-export.docx")
    def export_project_official_docx(project_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        output_path = export_official_docx(package, settings.data_dir / "exports" / f"{project.id}-official.docx")
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}-正式提交稿.docx",
        )

    @app.get("/api/projects/{project_id}/official-export.md")
    def export_project_official_markdown(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(official_package_to_markdown(package), media_type="text/markdown; charset=utf-8")

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
    project: ProjectRecord,
    run: DisclosureRun,
) -> DisclosureRun:
    running = run.model_copy(update={"status": "running", "events": [*run.events, "run started"]})
    store.update_disclosure_run(running)
    materials = store.list_project_materials(project.id)
    brief = _brief_from_draft(project)
    context = _retrieve_generation_context(index, brief)
    try:
        generator = DisclosureGenerator(llm, prior_art_provider)
        user_candidates = store.list_project_patent_points(project.id)
        package, stage_results, warnings = generator.generate(
            project=project,
            materials=materials,
            context_chunks=context,
            max_prior_art_results=run.max_prior_art_results,
            user_candidates=user_candidates,
        )
        run_dir = Path(run.run_dir)
        write_disclosure_artifacts(package, run_dir)
        completed = running.model_copy(
            update={
                "status": "completed",
                "stage_results": stage_results,
                "package": package,
                "events": [
                    *running.events,
                    "project scan completed",
                    "patent points generated",
                    "prior art search completed",
                    "disclosure package generated",
                    *[f"warning: {warning}" for warning in warnings],
                ],
            }
        )
        store.update_disclosure_run(completed)
        return completed
    except ConfigError:
        raise
    except Exception as exc:
        failed = running.model_copy(update={"status": "failed", "failures": [str(exc)], "events": [*running.events, f"run failed: {exc}"]})
        store.update_disclosure_run(failed)
        return failed


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
            )
        )
        store.update_deliberation_run(completed)
        return completed
    except Exception as exc:
        failed = running.model_copy(update={"status": "failed", "events": [*running.events, f"run failed: {exc}"]})
        store.update_deliberation_run(failed)
        return failed


def _build_llm(settings: Settings) -> LLMClient:
    if not settings.deepseek_api_key:
        return MissingLLMClient()
    return DeepSeekLLMClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url or None,
        model=settings.llm_model,
    )


def _require_project(store: SQLiteStore, project_id: str) -> ProjectRecord:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _require_package(project: ProjectRecord) -> DraftPackage:
    if not project.package:
        raise HTTPException(status_code=409, detail="Generate a draft before export.")
    return project.package


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
        if run.status != "completed":
            raise HTTPException(status_code=409, detail="Deliberation run is not completed.")
        return run
    return store.get_latest_completed_deliberation_run(project_id)


def _brief_from_draft(project: ProjectRecord, disclosure: DisclosurePackage | None = None) -> InventionBrief:
    draft = project.draft_text.strip()
    first_sentence = draft.split("。", 1)[0]
    title = project.name if project.name else first_sentence[:40]
    selected = disclosure.selected_candidate if disclosure else None
    return InventionBrief(
        title=f"一种{title}方法" if not title.startswith("一种") else title,
        technical_field="人工智能软件方法",
        technical_problem=selected.technical_problem if selected else _infer_problem(draft),
        technical_solution=selected.technical_solution if selected else draft,
        beneficial_effects=selected.beneficial_effects if selected else ["提升申请文本结构完整性", "降低专利初稿撰写遗漏风险"],
        key_steps=selected.protection_focus if selected and selected.protection_focus else _infer_steps(draft),
        raw_draft=draft,
        disclosure_summary=disclosure.summary if disclosure else None,
        patent_point_summary=selected.title if selected else None,
        prior_art_differences=disclosure.prior_art_differences if disclosure else None,
        supporting_materials_summary=disclosure.materials_summary if disclosure else None,
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
