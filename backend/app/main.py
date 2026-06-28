from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from itertools import combinations
from pathlib import Path
from urllib.parse import quote

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import ValidationError

from backend.app.corpus.pipeline import CorpusImportService
from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.core_formula import assess_formula_need, formula_package_to_markdown, generate_formula_run
from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.deliberation.providers import AgentProviderRunner, repair_suggestion_for_failure
from backend.app.disclosure.exporter import (
    clean_disclosure_to_markdown,
    disclosure_sidecar_to_markdown,
    disclosure_to_markdown,
    export_disclosure_docx,
    write_disclosure_artifacts,
)
from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.material_parser import read_project_material_text
from backend.app.disclosure.prior_art import PublicPriorArtProvider
from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
from backend.app.evidence_binding import build_evidence_bindings
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
from backend.app.grantability import generate_grantability_report, grantability_report_to_markdown
from backend.app.kimi_language_polish import run_kimi_language_polish
from backend.app.desktop_config import (
    DesktopConfig,
    DesktopConfigError,
    load_desktop_config,
)
from backend.app.llm import ConfigError, LLMClient, MissingLLMClient
from backend.app.llm_cache import CachedStageLLMClient, clear_project_llm_cache
from backend.app.moat import score_moat
from backend.app.official_compile import (
    OfficialDraftCompiler,
    clean_source_draft_for_official_compile,
    export_official_package_docx,
    official_compile_run_to_markdown,
    official_package_to_markdown,
    source_draft_hash,
)
from backend.app.patch_generator import PatchGenerationContext, generate_evidence_backed_patches
from backend.app.patent_mode import is_utility_model_project
from backend.app.patent_parser import chunk_document, make_patent_document, read_document_text
from backend.app.post_draft_review import (
    package_hash_for_review,
    post_draft_review_to_markdown,
    run_post_draft_review,
)
from backend.app.revision_ledger import create_revision_record
from backend.app.post_draft_repair import (
    apply_section_patch,
    create_repair_patch_payload,
    normalize_post_draft_issues,
    validate_repair_patch_text,
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
from backend.app.runtime import RuntimeCancelled, RuntimeContext, RuntimeTimeout
from backend.app.schemas import (
    AgentFailure,
    ClaimDefenseWorksheet,
    DeepResearchPacket,
    DeliberationRun,
    DeliberationLogEntry,
    DeliberationRunCreate,
    DisclosurePackage,
    DisclosureRun,
    DisclosureRunCreate,
    DraftCompletionRun,
    DraftPackageManualUpdate,
    ExternalDraftIntakeConfirmRequest,
    ExternalDraftReviewBundle,
    ExternalDraftSourceCreate,
    DraftPackage,
    DraftRepairPatch,
    DraftRepairPatchCreate,
    DraftRepairPatchApplyResult,
    DraftReviewIssue,
    EvidenceBinding,
    FilingReadinessReport,
    FormulaRun,
    FormulaRunCreate,
    GenerateRequest,
    InventionBrief,
    OfficialDraftPackage,
    OfficialCompileRunCreate,
    OfficialCompileCleanupResult,
    OfficialCompileRun,
    PatentChunk,
    PatentPointCandidate,
    PatentPointCreate,
    PatentPointUpdate,
    PatentStrategyBrief,
    PostDraftReviewRun,
    PostDraftReviewRunCreate,
    PostDraftRepairSession,
    PostDraftSafePatchApplyResult,
    ProposedPatch,
    CorpusImportJobCreate,
    ProjectMaterial,
    ProjectCreate,
    ProjectUpdate,
    ProjectRecord,
    RuntimeFailure,
    SectionType,
    CompletionScoreCard,
    ScoreImprovementRequest,
    ScoreImprovementResult,
)
from backend.app.settings import Settings, build_settings
from backend.app.storage import SQLiteStore

from backend.app.api.desktop_config import router as desktop_config_router
from backend.app.api.system import router as system_router
from backend.app.api.corpus import router as corpus_router
from backend.app.api.projects import router as projects_router
from backend.app.services.desktop_config_service import LOCAL_RENDERER_ORIGINS
from backend.app.services.llm_factory import build_llm


DELIBERATION_CHAIR_PROVIDER = "codex"
DELIBERATION_EXPERT_SEAT_COUNT = 3
STRICT_DELIBERATION_PROVIDERS = ("codex", "deepseek", "claude")
APP_VERSION = "1.1.0"


def _ascii_download_filename(raw: str) -> str:
    """Extract the ASCII subset of a filename, preserving the extension.

    Keeps alphanumeric chars, dots, hyphens, underscores, and spaces.
    Strips leading/trailing whitespace. Falls back to ``download`` (with
    the original extension when present) for names whose stem contains no
    ASCII alphanumeric characters — this avoids producing bare fallbacks
    like ``.docx`` or ``-.md`` for pure-CJK project names.
    """
    ascii_chars = [ch for ch in raw if ch.isascii() and (ch.isalnum() or ch in "._- ")]
    stripped = "".join(ascii_chars).strip()
    if not stripped or not any(ch.isalnum() for ch in stripped):
        # Entire name is non-ASCII or empty — use a safe fallback.
        if "." in raw:
            ext = raw.rsplit(".", 1)[-1]
            ext_clean = "".join(ch for ch in ext if ch.isalnum())
            if ext_clean:
                return f"download.{ext_clean}"
        return "download"
    # When the stem (before the last dot) has no alphanumeric ASCII content,
    # the fallback is effectively a bare extension like ``.md``.  Prepend
    # ``download`` to give clients a useful filename.
    if "." in stripped:
        stem_part = stripped.rsplit(".", 1)[0]
        if not any(ch.isalnum() for ch in stem_part):
            ext = stripped.rsplit(".", 1)[1]
            return f"download.{ext}"
    return stripped


def _content_disposition_header(filename: str) -> dict[str, str]:
    """Build a Content-Disposition header dict with UTF-8 encoded filename.

    Returns both an ASCII fallback (``filename=``) and a UTF-8 encoded
    filename (``filename*=UTF-8''...``) for maximum browser compatibility.
    """
    safe = filename.replace("/", "_").replace("\\", "_").strip()
    ascii_fallback = _ascii_download_filename(safe)
    encoded = quote(safe)
    return {"Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'}


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
    llm = llm_client or build_llm(settings, desktop_config)

    app = FastAPI(title="Patents Agent", version=APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(LOCAL_RENDERER_ORIGINS),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(system_router)
    app.include_router(desktop_config_router)
    app.include_router(corpus_router)
    app.include_router(projects_router)
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
                stage_timeout_ms=payload.stage_timeout_ms,
                run_timeout_ms=payload.run_timeout_ms,
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
            payload.stage_timeout_ms,
            payload.run_timeout_ms,
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

    @app.post("/api/projects/{project_id}/disclosures/{run_id}/cancel")
    def cancel_disclosure(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_disclosure_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Disclosure run not found.")
        updated = _mark_disclosure_cancel_requested(store, run)
        return updated.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/disclosures/{run_id}/retry")
    def retry_disclosure(
        project_id: str,
        run_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict:
        project = _require_project(store, project_id)
        previous = store.get_disclosure_run(project_id, run_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Disclosure run not found.")
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured. Set DEEPSEEK_API_KEY before generating disclosures.")
        retry_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "disclosures" / project_id / retry_id
        retry_run = DisclosureRun(
            id=retry_id,
            project_id=project_id,
            status="queued",
            trace=previous.trace,
            max_prior_art_results=previous.max_prior_art_results,
            research_mode=previous.research_mode,
            run_dir=str(run_dir),
            retry_of=previous.id,
            events=[f"retry requested for disclosure run {previous.id}"],
        )
        store.create_disclosure_run(retry_run)
        if app.state.disclosure_inline:
            completed = _execute_disclosure(
                store=store,
                index=index,
                llm=app.state.llm,
                prior_art_provider=app.state.prior_art_provider,
                research_search_provider=app.state.research_search_provider,
                project=project,
                run=retry_run,
                stage_timeout_ms=None,
                run_timeout_ms=None,
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
            retry_run,
            None,
            None,
        )
        return retry_run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/deliberations")
    def create_deliberation(
        project_id: str,
        payload: DeliberationRunCreate,
        background_tasks: BackgroundTasks,
    ) -> dict:
        project = _require_project(store, project_id)
        doctor = inspect_agent_environment()
        requested, participants, seat_warnings = _deliberation_provider_plan(
            doctor,
            payload.providers,
            payload.participant_providers,
            auto_fill_missing=payload.providers is None,
        )
        active_requested_count = len(requested)
        run_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "deliberation-runs" / project_id / run_id
        chair_missing = DELIBERATION_CHAIR_PROVIDER not in requested
        if len(requested) < DELIBERATION_EXPERT_SEAT_COUNT or chair_missing:
            block_reason = "chair_unavailable" if chair_missing else "insufficient_experts"
            block_message = (
                "Codex chair is not available for deliberation."
                if chair_missing
                else "Not enough expert seats are ready for deliberation."
            )
            detail = (
                f"Codex 主席不可用，无法启动会审；当前可用决策专家为 {len(requested)} 席：{', '.join(requested) or '无'}。"
                if chair_missing
                else f"至少 {DELIBERATION_EXPERT_SEAT_COUNT} 席决策专家才能启动会审；当前为 {len(requested)} 席：{', '.join(requested) or '无'}。"
            )
            if seat_warnings:
                detail = f"{detail} {'；'.join(seat_warnings)}"
            failed_run = DeliberationRun(
                id=run_id,
                project_id=project_id,
                status="failed",
                providers=requested,
                participant_providers=participants,
                run_mode="blocked",
                round_depth=payload.round_depth,
                trace=payload.trace,
                run_dir=str(run_dir),
                failures=[
                    AgentFailure(
                        provider_id=DELIBERATION_CHAIR_PROVIDER,
                        phase="doctor",
                        reason=block_reason,
                        message=block_message,
                    )
                ],
                events=[f"deliberation blocked: {block_reason}", *seat_warnings],
                logs=[
                    DeliberationLogEntry(
                        level="error",
                        phase="doctor",
                        provider_id=DELIBERATION_CHAIR_PROVIDER,
                        message=block_reason.replace("_", " "),
                        detail=detail,
                        repair_suggestion=(
                            "请先修复 Codex CLI 的安装或认证状态；Codex 是固定主席，不能由其他 agent 代替。"
                            if chair_missing
                            else "请在会审卡片中选择 Codex 主席之外的 2 个可用专家；Claude 不可用时可选择 DeepSeek、KimiCode、MimoCode 等已安装 agent。"
                        ),
                    )
                ],
            )
            store.create_deliberation_run(failed_run)
            return failed_run.model_dump(mode="json")
        run = DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="queued",
            providers=requested,
            participant_providers=participants,
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
                run_timeout_ms=payload.run_timeout_ms,
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
            payload.run_timeout_ms,
        )
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/deliberations")
    def list_deliberations(project_id: str) -> dict:
        _require_project(store, project_id)
        runs = [_reconcile_deliberation_run(store, run) for run in store.list_deliberation_runs(project_id)]
        return {"runs": [run.model_dump(mode="json") for run in runs]}

    @app.get("/api/projects/{project_id}/deliberations/{run_id}")
    def get_deliberation(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_deliberation_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Deliberation run not found.")
        run = _reconcile_deliberation_run(store, run)
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/deliberations/{run_id}/cancel")
    def cancel_deliberation(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_deliberation_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Deliberation run not found.")
        updated = _mark_deliberation_cancel_requested(store, run)
        return updated.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/deliberations/{run_id}/retry")
    def retry_deliberation(
        project_id: str,
        run_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict:
        project = _require_project(store, project_id)
        previous = store.get_deliberation_run(project_id, run_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Deliberation run not found.")
        doctor = inspect_agent_environment()
        providers, participants, seat_warnings = _deliberation_provider_plan(
            doctor,
            previous.providers,
            previous.participant_providers,
            auto_fill_missing=True,
        )
        retry_id = uuid.uuid4().hex
        run_dir = settings.data_dir / "deliberation-runs" / project_id / retry_id
        chair_missing = DELIBERATION_CHAIR_PROVIDER not in providers
        if len(providers) < DELIBERATION_EXPERT_SEAT_COUNT or chair_missing:
            block_reason = "chair_unavailable" if chair_missing else "insufficient_experts"
            block_message = (
                "Codex chair is not available for deliberation retry."
                if chair_missing
                else "Not enough expert seats are ready for deliberation retry."
            )
            detail = (
                f"Codex 主席不可用，无法重试会审；当前可用决策专家为 {len(providers)} 席：{', '.join(providers) or '无'}。"
                if chair_missing
                else f"至少 {DELIBERATION_EXPERT_SEAT_COUNT} 席决策专家才能重试会审；当前为 {len(providers)} 席：{', '.join(providers) or '无'}。"
            )
            if seat_warnings:
                detail = f"{detail} {'；'.join(seat_warnings)}"
            retry_run = DeliberationRun(
                id=retry_id,
                project_id=project_id,
                status="failed",
                providers=providers,
                participant_providers=participants,
                run_mode="blocked",
                round_depth=previous.round_depth,
                trace=previous.trace,
                run_dir=str(run_dir),
                retry_of=previous.id,
                failures=[
                    AgentFailure(
                        provider_id=DELIBERATION_CHAIR_PROVIDER,
                        phase="doctor",
                        reason=block_reason,
                        message=block_message,
                    )
                ],
                events=[f"retry requested for deliberation run {previous.id}", f"retry blocked: {block_reason}", *seat_warnings],
                logs=[
                    DeliberationLogEntry(
                        level="error",
                        phase="doctor",
                        provider_id=DELIBERATION_CHAIR_PROVIDER,
                        message=block_reason.replace("_", " "),
                        detail=detail,
                        repair_suggestion=(
                            "请先修复 Codex CLI 的安装或认证状态；Codex 是固定主席，不能由其他 agent 代替。"
                            if chair_missing
                            else "请重新选择 Codex 主席之外的 2 个可用专家后再重试。"
                        ),
                    )
                ],
            )
            store.create_deliberation_run(retry_run)
            return retry_run.model_dump(mode="json")
        retry_run = DeliberationRun(
            id=retry_id,
            project_id=project_id,
            status="queued",
            providers=providers,
            participant_providers=participants,
            run_mode=_run_mode(len(providers)),
            round_depth=previous.round_depth,
            trace=previous.trace,
            run_dir=str(run_dir),
            retry_of=previous.id,
            events=[
                f"retry requested for deliberation run {previous.id}",
                f"providers normalized: {','.join(providers)}",
                f"participants normalized: {','.join(participants)}",
                *seat_warnings,
            ],
        )
        store.create_deliberation_run(retry_run)
        if app.state.provider_runner is not None:
            completed = _execute_deliberation(
                store=store,
                index=index,
                provider_runner=app.state.provider_runner,
                project=project,
                run=retry_run,
                trace=retry_run.trace,
                task_timeout_ms=180_000,
                run_timeout_ms=None,
            )
            return completed.model_dump(mode="json")
        background_tasks.add_task(
            _execute_deliberation,
            store,
            index,
            app.state.provider_runner,
            project,
            retry_run,
            retry_run.trace,
            180_000,
            None,
        )
        return retry_run.model_dump(mode="json")

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
        run = _execute_formula_run(
            store=store,
            project_id=project_id,
            project=project,
            patent_points=patent_points,
            disclosure=disclosure.package if disclosure else None,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
            llm=app.state.llm,
            providers=providers,
            stage_timeout_ms=payload.stage_timeout_ms if payload else None,
            run_timeout_ms=payload.run_timeout_ms if payload else None,
            retry_of=None,
        )
        return run.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/formula-runs")
    def list_formula_runs(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"runs": [run.model_dump(mode="json") for run in store.list_formula_runs(project_id)]}

    @app.get("/api/projects/{project_id}/formula-runs/{run_id}")
    def get_formula_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_formula_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Formula run not found.")
        return run.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/formula-runs/{run_id}/cancel")
    def cancel_formula_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_formula_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Formula run not found.")
        updated = _mark_formula_cancel_requested(store, run)
        return updated.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/formula-runs/{run_id}/retry")
    def retry_formula_run(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        previous = store.get_formula_run(project_id, run_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Formula run not found.")
        disclosure = store.get_latest_completed_disclosure_run(project_id)
        deliberation = _resolve_deliberation(store, project_id, None)
        patent_points = store.list_project_patent_points(project_id)
        if previous.requirement.required and isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured. Set DEEPSEEK_API_KEY before generating core formulas.")
        run = _execute_formula_run(
            store=store,
            project_id=project_id,
            project=project,
            patent_points=patent_points,
            disclosure=disclosure.package if disclosure else None,
            strategy_brief=deliberation.strategy_brief if deliberation else None,
            llm=app.state.llm,
            providers=list(previous.providers),
            stage_timeout_ms=None,
            run_timeout_ms=None,
            retry_of=previous.id,
        )
        return run.model_dump(mode="json")

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
        cached_llm = _cached_llm(
            store=store,
            project_id=project_id,
            source_hash_value=_draft_generation_source_hash(project, deliberation, disclosure, formula_run, user_candidates),
            llm=app.state.llm,
        )
        generator = PatentDraftGenerator(cached_llm)
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

    @app.put("/api/projects/{project_id}/draft-package")
    def update_draft_package(project_id: str, payload: DraftPackageManualUpdate) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        updated = package.model_copy(update=payload.model_dump())
        store.update_project_package(project_id, updated)
        return updated.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/revision-ledger")
    def list_revision_ledger(project_id: str) -> list[dict]:
        _require_project(store, project_id)
        return [record.model_dump(mode="json") for record in store.list_revision_ledger_records(project_id)]

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
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "reports": [
                report.model_dump(mode="json")
                for report in store.list_filing_readiness_reports(project_id)
            ],
            "current_source_draft_hash": current_hash,
        }

    @app.get("/api/projects/{project_id}/filing-readiness/{report_id}/export.md")
    def export_filing_readiness_report(project_id: str, report_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        report = store.get_filing_readiness_report(project_id, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Filing readiness report not found.")
        return PlainTextResponse(readiness_report_to_markdown(report), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/grantability-reports")
    def create_grantability_report(project_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        disclosures = store.list_disclosure_runs(project_id)
        patent_points = store.list_project_patent_points(project_id)
        strategy_brief = _latest_strategy_brief(store, project_id)
        report = generate_grantability_report(
            project_id=project_id,
            package=package,
            disclosures=disclosures,
            patent_points=patent_points,
            strategy_brief=strategy_brief,
            deep_research_packets=_deep_research_packets_from_disclosures(disclosures),
        )
        stored = store.create_grantability_report(report)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/grantability-reports")
    def list_grantability_reports(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "reports": [
                report.model_dump(mode="json")
                for report in store.list_grantability_reports(project_id)
            ],
            "current_source_draft_hash": current_hash,
        }

    @app.get("/api/projects/{project_id}/grantability-reports/{report_id}")
    def get_grantability_report(project_id: str, report_id: str) -> dict:
        _require_project(store, project_id)
        report = store.get_grantability_report(project_id, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Grantability report not found.")
        return report.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/grantability-reports/{report_id}/export.md")
    def export_grantability_report(project_id: str, report_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        report = store.get_grantability_report(project_id, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Grantability report not found.")
        return PlainTextResponse(grantability_report_to_markdown(report), media_type="text/markdown; charset=utf-8")

    @app.post("/api/projects/{project_id}/claim-defense-worksheets")
    def create_claim_defense_worksheet(project_id: str) -> dict:
        project = _require_project(store, project_id)
        _materials, disclosures, patent_points, _formula_runs, evidence_bindings = _build_evidence_bindings_for_project(
            store, project
        )
        worksheet = generate_claim_defense_worksheet(
            project_id=project_id,
            package=project.package,
            disclosures=disclosures,
            patent_points=patent_points,
            llm=app.state.llm,
            evidence_bindings=evidence_bindings,
        )
        stored = store.create_claim_defense_worksheet(worksheet)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/claim-defense-worksheets")
    def list_claim_defense_worksheets(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "worksheets": [
                worksheet.model_dump(mode="json")
                for worksheet in store.list_claim_defense_worksheets(project_id)
            ],
            "current_source_draft_hash": current_hash,
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
        materials, disclosures, patent_points, _formula_runs, evidence_bindings = _build_evidence_bindings_for_project(
            store, project
        )
        run = run_draft_completion(
            project_id=project_id,
            package=package,
            filing_reports=store.list_filing_readiness_reports(project_id),
            worksheets=store.list_claim_defense_worksheets(project_id),
            patent_points=patent_points,
            disclosures=disclosures,
            materials=materials,
            evidence_bindings=evidence_bindings,
        )
        stored = store.create_draft_completion_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/completion-runs")
    def list_draft_completion_runs(project_id: str) -> dict:
        project = _require_project(store, project_id)
        current_hash = source_draft_hash(project.package) if project.package else ""
        return {
            "runs": [
                run.model_dump(mode="json")
                for run in store.list_draft_completion_runs(project_id)
            ],
            "current_source_draft_hash": current_hash,
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

    @app.post("/api/projects/{project_id}/llm-cache/clear")
    def clear_project_stage_cache(project_id: str) -> dict:
        _require_project(store, project_id)
        deleted = clear_project_llm_cache(store, project_id)
        return {"deleted": deleted}

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/generate")
    def generate_completion_patches(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = store.get_draft_completion_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        current_hash = source_draft_hash(package)
        if run.draft_package_hash != current_hash:
            raise HTTPException(status_code=409, detail="Completion run is stale for the current draft.")
        _materials, _disclosures, _patent_points, _formula_runs, evidence_bindings = _build_evidence_bindings_for_project(
            store, project
        )
        generated = generate_evidence_backed_patches(
            PatchGenerationContext(
                package=package,
                issues=run.issues,
                tasks=run.tasks,
                support_matrix=run.support_matrix,
                evidence_bindings=evidence_bindings,
                existing_patch_count=len(run.patches),
            )
        )
        if not generated:
            return run.model_dump(mode="json")
        updated = run.model_copy(update={"patches": [*run.patches, *generated]})
        stored = store.update_draft_completion_run(updated)
        if not stored:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        return stored.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/accept")
    def accept_completion_patch(project_id: str, run_id: str, patch_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        existing_run = store.get_draft_completion_run(project_id, run_id)
        if not existing_run:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        current_hash = source_draft_hash(package)
        if existing_run.draft_package_hash and existing_run.draft_package_hash != current_hash:
            raise HTTPException(status_code=409, detail="Completion run is stale for the current draft.")
        run = store.update_completion_patch_status(project_id, run_id, patch_id, "accepted")
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion patch not found.")
        adjusted = store.update_draft_completion_run(_completion_run_with_progress_score(run))
        if not adjusted:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        patch = next((candidate for candidate in adjusted.patches if candidate.id == patch_id), None)
        if patch:
            updated_package = _apply_completion_patch(package, patch, run_draft_package_hash=adjusted.draft_package_hash)
            if updated_package != package:
                store.update_project_package(project_id, updated_package)
                _record_revision_ledger_event(
                    store,
                    project_id=project_id,
                    before_package=package,
                    after_package=updated_package,
                    revision_kind="completion_patch",
                    user_intent_summary=patch.rationale,
                    affected_sections=_completion_patch_affected_sections(patch),
                    protection_scope_changed=patch.target_section == "claim",
                    artifact_refs=[f"completion-run:{run_id}", f"completion-patch:{patch_id}"],
                )
        return adjusted.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/reject")
    def reject_completion_patch(project_id: str, run_id: str, patch_id: str) -> dict:
        _require_project(store, project_id)
        run = store.update_completion_patch_status(project_id, run_id, patch_id, "rejected")
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion patch not found.")
        adjusted = store.update_draft_completion_run(_completion_run_with_progress_score(run))
        if not adjusted:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        return adjusted.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/completion-runs/{run_id}/patches/accept-all")
    def accept_all_completion_patches(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = store.get_draft_completion_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        current_hash = source_draft_hash(package)
        if run.draft_package_hash and run.draft_package_hash != current_hash:
            raise HTTPException(status_code=409, detail="Completion run is stale for the current draft.")
        current = run
        current_package = package
        for patch in [patch for patch in run.patches if patch.status == "proposed"]:
            updated = store.update_completion_patch_status(project_id, run_id, patch.id, "accepted")
            if not updated:
                raise HTTPException(status_code=404, detail="Draft completion patch not found.")
            current = updated
            patched_package = _apply_completion_patch(current_package, patch)
            if patched_package != current_package:
                store.update_project_package(project_id, patched_package)
                _record_revision_ledger_event(
                    store,
                    project_id=project_id,
                    before_package=current_package,
                    after_package=patched_package,
                    revision_kind="completion_patch",
                    user_intent_summary=patch.rationale,
                    affected_sections=_completion_patch_affected_sections(patch),
                    protection_scope_changed=patch.target_section == "claim",
                    artifact_refs=[f"completion-run:{run_id}", f"completion-patch:{patch.id}"],
                )
                current_package = patched_package
        adjusted = store.update_draft_completion_run(_completion_run_with_progress_score(current))
        if not adjusted:
            raise HTTPException(status_code=404, detail="Draft completion run not found.")
        return adjusted.model_dump(mode="json")

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
            round_accepted = False
            for patch in safe_patches:
                patched_package = _apply_completion_patch(
                    current_package,
                    patch,
                    run_draft_package_hash=current_run.draft_package_hash,
                )
                if patched_package == current_package:
                    logs.append(f"score-improvement: 补丁 {patch.id} 未通过安全检查，未应用")
                    continue
                current_package = patched_package
                store.update_completion_patch_status(project_id, current_run.id, patch.id, "accepted")
                accepted_patch_ids.append(patch.id)
                round_accepted = True
                logs.append(f"score-improvement: 已应用补丁 {patch.id} -> {patch.target_section}")
                # Remaining patches in this batch were generated against the
                # pre-patch draft hash and can no longer apply cleanly to the
                # mutated package; stop and re-score so the next round
                # regenerates patches against the new draft. (Without this the
                # stale patches log a misleading "未通过安全检查" line.)
                break
            if not round_accepted:
                logs.append("score-improvement: 本轮没有补丁通过安全检查")
                break
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
        providers, participant_providers = _post_draft_review_provider_plan(
            payload.providers if payload else None,
            payload.participant_providers if payload else None,
        )
        blocked_run = _blocked_post_draft_review_for_seats(
            store=store,
            project_id=project_id,
            package=compile_run.official_package,
            providers=providers,
            participant_providers=participant_providers,
            official_compile_run_id=compile_run.id,
            retry_of=None,
        )
        if blocked_run:
            return blocked_run.model_dump(mode="json")
        run = _execute_post_draft_review(
            store=store,
            project_id=project_id,
            package=compile_run.official_package,
            llm=app.state.llm,
            providers=providers,
            participant_providers=participant_providers,
            official_compile_run_id=compile_run.id,
            stage_timeout_ms=payload.stage_timeout_ms if payload else None,
            run_timeout_ms=payload.run_timeout_ms if payload else None,
            retry_of=None,
        )
        return run.model_dump(mode="json")

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

    @app.get(
        "/api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session",
        response_model=PostDraftRepairSession,
    )
    def get_post_draft_repair_session(project_id: str, run_id: str) -> PostDraftRepairSession:
        project = _require_project(store, project_id)
        if not project.package:
            raise HTTPException(status_code=404, detail="Draft package not found")
        review = _get_post_draft_review_or_404(store, project_id, run_id)

        sections = {
            "title": project.package.title,
            "abstract": project.package.abstract,
            "claims": project.package.claims,
            "description": project.package.description,
            "drawing_description": project.package.drawing_description,
        }
        current_hash = source_draft_hash(project.package)
        review_hash = getattr(review, "draft_package_hash", None)
        raw_issues = normalize_post_draft_issues(review.model_dump(), sections)
        issues = [DraftReviewIssue.model_validate(item) for item in raw_issues]
        return PostDraftRepairSession(
            project_id=project_id,
            review_run_id=run_id,
            draft_package_hash=review_hash,
            current_draft_hash=current_hash,
            stale=bool(review_hash and review_hash != current_hash),
            issues=issues,
            sections=sections,
        )

    @app.post(
        "/api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches",
        response_model=DraftRepairPatch,
    )
    def create_post_draft_repair_patch(
        project_id: str, run_id: str, payload: DraftRepairPatchCreate
    ) -> DraftRepairPatch:
        project = _require_project(store, project_id)
        package = _require_package(project)
        review = _get_post_draft_review_or_404(store, project_id, run_id)

        # Verify the issue exists in the current session
        sections = {
            "title": package.title,
            "abstract": package.abstract,
            "claims": package.claims,
            "description": package.description,
            "drawing_description": package.drawing_description,
        }
        raw_issues = normalize_post_draft_issues(review.model_dump(), sections)
        issues_by_id = {item["id"]: item for item in raw_issues}
        issue = issues_by_id.get(payload.issue_id)
        if issue is None:
            raise HTTPException(status_code=404, detail="Issue not found in current repair session.")

        current_hash = source_draft_hash(package)
        _ensure_post_draft_review_current(review, current_hash)
        if payload.draft_package_hash and payload.draft_package_hash != current_hash:
            raise HTTPException(status_code=409, detail="Draft package has changed since the repair session was opened.")

        patch_dict = create_repair_patch_payload(
            issue_id=payload.issue_id,
            target_section=payload.target_section,
            draft_package_hash=current_hash,
            selected_text=payload.selected_text or _repair_issue_anchor_snippet(issue),
            nearby_context=payload.nearby_context,
            project_id=project_id,
            review_run_id=run_id,
            issue_message=str(issue.get("message") or ""),
            llm=None if isinstance(app.state.llm, MissingLLMClient) else app.state.llm,
        )

        if patch_dict["status"] == "stale":
            raise HTTPException(status_code=422, detail="Selected text is required to create a repair patch.")

        if patch_dict["status"] == "unsafe":
            unsafe_terms = ", ".join(patch_dict.get("risk_notes", []))
            raise HTTPException(
                status_code=422,
                detail=f"Patch text is unsafe. Detected markers: {unsafe_terms}. Manually clean the source text before regenerating.",
            )

        patch = DraftRepairPatch.model_validate(patch_dict)
        # Store the patch in-memory for later apply
        _repair_patch_store()[patch.id] = patch
        return patch

    @app.post(
        "/api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches/{patch_id}/apply",
        response_model=DraftRepairPatchApplyResult,
    )
    def apply_post_draft_repair_patch(project_id: str, run_id: str, patch_id: str) -> DraftRepairPatchApplyResult:
        project = _require_project(store, project_id)
        package = _require_package(project)
        review = _get_post_draft_review_or_404(store, project_id, run_id)

        patch = _repair_patch_store().get(patch_id)
        if not patch:
            raise HTTPException(status_code=404, detail="Repair patch not found. Re-create the patch first.")

        if patch.project_id != project_id or patch.review_run_id != run_id:
            raise HTTPException(status_code=404, detail="Repair patch not found for this review run.")

        current_hash = source_draft_hash(package)
        _ensure_post_draft_review_current(review, current_hash)
        if patch.draft_package_hash != current_hash:
            raise HTTPException(
                status_code=409,
                detail="Draft package has changed since the patch was created. Re-open the repair session.",
            )

        if patch.status == "applied":
            raise HTTPException(status_code=409, detail="Patch has already been applied.")

        if patch.status != "proposed":
            raise HTTPException(status_code=422, detail=f"Cannot apply a patch with status {patch.status}.")

        section_attr = {
            "title": "title",
            "abstract": "abstract",
            "claims": "claims",
            "description": "description",
            "drawing_description": "drawing_description",
        }.get(patch.target_section)
        if not section_attr:
            raise HTTPException(status_code=422, detail=f"Unknown target section: {patch.target_section}")

        section_text = getattr(package, section_attr, "")
        try:
            new_section_text = apply_section_patch(section_text, patch.original, patch.patched)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail="Patch original text is no longer present in the draft section.",
            ) from exc

        updated_package = package.model_copy(update={section_attr: new_section_text})
        updated_package = updated_package.model_copy(
            update={
                "generation_logs": [
                    *updated_package.generation_logs,
                    f"post_draft_repair: applied AI patch {patch_id} to {patch.target_section} (issue {patch.issue_id})",
                ]
            }
        )
        store.update_project_package(project_id, updated_package)
        _record_revision_ledger_event(
            store,
            project_id=project_id,
            before_package=package,
            after_package=updated_package,
            revision_kind="post_draft_repair",
            user_intent_summary=patch.diff_summary,
            affected_sections=[patch.target_section],
            artifact_refs=[f"post-draft-review:{run_id}", f"repair-patch:{patch_id}"],
        )

        # Mark the patch as applied so it can't be re-applied
        applied_patch = patch.model_copy(update={"status": "applied"})
        _repair_patch_store()[patch.id] = applied_patch

        return DraftRepairPatchApplyResult(
            package=updated_package,
            current_draft_hash=source_draft_hash(updated_package),
        )

    @app.post("/api/projects/{project_id}/post-draft-reviews/{run_id}/apply-safe-patches")
    def apply_post_draft_safe_patches(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = store.get_post_draft_review_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Post-draft review run not found.")
        result = _apply_post_draft_safe_patches(project_id=project_id, package=package, run=run)
        store.update_project_package(project_id, result.package)
        _record_revision_ledger_event(
            store,
            project_id=project_id,
            before_package=package,
            after_package=result.package,
            revision_kind="post_draft_repair",
            user_intent_summary=f"Applied post-draft safe patches from run {run.id}",
            affected_sections=_changed_draft_sections(package, result.package),
            artifact_refs=[f"post-draft-review:{run_id}"],
        )
        return result.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/post-draft-reviews/{run_id}/cancel")
    def cancel_post_draft_review(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        run = store.get_post_draft_review_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Post-draft review run not found.")
        updated = _mark_post_draft_cancel_requested(store, run)
        return updated.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/post-draft-reviews/{run_id}/retry")
    def retry_post_draft_review(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_latest_completed_official_compile(store, project_id, package)
        previous = store.get_post_draft_review_run(project_id, run_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Post-draft review run not found.")
        if isinstance(app.state.llm, MissingLLMClient):
            raise HTTPException(status_code=503, detail="LLM is not configured for post-draft multi-agent review.")
        providers, participant_providers = _post_draft_review_provider_plan(
            previous.providers,
            previous.participant_providers,
        )
        blocked_run = _blocked_post_draft_review_for_seats(
            store=store,
            project_id=project_id,
            package=compile_run.official_package,
            providers=providers,
            participant_providers=participant_providers,
            official_compile_run_id=compile_run.id,
            retry_of=previous.id,
        )
        if blocked_run:
            return blocked_run.model_dump(mode="json")
        run = _execute_post_draft_review(
            store=store,
            project_id=project_id,
            package=compile_run.official_package,
            llm=app.state.llm,
            providers=providers,
            participant_providers=participant_providers,
            official_compile_run_id=compile_run.id,
            stage_timeout_ms=None,
            run_timeout_ms=None,
            retry_of=previous.id,
        )
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

    @app.post("/api/projects/{project_id}/official-compile-runs/{run_id}/apply-cleanup")
    def apply_official_compile_cleanup(project_id: str, run_id: str) -> dict:
        project = _require_project(store, project_id)
        package = _require_package(project)
        run = store.get_official_compile_run(project_id, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        result = _apply_official_compile_cleanup(project_id=project_id, package=package, run=run)
        store.update_project_package(project_id, result.package)
        _record_revision_ledger_event(
            store,
            project_id=project_id,
            before_package=package,
            after_package=result.package,
            revision_kind="official_cleanup",
            user_intent_summary=f"Applied official compile cleanup from run {run.id}",
            affected_sections=_changed_draft_sections(package, result.package),
            artifact_refs=[f"official-compile:{run_id}"],
        )
        return result.model_dump(mode="json")

    @app.post("/api/projects/{project_id}/official-compile-runs/{run_id}/kimi-language-polish")
    async def create_kimi_language_polish_run(project_id: str, run_id: str) -> dict:
        _require_project(store, project_id)
        source_run = store.get_official_compile_run(project_id, run_id)
        if not source_run:
            raise HTTPException(status_code=404, detail="Official compile run not found.")
        if source_run.status != "completed" or not source_run.official_package:
            raise HTTPException(status_code=409, detail="Completed official draft compile is required before Kimi language polish.")
        runner = app.state.provider_runner or AgentProviderRunner()
        run = await run_kimi_language_polish(
            project_id=project_id,
            source_run=source_run,
            provider_runner=runner,
            workdir=settings.data_dir / "official-language-polish-runs" / project_id / uuid.uuid4().hex,
        )
        stored = store.create_official_compile_run(run)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/export-readiness")
    def export_readiness(project_id: str) -> dict:
        """Return structured export readiness state.

        After official compile, the compile report may show ``completed`` with
        ``blocked_items=none``, which can mislead users into thinking export is
        ready.  This endpoint exposes the full gate chain so the UI can show a
        specific lock reason and CTA instead of a generic 409 on the export link.
        """
        project = _require_project(store, project_id)
        package = project.package
        if not package:
            return {
                "export_allowed": False,
                "draft_required": True,
                "quality_required": False,
                "official_compile_required": False,
                "post_draft_review_required": False,
                "next_action": "generate_draft",
                "reason": "请先生成专利初稿后再导出。",
            }
        current_source_hash = source_draft_hash(package)
        quality_state = _current_quality_gate_state(store, project_id, current_source_hash)
        if quality_state["quality_required"]:
            return {
                "export_allowed": False,
                "draft_required": False,
                "quality_required": True,
                "official_compile_required": False,
                "post_draft_review_required": False,
                "next_action": "run_quality_checks",
                "reason": "当前初稿尚未完成质量检查。请先运行提交前质量检查和成稿完整度检查，再进入正式导出链路。",
                "current_source_draft_hash": current_source_hash,
                **quality_state,
            }
        latest_compile_attempt = _latest_official_compile_attempt_for_source(store, project_id, current_source_hash)
        compile_run = latest_compile_attempt
        compile_current = _official_compile_export_ready(compile_run, current_source_hash)
        if not compile_current:
            compile_for_state = latest_compile_attempt
            return {
                "export_allowed": False,
                "draft_required": False,
                "quality_required": False,
                "official_compile_required": True,
                "post_draft_review_required": False,
                "next_action": "run_official_compile",
                "reason": "当前初稿尚未编译为正式稿。请先生成正式稿（清除内部痕迹后生成可提交版本）。",
                "current_source_draft_hash": current_source_hash,
                "has_compile_run": compile_for_state is not None,
                "compile_run_id": compile_for_state.id if compile_for_state else None,
                "compile_status": compile_for_state.status if compile_for_state else "missing",
                "compile_artifact_state": _official_compile_artifact_state(
                    compile_for_state,
                    current_source_hash,
                ),
                "compile_blocked_items": compile_for_state.blocked_items if compile_for_state else [],
                **quality_state,
            }
        matching_review_attempt = _latest_matching_post_draft_review_attempt(
            store, project_id, current_source_hash, compile_run
        )
        latest_matching_review = _latest_completed_matching_post_draft_review(
            store, project_id, current_source_hash, compile_run
        )
        review_ready = _post_draft_review_export_ready(matching_review_attempt)
        if not review_ready:
            review_for_state = matching_review_attempt or latest_matching_review
            return {
                "export_allowed": False,
                "draft_required": False,
                "quality_required": False,
                "official_compile_required": False,
                "post_draft_review_required": True,
                "next_action": "run_post_draft_review",
                "reason": "正式稿编译已完成，但需通过成稿后多智能体会审后方可导出。会审将检查权利要求质量、说明书清洁度、技术硬度和内部痕迹，通过后即可解锁正式导出。",
                "compile_run_id": compile_run.id,
                "official_package_hash": compile_run.official_package_hash,
                "current_source_draft_hash": current_source_hash,
                "has_review_run": matching_review_attempt is not None,
                "review_export_allowed": _post_draft_review_export_ready(review_for_state),
                "review_run_id": review_for_state.id if review_for_state else None,
                "review_status": review_for_state.status if review_for_state else "missing",
                "review_gate_status": _post_draft_review_gate_status(review_for_state),
                "review_blocking_issues": review_for_state.blocking_issues if review_for_state else [],
                **quality_state,
            }
        return {
            "export_allowed": True,
            "draft_required": False,
            "quality_required": False,
            "official_compile_required": False,
            "post_draft_review_required": False,
            "next_action": "export_ready",
            "reason": "正式导出已就绪。请专业人员最终复核后提交。",
            "compile_run_id": compile_run.id,
            "review_run_id": matching_review_attempt.id,
            **quality_state,
        }

    @app.get("/api/projects/{project_id}/official-export.docx")
    def export_project_official_docx(project_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, package)
        output_path = export_official_package_docx(
            compile_run.official_package,
            settings.data_dir / "exports" / f"{project.id}-official.docx",
        )
        response = FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}-正式提交稿.docx",
        )
        response.headers["Content-Disposition"] = _content_disposition_header(
            f"{project.name}-正式提交稿.docx"
        )["Content-Disposition"]
        return response

    @app.get("/api/projects/{project_id}/official-export.md")
    def export_project_official_markdown(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        compile_run = _require_official_export_gate(store, project_id, package)
        return PlainTextResponse(
            official_package_to_markdown(compile_run.official_package),
            media_type="text/markdown; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}-正式提交稿.md"),
        )

    @app.get("/api/projects/{project_id}/export.docx")
    def export_project_docx(project_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        output_path = export_docx(package, settings.data_dir / "exports" / f"{project.id}.docx")
        response = FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}.docx",
        )
        response.headers["Content-Disposition"] = _content_disposition_header(
            f"{project.name}.docx"
        )["Content-Disposition"]
        return response

    @app.get("/api/projects/{project_id}/export.md")
    def export_project_markdown(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(
            package_to_markdown(package),
            media_type="text/markdown; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}.md"),
        )

    @app.get("/api/projects/{project_id}/diagram.mmd")
    def export_project_mermaid(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(
            package.mermaid,
            media_type="text/plain; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}.mmd"),
        )

    @app.get("/api/projects/{project_id}/image-prompt.md")
    def export_project_image_prompt(project_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        package = _require_package(project)
        return PlainTextResponse(
            package.image_prompt,
            media_type="text/markdown; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}-绘图提示词.md"),
        )

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/export.docx")
    def export_disclosure_run_docx(project_id: str, run_id: str) -> FileResponse:
        project = _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        output_path = export_disclosure_docx(package, Path(run.run_dir) / "disclosure.docx", Path(run.run_dir))
        response = FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{project.name}-技术交底书.docx",
        )
        response.headers["Content-Disposition"] = _content_disposition_header(
            f"{project.name}-技术交底书.docx"
        )["Content-Disposition"]
        return response

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/export.md")
    def export_disclosure_run_markdown(project_id: str, run_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        return PlainTextResponse(
            clean_disclosure_to_markdown(package),
            media_type="text/markdown; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}-技术交底书.md"),
        )

    @app.get("/api/projects/{project_id}/disclosures/{run_id}/sidecar.md")
    def export_disclosure_run_sidecar(project_id: str, run_id: str) -> PlainTextResponse:
        project = _require_project(store, project_id)
        run = _require_disclosure_run(store, project_id, run_id)
        package = _require_disclosure_package(run)
        return PlainTextResponse(
            disclosure_sidecar_to_markdown(package),
            media_type="text/markdown; charset=utf-8",
            headers=_content_disposition_header(f"{project.name}-交底书内部侧车.md"),
        )

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


_TERMINAL_RUN_STATUSES = {"completed", "failed", "interrupted"}
_ACTIVE_RUN_STATUSES = {"queued", "running"}


def _runtime_failure(
    *,
    flow: str,
    reason: str,
    message: str,
    state: object | None = None,
    retryable: bool = True,
    repair_suggestion: str = "",
) -> RuntimeFailure:
    return RuntimeFailure(
        flow=flow,
        stage=str(getattr(state, "current_stage", "") or "queued"),
        provider=str(getattr(state, "provider", "") or ""),
        reason=reason,
        message=message,
        retryable=retryable,
        elapsed_ms=int(getattr(state, "elapsed_ms", 0) or 0),
        repair_suggestion=repair_suggestion,
        partial_artifact_count=int(getattr(state, "partial_artifact_count", 0) or 0),
    )


def _with_event_once(events: list[str], event: str) -> list[str]:
    if event in events:
        return events
    return [*events, event]


def _cancelled_deliberation_run(run: DeliberationRun) -> DeliberationRun:
    failure_details = list(run.failure_details)
    if not any(failure.reason == "cancelled" for failure in failure_details):
        failure_details.append(
            _runtime_failure(
                flow="deliberation",
                reason="cancelled",
                message="Deliberation run was cancelled; partial artifacts were preserved for retry.",
                state=run.runtime_state,
                repair_suggestion="Review partial stage results, then retry the run when ready.",
            )
        )
    events = _with_event_once(list(run.events), "cancel requested")
    events = _with_event_once(events, "run cancelled")
    return run.model_copy(
        update={
            "status": "interrupted",
            "cancel_requested": True,
            "failure_details": failure_details,
            "events": events,
        }
    )


def _reconcile_deliberation_run(store: SQLiteStore, run: DeliberationRun) -> DeliberationRun:
    if run.status not in _ACTIVE_RUN_STATUSES:
        return run
    if run.cancel_requested or any(failure.reason == "cancelled" for failure in run.failure_details):
        updated = _cancelled_deliberation_run(run)
        store.update_deliberation_run(updated)
        return updated
    if run.failure_details:
        updated = run.model_copy(
            update={
                "status": "failed",
                "events": _with_event_once(list(run.events), "run failed"),
            }
        )
        store.update_deliberation_run(updated)
        return updated
    return run


def _mark_disclosure_cancel_requested(store: SQLiteStore, run: DisclosureRun) -> DisclosureRun:
    if run.status in _TERMINAL_RUN_STATUSES:
        return run
    failure_details = list(run.failure_details)
    events = [*run.events, "cancel requested"]
    status = run.status
    if run.status == "queued":
        status = "interrupted"
        failure_details.append(
            _runtime_failure(
                flow="disclosure",
                reason="cancelled",
                message="Disclosure run was cancelled before execution started.",
                state=run.runtime_state,
                repair_suggestion="Retry the run when ready.",
            )
        )
    updated = run.model_copy(
        update={
            "status": status,
            "cancel_requested": True,
            "failure_details": failure_details,
            "events": events,
        }
    )
    store.update_disclosure_run(updated)
    return updated


def _mark_deliberation_cancel_requested(store: SQLiteStore, run: DeliberationRun) -> DeliberationRun:
    if run.status in _TERMINAL_RUN_STATUSES:
        return run
    updated = _cancelled_deliberation_run(run)
    store.update_deliberation_run(updated)
    return updated


def _mark_formula_cancel_requested(store: SQLiteStore, run: FormulaRun) -> FormulaRun:
    if run.status in _TERMINAL_RUN_STATUSES:
        return run
    failure_details = list(run.failure_details)
    status = run.status
    if run.status == "queued":
        status = "interrupted"
        failure_details.append(
            _runtime_failure(
                flow="formula",
                reason="cancelled",
                message="Formula run was cancelled before execution started.",
                state=run.runtime_state,
                repair_suggestion="Retry the formula run when ready.",
            )
        )
    updated = run.model_copy(
        update={
            "status": status,
            "cancel_requested": True,
            "failure_details": failure_details,
            "events": [*run.events, "cancel requested"],
        }
    )
    store.update_formula_run(updated)
    return updated


def _mark_post_draft_cancel_requested(store: SQLiteStore, run: PostDraftReviewRun) -> PostDraftReviewRun:
    if run.status in _TERMINAL_RUN_STATUSES:
        return run
    failure_details = list(run.failure_details)
    status = run.status
    if status == "queued":
        status = "interrupted"
        failure_details.append(
            _runtime_failure(
                flow="post_draft_review",
                reason="cancelled",
                message="Post-draft review run was cancelled before execution started.",
                state=run.runtime_state,
                repair_suggestion="Retry the review after the official draft is ready.",
            )
        )
    updated = run.model_copy(
        update={
            "status": status,
            "cancel_requested": True,
            "failure_details": failure_details,
        }
    )
    store.update_post_draft_review_run(updated)
    return updated


def _execute_formula_run(
    *,
    store: SQLiteStore,
    project_id: str,
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate],
    disclosure: DisclosurePackage | None,
    strategy_brief: object | None,
    llm: LLMClient,
    providers: list[str],
    stage_timeout_ms: int | None,
    run_timeout_ms: int | None,
    retry_of: str | None,
) -> FormulaRun:
    requirement = assess_formula_need(
        project=project,
        patent_points=patent_points,
        disclosure=disclosure,
        strategy_brief=strategy_brief,
    )
    run_id = uuid.uuid4().hex
    running = FormulaRun(
        id=run_id,
        project_id=project_id,
        status="running",
        providers=providers,
        requirement=requirement,
        retry_of=retry_of,
        events=["run started"],
    )
    store.create_formula_run(running)

    def is_cancelled() -> bool:
        current = store.get_formula_run(project_id, run_id)
        return bool(current and current.cancel_requested)

    def persist_runtime(state: object) -> None:
        current = store.get_formula_run(project_id, run_id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return
        store.update_formula_run(current.model_copy(update={"runtime_state": state}))

    runtime = RuntimeContext(
        flow="formula",
        run_id=run_id,
        stage_timeout_ms=stage_timeout_ms,
        run_timeout_ms=run_timeout_ms,
        cancel_check=is_cancelled,
        on_update=persist_runtime,
    )
    try:
        runtime.begin_stage("formula_assessment", provider="system", subtask="formula requirement")
        runtime.complete_stage(partial_artifact_count=0, warning_count=0)
        runtime.begin_stage("formula_generation", provider="llm", subtask="core formula package")
        generated = generate_formula_run(
            project_id=project_id,
            project=project,
            patent_points=patent_points,
            disclosure=disclosure,
            strategy_brief=strategy_brief,
            llm=llm,
            providers=providers,
        )
        state = runtime.complete_stage(
            partial_artifact_count=1 if generated.package else 0,
            warning_count=len(generated.failures),
        )
        current = store.get_formula_run(project_id, run_id) or running
        completed = generated.model_copy(
            update={
                "id": run_id,
                "project_id": project_id,
                "providers": providers,
                "runtime_state": state,
                "cancel_requested": current.cancel_requested,
                "retry_of": retry_of,
                "failure_details": [*current.failure_details, *generated.failure_details],
                "events": [*current.events, *generated.events],
            }
        )
        store.update_formula_run(completed)
        return completed
    except RuntimeCancelled:
        current = store.get_formula_run(project_id, run_id) or running
        failure = runtime.cancelled_failure()
        interrupted = current.model_copy(
            update={
                "status": "interrupted",
                "cancel_requested": True,
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, "run cancelled"],
            }
        )
        store.update_formula_run(interrupted)
        return interrupted
    except RuntimeTimeout as exc:
        current = store.get_formula_run(project_id, run_id) or running
        failure = runtime.timeout_failure(str(exc))
        failed = current.model_copy(
            update={
                "status": "failed",
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run timed out: {exc}"],
            }
        )
        store.update_formula_run(failed)
        return failed
    except Exception as exc:
        current = store.get_formula_run(project_id, run_id) or running
        if current.cancel_requested:
            failure_details = list(current.failure_details)
            if not any(failure.reason == "cancelled" for failure in failure_details):
                failure_details.append(runtime.cancelled_failure())
            interrupted = current.model_copy(
                update={
                    "status": "interrupted",
                    "cancel_requested": True,
                    "failure_details": failure_details,
                    "events": _with_event_once(list(current.events), "run cancelled"),
                }
            )
            store.update_formula_run(interrupted)
            return interrupted
        failure = runtime.failure(
            reason="exception",
            message=str(exc),
            retryable=True,
            repair_suggestion="Retry after fixing the formula provider or prompt/schema issue.",
        )
        failed = current.model_copy(
            update={
                "status": "failed",
                "failures": [*current.failures, str(exc)],
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run failed: {exc}"],
            }
        )
        store.update_formula_run(failed)
        return failed


def _execute_post_draft_review(
    *,
    store: SQLiteStore,
    project_id: str,
    package: OfficialDraftPackage,
    llm: LLMClient,
    providers: list[str],
    participant_providers: list[str],
    official_compile_run_id: str,
    stage_timeout_ms: int | None,
    run_timeout_ms: int | None,
    retry_of: str | None,
) -> PostDraftReviewRun:
    run_id = uuid.uuid4().hex
    running = PostDraftReviewRun(
        id=run_id,
        project_id=project_id,
        status="running",
        providers=providers,
        participant_providers=participant_providers,
        draft_package_hash=package.source_draft_hash,
        official_compile_run_id=official_compile_run_id,
        official_package_hash=package_hash_for_review(package),
        retry_of=retry_of,
    )
    store.create_post_draft_review_run(running)

    def is_cancelled() -> bool:
        current = store.get_post_draft_review_run(project_id, run_id)
        return bool(current and current.cancel_requested)

    def persist_runtime(state: object) -> None:
        current = store.get_post_draft_review_run(project_id, run_id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return
        store.update_post_draft_review_run(current.model_copy(update={"runtime_state": state}))

    def persist_progress(progress: dict[str, object]) -> None:
        current = store.get_post_draft_review_run(project_id, run_id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return
        store.update_post_draft_review_run(current.model_copy(update=progress))

    runtime = RuntimeContext(
        flow="post_draft_review",
        run_id=run_id,
        stage_timeout_ms=stage_timeout_ms,
        run_timeout_ms=run_timeout_ms,
        cancel_check=is_cancelled,
        on_update=persist_runtime,
    )
    try:
        runtime.begin_stage("post_draft_review", provider="llm", subtask="role review")
        cached_llm = _cached_llm(
            store=store,
            project_id=project_id,
            source_hash_value=package_hash_for_review(package),
            llm=llm,
            prompt_pack_version="post-draft-review-v1",
        )
        runtime_llm = _RuntimeCheckpointLLM(cached_llm, runtime=runtime)
        generated = run_post_draft_review(
            project_id=project_id,
            package=package,
            llm=runtime_llm,
            providers=providers,
            official_compile_run_id=official_compile_run_id,
            participant_providers=participant_providers,
            on_progress=persist_progress,
        )
        state = runtime.complete_stage(
            partial_artifact_count=len(generated.role_results) + (1 if generated.chair_result else 0),
            warning_count=len(generated.blocking_issues) + len(generated.contamination_hits),
        )
        current = store.get_post_draft_review_run(project_id, run_id) or running
        completed = generated.model_copy(
            update={
                "id": run_id,
                "project_id": project_id,
                "providers": providers,
                "runtime_state": state,
                "cancel_requested": current.cancel_requested,
                "retry_of": retry_of,
                "failure_details": [*current.failure_details, *generated.failure_details],
            }
        )
        store.update_post_draft_review_run(completed)
        return completed
    except RuntimeCancelled:
        current = store.get_post_draft_review_run(project_id, run_id) or running
        failure = runtime.cancelled_failure()
        interrupted = current.model_copy(
            update={
                "status": "interrupted",
                "cancel_requested": True,
                "failure_details": [*current.failure_details, failure],
            }
        )
        store.update_post_draft_review_run(interrupted)
        return interrupted
    except RuntimeTimeout as exc:
        current = store.get_post_draft_review_run(project_id, run_id) or running
        failure = runtime.timeout_failure(str(exc))
        failed = current.model_copy(
            update={
                "status": "failed",
                "failure_details": [*current.failure_details, failure],
            }
        )
        store.update_post_draft_review_run(failed)
        return failed
    except Exception as exc:
        current = store.get_post_draft_review_run(project_id, run_id) or running
        failure = runtime.failure(
            reason="exception",
            message=str(exc),
            retryable=True,
            repair_suggestion="Retry after fixing the review provider or schema issue.",
        )
        failed = current.model_copy(
            update={
                "status": "failed",
                "failure_details": [*current.failure_details, failure],
            }
        )
        store.update_post_draft_review_run(failed)
        return failed


def _execute_disclosure(
    store: SQLiteStore,
    index: LocalVectorIndex,
    llm: LLMClient,
    prior_art_provider: object,
    research_search_provider: DeepResearchSearchProvider | None,
    project: ProjectRecord,
    run: DisclosureRun,
    stage_timeout_ms: int | None = None,
    run_timeout_ms: int | None = None,
) -> DisclosureRun:
    running = run.model_copy(update={"status": "running", "events": [*run.events, "run started"]})
    store.update_disclosure_run(running)
    partial_stage_results: list[dict[str, Any]] = list(run.stage_results)

    def is_cancelled() -> bool:
        current = store.get_disclosure_run(project.id, run.id)
        return bool(current and current.cancel_requested)

    def persist_runtime(state: object) -> None:
        current = store.get_disclosure_run(project.id, run.id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return
        store.update_disclosure_run(current.model_copy(update={"runtime_state": state}))

    def persist_stage_results(stages: list[dict[str, Any]]) -> None:
        nonlocal partial_stage_results
        partial_stage_results = list(stages)
        current = store.get_disclosure_run(project.id, run.id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return
        store.update_disclosure_run(current.model_copy(update={"stage_results": partial_stage_results}))

    runtime = RuntimeContext(
        flow="disclosure",
        run_id=run.id,
        stage_timeout_ms=stage_timeout_ms,
        run_timeout_ms=run_timeout_ms,
        cancel_check=is_cancelled,
        on_update=persist_runtime,
    )
    materials = _processed_project_materials(store.list_project_materials(project.id))
    brief = _brief_from_draft(project)
    context = _retrieve_generation_context(index, brief)

    # ---- V1.1: pre-flight provider diagnostics ----
    pre_diagnostics = _collect_provider_diagnostics(
        prior_art_provider=prior_art_provider,
        research_search_provider=research_search_provider,
    )

    try:
        user_candidates = store.list_project_patent_points(project.id)
        cached_llm = _cached_llm(
            store=store,
            project_id=project.id,
            source_hash_value=_disclosure_source_hash(project, materials, user_candidates, run.max_prior_art_results),
            llm=llm,
        )
        generator = DisclosureGenerator(cached_llm, prior_art_provider)
        package, stage_results, warnings = generator.generate(
            project=project,
            materials=materials,
            context_chunks=context,
            max_prior_art_results=run.max_prior_art_results,
            user_candidates=user_candidates,
            pre_diagnostics=[d.model_dump(mode="json") for d in pre_diagnostics],
            runtime=runtime,
            on_stage_result=persist_stage_results,
        )
        partial_stage_results = list(stage_results)
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
                runtime=runtime,
                on_stage_result=lambda stages: persist_stage_results([*stage_results, *stages]),
            )
            stage_results.extend(deep_stages)
            partial_stage_results = list(stage_results)
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
                "runtime_state": (store.get_disclosure_run(project.id, run.id) or running).runtime_state,
                "cancel_requested": (store.get_disclosure_run(project.id, run.id) or running).cancel_requested,
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
    except RuntimeCancelled:
        current = store.get_disclosure_run(project.id, run.id) or running
        failure = runtime.cancelled_failure()
        interrupted = current.model_copy(
            update={
                "status": "interrupted",
                "stage_results": partial_stage_results or current.stage_results,
                "cancel_requested": True,
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, "run cancelled"],
            }
        )
        store.update_disclosure_run(interrupted)
        return interrupted
    except RuntimeTimeout as exc:
        current = store.get_disclosure_run(project.id, run.id) or running
        failure = runtime.timeout_failure(str(exc))
        failed = current.model_copy(
            update={
                "status": "failed",
                "stage_results": partial_stage_results or current.stage_results,
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run timed out: {exc}"],
            }
        )
        store.update_disclosure_run(failed)
        return failed
    except Exception as exc:
        current = store.get_disclosure_run(project.id, run.id) or running
        if current.cancel_requested:
            failure_details = list(current.failure_details)
            if not any(failure.reason == "cancelled" for failure in failure_details):
                failure_details.append(runtime.cancelled_failure())
            interrupted = current.model_copy(
                update={
                    "status": "interrupted",
                    "stage_results": partial_stage_results or current.stage_results,
                    "cancel_requested": True,
                    "failure_details": failure_details,
                    "events": _with_event_once(list(current.events), "run cancelled"),
                }
            )
            store.update_disclosure_run(interrupted)
            return interrupted
        failure = runtime.failure(
            reason="exception",
            message=str(exc),
            retryable=True,
            repair_suggestion="Retry after fixing the disclosure provider or prompt/schema issue.",
        )
        failed = current.model_copy(
            update={
                "status": "failed",
                "stage_results": partial_stage_results or current.stage_results,
                "failures": [*current.failures, str(exc)],
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run failed: {exc}"],
            }
        )
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
    runtime: RuntimeContext | None = None,
    on_stage_result: object | None = None,
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
            runtime=runtime,
            on_stage_result=on_stage_result,
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
    run_timeout_ms: int | None = None,
) -> DeliberationRun:
    running = run.model_copy(update={"status": "running", "events": [*run.events, "run started"]})
    store.update_deliberation_run(running)
    disclosure = store.get_latest_completed_disclosure_run(project.id)
    brief = _brief_from_draft(project, disclosure.package if disclosure else None)
    context = _retrieve_generation_context(index, brief)
    runtime = RuntimeContext(
        flow="deliberation",
        run_id=run.id,
        stage_timeout_ms=task_timeout_ms,
        run_timeout_ms=run_timeout_ms,
        cancel_check=lambda: bool((store.get_deliberation_run(project.id, run.id) or running).cancel_requested),
    )

    def persist_update(updated: DeliberationRun) -> None:
        current = store.get_deliberation_run(project.id, run.id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            if current.cancel_requested:
                raise RuntimeCancelled(f"deliberation run {run.id} cancelled")
            return
        runtime.begin_stage(
            updated.stage_results[-1].phase if updated.stage_results else "deliberation",
            provider=updated.logs[-1].provider_id if updated.logs else ",".join(updated.providers),
            subtask=updated.logs[-1].message if updated.logs else "",
            partial_artifact_count=len(updated.stage_results),
            warning_count=len(updated.failures),
        )
        state = runtime.complete_stage(
            partial_artifact_count=len(updated.stage_results),
            warning_count=len(updated.failures),
        )
        store.update_deliberation_run(
            updated.model_copy(
                update={
                    "runtime_state": state,
                    "failure_details": current.failure_details,
                    "cancel_requested": current.cancel_requested,
                    "retry_of": current.retry_of,
                }
            )
        )

    try:
        runtime.begin_stage("deliberation_prepare", provider="system", subtask="context retrieval")
        orchestrator = DeliberationOrchestrator(provider_runner=provider_runner)
        completed = __import__("asyncio").run(
            orchestrator.run(
                run_id=run.id,
                project_id=run.project_id,
                brief=brief,
                context_chunks=context,
                providers=run.providers,
                participant_providers=run.participant_providers,
                run_dir=Path(run.run_dir),
                trace=trace,
                task_timeout_ms=task_timeout_ms,
                on_update=persist_update,
            )
        )
        current = store.get_deliberation_run(project.id, run.id) or running
        if current.status in _TERMINAL_RUN_STATUSES:
            return current
        if current.cancel_requested:
            raise RuntimeCancelled(f"deliberation run {run.id} cancelled")
        runtime.begin_stage("deliberation_finalize", provider="system", subtask="strategy brief")
        state = runtime.complete_stage(
            partial_artifact_count=len(completed.stage_results),
            warning_count=len(completed.failures),
        )
        current = store.get_deliberation_run(project.id, run.id) or running
        completed = completed.model_copy(
            update={
                "runtime_state": state,
                "failure_details": current.failure_details,
                "cancel_requested": current.cancel_requested,
                "retry_of": current.retry_of,
            }
        )
        store.update_deliberation_run(completed)
        return completed
    except RuntimeCancelled:
        current = store.get_deliberation_run(project.id, run.id) or running
        if current.status == "interrupted" and current.cancel_requested:
            return current
        failure = runtime.cancelled_failure()
        interrupted = current.model_copy(
            update={
                "status": "interrupted",
                "cancel_requested": True,
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, "run cancelled"],
            }
        )
        store.update_deliberation_run(interrupted)
        return interrupted
    except RuntimeTimeout as exc:
        current = store.get_deliberation_run(project.id, run.id) or running
        failure = runtime.timeout_failure(str(exc))
        failed = current.model_copy(
            update={
                "status": "failed",
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run timed out: {exc}"],
            }
        )
        store.update_deliberation_run(failed)
        return failed
    except Exception as exc:
        current = store.get_deliberation_run(project.id, run.id) or running
        if current.cancel_requested:
            failure_details = list(current.failure_details)
            if not any(failure.reason == "cancelled" for failure in failure_details):
                failure_details.append(runtime.cancelled_failure())
            interrupted = current.model_copy(
                update={
                    "status": "interrupted",
                    "cancel_requested": True,
                    "failure_details": failure_details,
                    "events": _with_event_once(list(current.events), "run cancelled"),
                }
            )
            store.update_deliberation_run(interrupted)
            return interrupted
        failure = runtime.failure(
            reason="exception",
            message=str(exc),
            retryable=True,
            repair_suggestion="Retry after fixing provider availability or task output schema.",
        )
        failed = current.model_copy(
            update={
                "status": "failed",
                "failure_details": [*current.failure_details, failure],
                "events": [*current.events, f"run failed: {exc}"],
            }
        )
        store.update_deliberation_run(failed)
        return failed


def _build_evidence_bindings_for_project(store: SQLiteStore, project: ProjectRecord) -> tuple[
    list[ProjectMaterial],
    list[DisclosureRun],
    list[PatentPointCandidate],
    list[FormulaRun],
    list[EvidenceBinding],
]:
    materials = _processed_project_materials(store.list_project_materials(project.id))
    disclosures = store.list_disclosure_runs(project.id)
    patent_points = store.list_project_patent_points(project.id)
    formula_runs = store.list_formula_runs(project.id)
    evidence_bindings = build_evidence_bindings(
        project,
        materials=materials,
        disclosures=disclosures,
        patent_points=patent_points,
        formula_runs=formula_runs,
    )
    return materials, disclosures, patent_points, formula_runs, evidence_bindings


def _processed_project_materials(materials: list[ProjectMaterial]) -> list[ProjectMaterial]:
    return [material for material in materials if material.status == "processed"]


def _deep_research_packets_from_disclosures(disclosures: list[DisclosureRun]) -> list[DeepResearchPacket]:
    packets: list[DeepResearchPacket] = []
    seen: set[str] = set()
    for disclosure in disclosures:
        for stage in disclosure.stage_results:
            for raw_packet in _deep_research_packet_payloads(stage):
                try:
                    packet = DeepResearchPacket.model_validate(raw_packet)
                except (TypeError, ValueError, ValidationError):
                    continue
                key = _hash_payload(packet.model_dump(mode="json"))
                if key in seen:
                    continue
                seen.add(key)
                packets.append(packet)
    return packets


def _deep_research_packet_payloads(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    packets: list[dict[str, object]] = []
    for key in ("packet", "deep_research_packet", "research_packet"):
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            packets.append(candidate)
    nested = payload.get("payload")
    if isinstance(nested, dict):
        packets.extend(_deep_research_packet_payloads(nested))
    return packets


def _latest_strategy_brief(store: SQLiteStore, project_id: str) -> PatentStrategyBrief | None:
    for run in store.list_deliberation_runs(project_id):
        if _is_strict_completed_deliberation(run) and run.strategy_brief is not None:
            return run.strategy_brief
    return None


def _cached_llm(
    *,
    store: SQLiteStore,
    project_id: str,
    source_hash_value: str,
    llm: LLMClient,
    prompt_pack_version: str = "",
    timeout_s: float | None = None,
) -> LLMClient:
    if not source_hash_value:
        return llm
    return CachedStageLLMClient(
        store=store,
        project_id=project_id,
        source_hash=source_hash_value,
        delegate=llm,
        prompt_pack_version=prompt_pack_version,
        timeout_s=timeout_s,
        retries=1,
    )


_RUNTIME_LLM_SUBTASK_LABELS = {
    "post_draft_claims_reviewer": "post-draft claims review",
    "post_draft_spec_cleaner": "post-draft specification cleanup",
    "post_draft_technical_hardness": "post-draft technical hardness review",
    "post_draft_chair_synthesis": "post-draft chair synthesis",
}


def _runtime_llm_subtask(stage: str) -> str:
    return _RUNTIME_LLM_SUBTASK_LABELS.get(stage, stage)


class _RuntimeCheckpointLLM:
    def __init__(self, delegate: LLMClient, *, runtime: RuntimeContext) -> None:
        self.delegate = delegate
        self.runtime = runtime

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        self.runtime.begin_stage(stage, provider="llm", subtask=_runtime_llm_subtask(stage))
        try:
            response = self.delegate.complete_stage(stage, system_prompt, user_prompt)
        except Exception:
            self.runtime.checkpoint()
            raise
        self.runtime.complete_stage()
        return response


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _draft_generation_source_hash(
    project: ProjectRecord,
    deliberation: DeliberationRun | None,
    disclosure: DisclosureRun | None,
    formula_run: FormulaRun | None,
    patent_points: list[PatentPointCandidate],
) -> str:
    return _hash_payload(
        {
            "project": project.model_dump(mode="json"),
            "deliberation_id": deliberation.id if deliberation else "",
            "disclosure_id": disclosure.id if disclosure else "",
            "formula_run_id": formula_run.id if formula_run else "",
            "patent_points": [point.model_dump(mode="json") for point in patent_points],
        }
    )


def _disclosure_source_hash(
    project: ProjectRecord,
    materials: list[ProjectMaterial],
    patent_points: list[PatentPointCandidate],
    max_prior_art_results: int,
) -> str:
    return _hash_payload(
        {
            "project": project.model_dump(mode="json"),
            "materials": [material.model_dump(mode="json") for material in materials],
            "patent_points": [point.model_dump(mode="json") for point in patent_points],
            "max_prior_art_results": max_prior_art_results,
        }
    )


def _run_quality_cycle(app: FastAPI, store: SQLiteStore, project_id: str) -> DraftCompletionRun:
    project = _require_project(store, project_id)
    package = _require_package(project)
    materials, disclosures, patent_points, _formula_runs, evidence_bindings = _build_evidence_bindings_for_project(
        store, project
    )
    verified_effects = any(point.evidence_status == "verified" for point in patent_points)
    report = assess_filing_readiness(project_id, package, verified_effects=verified_effects)
    store.create_filing_readiness_report(report)
    worksheet = generate_claim_defense_worksheet(
        project_id=project_id,
        package=package,
        disclosures=disclosures,
        patent_points=patent_points,
        llm=app.state.llm,
        evidence_bindings=evidence_bindings,
    )
    store.create_claim_defense_worksheet(worksheet)
    run = run_draft_completion(
        project_id=project_id,
        package=package,
        filing_reports=store.list_filing_readiness_reports(project_id),
        worksheets=store.list_claim_defense_worksheets(project_id),
        patent_points=patent_points,
        disclosures=disclosures,
        materials=materials,
        evidence_bindings=evidence_bindings,
    )
    return store.create_draft_completion_run(run)


def _apply_completion_patch(
    package: DraftPackage,
    patch: ProposedPatch,
    *,
    run_draft_package_hash: str = "",
) -> DraftPackage:
    if run_draft_package_hash and source_draft_hash(package) != run_draft_package_hash:
        return package
    if patch.patch_kind == "sidecar_only":
        return package
    if not patch.can_enter_official_draft or not patch.after_text.strip():
        return package
    if not _patch_has_real_evidence_refs(patch):
        return package
    text = patch.after_text.strip()
    if patch.target_section in {"description", "embodiment", "term"}:
        return package.model_copy(update={"description": _insert_or_append(package.description, patch, "补充实施方式")})
    if patch.target_section == "claim":
        return package.model_copy(update={"claims": _insert_or_append(package.claims, patch, "补充权利要求")})
    if patch.target_section == "drawing":
        return package.model_copy(update={"drawing_description": _insert_or_append(package.drawing_description, patch, "补充附图说明")})
    return package


def _apply_official_compile_cleanup(
    *,
    project_id: str,
    package: DraftPackage,
    run: OfficialCompileRun,
) -> OfficialCompileCleanupResult:
    previous_hash = source_draft_hash(package)
    if run.source_draft_hash and run.source_draft_hash != previous_hash:
        raise HTTPException(
            status_code=409,
            detail="Official compile cleanup is stale for the current draft.",
        )
    if not run.contamination_removed:
        raise HTTPException(status_code=409, detail="Official compile run did not record cleanup candidates.")

    cleaned_package, contamination_removed, _sidecar_notes = clean_source_draft_for_official_compile(package)
    applied_actions = [_official_compile_cleanup_action_label(item) for item in contamination_removed]
    changed_sections = [
        section
        for section in ("title", "abstract", "claims", "description", "drawing_description")
        if getattr(package, section) != getattr(cleaned_package, section)
    ]
    if not changed_sections:
        raise HTTPException(status_code=409, detail="No official compile cleanup changed the current draft.")

    cleaned_package = cleaned_package.model_copy(
        update={
            "generation_logs": [
                *cleaned_package.generation_logs,
                f"official_compile_cleanup: applied {len(applied_actions)} cleanup items from run {run.id}",
            ]
        }
    )
    return OfficialCompileCleanupResult(
        project_id=project_id,
        compile_run_id=run.id,
        applied_count=len(applied_actions),
        applied_actions=applied_actions,
        previous_draft_hash=previous_hash,
        current_draft_hash=source_draft_hash(cleaned_package),
        package=cleaned_package,
    )


def _record_revision_ledger_event(
    store: SQLiteStore,
    *,
    project_id: str,
    before_package: DraftPackage,
    after_package: DraftPackage,
    revision_kind: str,
    user_intent_summary: str,
    affected_sections: list[str],
    prior_art_changed: bool = False,
    protection_scope_changed: bool = False,
    artifact_refs: list[str] | None = None,
) -> None:
    if before_package == after_package:
        return
    store.create_revision_ledger_record(
        create_revision_record(
            project_id=project_id,
            baseline_package=before_package,
            updated_package=after_package,
            revision_kind=revision_kind,
            user_intent_summary=user_intent_summary,
            affected_sections=affected_sections,
            prior_art_changed=prior_art_changed,
            protection_scope_changed=protection_scope_changed,
            artifact_refs=artifact_refs,
        )
    )


def _changed_draft_sections(before: DraftPackage, after: DraftPackage) -> list[str]:
    return [
        section
        for section in ("title", "abstract", "claims", "description", "drawing_description")
        if getattr(before, section) != getattr(after, section)
    ]


def _completion_patch_affected_sections(patch: ProposedPatch) -> list[str]:
    if patch.target_section in {"description", "embodiment", "term"}:
        return ["description"]
    if patch.target_section == "claim":
        return ["claims"]
    if patch.target_section == "drawing":
        return ["drawing_description"]
    return []


def _official_compile_cleanup_action_label(item: dict[str, str]) -> str:
    section = item.get("section") or "unknown"
    pattern = item.get("pattern") or item.get("category") or "cleanup"
    text = (item.get("text") or "").strip()
    if len(text) > 80:
        text = f"{text[:77]}..."
    return f"{section}: removed {pattern}" + (f" `{text}`" if text else "")


def _apply_post_draft_safe_patches(
    *,
    project_id: str,
    package: DraftPackage,
    run: PostDraftReviewRun,
) -> PostDraftSafePatchApplyResult:
    previous_hash = source_draft_hash(package)
    if run.draft_package_hash and run.draft_package_hash != previous_hash:
        raise HTTPException(
            status_code=409,
            detail="Post-draft review safe patches are stale for the current draft.",
        )
    raw_patches = _post_draft_safe_patch_payloads(run)
    if not raw_patches:
        raise HTTPException(status_code=409, detail="Post-draft review did not provide official safe patches.")

    current_package = package
    applied_actions: list[str] = []
    skipped_patches: list[str] = []
    for raw_patch in raw_patches:
        patch_payload = _parse_post_draft_safe_patch(raw_patch)
        if not patch_payload:
            skipped_patches.append(_safe_patch_label(raw_patch, "invalid_json"))
            continue
        patched_package, action_label = _apply_post_draft_safe_patch(current_package, patch_payload)
        if not action_label or patched_package == current_package:
            skipped_patches.append(_safe_patch_label(raw_patch, "no_change"))
            continue
        unsafe_terms = _unsafe_post_draft_safe_patch_terms(current_package, patched_package)
        if unsafe_terms:
            raise HTTPException(
                status_code=422,
                detail=f"Official safe patch contains unsafe draft markers: {', '.join(unsafe_terms)}.",
            )
        current_package = patched_package
        applied_actions.append(action_label)

    if not applied_actions:
        raise HTTPException(status_code=409, detail="No applicable official safe patches changed the current draft.")

    current_package = current_package.model_copy(
        update={
            "generation_logs": [
                *current_package.generation_logs,
                f"post_draft_review: applied official safe patches from run {run.id}",
            ]
        }
    )
    return PostDraftSafePatchApplyResult(
        project_id=project_id,
        review_run_id=run.id,
        applied_count=len(applied_actions),
        skipped_count=len(skipped_patches),
        applied_actions=applied_actions,
        skipped_patches=skipped_patches,
        previous_draft_hash=previous_hash,
        current_draft_hash=source_draft_hash(current_package),
        package=current_package,
    )


def _post_draft_safe_patch_payloads(run: PostDraftReviewRun) -> list[str]:
    if run.chair_result and run.chair_result.official_safe_patches:
        return list(run.chair_result.official_safe_patches)
    patches: list[str] = []
    for role_result in run.role_results:
        patches.extend(role_result.official_safe_patches)
    return patches


def _ensure_post_draft_review_current(run: PostDraftReviewRun, current_hash: str) -> None:
    if run.draft_package_hash and run.draft_package_hash != current_hash:
        raise HTTPException(
            status_code=409,
            detail="Post-draft review is stale for the current draft. Recompile and re-run post-draft review.",
        )


def _unsafe_post_draft_safe_patch_terms(before: DraftPackage, after: DraftPackage) -> list[str]:
    findings: list[str] = []
    for section in ("title", "abstract", "claims", "description", "drawing_description"):
        before_text = getattr(before, section, "") or ""
        after_text = getattr(after, section, "") or ""
        if before_text == after_text:
            continue
        for term in validate_repair_patch_text(after_text):
            findings.append(f"{section}:{term}")
    return findings


def _parse_post_draft_safe_patch(raw_patch: str) -> dict[str, object] | None:
    text = raw_patch.strip()
    if not text:
        return None
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _apply_post_draft_safe_patch(
    package: DraftPackage,
    payload: dict[str, object],
) -> tuple[DraftPackage, str]:
    action = str(payload.get("action") or payload.get("operation") or "").strip().lower()
    section = _post_draft_safe_patch_section(payload)
    if not section:
        return package, ""
    data = package.model_dump()

    match_text = str(payload.get("match") or payload.get("original_clause") or "").strip()
    replacement_text = str(
        payload.get("replacement")
        or payload.get("proposed_clause")
        or payload.get("patched")
        or ""
    ).strip()
    if match_text and action in {"delete", "remove"}:
        current = str(data.get(section, "") or "")
        updated, changed = _replace_post_draft_patch_text(current, match_text, "")
        if changed:
            data[section] = _squash_patch_blank_lines(updated)
            return DraftPackage(**data), f"{section}: delete matched passage"
    if match_text and (replacement_text or action == "replace"):
        current = str(data.get(section, "") or "")
        replacement = replacement_text or _patch_content(payload)
        updated, changed = _replace_post_draft_patch_text(current, match_text, replacement)
        if changed:
            data[section] = updated
            return DraftPackage(**data), f"{section}: replace matched passage"

    instruction = str(payload.get("patch") or "").strip()
    if instruction:
        current = str(data.get(section, "") or "")
        updated, action_label = _apply_post_draft_patch_instruction(current, instruction, section)
        if action_label:
            data[section] = updated
            return DraftPackage(**data), action_label

    if section == "title":
        replacement = _patch_content(payload)
        if action in {"replace", "replace_with"} and replacement:
            data["title"] = replacement
            return DraftPackage(**data), "title: replace"

    if section in {"abstract", "claims", "drawing_description"}:
        replacement = _patch_content(payload)
        if action in {"replace", "replace_with"} and replacement:
            data[section] = replacement
            return DraftPackage(**data), f"{section}: replace"

    if section == "description":
        description = str(data["description"])
        if action == "remove_all_instances_of":
            markers = _patch_string_list(payload.get("content"))
            data["description"] = _remove_post_draft_internal_blocks(description, markers)
            return DraftPackage(**data), "description: remove internal markers"
        if action == "replace":
            original = str(payload.get("original") or "")
            patched = str(payload.get("patched") or payload.get("content") or "")
            if original and patched and original in description:
                data["description"] = description.replace(original, patched)
                return DraftPackage(**data), "description: replace passage"
        if action == "replace_with":
            replacement = _patch_content(payload)
            if replacement:
                data["description"] = replacement
                return DraftPackage(**data), "description: replace"

    return package, ""


def _post_draft_safe_patch_section(payload: dict[str, object]) -> str:
    raw_target = str(payload.get("target") or payload.get("apply_to") or "").strip()
    if not raw_target:
        return ""
    target = raw_target.lower().replace("-", "_")
    first_token = re.split(r"[\s.:：,，/]+", target, maxsplit=1)[0]
    if first_token in {"title", "abstract", "claims", "description", "drawing_description"}:
        return first_token
    if first_token in {"claim", "claims"} or "权利要求" in raw_target:
        return "claims"
    if "说明书" in raw_target or "description" in target:
        return "description"
    if "摘要" in raw_target or "abstract" in target:
        return "abstract"
    if "附图" in raw_target or "drawing" in target:
        return "drawing_description"
    if "标题" in raw_target or "title" in target:
        return "title"
    return ""


def _replace_post_draft_patch_text(text: str, match_text: str, replacement: str) -> tuple[str, bool]:
    if not match_text:
        return text, False
    if match_text in text:
        return text.replace(match_text, replacement, 1), True
    if ".*" not in match_text:
        return text, False
    try:
        updated, count = re.subn(match_text, lambda _: replacement, text, count=1, flags=re.DOTALL)
    except re.error:
        return text, False
    return updated, count > 0


def _apply_post_draft_patch_instruction(text: str, instruction: str, section: str) -> tuple[str, str]:
    if section == "description" and "删除" in instruction and (
        "内部提示" in instruction or "补充材料" in instruction or "需补强" in instruction
    ):
        updated = _remove_post_draft_internal_blocks(
            text,
            ["为增强本申请的可授权性", "提交前", "需补强", "补充材料", "待实验验证"],
        )
        if updated != text:
            return updated, "description: remove internal markers"

    replacement = _patch_instruction_replacement(instruction)
    if replacement:
        original, patched = replacement
        updated, changed = _replace_patch_instruction_original(text, original, patched)
        if changed:
            return updated, f"{section}: replace instructed passage"

    supplement = _patch_instruction_supplement(instruction)
    if supplement:
        anchor, addition = supplement
        updated = _insert_post_draft_patch_addition(text, anchor, addition)
        if updated != text:
            return updated, f"{section}: add instructed passage"

    if section == "description" and "首次" in instruction and "改为" in instruction and "首次" in text:
        return text.replace("首次", "", 1), "description: remove absolute wording"

    return text, ""


def _patch_instruction_replacement(instruction: str) -> tuple[str, str] | None:
    quoted = re.search(
        r"将[“\"'](?P<old>.+?)[”\"'](?:修改为|替换为|改为)[“\"'](?P<new>.+?)[”\"']",
        instruction,
    )
    if not quoted:
        quoted = re.search(r"将‘(?P<old>.+?)’(?:修改为|替换为|改为)‘(?P<new>.+?)’", instruction)
    if quoted:
        return quoted.group("old").strip(), quoted.group("new").strip()

    plain = re.search(r"^将(?P<old>.+?)(?:修改为|替换为|改为)(?P<new>.+?)(?:，并(?P<tail>.+))?$", instruction)
    if not plain:
        return None
    return plain.group("old").strip(), plain.group("new").strip().rstrip("。")


def _patch_instruction_supplement(instruction: str) -> tuple[str, str] | None:
    supplement = re.search(r"在(?P<anchor>.+?)后补充[‘“\"'](?P<addition>.+?)[’”\"']", instruction)
    if not supplement:
        return None
    return supplement.group("anchor").strip(), supplement.group("addition").strip()


def _replace_patch_instruction_original(text: str, original: str, patched: str) -> tuple[str, bool]:
    if not original or not patched:
        return text, False
    if "…" in original:
        prefix = original.split("…", 1)[0]
        if prefix and prefix in text:
            return text.replace(prefix, patched, 1), True
        if "首次" in original and "首次" in text:
            return text.replace("首次", "", 1), True
        return text, False
    if original in text:
        return text.replace(original, patched, 1), True
    formula_updated, formula_changed = _replace_patch_formula_alias(text, original, patched)
    if formula_changed:
        return formula_updated, True
    return text, False


def _replace_patch_formula_alias(text: str, original: str, patched: str) -> tuple[str, bool]:
    normalized = re.sub(r"\s+", "", original)
    if normalized != "C_det=P_class×IoU":
        return text, False
    patterns = (
        r"!\[[^\]\n]*(?:C_\{\\text\{det\}\}|C_det)[^\]\n]*(?:\\text\{IoU\}|IoU)[^\]\n]*\]\([^\)\n]*\)",
        r"C_\{\\text\{det\}\}\s*=\s*P_\{\\text\{class\}\}\s*\\times\s*\\text\{IoU\}",
        r"C_\{det\}\s*=\s*P_\{class\}\s*\\times\s*IoU",
        r"C_det\s*=\s*P_class\s*[×x]\s*IoU",
    )
    for pattern in patterns:
        updated, count = re.subn(pattern, lambda _: patched, text, count=1)
        if count:
            return _replace_cdet_iou_definition(updated), True
    return text, False


def _replace_cdet_iou_definition(text: str) -> str:
    replacement = (
        "P_class为病害分类器输出的最大类别概率，"
        "U_seg为病害分割掩膜的空间不确定性度量，"
        "所述空间不确定性度量基于分割掩膜预测的熵或边界置信度获得；"
    )
    patterns = (
        r"P_class为病害分类器输出的最大类别概率，IoU为病害分割掩膜的交并比；?",
        r"P_class\s*为病害分类器输出的最大类别概率，\s*IoU\s*为病害分割掩膜的交并比；?",
    )
    updated = text
    for pattern in patterns:
        updated, count = re.subn(pattern, replacement, updated, count=1)
        if count:
            return updated
    return updated


def _insert_post_draft_patch_addition(text: str, anchor: str, addition: str) -> str:
    if not addition or addition in text:
        return text
    if anchor and anchor in text:
        return text.replace(anchor, f"{anchor}{addition}", 1)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if ("CCI" in anchor or "CCI" in addition) and "CCI" in line:
            separator = "" if line.rstrip().endswith(("；", ";", "。", ".")) else "；"
            lines[index] = f"{line.rstrip()}{separator}{addition}"
            return "\n".join(lines)
    return f"{text.rstrip()}\n{addition}"


def _squash_patch_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _patch_content(payload: dict[str, object]) -> str:
    value = payload.get("content")
    return value.strip() if isinstance(value, str) else ""


def _patch_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _remove_post_draft_internal_blocks(text: str, markers: list[str]) -> str:
    internal_markers = [
        *markers,
        "好的，根据",
        "多代理会审",
        "多Agent会审",
        "主席",
        "补充权利要求",
        "针对权利要求特征",
        "中间状态记录",
        "input_data",
        "processing_rule",
        "intermediate_state",
        "confidence_record",
        "伪代码",
        "支撑材料缺失风险提醒",
        "提交前",
        "补强建议",
        "support_gap",
        "attorney_memo",
        "official_safe_patches",
    ]
    cleaned_blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        stripped = block.strip()
        if not stripped:
            continue
        if any(marker and marker in stripped for marker in internal_markers):
            continue
        lines: list[str] = []
        for raw_line in stripped.splitlines():
            line = raw_line.strip()
            if not line or re.fullmatch(r"-{3,}", line):
                continue
            if any(marker and marker in line for marker in internal_markers):
                continue
            line = re.sub(r"^\*\*(.+?)\*\*$", r"\1", line)
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            lines.append(line)
        if lines:
            cleaned_blocks.append("\n".join(lines))
    return "\n\n".join(cleaned_blocks).strip()


def _safe_patch_label(raw_patch: str, reason: str) -> str:
    label = raw_patch.strip().replace("\n", " ")
    if len(label) > 160:
        label = f"{label[:157]}..."
    return f"{reason}: {label or '<empty>'}"


def _patch_has_real_evidence_refs(patch: ProposedPatch) -> bool:
    # "patent_points" is a stage aggregate tag; "patent_point:*" is project evidence.
    ignored_refs = {"patent_points"}
    ignored_prefixes = ("task:", "claim:", "term:", "filing_readiness:")
    for ref in patch.evidence_refs:
        if ref and ref not in ignored_refs and not ref.startswith(ignored_prefixes):
            return True
    return False


def _insert_or_append(original: str, patch: ProposedPatch, heading: str) -> str:
    addition = patch.after_text.strip()
    anchor = patch.before_text.strip()
    if anchor and anchor in original and addition not in original:
        return original.replace(anchor, f"{anchor.rstrip()}\n{addition}", 1)
    return _append_once(original, heading, addition)


def _append_once(original: str, heading: str, addition: str) -> str:
    if addition in original:
        return original
    return f"{original.rstrip()}\n\n{heading}：\n{addition}\n"


def _repair_issue_anchor_snippet(issue: dict) -> str | None:
    anchor = issue.get("anchor")
    if isinstance(anchor, dict):
        snippet = anchor.get("snippet")
        if isinstance(snippet, str) and snippet.strip():
            return snippet.strip()
    snippet = issue.get("snippet")
    if isinstance(snippet, str) and snippet.strip():
        return snippet.strip()
    return None


def _require_project(store: SQLiteStore, project_id: str) -> ProjectRecord:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _require_package(project: ProjectRecord) -> DraftPackage:
    if not project.package:
        raise HTTPException(status_code=409, detail="Generate a draft before export.")
    return project.package


def _get_post_draft_review_or_404(store: SQLiteStore, project_id: str, run_id: str) -> PostDraftReviewRun:
    run = store.get_post_draft_review_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Post-draft review run not found.")
    return run


def _require_latest_completed_official_compile(
    store: SQLiteStore, project_id: str, package: DraftPackage
) -> OfficialCompileRun:
    current_source_hash = source_draft_hash(package)
    latest_attempt = _latest_official_compile_attempt_for_source(store, project_id, current_source_hash)
    if latest_attempt and (
        latest_attempt.status in {"queued", "running", "blocked", "failed"}
        or (latest_attempt.status == "completed" and latest_attempt.blocked_items)
    ):
        raise HTTPException(
            status_code=409,
            detail=_official_compile_gate_error_detail(latest_attempt).replace(
                " before official export.", " before post-draft review."
            ),
        )
    run = store.get_latest_completed_official_compile_run_for_hash(project_id, current_source_hash)
    if not run:
        raise HTTPException(status_code=409, detail="Official draft compile is required before post-draft review.")
    if not run.official_package:
        raise HTTPException(
            status_code=409,
            detail="Current draft has an incomplete official compile: missing official package. Re-run official compile before post-draft review.",
        )
    if not run.official_package_hash:
        raise HTTPException(
            status_code=409,
            detail="Current draft has an incomplete official compile: missing official package hash. Re-run official compile before post-draft review.",
        )
    return run


def _current_quality_artifacts(
    store: SQLiteStore, project_id: str, current_source_hash: str
) -> tuple[FilingReadinessReport | None, ClaimDefenseWorksheet | None]:
    filing_report = next(
        (
            report
            for report in store.list_filing_readiness_reports(project_id)
            if report.draft_package_hash == current_source_hash
        ),
        None,
    )
    worksheet = next(
        (
            worksheet
            for worksheet in store.list_claim_defense_worksheets(project_id)
            if worksheet.draft_package_hash == current_source_hash and worksheet.status != "superseded"
        ),
        None,
    )
    return filing_report, worksheet


def _current_quality_gate_state(store: SQLiteStore, project_id: str, current_source_hash: str) -> dict:
    filing_report, worksheet = _current_quality_artifacts(store, project_id, current_source_hash)
    completion_runs = store.list_draft_completion_runs(project_id)
    latest_filing = next(iter(store.list_filing_readiness_reports(project_id)), None)
    latest_worksheet = next(
        (worksheet for worksheet in store.list_claim_defense_worksheets(project_id) if worksheet.status != "superseded"),
        None,
    )
    latest_completion = next(
        (run for run in completion_runs if run.status == "completed"),
        None,
    )
    latest_current_completion = next(
        (run for run in completion_runs if run.draft_package_hash == current_source_hash),
        None,
    )
    current_completed_completion = (
        latest_current_completion if latest_current_completion and latest_current_completion.status == "completed" else None
    )
    quality_check_states = {
        "filing_readiness": _quality_artifact_state(
            current=filing_report,
            latest_hash=latest_filing.draft_package_hash if latest_filing else "",
            latest_exists=latest_filing is not None,
        ),
        "claim_defense_worksheet": _quality_artifact_state(
            current=worksheet,
            latest_hash=latest_worksheet.draft_package_hash if latest_worksheet else "",
            latest_exists=latest_worksheet is not None,
        ),
        "draft_completion": _quality_artifact_state(
            current=current_completed_completion,
            latest_hash=latest_completion.draft_package_hash if latest_completion else "",
            latest_exists=latest_completion is not None,
            failed_current=latest_current_completion if latest_current_completion and latest_current_completion.status == "failed" else None,
        ),
    }
    missing = [name for name, state in quality_check_states.items() if state == "missing"]
    stale = [name for name, state in quality_check_states.items() if state == "stale"]
    failed = [name for name, state in quality_check_states.items() if state == "failed"]
    unknown = [name for name, state in quality_check_states.items() if state == "unknown"]
    return {
        "quality_done": not missing and not stale and not failed and not unknown,
        "quality_required": bool(missing or stale or failed or unknown),
        "missing_quality_checks": missing,
        "stale_quality_checks": stale,
        "failed_quality_checks": failed,
        "unknown_quality_checks": unknown,
        "quality_check_states": quality_check_states,
        "filing_readiness_report_id": filing_report.id if filing_report else "",
        "claim_defense_worksheet_id": worksheet.id if worksheet else "",
        "draft_completion_run_id": current_completed_completion.id if current_completed_completion else "",
    }


def _quality_artifact_state(
    *,
    current: object | None,
    latest_hash: str,
    latest_exists: bool,
    failed_current: object | None = None,
) -> str:
    if current is not None:
        return "current"
    if failed_current is not None:
        return "failed"
    if latest_hash:
        return "stale"
    if latest_exists:
        return "unknown"
    return "missing"


def _require_current_quality_gate(store: SQLiteStore, project_id: str, current_source_hash: str) -> None:
    state = _current_quality_gate_state(store, project_id, current_source_hash)
    if state["quality_done"]:
        return
    raise HTTPException(
        status_code=409,
        detail=_quality_gate_error_detail(state),
    )


def _quality_gate_error_detail(state: dict) -> str:
    missing = ", ".join(state["missing_quality_checks"])
    stale = ", ".join(state["stale_quality_checks"])
    failed = ", ".join(state.get("failed_quality_checks", []))
    unknown = ", ".join(state.get("unknown_quality_checks", []))
    details = []
    if missing:
        details.append(f"missing quality checks: {missing}")
    if stale:
        details.append(f"stale quality checks: {stale}")
    if failed:
        details.append(f"failed quality checks: {failed}")
    if unknown:
        details.append(f"unknown-hash quality checks: {unknown}")
    return f"Quality checks are required for the current draft before official export: {'; '.join(details)}."


def _latest_official_compile_attempt_for_source(
    store: SQLiteStore,
    project_id: str,
    current_source_hash: str,
) -> OfficialCompileRun | None:
    return next(
        (
            run
            for run in store.list_official_compile_runs(project_id)
            if run.source_draft_hash == current_source_hash
        ),
        None,
    )


def _official_compile_gate_error_detail(run: OfficialCompileRun | None) -> str:
    if run and run.status == "queued":
        return "Current draft has a queued official compile. Wait for it to finish or cancel and retry before official export."
    if run and run.status == "running":
        return "Current draft has a running official compile. Wait for it to finish or cancel and retry before official export."
    if run and run.status == "blocked":
        return "Current draft has a blocked official compile. Resolve the blocked compile items and re-run official compile before official export."
    if run and run.status == "failed":
        return "Current draft has a failed official compile. Re-run official compile before official export."
    if run and run.status == "completed" and run.blocked_items:
        return "Current draft has a blocked official compile. Resolve the blocked compile items and re-run official compile before official export."
    if run and run.status == "completed" and not run.official_package:
        return "Current draft has an incomplete official compile: missing official package. Re-run official compile before official export."
    if run and run.status == "completed" and not run.official_package_hash:
        return "Current draft has an incomplete official compile: missing official package hash. Re-run official compile before official export."
    return "Official draft compile is required for the current draft before official export."


def _official_compile_export_ready(run: OfficialCompileRun | None, current_source_hash: str) -> bool:
    return bool(
        run
        and run.status == "completed"
        and run.official_package
        and run.official_package_hash
        and run.source_draft_hash == current_source_hash
        and not run.blocked_items
    )


def _official_compile_artifact_state(run: OfficialCompileRun | None, current_source_hash: str) -> str:
    if run is None:
        return "missing"
    if run.source_draft_hash != current_source_hash:
        return "stale"
    if run.status in {"queued", "running"}:
        return run.status
    if run.status in {"blocked", "failed"}:
        return run.status
    if run.status == "completed" and run.blocked_items:
        return "blocked"
    if run.status == "completed" and not run.official_package:
        return "missing_official_package"
    if run.status == "completed" and not run.official_package_hash:
        return "missing_official_package_hash"
    return "current"


def _latest_matching_post_draft_review_attempt(
    store: SQLiteStore,
    project_id: str,
    current_source_hash: str,
    compile_run: OfficialCompileRun,
) -> PostDraftReviewRun | None:
    return next(
        (
            run
            for run in store.list_post_draft_review_runs(project_id)
            if run.draft_package_hash == current_source_hash
            and run.official_compile_run_id == compile_run.id
            and run.official_package_hash == compile_run.official_package_hash
        ),
        None,
    )


def _latest_completed_matching_post_draft_review(
    store: SQLiteStore,
    project_id: str,
    current_source_hash: str,
    compile_run: OfficialCompileRun,
) -> PostDraftReviewRun | None:
    return next(
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


def _post_draft_review_gate_error_detail(review: PostDraftReviewRun | None) -> str:
    if review and review.status == "queued":
        return "Current official draft has a queued post-draft review. Wait for it to finish or cancel and retry before official export."
    if review and review.status == "running":
        return "Current official draft has a running post-draft review. Wait for it to finish or cancel and retry before official export."
    if review and review.status == "failed":
        return "Current official draft has a failed post-draft review. Re-run the post-draft multi-agent review before official export."
    if review and review.status == "interrupted":
        return "Current official draft has an interrupted post-draft review. Re-run the post-draft multi-agent review before official export."
    if review and review.status == "completed" and not _post_draft_review_export_ready(review):
        return "Current official draft has a blocked post-draft review. Resolve the review blocking issues and re-run post-draft review before official export."
    return "Post-draft multi-agent review is required for the current official draft before official export."


def _post_draft_review_export_ready(review: PostDraftReviewRun | None) -> bool:
    return bool(
        review
        and review.status == "completed"
        and review.export_allowed
        and not review.blocking_issues
    )


def _post_draft_review_gate_status(review: PostDraftReviewRun | None) -> str:
    if review is None:
        return "missing"
    if review.status != "completed":
        return review.status
    if _post_draft_review_export_ready(review):
        return "passed"
    if review.chair_result and review.chair_result.status:
        return review.chair_result.status
    return "blocked"


def _require_official_export_gate(store: SQLiteStore, project_id: str, package: DraftPackage) -> OfficialCompileRun:
    current_source_hash = source_draft_hash(package)
    quality_state = _current_quality_gate_state(store, project_id, current_source_hash)
    if quality_state["quality_required"]:
        raise HTTPException(
            status_code=409,
            detail=_quality_gate_error_detail(quality_state),
        )
    latest_compile_attempt = _latest_official_compile_attempt_for_source(store, project_id, current_source_hash)
    compile_run = latest_compile_attempt
    if not _official_compile_export_ready(compile_run, current_source_hash):
        raise HTTPException(
            status_code=409,
            detail=_official_compile_gate_error_detail(latest_compile_attempt),
        )
    matching_review_attempt = _latest_matching_post_draft_review_attempt(
        store, project_id, current_source_hash, compile_run
    )
    latest_matching_review = _latest_completed_matching_post_draft_review(
        store, project_id, current_source_hash, compile_run
    )
    review_ready = _post_draft_review_export_ready(matching_review_attempt)
    if not review_ready:
        raise HTTPException(
            status_code=409,
            detail=_post_draft_review_gate_error_detail(matching_review_attempt or latest_matching_review),
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
    decision_providers = list(dict.fromkeys(run.providers))
    if len(decision_providers) < DELIBERATION_EXPERT_SEAT_COUNT:
        return False
    if DELIBERATION_CHAIR_PROVIDER not in decision_providers:
        return False
    completed = {(stage.phase, stage.provider_id, stage.label) for stage in run.stage_results if stage.status == "completed"}
    if not all(("opening", provider, f"opening {provider}") in completed for provider in decision_providers):
        return False
    pair_labels = {f"pair {provider_a}-vs-{provider_b}" for provider_a, provider_b in combinations(decision_providers, 2)}
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


def _selectable_agent_provider_ids(doctor: AgentDoctorReport) -> set[str]:
    return (
        set(doctor.active_provider_ids)
        | set(doctor.unknown_required)
        | {provider_id for provider_id, status in doctor.commands.items() if status.selectable}
    )


def _agent_provider_unavailable_reason(doctor: AgentDoctorReport, provider_id: str) -> str:
    status = doctor.commands.get(provider_id)
    if status is None or not status.installed:
        return "provider_missing"
    return status.auth_status or "provider_unavailable"


def _agent_provider_unavailable_detail(doctor: AgentDoctorReport, provider_id: str) -> str:
    status = doctor.commands.get(provider_id)
    if status is None:
        return f"{provider_id} provider is not registered in the agent doctor report."
    if status.diagnostic:
        return status.diagnostic
    if not status.installed:
        return f"{provider_id} CLI is not available in PATH or is not usable by the backend process."
    return f"{provider_id} CLI auth_status={status.auth_status}; it is not selectable for this run."


def _agent_provider_repair_suggestion(doctor: AgentDoctorReport, provider_id: str) -> str:
    status = doctor.commands.get(provider_id)
    if status is not None and status.repair_suggestion:
        return status.repair_suggestion
    return repair_suggestion_for_failure(_agent_provider_unavailable_reason(doctor, provider_id), provider_id)


def _deliberation_provider_plan(
    doctor: AgentDoctorReport,
    requested: list[str] | None,
    participant_requested: list[str] | None,
    *,
    auto_fill_missing: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    eligible = {
        provider_id
        for provider_id, status in doctor.commands.items()
        if status.installed and status.selectable and ("deliberation" in status.roles or provider_id == DELIBERATION_CHAIR_PROVIDER)
    }
    ordered_candidates = [
        provider_id
        for provider_id, status in doctor.commands.items()
        if ("deliberation" in status.roles or provider_id == DELIBERATION_CHAIR_PROVIDER) and status.installed
    ]
    requested_order = _dedupe_provider_ids(requested or ordered_candidates)
    warnings: list[str] = []

    providers: list[str] = []
    if DELIBERATION_CHAIR_PROVIDER in eligible:
        providers.append(DELIBERATION_CHAIR_PROVIDER)
    else:
        warnings.append(_provider_plan_warning(doctor, DELIBERATION_CHAIR_PROVIDER))

    overflow: list[str] = []
    for provider_id in requested_order:
        if provider_id == DELIBERATION_CHAIR_PROVIDER:
            continue
        if provider_id not in ordered_candidates:
            continue
        if provider_id not in eligible:
            warnings.append(_provider_plan_warning(doctor, provider_id))
            continue
        if len(providers) < DELIBERATION_EXPERT_SEAT_COUNT:
            providers.append(provider_id)
        else:
            overflow.append(provider_id)

    if auto_fill_missing and len(providers) < DELIBERATION_EXPERT_SEAT_COUNT:
        for provider_id in ordered_candidates:
            if provider_id == DELIBERATION_CHAIR_PROVIDER or provider_id in providers:
                continue
            if provider_id not in eligible:
                continue
            providers.append(provider_id)
            if len(providers) >= DELIBERATION_EXPERT_SEAT_COUNT:
                break

    participant_source = _dedupe_provider_ids([*(participant_requested or []), *overflow])
    participants: list[str] = []
    for provider_id in participant_source:
        if provider_id in providers or provider_id not in ordered_candidates:
            continue
        if provider_id not in eligible:
            if participant_requested and provider_id in participant_requested:
                warnings.append(_provider_plan_warning(doctor, provider_id))
            continue
        participants.append(provider_id)

    return providers, participants, _dedupe_provider_ids(warnings)


def _post_draft_review_provider_plan(
    requested: list[str] | None,
    participant_requested: list[str] | None,
) -> tuple[list[str], list[str]]:
    requested_order = _dedupe_provider_ids(list(requested or STRICT_DELIBERATION_PROVIDERS))
    providers: list[str] = []
    overflow: list[str] = []

    if DELIBERATION_CHAIR_PROVIDER in requested_order:
        providers.append(DELIBERATION_CHAIR_PROVIDER)

    for provider_id in requested_order:
        if provider_id == DELIBERATION_CHAIR_PROVIDER:
            continue
        if len(providers) < DELIBERATION_EXPERT_SEAT_COUNT:
            providers.append(provider_id)
        else:
            overflow.append(provider_id)

    participant_source = _dedupe_provider_ids([*(participant_requested or []), *overflow])
    participants = [provider_id for provider_id in participant_source if provider_id not in providers]
    return providers, participants


def _blocked_post_draft_review_for_seats(
    *,
    store: SQLiteStore,
    project_id: str,
    package: OfficialDraftPackage,
    providers: list[str],
    participant_providers: list[str],
    official_compile_run_id: str,
    retry_of: str | None,
) -> PostDraftReviewRun | None:
    chair_missing = DELIBERATION_CHAIR_PROVIDER not in providers
    if len(providers) >= DELIBERATION_EXPERT_SEAT_COUNT and not chair_missing:
        return None

    reason = "chair_unavailable" if chair_missing else "insufficient_experts"
    message = (
        "Codex chair is required for post-draft review."
        if chair_missing
        else "Not enough expert seats are ready for post-draft review."
    )
    detail = (
        f"Codex 主席不可用，无法启动成稿会审；当前决策专家为 {len(providers)} 席：{', '.join(providers) or '无'}。"
        if chair_missing
        else f"至少 {DELIBERATION_EXPERT_SEAT_COUNT} 席决策专家才能启动成稿会审；当前为 {len(providers)} 席：{', '.join(providers) or '无'}。"
    )
    repair_suggestion = (
        "请在成稿会审卡片中保留 Codex 主席，并另外选择 2 个可用专家。"
        if chair_missing
        else "请在成稿会审卡片中选择 Codex 主席之外的 2 个可用专家。"
    )
    run = PostDraftReviewRun(
        id=uuid.uuid4().hex,
        project_id=project_id,
        status="failed",
        providers=providers,
        participant_providers=participant_providers,
        draft_package_hash=package.source_draft_hash,
        official_compile_run_id=official_compile_run_id,
        official_package_hash=package_hash_for_review(package),
        blocking_issues=[detail],
        logs=[
            DeliberationLogEntry(
                level="error",
                phase="doctor",
                provider_id=DELIBERATION_CHAIR_PROVIDER,
                message=reason.replace("_", " "),
                detail=detail,
                repair_suggestion=repair_suggestion,
            )
        ],
        failure_details=[
            RuntimeFailure(
                flow="post_draft_review",
                stage="doctor",
                provider=DELIBERATION_CHAIR_PROVIDER,
                reason=reason,
                message=message,
                repair_suggestion=repair_suggestion,
            )
        ],
        retry_of=retry_of,
    )
    return store.create_post_draft_review_run(run)


def _provider_plan_warning(doctor: AgentDoctorReport, provider_id: str) -> str:
    status = doctor.commands.get(provider_id)
    if status is None:
        return f"{provider_id} 未注册，已跳过。"
    if status.diagnostic:
        return f"{provider_id} 不可用于会审：{status.diagnostic}"
    if not status.installed:
        return f"{provider_id} 未安装，已跳过。"
    return f"{provider_id} auth_status={status.auth_status}，已跳过。"


def _dedupe_provider_ids(provider_ids: list[str]) -> list[str]:
    deduped: list[str] = []
    for provider_id in provider_ids:
        if provider_id and provider_id not in deduped:
            deduped.append(provider_id)
    return deduped


def _completion_run_with_progress_score(run: DraftCompletionRun) -> DraftCompletionRun:
    baseline = run.scorecard_baseline or run.scorecard
    accepted_task_ids = {patch.task_id for patch in run.patches if patch.status == "accepted"}
    accepted_issue_ids = {
        task.issue_id
        for task in run.tasks
        if task.status == "accepted" or task.id in accepted_task_ids
    }
    resolved_issues = [issue for issue in run.issues if issue.id in accepted_issue_ids]
    if not resolved_issues:
        return run.model_copy(update={"scorecard": baseline, "scorecard_baseline": run.scorecard_baseline})

    severity_weight = {"high": 3, "medium": 2, "low": 1}
    total_weight = sum(severity_weight.get(issue.severity, 1) for issue in resolved_issues)
    support_weight = sum(
        severity_weight.get(issue.severity, 1)
        for issue in resolved_issues
        if issue.category in {"claim_support_gap", "specification_sufficiency_gap", "term_definition_gap"}
    )
    scope_weight = sum(
        severity_weight.get(issue.severity, 1)
        for issue in resolved_issues
        if issue.category in {"claim_support_gap", "claim_scope_risk", "specification_sufficiency_gap"}
    )
    hygiene_weight = sum(
        severity_weight.get(issue.severity, 1)
        for issue in resolved_issues
        if issue.category in {"format_pollution", "unfavorable_statement", "subject_matter_risk"}
    )
    prior_art_weight = sum(
        severity_weight.get(issue.severity, 1)
        for issue in resolved_issues
        if issue.category == "prior_art_distinction_gap"
    )

    authorization = _bounded_score(baseline.authorization_stability + min(24, total_weight * 4))
    protection = _bounded_score(baseline.protection_scope + min(24, max(scope_weight, support_weight, total_weight) * 3))
    support = _bounded_score(baseline.support_strength + min(24, support_weight * 5))
    hygiene = _bounded_score(baseline.official_hygiene + min(24, hygiene_weight * 6))
    prior_art = _bounded_score(baseline.prior_art_distinction + min(18, prior_art_weight * 6))
    filing = _bounded_score(round((authorization + support + hygiene) / 3))
    overall = _bounded_score(round((authorization + protection + support + prior_art + filing + hygiene) / 6))
    notes = _completion_progress_notes(run.notes)

    return run.model_copy(
        update={
            "scorecard": CompletionScoreCard(
                authorization_stability=authorization,
                protection_scope=protection,
                support_strength=support,
                prior_art_distinction=prior_art,
                filing_maturity=filing,
                official_hygiene=hygiene,
                overall=overall,
            ),
            "scorecard_baseline": baseline,
            "notes": notes,
        }
    )


def _completion_progress_notes(notes: list[str]) -> list[str]:
    progress_note = "accepted completion patches update this run's scorecard; rerun quality checks for a full re-analysis."
    if progress_note in notes:
        return notes
    return [*notes, progress_note]


def _bounded_score(value: int) -> int:
    return max(0, min(100, value))


def _run_mode(active_count: int) -> str:
    if active_count >= 3:
        return "full"
    if active_count == 2:
        return "partial"
    if active_count == 1:
        return "minimal"
    return "blocked"


_repair_patches: dict[str, DraftRepairPatch] = {}


def _repair_patch_store() -> dict[str, DraftRepairPatch]:
    return _repair_patches


app = create_app()
