from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from backend.app.schemas import (
    ClaimDefenseWorksheet,
    CorpusImportJob,
    CorpusQualityReport,
    CorpusVersion,
    DeliberationRun,
    DisclosureRun,
    DraftCompletionRun,
    DraftPackage,
    ExternalDraftIntakeRun,
    ExternalDraftSource,
    FilingReadinessReport,
    FormulaRun,
    GenerateRun,
    OfficialCompileRun,
    OfficialDraftPackage,
    PatentAsset,
    PatentChunk,
    PatentPointCandidate,
    PatentDocument,
    PatentType,
    PostDraftReviewRun,
    ProjectMaterial,
    ProjectRecord,
    SectionType,
)


def _patent_type_to_db(value: PatentType | str | None) -> str:
    """Normalize a patent-type value to its on-disk string form.

    Accepts a :class:`PatentType` enum, a raw ``"invention"``/``"utility_model"``
    string (e.g. from a hand-rolled DB row), or ``None`` (treated as the
    invention default). Unknown strings round-trip as ``"invention"`` so
    legacy rows created before the field existed do not crash callers.
    """

    if value is None:
        return PatentType.INVENTION.value
    if isinstance(value, PatentType):
        return value.value
    try:
        return PatentType(value).value
    except ValueError:
        return PatentType.INVENTION.value


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        raw_connection = sqlite3.connect(path, check_same_thread=False)
        raw_connection.row_factory = sqlite3.Row
        self.connection = _LockedConnection(raw_connection, self._lock)
        self._migrate()

    def add_document(self, document: PatentDocument, chunks: list[PatentChunk]) -> None:
        with self.connection:
            self.connection.execute(
                """
                insert or replace into documents(id, title, source_name, text, metadata_json, sections_json)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.source_name,
                    document.text,
                    json.dumps(document.metadata, ensure_ascii=False),
                    json.dumps([section.model_dump(mode="json") for section in document.sections], ensure_ascii=False),
                ),
            )
            self.connection.executemany(
                """
                insert or replace into chunks(id, document_id, section_type, text, ordinal, metadata_json)
                values (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.section_type.value,
                        chunk.text,
                        chunk.ordinal,
                        json.dumps(chunk.metadata, ensure_ascii=False),
                    )
                    for chunk in chunks
                ],
            )

    def list_documents(self) -> list[PatentDocument]:
        rows = self.connection.execute("select * from documents order by created_at desc").fetchall()
        return [self._document_from_row(row) for row in rows]

    def get_document(self, document_id: str) -> PatentDocument | None:
        row = self.connection.execute("select * from documents where id = ?", (document_id,)).fetchone()
        return self._document_from_row(row) if row else None

    def list_chunks(self) -> list[PatentChunk]:
        rows = self.connection.execute("select * from chunks order by ordinal asc").fetchall()
        return [self._chunk_from_row(row) for row in rows]

    def find_duplicate_document(self, metadata: dict[str, Any], content_hash: str) -> PatentDocument | None:
        incoming_version = str(metadata.get("version_name", "")).strip()
        incoming_numbers = {
            key: str(metadata.get(key, "")).strip().upper()
            for key in ["grant_number", "publication_number", "application_number"]
            if str(metadata.get(key, "")).strip()
        }
        incoming_title = str(metadata.get("title", "")).strip()
        incoming_applicants = "|".join(str(value) for value in metadata.get("applicants", []) or [])
        incoming_date = str(metadata.get("application_date", "")).strip()
        for document in self.list_documents():
            doc_meta = document.metadata
            if incoming_version and str(doc_meta.get("version_name", "")).strip() != incoming_version:
                continue
            for key, value in incoming_numbers.items():
                if str(doc_meta.get(key, "")).strip().upper() == value:
                    return document
            if content_hash and str(doc_meta.get("content_hash", "")) == content_hash:
                return document
            doc_title = str(doc_meta.get("title", "") or document.title).strip()
            doc_applicants = "|".join(str(value) for value in doc_meta.get("applicants", []) or [])
            doc_date = str(doc_meta.get("application_date", "")).strip()
            if incoming_title and incoming_title == doc_title and incoming_applicants == doc_applicants and incoming_date == doc_date:
                return document
        return None

    def create_corpus_job(self, job: CorpusImportJob) -> CorpusImportJob:
        with self.connection:
            self.connection.execute(
                """
                insert into corpus_jobs(
                    id, source_type, source_name, query, domain, version_name, status,
                    input_paths_json, total_files, processed_files, imported_documents,
                    duplicate_documents, filtered_documents, failed_documents, errors_json,
                    quality_report_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._corpus_job_values(job),
            )
        return job

    def update_corpus_job(self, job: CorpusImportJob) -> None:
        with self.connection:
            self.connection.execute(
                """
                update corpus_jobs
                set source_type = ?, source_name = ?, query = ?, domain = ?, version_name = ?,
                    status = ?, input_paths_json = ?, total_files = ?, processed_files = ?,
                    imported_documents = ?, duplicate_documents = ?, filtered_documents = ?,
                    failed_documents = ?, errors_json = ?, quality_report_json = ?,
                    updated_at = current_timestamp
                where id = ?
                """,
                (
                    job.source_type,
                    job.source_name,
                    job.query,
                    job.domain,
                    job.version_name,
                    job.status,
                    json.dumps(job.input_paths, ensure_ascii=False),
                    job.total_files,
                    job.processed_files,
                    job.imported_documents,
                    job.duplicate_documents,
                    job.filtered_documents,
                    job.failed_documents,
                    json.dumps(job.errors, ensure_ascii=False),
                    json.dumps(job.quality_report.model_dump(mode="json"), ensure_ascii=False)
                    if job.quality_report
                    else None,
                    job.id,
                ),
            )

    def get_corpus_job(self, job_id: str) -> CorpusImportJob | None:
        row = self.connection.execute("select * from corpus_jobs where id = ?", (job_id,)).fetchone()
        return self._corpus_job_from_row(row) if row else None

    def list_corpus_jobs(self) -> list[CorpusImportJob]:
        rows = self.connection.execute("select * from corpus_jobs order by updated_at desc").fetchall()
        return [self._corpus_job_from_row(row) for row in rows]

    def add_patent_asset(self, asset: PatentAsset) -> PatentAsset:
        with self.connection:
            self.connection.execute(
                """
                insert or replace into patent_assets(
                    id, job_id, file_name, path, file_type, status, document_id, error, metadata_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.id,
                    asset.job_id,
                    asset.file_name,
                    asset.path,
                    asset.file_type,
                    asset.status,
                    asset.document_id,
                    asset.error,
                    json.dumps(asset.metadata, ensure_ascii=False),
                ),
            )
        return asset

    def upsert_corpus_version(self, version: CorpusVersion) -> CorpusVersion:
        with self.connection:
            self.connection.execute(
                """
                insert into corpus_versions(
                    id, name, domain, source_type, source_name, query,
                    document_count, chunk_count, quality_report_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(name) do update set
                    domain = excluded.domain,
                    source_type = excluded.source_type,
                    source_name = excluded.source_name,
                    query = excluded.query,
                    document_count = excluded.document_count,
                    chunk_count = excluded.chunk_count,
                    quality_report_json = excluded.quality_report_json,
                    updated_at = current_timestamp
                """,
                (
                    version.id,
                    version.name,
                    version.domain,
                    version.source_type,
                    version.source_name,
                    version.query,
                    version.document_count,
                    version.chunk_count,
                    json.dumps(version.quality_report.model_dump(mode="json"), ensure_ascii=False)
                    if version.quality_report
                    else None,
                ),
            )
        return version

    def list_corpus_versions(self) -> list[CorpusVersion]:
        rows = self.connection.execute("select * from corpus_versions order by updated_at desc").fetchall()
        return [self._corpus_version_from_row(row) for row in rows]

    def get_corpus_stats(self, version_name: str | None = None) -> dict[str, Any]:
        documents = self.list_documents()
        if version_name:
            documents = [document for document in documents if document.metadata.get("version_name") == version_name]
        document_ids = {document.id for document in documents}
        chunks = [chunk for chunk in self.list_chunks() if chunk.document_id in document_ids]
        section_coverage = self._section_coverage(documents)
        ipc_distribution: dict[str, int] = {}
        year_distribution: dict[str, int] = {}
        source_distribution: dict[str, int] = {}
        for document in documents:
            for ipc in _as_list(document.metadata.get("ipc")):
                prefix = str(ipc).strip().upper().replace(" ", "")[:4]
                if prefix:
                    ipc_distribution[prefix] = ipc_distribution.get(prefix, 0) + 1
            year = str(document.metadata.get("application_date", ""))[:4]
            if year.isdigit():
                year_distribution[year] = year_distribution.get(year, 0) + 1
            source = str(document.metadata.get("source_name") or document.source_name or "unknown")
            source_distribution[source] = source_distribution.get(source, 0) + 1
        return {
            "version_name": version_name,
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "document_ids": [document.id for document in documents],
            "section_coverage": section_coverage,
            "ipc_distribution": ipc_distribution,
            "application_year_distribution": year_distribution,
            "source_distribution": source_distribution,
        }

    def create_project(self, project: ProjectRecord) -> ProjectRecord:
        with self.connection:
            self.connection.execute(
                """
                insert into projects(id, name, draft_text, patent_type, package_json)
                values (?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.name,
                    project.draft_text,
                    _patent_type_to_db(project.patent_type),
                    json.dumps(project.package.model_dump(mode="json"), ensure_ascii=False)
                    if project.package
                    else None,
                ),
            )
        return self.get_project(project.id) or project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        row = self.connection.execute("select * from projects where id = ?", (project_id,)).fetchone()
        return self._project_from_row(row) if row else None

    def list_projects(self) -> list[ProjectRecord]:
        rows = self.connection.execute("select * from projects order by updated_at desc").fetchall()
        return [self._project_from_row(row) for row in rows]

    def delete_project(self, project_id: str) -> bool:
        with self.connection:
            for table in [
                "project_materials",
                "project_patent_points",
                "disclosure_runs",
                "deliberation_runs",
                "formula_runs",
                "generate_runs",
                "external_draft_intake_runs",
                "external_draft_sources",
                "official_compile_runs",
                "post_draft_review_runs",
                "filing_readiness_reports",
                "claim_defense_worksheets",
                "draft_completion_runs",
            ]:
                self.connection.execute(f"delete from {table} where project_id = ?", (project_id,))
            cursor = self.connection.execute("delete from projects where id = ?", (project_id,))
        return cursor.rowcount > 0

    def update_project_package(self, project_id: str, package: DraftPackage) -> None:
        with self.connection:
            self.connection.execute(
                """
                update projects
                set package_json = ?, updated_at = current_timestamp
                where id = ?
                """,
                (json.dumps(package.model_dump(mode="json"), ensure_ascii=False), project_id),
            )

    def create_external_draft_source(self, source: ExternalDraftSource) -> ExternalDraftSource:
        with self.connection:
            self.connection.execute(
                """
                insert into external_draft_sources(
                    id, project_id, source_type, file_name, content_hash, raw_text, raw_path, metadata_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.project_id,
                    source.source_type,
                    source.file_name,
                    source.content_hash,
                    source.raw_text,
                    source.raw_path,
                    json.dumps(source.metadata, ensure_ascii=False),
                ),
            )
        return self.get_external_draft_source(source.project_id, source.id) or source

    def list_external_draft_sources(self, project_id: str) -> list[ExternalDraftSource]:
        rows = self.connection.execute(
            "select * from external_draft_sources where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._external_draft_source_from_row(row) for row in rows]

    def get_external_draft_source(self, project_id: str, source_id: str) -> ExternalDraftSource | None:
        row = self.connection.execute(
            "select * from external_draft_sources where project_id = ? and id = ?",
            (project_id, source_id),
        ).fetchone()
        return self._external_draft_source_from_row(row) if row else None

    def create_external_draft_intake_run(self, run: ExternalDraftIntakeRun) -> ExternalDraftIntakeRun:
        with self.connection:
            self.connection.execute(
                """
                insert into external_draft_intake_runs(
                    id, project_id, source_id, status, parser_version, source_hash,
                    parsed_package_json, section_confidence_json, intake_issues_json,
                    unassigned_fragments_json, working_draft_hash, logs_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._external_draft_intake_run_values(run),
            )
        return self.get_external_draft_intake_run(run.project_id, run.id) or run

    def list_external_draft_intake_runs(
        self, project_id: str, source_id: str | None = None
    ) -> list[ExternalDraftIntakeRun]:
        if source_id:
            rows = self.connection.execute(
                """
                select * from external_draft_intake_runs
                where project_id = ? and source_id = ?
                order by created_at desc, rowid desc
                """,
                (project_id, source_id),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "select * from external_draft_intake_runs where project_id = ? order by created_at desc, rowid desc",
                (project_id,),
            ).fetchall()
        return [self._external_draft_intake_run_from_row(row) for row in rows]

    def get_external_draft_intake_run(self, project_id: str, run_id: str) -> ExternalDraftIntakeRun | None:
        row = self.connection.execute(
            "select * from external_draft_intake_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._external_draft_intake_run_from_row(row) if row else None

    def update_external_draft_intake_run(self, run: ExternalDraftIntakeRun) -> ExternalDraftIntakeRun | None:
        with self.connection:
            cursor = self.connection.execute(
                """
                update external_draft_intake_runs
                set status = ?, parser_version = ?, source_hash = ?, parsed_package_json = ?,
                    section_confidence_json = ?, intake_issues_json = ?, unassigned_fragments_json = ?,
                    working_draft_hash = ?, logs_json = ?
                where project_id = ? and id = ?
                """,
                (
                    run.status,
                    run.parser_version,
                    run.source_hash,
                    json.dumps(run.parsed_package.model_dump(mode="json"), ensure_ascii=False)
                    if run.parsed_package
                    else None,
                    json.dumps(run.section_confidence.model_dump(mode="json"), ensure_ascii=False)
                    if run.section_confidence
                    else None,
                    json.dumps([issue.model_dump(mode="json") for issue in run.intake_issues], ensure_ascii=False),
                    json.dumps(run.unassigned_fragments, ensure_ascii=False),
                    run.working_draft_hash,
                    json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
                    run.project_id,
                    run.id,
                ),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_external_draft_intake_run(run.project_id, run.id)

    def create_filing_readiness_report(self, report: FilingReadinessReport) -> FilingReadinessReport:
        with self.connection:
            self.connection.execute(
                """
                insert into filing_readiness_reports(id, project_id, report_json)
                values (?, ?, ?)
                """,
                (
                    report.id,
                    report.project_id,
                    json.dumps(report.model_dump(mode="json"), ensure_ascii=False),
                ),
            )
        return report

    def list_filing_readiness_reports(self, project_id: str) -> list[FilingReadinessReport]:
        rows = self.connection.execute(
            "select * from filing_readiness_reports where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._filing_readiness_report_from_row(row) for row in rows]

    def get_filing_readiness_report(self, project_id: str, report_id: str) -> FilingReadinessReport | None:
        row = self.connection.execute(
            "select * from filing_readiness_reports where project_id = ? and id = ?",
            (project_id, report_id),
        ).fetchone()
        return self._filing_readiness_report_from_row(row) if row else None

    def create_claim_defense_worksheet(self, worksheet: ClaimDefenseWorksheet) -> ClaimDefenseWorksheet:
        with self.connection:
            self.connection.execute(
                """
                insert into claim_defense_worksheets(id, project_id, worksheet_json)
                values (?, ?, ?)
                """,
                (
                    worksheet.id,
                    worksheet.project_id,
                    json.dumps(worksheet.model_dump(mode="json"), ensure_ascii=False),
                ),
            )
        return worksheet

    def list_claim_defense_worksheets(self, project_id: str) -> list[ClaimDefenseWorksheet]:
        rows = self.connection.execute(
            "select * from claim_defense_worksheets where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._claim_defense_worksheet_from_row(row) for row in rows]

    def get_claim_defense_worksheet(self, project_id: str, worksheet_id: str) -> ClaimDefenseWorksheet | None:
        row = self.connection.execute(
            "select * from claim_defense_worksheets where project_id = ? and id = ?",
            (project_id, worksheet_id),
        ).fetchone()
        return self._claim_defense_worksheet_from_row(row) if row else None

    def create_draft_completion_run(self, run: DraftCompletionRun) -> DraftCompletionRun:
        with self.connection:
            self.connection.execute(
                """
                insert into draft_completion_runs(id, project_id, run_json)
                values (?, ?, ?)
                """,
                (
                    run.id,
                    run.project_id,
                    json.dumps(run.model_dump(mode="json"), ensure_ascii=False),
                ),
            )
        return run

    def list_draft_completion_runs(self, project_id: str) -> list[DraftCompletionRun]:
        rows = self.connection.execute(
            "select * from draft_completion_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._draft_completion_run_from_row(row) for row in rows]

    def get_draft_completion_run(self, project_id: str, run_id: str) -> DraftCompletionRun | None:
        row = self.connection.execute(
            "select * from draft_completion_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._draft_completion_run_from_row(row) if row else None

    def update_draft_completion_run(self, run: DraftCompletionRun) -> DraftCompletionRun | None:
        with self.connection:
            cursor = self.connection.execute(
                """
                update draft_completion_runs
                set run_json = ?
                where project_id = ? and id = ?
                """,
                (
                    json.dumps(run.model_dump(mode="json"), ensure_ascii=False),
                    run.project_id,
                    run.id,
                ),
            )
        if cursor.rowcount == 0:
            return None
        return self.get_draft_completion_run(run.project_id, run.id) or run

    def get_llm_stage_cache(self, cache_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            select * from llm_stage_cache
            where cache_key = ?
                and (expires_at is null or expires_at = '' or datetime(expires_at) > datetime('now'))
            """,
            (cache_key,),
        ).fetchone()
        return dict(row) if row else None

    def put_llm_stage_cache(
        self,
        *,
        cache_key: str,
        project_id: str,
        stage: str,
        model: str,
        prompt_hash: str,
        input_hash: str,
        prompt_pack_version: str,
        response_text: str,
        response_json: str | None = None,
        status: str = "completed",
        expires_at: str | None = None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                insert or replace into llm_stage_cache(
                    cache_key, project_id, stage, model, prompt_hash, input_hash,
                    prompt_pack_version, response_text, response_json, status, expires_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    project_id,
                    stage,
                    model,
                    prompt_hash,
                    input_hash,
                    prompt_pack_version,
                    response_text,
                    response_json,
                    status,
                    expires_at,
                ),
            )

    def clear_project_llm_cache(self, project_id: str) -> int:
        with self.connection:
            cursor = self.connection.execute("delete from llm_stage_cache where project_id = ?", (project_id,))
        return cursor.rowcount

    def create_formula_run(self, run: FormulaRun) -> FormulaRun:
        with self.connection:
            self.connection.execute(
                """
                insert into formula_runs(
                    id, project_id, status, providers_json, requirement_json, package_json,
                    failures_json, events_json, runtime_state_json, failure_details_json,
                    cancel_requested, retry_of
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._formula_run_values(run),
            )
        return run

    def update_formula_run(self, run: FormulaRun) -> None:
        with self.connection:
            self.connection.execute(
                """
                update formula_runs
                set status = ?, providers_json = ?, requirement_json = ?, package_json = ?,
                    failures_json = ?, events_json = ?, runtime_state_json = ?,
                    failure_details_json = ?, cancel_requested = ?, retry_of = ?,
                    updated_at = current_timestamp
                where id = ? and project_id = ?
                """,
                (
                    run.status,
                    json.dumps(run.providers, ensure_ascii=False),
                    json.dumps(run.requirement.model_dump(mode="json"), ensure_ascii=False),
                    json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False) if run.package else None,
                    json.dumps(run.failures, ensure_ascii=False),
                    json.dumps(run.events, ensure_ascii=False),
                    json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False)
                    if run.runtime_state
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
                    1 if run.cancel_requested else 0,
                    run.retry_of or "",
                    run.id,
                    run.project_id,
                ),
            )

    def list_formula_runs(self, project_id: str) -> list[FormulaRun]:
        rows = self.connection.execute(
            "select * from formula_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._formula_run_from_row(row) for row in rows]

    def get_formula_run(self, project_id: str, run_id: str) -> FormulaRun | None:
        row = self.connection.execute(
            "select * from formula_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._formula_run_from_row(row) if row else None

    def get_latest_completed_formula_run(self, project_id: str) -> FormulaRun | None:
        row = self.connection.execute(
            """
            select * from formula_runs
            where project_id = ? and status = 'completed'
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._formula_run_from_row(row) if row else None

    def create_generate_run(self, run: GenerateRun) -> GenerateRun:
        with self.connection:
            self.connection.execute(
                """
                insert into generate_runs(
                    id, project_id, status, providers_json, deliberation_run_id, formula_run_id,
                    package_json, failures_json, events_json, runtime_state_json,
                    failure_details_json, cancel_requested, retry_of
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._generate_run_values(run),
            )
        return self.get_generate_run(run.project_id, run.id) or run

    def update_generate_run(self, run: GenerateRun) -> None:
        with self.connection:
            self.connection.execute(
                """
                update generate_runs
                set status = ?, providers_json = ?, deliberation_run_id = ?, formula_run_id = ?,
                    package_json = ?, failures_json = ?, events_json = ?, runtime_state_json = ?,
                    failure_details_json = ?, cancel_requested = ?, retry_of = ?,
                    updated_at = current_timestamp
                where id = ? and project_id = ?
                """,
                (
                    run.status,
                    json.dumps(run.providers, ensure_ascii=False),
                    run.deliberation_run_id or "",
                    run.formula_run_id or "",
                    json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False)
                    if run.package
                    else None,
                    json.dumps(run.failures, ensure_ascii=False),
                    json.dumps(run.events, ensure_ascii=False),
                    json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False)
                    if run.runtime_state
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
                    1 if run.cancel_requested else 0,
                    run.retry_of or "",
                    run.id,
                    run.project_id,
                ),
            )

    def list_generate_runs(self, project_id: str) -> list[GenerateRun]:
        rows = self.connection.execute(
            "select * from generate_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._generate_run_from_row(row) for row in rows]

    def get_generate_run(self, project_id: str, run_id: str) -> GenerateRun | None:
        row = self.connection.execute(
            "select * from generate_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._generate_run_from_row(row) if row else None

    def get_active_generate_run(self, project_id: str) -> GenerateRun | None:
        row = self.connection.execute(
            """
            select * from generate_runs
            where project_id = ? and status in ('queued', 'running')
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._generate_run_from_row(row) if row else None

    def get_latest_completed_generate_run(self, project_id: str) -> GenerateRun | None:
        row = self.connection.execute(
            """
            select * from generate_runs
            where project_id = ? and status = 'completed'
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._generate_run_from_row(row) if row else None

    def create_post_draft_review_run(self, run: PostDraftReviewRun) -> PostDraftReviewRun:
        with self.connection:
            self.connection.execute(
                """
                insert into post_draft_review_runs(
                    id, project_id, status, providers_json, prompt_pack_version, draft_package_hash,
                    official_compile_run_id, official_package_hash, role_results_json, chair_result_json,
                    export_allowed, blocking_issues_json, contamination_hits_json, logs_json,
                    runtime_state_json, failure_details_json, cancel_requested, retry_of
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._post_draft_review_run_values(run),
            )
        return self.get_post_draft_review_run(run.project_id, run.id) or run

    def update_post_draft_review_run(self, run: PostDraftReviewRun) -> None:
        with self.connection:
            self.connection.execute(
                """
                update post_draft_review_runs
                set status = ?, providers_json = ?, prompt_pack_version = ?, draft_package_hash = ?,
                    official_compile_run_id = ?, official_package_hash = ?, role_results_json = ?,
                    chair_result_json = ?, export_allowed = ?, blocking_issues_json = ?,
                    contamination_hits_json = ?, logs_json = ?, runtime_state_json = ?,
                    failure_details_json = ?, cancel_requested = ?, retry_of = ?,
                    updated_at = current_timestamp
                where id = ? and project_id = ?
                """,
                (
                    run.status,
                    json.dumps(run.providers, ensure_ascii=False),
                    run.prompt_pack_version,
                    run.draft_package_hash,
                    run.official_compile_run_id,
                    run.official_package_hash,
                    json.dumps([result.model_dump(mode="json") for result in run.role_results], ensure_ascii=False),
                    json.dumps(run.chair_result.model_dump(mode="json"), ensure_ascii=False) if run.chair_result else None,
                    1 if run.export_allowed else 0,
                    json.dumps(run.blocking_issues, ensure_ascii=False),
                    json.dumps(run.contamination_hits, ensure_ascii=False),
                    json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
                    json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False)
                    if run.runtime_state
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
                    1 if run.cancel_requested else 0,
                    run.retry_of or "",
                    run.id,
                    run.project_id,
                ),
            )

    def list_post_draft_review_runs(self, project_id: str) -> list[PostDraftReviewRun]:
        rows = self.connection.execute(
            "select * from post_draft_review_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._post_draft_review_run_from_row(row) for row in rows]

    def get_post_draft_review_run(self, project_id: str, run_id: str) -> PostDraftReviewRun | None:
        row = self.connection.execute(
            "select * from post_draft_review_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._post_draft_review_run_from_row(row) if row else None

    def get_latest_export_allowed_post_draft_review(
        self, project_id: str, draft_package_hash: str
    ) -> PostDraftReviewRun | None:
        row = self.connection.execute(
            """
            select * from post_draft_review_runs
            where project_id = ?
                and draft_package_hash = ?
                and status = 'completed'
                and export_allowed = 1
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id, draft_package_hash),
        ).fetchone()
        return self._post_draft_review_run_from_row(row) if row else None

    def create_official_compile_run(self, run: OfficialCompileRun) -> OfficialCompileRun:
        with self.connection:
            self.connection.execute(
                """
                insert into official_compile_runs(
                    id, project_id, status, source_draft_hash, official_package_hash,
                    official_package_json, contamination_removed_json, blocked_items_json,
                    sidecar_notes_json, logs_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._official_compile_run_values(run),
            )
        return self.get_official_compile_run(run.project_id, run.id) or run

    def list_official_compile_runs(self, project_id: str) -> list[OfficialCompileRun]:
        rows = self.connection.execute(
            "select * from official_compile_runs where project_id = ? order by created_at desc, rowid desc",
            (project_id,),
        ).fetchall()
        return [self._official_compile_run_from_row(row) for row in rows]

    def get_official_compile_run(self, project_id: str, run_id: str) -> OfficialCompileRun | None:
        row = self.connection.execute(
            "select * from official_compile_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._official_compile_run_from_row(row) if row else None

    def get_latest_completed_official_compile_run(self, project_id: str) -> OfficialCompileRun | None:
        row = self.connection.execute(
            """
            select * from official_compile_runs
            where project_id = ?
                and status = 'completed'
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._official_compile_run_from_row(row) if row else None

    def get_latest_completed_official_compile_run_for_hash(
        self, project_id: str, source_draft_hash: str
    ) -> OfficialCompileRun | None:
        row = self.connection.execute(
            """
            select * from official_compile_runs
            where project_id = ?
                and source_draft_hash = ?
                and status = 'completed'
            order by updated_at desc, rowid desc
            limit 1
            """,
            (project_id, source_draft_hash),
        ).fetchone()
        return self._official_compile_run_from_row(row) if row else None

    def update_completion_patch_status(
        self, project_id: str, run_id: str, patch_id: str, status: str
    ) -> DraftCompletionRun | None:
        with self.connection:
            row = self.connection.execute(
                "select * from draft_completion_runs where project_id = ? and id = ?",
                (project_id, run_id),
            ).fetchone()
            if not row:
                return None
            run = self._draft_completion_run_from_row(row)
            payload = run.model_dump(mode="json")
            found = False
            task_id = ""
            for patch in payload["patches"]:
                if patch["id"] == patch_id:
                    patch["status"] = status
                    task_id = patch["task_id"]
                    found = True
                    break
            if not found:
                return None
            if status in {"accepted", "rejected"}:
                for task in payload["tasks"]:
                    if task["id"] == task_id:
                        task["status"] = status
                        break
            updated = DraftCompletionRun.model_validate(payload)
            self.connection.execute(
                """
                update draft_completion_runs
                set run_json = ?
                where project_id = ? and id = ?
                """,
                (
                    json.dumps(updated.model_dump(mode="json"), ensure_ascii=False),
                    project_id,
                    run_id,
                ),
            )
        return updated

    def add_project_material(self, material: ProjectMaterial) -> ProjectMaterial:
        with self.connection:
            self.connection.execute(
                """
                insert or replace into project_materials(
                    id, project_id, file_name, path, file_type, text, status, warnings_json, metadata_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material.id,
                    material.project_id,
                    material.file_name,
                    material.path,
                    material.file_type,
                    material.text,
                    material.status,
                    json.dumps(material.warnings, ensure_ascii=False),
                    json.dumps(material.metadata, ensure_ascii=False),
                ),
            )
        return material

    def list_project_materials(self, project_id: str) -> list[ProjectMaterial]:
        rows = self.connection.execute(
            "select * from project_materials where project_id = ? order by created_at desc",
            (project_id,),
        ).fetchall()
        return [self._project_material_from_row(row) for row in rows]

    def add_project_patent_point(self, project_id: str, point: PatentPointCandidate) -> PatentPointCandidate:
        with self.connection:
            if point.selected:
                self.connection.execute("update project_patent_points set selected = 0 where project_id = ?", (project_id,))
            self.connection.execute(
                """
                insert into project_patent_points(id, project_id, candidate_json, selected, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                on conflict(project_id, id) do update set
                    candidate_json = excluded.candidate_json,
                    selected = excluded.selected,
                    updated_at = current_timestamp
                """,
                (
                    point.id,
                    project_id,
                    json.dumps(point.model_dump(mode="json"), ensure_ascii=False),
                    1 if point.selected else 0,
                ),
            )
        return point

    def list_project_patent_points(self, project_id: str) -> list[PatentPointCandidate]:
        rows = self.connection.execute(
            "select * from project_patent_points where project_id = ? order by selected desc, updated_at desc",
            (project_id,),
        ).fetchall()
        points: list[PatentPointCandidate] = []
        for row in rows:
            point = PatentPointCandidate(**json.loads(row["candidate_json"]))
            points.append(point.model_copy(update={"selected": bool(row["selected"])}))
        return points

    def get_project_patent_point(self, project_id: str, point_id: str) -> PatentPointCandidate | None:
        row = self.connection.execute(
            "select * from project_patent_points where project_id = ? and id = ?",
            (project_id, point_id),
        ).fetchone()
        if not row:
            return None
        point = PatentPointCandidate(**json.loads(row["candidate_json"]))
        return point.model_copy(update={"selected": bool(row["selected"])})

    def delete_project_patent_point(self, project_id: str, point_id: str) -> bool:
        with self.connection:
            cursor = self.connection.execute(
                "delete from project_patent_points where project_id = ? and id = ?",
                (project_id, point_id),
            )
        return cursor.rowcount > 0

    def create_disclosure_run(self, run: DisclosureRun) -> DisclosureRun:
        with self.connection:
            self.connection.execute(
                """
                insert into disclosure_runs(
                    id, project_id, status, trace, max_prior_art_results, research_mode, run_dir,
                    stage_results_json, package_json, failures_json, events_json,
                    runtime_state_json, failure_details_json, cancel_requested, retry_of
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._disclosure_run_values(run),
            )
        return run

    def update_disclosure_run(self, run: DisclosureRun) -> None:
        with self.connection:
            self.connection.execute(
                """
                update disclosure_runs
                set status = ?, trace = ?, max_prior_art_results = ?, research_mode = ?,
                    run_dir = ?, stage_results_json = ?, package_json = ?, failures_json = ?,
                    events_json = ?, runtime_state_json = ?, failure_details_json = ?,
                    cancel_requested = ?, retry_of = ?, updated_at = current_timestamp
                where id = ? and project_id = ?
                """,
                (
                    run.status,
                    1 if run.trace else 0,
                    run.max_prior_art_results,
                    run.research_mode,
                    run.run_dir,
                    json.dumps(run.stage_results, ensure_ascii=False),
                    json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False) if run.package else None,
                    json.dumps(run.failures, ensure_ascii=False),
                    json.dumps(run.events, ensure_ascii=False),
                    json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False)
                    if run.runtime_state
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
                    1 if run.cancel_requested else 0,
                    run.retry_of or "",
                    run.id,
                    run.project_id,
                ),
            )

    def get_disclosure_run(self, project_id: str, run_id: str) -> DisclosureRun | None:
        row = self.connection.execute(
            "select * from disclosure_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._disclosure_run_from_row(row) if row else None

    def list_disclosure_runs(self, project_id: str) -> list[DisclosureRun]:
        rows = self.connection.execute(
            "select * from disclosure_runs where project_id = ? order by created_at desc",
            (project_id,),
        ).fetchall()
        return [self._disclosure_run_from_row(row) for row in rows]

    def get_latest_completed_disclosure_run(self, project_id: str) -> DisclosureRun | None:
        row = self.connection.execute(
            """
            select * from disclosure_runs
            where project_id = ? and status = 'completed'
            order by updated_at desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._disclosure_run_from_row(row) if row else None

    def create_deliberation_run(self, run: DeliberationRun) -> DeliberationRun:
        with self.connection:
            self.connection.execute(
                """
                insert into deliberation_runs(
                    id, project_id, status, providers_json, run_mode, round_depth, trace,
                    run_dir, stage_results_json, strategy_brief_json, failures_json, events_json,
                    logs_json, runtime_state_json, failure_details_json, cancel_requested, retry_of
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._run_values(run),
            )
        return run

    def update_deliberation_run(self, run: DeliberationRun) -> None:
        with self.connection:
            self.connection.execute(
                """
                update deliberation_runs
                set status = ?, providers_json = ?, run_mode = ?, round_depth = ?, trace = ?,
                    run_dir = ?, stage_results_json = ?, strategy_brief_json = ?,
                    failures_json = ?, events_json = ?, logs_json = ?, runtime_state_json = ?,
                    failure_details_json = ?, cancel_requested = ?, retry_of = ?,
                    updated_at = current_timestamp
                where id = ? and project_id = ?
                """,
                (
                    run.status,
                    json.dumps(run.providers, ensure_ascii=False),
                    run.run_mode,
                    run.round_depth,
                    1 if run.trace else 0,
                    run.run_dir,
                    json.dumps([result.model_dump(mode="json") for result in run.stage_results], ensure_ascii=False),
                    json.dumps(run.strategy_brief.model_dump(mode="json"), ensure_ascii=False)
                    if run.strategy_brief
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failures], ensure_ascii=False),
                    json.dumps(run.events, ensure_ascii=False),
                    json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
                    json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False)
                    if run.runtime_state
                    else None,
                    json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
                    1 if run.cancel_requested else 0,
                    run.retry_of or "",
                    run.id,
                    run.project_id,
                ),
            )

    def get_deliberation_run(self, project_id: str, run_id: str) -> DeliberationRun | None:
        row = self.connection.execute(
            "select * from deliberation_runs where project_id = ? and id = ?",
            (project_id, run_id),
        ).fetchone()
        return self._run_from_row(row) if row else None

    def list_deliberation_runs(self, project_id: str) -> list[DeliberationRun]:
        rows = self.connection.execute(
            "select * from deliberation_runs where project_id = ? order by created_at desc",
            (project_id,),
        ).fetchall()
        return [self._run_from_row(row) for row in rows]

    def get_latest_completed_deliberation_run(self, project_id: str) -> DeliberationRun | None:
        row = self.connection.execute(
            """
            select * from deliberation_runs
            where project_id = ? and status = 'completed'
            order by updated_at desc
            limit 1
            """,
            (project_id,),
        ).fetchone()
        return self._run_from_row(row) if row else None

    def _migrate(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                create table if not exists documents (
                    id text primary key,
                    title text not null,
                    source_name text not null,
                    text text not null,
                    metadata_json text not null,
                    sections_json text not null,
                    created_at text not null default current_timestamp
                );

                create table if not exists chunks (
                    id text primary key,
                    document_id text not null,
                    section_type text not null,
                    text text not null,
                    ordinal integer not null,
                    metadata_json text not null,
                    foreign key(document_id) references documents(id)
                );

                create table if not exists projects (
                    id text primary key,
                    name text not null,
                    draft_text text not null,
                    patent_type text not null default 'invention',
                    package_json text,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );

                create table if not exists deliberation_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    providers_json text not null,
                    run_mode text not null,
                    round_depth text not null,
                    trace integer not null default 0,
                    run_dir text not null,
                    stage_results_json text not null,
                    strategy_brief_json text,
                    failures_json text not null,
                    events_json text not null,
                    logs_json text not null default '[]',
                    runtime_state_json text,
                    failure_details_json text not null default '[]',
                    cancel_requested integer not null default 0,
                    retry_of text not null default '',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists corpus_jobs (
                    id text primary key,
                    source_type text not null,
                    source_name text not null,
                    query text not null,
                    domain text not null,
                    version_name text not null,
                    status text not null,
                    input_paths_json text not null,
                    total_files integer not null default 0,
                    processed_files integer not null default 0,
                    imported_documents integer not null default 0,
                    duplicate_documents integer not null default 0,
                    filtered_documents integer not null default 0,
                    failed_documents integer not null default 0,
                    errors_json text not null,
                    quality_report_json text,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );

                create table if not exists corpus_versions (
                    id text primary key,
                    name text not null unique,
                    domain text not null,
                    source_type text not null,
                    source_name text not null,
                    query text not null,
                    document_count integer not null default 0,
                    chunk_count integer not null default 0,
                    quality_report_json text,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                );

                create table if not exists patent_assets (
                    id text primary key,
                    job_id text not null,
                    file_name text not null,
                    path text not null,
                    file_type text not null,
                    status text not null,
                    document_id text,
                    error text,
                    metadata_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(job_id) references corpus_jobs(id)
                );

                create table if not exists project_materials (
                    id text primary key,
                    project_id text not null,
                    file_name text not null,
                    path text not null,
                    file_type text not null,
                    text text not null,
                    status text not null,
                    warnings_json text not null,
                    metadata_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists external_draft_sources (
                    id text primary key,
                    project_id text not null,
                    source_type text not null,
                    file_name text not null,
                    content_hash text not null,
                    raw_text text not null,
                    raw_path text not null,
                    metadata_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists external_draft_intake_runs (
                    id text primary key,
                    project_id text not null,
                    source_id text not null,
                    status text not null,
                    parser_version text not null,
                    source_hash text not null,
                    parsed_package_json text,
                    section_confidence_json text,
                    intake_issues_json text not null,
                    unassigned_fragments_json text not null,
                    working_draft_hash text not null,
                    logs_json text not null default '[]',
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id),
                    foreign key(source_id) references external_draft_sources(id)
                );

                create table if not exists filing_readiness_reports (
                    id text primary key,
                    project_id text not null,
                    report_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists claim_defense_worksheets (
                    id text primary key,
                    project_id text not null,
                    worksheet_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists draft_completion_runs (
                    id text primary key,
                    project_id text not null,
                    run_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists llm_stage_cache (
                    cache_key text primary key,
                    project_id text not null,
                    stage text not null,
                    model text not null,
                    prompt_hash text not null,
                    input_hash text not null,
                    prompt_pack_version text not null default '',
                    response_text text not null,
                    response_json text,
                    status text not null,
                    created_at text not null default current_timestamp,
                    expires_at text
                );

                create table if not exists formula_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    providers_json text not null default '[]',
                    requirement_json text not null,
                    package_json text,
                    failures_json text not null,
                    events_json text not null,
                    runtime_state_json text,
                    failure_details_json text not null default '[]',
                    cancel_requested integer not null default 0,
                    retry_of text not null default '',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists generate_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    providers_json text not null default '[]',
                    deliberation_run_id text not null default '',
                    formula_run_id text not null default '',
                    package_json text,
                    failures_json text not null default '[]',
                    events_json text not null default '[]',
                    runtime_state_json text,
                    failure_details_json text not null default '[]',
                    cancel_requested integer not null default 0,
                    retry_of text not null default '',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists post_draft_review_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    providers_json text not null default '[]',
                    prompt_pack_version text not null,
                    draft_package_hash text not null,
                    official_compile_run_id text not null default '',
                    official_package_hash text not null default '',
                    role_results_json text not null,
                    chair_result_json text,
                    export_allowed integer not null default 0,
                    blocking_issues_json text not null,
                    contamination_hits_json text not null,
                    logs_json text not null default '[]',
                    runtime_state_json text,
                    failure_details_json text not null default '[]',
                    cancel_requested integer not null default 0,
                    retry_of text not null default '',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists official_compile_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    source_draft_hash text not null,
                    official_package_hash text not null,
                    official_package_json text,
                    contamination_removed_json text not null,
                    blocked_items_json text not null,
                    sidecar_notes_json text not null,
                    logs_json text not null default '[]',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );

                create table if not exists project_patent_points (
                    id text not null,
                    project_id text not null,
                    candidate_json text not null,
                    selected integer not null default 0,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    primary key(project_id, id),
                    foreign key(project_id) references projects(id)
                );

                create table if not exists disclosure_runs (
                    id text primary key,
                    project_id text not null,
                    status text not null,
                    trace integer not null default 0,
                    max_prior_art_results integer not null default 8,
                    research_mode text not null default 'standard',
                    run_dir text not null,
                    stage_results_json text not null,
                    package_json text,
                    failures_json text not null,
                    events_json text not null,
                    runtime_state_json text,
                    failure_details_json text not null default '[]',
                    cancel_requested integer not null default 0,
                    retry_of text not null default '',
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );
                """
            )
            self._migrate_project_patent_points_primary_key()
            self._ensure_column("projects", "patent_type", "text not null default 'invention'")
            self._ensure_column("deliberation_runs", "logs_json", "text not null default '[]'")
            self._ensure_column("deliberation_runs", "runtime_state_json", "text")
            self._ensure_column("deliberation_runs", "failure_details_json", "text not null default '[]'")
            self._ensure_column("deliberation_runs", "cancel_requested", "integer not null default 0")
            self._ensure_column("deliberation_runs", "retry_of", "text not null default ''")
            self._ensure_column("formula_runs", "providers_json", "text not null default '[]'")
            self._ensure_column("formula_runs", "runtime_state_json", "text")
            self._ensure_column("formula_runs", "failure_details_json", "text not null default '[]'")
            self._ensure_column("formula_runs", "cancel_requested", "integer not null default 0")
            self._ensure_column("formula_runs", "retry_of", "text not null default ''")
            self._ensure_column("post_draft_review_runs", "official_compile_run_id", "text not null default ''")
            self._ensure_column("post_draft_review_runs", "official_package_hash", "text not null default ''")
            self._ensure_column("post_draft_review_runs", "runtime_state_json", "text")
            self._ensure_column("post_draft_review_runs", "failure_details_json", "text not null default '[]'")
            self._ensure_column("post_draft_review_runs", "cancel_requested", "integer not null default 0")
            self._ensure_column("post_draft_review_runs", "retry_of", "text not null default ''")
            self._ensure_column("disclosure_runs", "research_mode", "text not null default 'standard'")
            self._ensure_column("disclosure_runs", "runtime_state_json", "text")
            self._ensure_column("disclosure_runs", "failure_details_json", "text not null default '[]'")
            self._ensure_column("disclosure_runs", "cancel_requested", "integer not null default 0")
            self._ensure_column("disclosure_runs", "retry_of", "text not null default ''")

    def _migrate_project_patent_points_primary_key(self) -> None:
        columns = self.connection.execute("pragma table_info(project_patent_points)").fetchall()
        primary_key_columns = [column["name"] for column in sorted(columns, key=lambda column: column["pk"]) if column["pk"]]
        if primary_key_columns == ["project_id", "id"]:
            return
        self.connection.executescript(
            """
            alter table project_patent_points rename to project_patent_points_legacy;

            create table project_patent_points (
                id text not null,
                project_id text not null,
                candidate_json text not null,
                selected integer not null default 0,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(project_id, id),
                foreign key(project_id) references projects(id)
            );

            insert into project_patent_points(id, project_id, candidate_json, selected, created_at, updated_at)
            select id, project_id, candidate_json, selected, created_at, updated_at
            from project_patent_points_legacy legacy
            where not exists (
                select 1
                from project_patent_points_legacy newer
                where newer.project_id = legacy.project_id
                    and newer.id = legacy.id
                    and (
                        newer.updated_at > legacy.updated_at
                        or (newer.updated_at = legacy.updated_at and newer.rowid > legacy.rowid)
                    )
            );

            drop table project_patent_points_legacy;
            """
        )

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = self.connection.execute(f"pragma table_info({table})").fetchall()
        if column in {row["name"] for row in columns}:
            return
        self.connection.execute(f"alter table {table} add column {column} {definition}")

    def _document_from_row(self, row: sqlite3.Row) -> PatentDocument:
        return PatentDocument(
            id=row["id"],
            title=row["title"],
            source_name=row["source_name"],
            text=row["text"],
            metadata=json.loads(row["metadata_json"]),
            sections=json.loads(row["sections_json"]),
        )

    def _chunk_from_row(self, row: sqlite3.Row) -> PatentChunk:
        return PatentChunk(
            id=row["id"],
            document_id=row["document_id"],
            section_type=row["section_type"],
            text=row["text"],
            ordinal=row["ordinal"],
            metadata=json.loads(row["metadata_json"]),
        )

    def _project_from_row(self, row: sqlite3.Row) -> ProjectRecord:
        package_json: str | None = row["package_json"]
        try:
            raw_patent_type = row["patent_type"]
        except (IndexError, KeyError):
            raw_patent_type = None
        try:
            patent_type = PatentType(raw_patent_type) if raw_patent_type else PatentType.INVENTION
        except ValueError:
            patent_type = PatentType.INVENTION
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            draft_text=row["draft_text"],
            patent_type=patent_type,
            package=DraftPackage(**json.loads(package_json)) if package_json else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _external_draft_source_from_row(self, row: sqlite3.Row) -> ExternalDraftSource:
        return ExternalDraftSource(
            id=row["id"],
            project_id=row["project_id"],
            source_type=row["source_type"],
            file_name=row["file_name"],
            content_hash=row["content_hash"],
            raw_text=row["raw_text"],
            raw_path=row["raw_path"],
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
        )

    def _external_draft_intake_run_values(self, run: ExternalDraftIntakeRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.source_id,
            run.status,
            run.parser_version,
            run.source_hash,
            json.dumps(run.parsed_package.model_dump(mode="json"), ensure_ascii=False)
            if run.parsed_package
            else None,
            json.dumps(run.section_confidence.model_dump(mode="json"), ensure_ascii=False)
            if run.section_confidence
            else None,
            json.dumps([issue.model_dump(mode="json") for issue in run.intake_issues], ensure_ascii=False),
            json.dumps(run.unassigned_fragments, ensure_ascii=False),
            run.working_draft_hash,
            json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
        )

    def _external_draft_intake_run_from_row(self, row: sqlite3.Row) -> ExternalDraftIntakeRun:
        payload = {
            "id": row["id"],
            "project_id": row["project_id"],
            "source_id": row["source_id"],
            "status": row["status"],
            "parser_version": row["parser_version"],
            "source_hash": row["source_hash"],
            "parsed_package": json.loads(row["parsed_package_json"]) if row["parsed_package_json"] else None,
            "section_confidence": json.loads(row["section_confidence_json"]) if row["section_confidence_json"] else None,
            "intake_issues": json.loads(row["intake_issues_json"]),
            "unassigned_fragments": json.loads(row["unassigned_fragments_json"]),
            "working_draft_hash": row["working_draft_hash"],
            "logs": json.loads(row["logs_json"]),
            "created_at": row["created_at"],
        }
        return ExternalDraftIntakeRun.model_validate(payload)

    def _filing_readiness_report_from_row(self, row: sqlite3.Row) -> FilingReadinessReport:
        report = FilingReadinessReport.model_validate(json.loads(row["report_json"]))
        if not report.created_at:
            report = report.model_copy(update={"created_at": row["created_at"]})
        return report

    def _claim_defense_worksheet_from_row(self, row: sqlite3.Row) -> ClaimDefenseWorksheet:
        worksheet = ClaimDefenseWorksheet.model_validate(json.loads(row["worksheet_json"]))
        if not worksheet.created_at:
            worksheet = worksheet.model_copy(update={"created_at": row["created_at"]})
        return worksheet

    def _draft_completion_run_from_row(self, row: sqlite3.Row) -> DraftCompletionRun:
        run = DraftCompletionRun.model_validate(json.loads(row["run_json"]))
        if not run.created_at:
            run = run.model_copy(update={"created_at": row["created_at"]})
        return run

    def _formula_run_values(self, run: FormulaRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            json.dumps(run.providers, ensure_ascii=False),
            json.dumps(run.requirement.model_dump(mode="json"), ensure_ascii=False),
            json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False) if run.package else None,
            json.dumps(run.failures, ensure_ascii=False),
            json.dumps(run.events, ensure_ascii=False),
            json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False) if run.runtime_state else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
            1 if run.cancel_requested else 0,
            run.retry_of or "",
        )

    def _formula_run_from_row(self, row: sqlite3.Row) -> FormulaRun:
        package_json: str | None = row["package_json"]
        run = FormulaRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            providers=json.loads(row["providers_json"] if "providers_json" in row.keys() else "[]"),
            requirement=json.loads(row["requirement_json"]),
            package=json.loads(package_json) if package_json else None,
            failures=json.loads(row["failures_json"]),
            events=json.loads(row["events_json"]),
            runtime_state=json.loads(row["runtime_state_json"]) if row["runtime_state_json"] else None,
            failure_details=json.loads(row["failure_details_json"] if "failure_details_json" in row.keys() else "[]"),
            cancel_requested=bool(row["cancel_requested"] if "cancel_requested" in row.keys() else 0),
            retry_of=(row["retry_of"] if "retry_of" in row.keys() else "") or None,
        )
        return run.model_copy(update={"created_at": row["created_at"], "updated_at": row["updated_at"]})

    def _generate_run_values(self, run: GenerateRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            json.dumps(run.providers, ensure_ascii=False),
            run.deliberation_run_id or "",
            run.formula_run_id or "",
            json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False) if run.package else None,
            json.dumps(run.failures, ensure_ascii=False),
            json.dumps(run.events, ensure_ascii=False),
            json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False) if run.runtime_state else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
            1 if run.cancel_requested else 0,
            run.retry_of or "",
        )

    def _generate_run_from_row(self, row: sqlite3.Row) -> GenerateRun:
        package_json: str | None = row["package_json"]
        run = GenerateRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            providers=json.loads(row["providers_json"] if "providers_json" in row.keys() else "[]"),
            deliberation_run_id=(row["deliberation_run_id"] if "deliberation_run_id" in row.keys() else "") or None,
            formula_run_id=(row["formula_run_id"] if "formula_run_id" in row.keys() else "") or None,
            package=DraftPackage.model_validate(json.loads(package_json)) if package_json else None,
            failures=json.loads(row["failures_json"] if "failures_json" in row.keys() else "[]"),
            events=json.loads(row["events_json"] if "events_json" in row.keys() else "[]"),
            runtime_state=json.loads(row["runtime_state_json"]) if row["runtime_state_json"] else None,
            failure_details=json.loads(row["failure_details_json"] if "failure_details_json" in row.keys() else "[]"),
            cancel_requested=bool(row["cancel_requested"] if "cancel_requested" in row.keys() else 0),
            retry_of=(row["retry_of"] if "retry_of" in row.keys() else "") or None,
        )
        return run.model_copy(update={"created_at": row["created_at"], "updated_at": row["updated_at"]})

    def _post_draft_review_run_values(self, run: PostDraftReviewRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            json.dumps(run.providers, ensure_ascii=False),
            run.prompt_pack_version,
            run.draft_package_hash,
            run.official_compile_run_id,
            run.official_package_hash,
            json.dumps([result.model_dump(mode="json") for result in run.role_results], ensure_ascii=False),
            json.dumps(run.chair_result.model_dump(mode="json"), ensure_ascii=False) if run.chair_result else None,
            1 if run.export_allowed else 0,
            json.dumps(run.blocking_issues, ensure_ascii=False),
            json.dumps(run.contamination_hits, ensure_ascii=False),
            json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
            json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False) if run.runtime_state else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
            1 if run.cancel_requested else 0,
            run.retry_of or "",
        )

    def _post_draft_review_run_from_row(self, row: sqlite3.Row) -> PostDraftReviewRun:
        run = PostDraftReviewRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            providers=json.loads(row["providers_json"]),
            prompt_pack_version=row["prompt_pack_version"],
            draft_package_hash=row["draft_package_hash"],
            official_compile_run_id=row["official_compile_run_id"] if "official_compile_run_id" in row.keys() else "",
            official_package_hash=row["official_package_hash"] if "official_package_hash" in row.keys() else "",
            role_results=json.loads(row["role_results_json"]),
            chair_result=json.loads(row["chair_result_json"]) if row["chair_result_json"] else None,
            export_allowed=bool(row["export_allowed"]),
            blocking_issues=json.loads(row["blocking_issues_json"]),
            contamination_hits=json.loads(row["contamination_hits_json"]),
            logs=json.loads(row["logs_json"]),
            runtime_state=json.loads(row["runtime_state_json"]) if row["runtime_state_json"] else None,
            failure_details=json.loads(row["failure_details_json"] if "failure_details_json" in row.keys() else "[]"),
            cancel_requested=bool(row["cancel_requested"] if "cancel_requested" in row.keys() else 0),
            retry_of=(row["retry_of"] if "retry_of" in row.keys() else "") or None,
        )
        return run.model_copy(update={"created_at": row["created_at"], "updated_at": row["updated_at"]})

    def _official_compile_run_values(self, run: OfficialCompileRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            run.source_draft_hash,
            run.official_package_hash,
            json.dumps(run.official_package.model_dump(mode="json"), ensure_ascii=False)
            if run.official_package
            else None,
            json.dumps(run.contamination_removed, ensure_ascii=False),
            json.dumps(run.blocked_items, ensure_ascii=False),
            json.dumps(run.sidecar_notes, ensure_ascii=False),
            json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
        )

    def _official_compile_run_from_row(self, row: sqlite3.Row) -> OfficialCompileRun:
        official_package_json: str | None = row["official_package_json"]
        run = OfficialCompileRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            source_draft_hash=row["source_draft_hash"],
            official_package_hash=row["official_package_hash"],
            official_package=OfficialDraftPackage.model_validate(json.loads(official_package_json))
            if official_package_json
            else None,
            contamination_removed=json.loads(row["contamination_removed_json"]),
            blocked_items=json.loads(row["blocked_items_json"]),
            sidecar_notes=json.loads(row["sidecar_notes_json"]),
            logs=json.loads(row["logs_json"]),
        )
        return run.model_copy(update={"created_at": row["created_at"], "updated_at": row["updated_at"]})

    def _project_material_from_row(self, row: sqlite3.Row) -> ProjectMaterial:
        return ProjectMaterial(
            id=row["id"],
            project_id=row["project_id"],
            file_name=row["file_name"],
            path=row["path"],
            file_type=row["file_type"],
            text=row["text"],
            status=row["status"],
            warnings=json.loads(row["warnings_json"]),
            metadata=json.loads(row["metadata_json"]),
        )

    def _run_values(self, run: DeliberationRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            json.dumps(run.providers, ensure_ascii=False),
            run.run_mode,
            run.round_depth,
            1 if run.trace else 0,
            run.run_dir,
            json.dumps([result.model_dump(mode="json") for result in run.stage_results], ensure_ascii=False),
            json.dumps(run.strategy_brief.model_dump(mode="json"), ensure_ascii=False) if run.strategy_brief else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failures], ensure_ascii=False),
            json.dumps(run.events, ensure_ascii=False),
            json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
            json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False) if run.runtime_state else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
            1 if run.cancel_requested else 0,
            run.retry_of or "",
        )

    def _run_from_row(self, row: sqlite3.Row) -> DeliberationRun:
        logs_json = row["logs_json"] if "logs_json" in row.keys() else "[]"
        return DeliberationRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            providers=json.loads(row["providers_json"]),
            run_mode=row["run_mode"],
            round_depth=row["round_depth"],
            trace=bool(row["trace"]),
            run_dir=row["run_dir"],
            stage_results=json.loads(row["stage_results_json"]),
            strategy_brief=json.loads(row["strategy_brief_json"]) if row["strategy_brief_json"] else None,
            failures=json.loads(row["failures_json"]),
            events=json.loads(row["events_json"]),
            logs=json.loads(logs_json),
            runtime_state=json.loads(row["runtime_state_json"]) if row["runtime_state_json"] else None,
            failure_details=json.loads(row["failure_details_json"] if "failure_details_json" in row.keys() else "[]"),
            cancel_requested=bool(row["cancel_requested"] if "cancel_requested" in row.keys() else 0),
            retry_of=(row["retry_of"] if "retry_of" in row.keys() else "") or None,
        )

    def _disclosure_run_values(self, run: DisclosureRun) -> tuple:
        return (
            run.id,
            run.project_id,
            run.status,
            1 if run.trace else 0,
            run.max_prior_art_results,
            run.research_mode,
            run.run_dir,
            json.dumps(run.stage_results, ensure_ascii=False),
            json.dumps(run.package.model_dump(mode="json"), ensure_ascii=False) if run.package else None,
            json.dumps(run.failures, ensure_ascii=False),
            json.dumps(run.events, ensure_ascii=False),
            json.dumps(run.runtime_state.model_dump(mode="json"), ensure_ascii=False) if run.runtime_state else None,
            json.dumps([failure.model_dump(mode="json") for failure in run.failure_details], ensure_ascii=False),
            1 if run.cancel_requested else 0,
            run.retry_of or "",
        )

    def _disclosure_run_from_row(self, row: sqlite3.Row) -> DisclosureRun:
        package_json: str | None = row["package_json"]
        # research_mode column was introduced after the initial schema; the
        # ALTER TABLE in _post_init backfills "standard" for legacy rows, but
        # fall back defensively in case a row was written before the migration.
        try:
            research_mode = row["research_mode"] or "standard"
        except (IndexError, KeyError):
            research_mode = "standard"
        return DisclosureRun(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            trace=bool(row["trace"]),
            max_prior_art_results=row["max_prior_art_results"],
            research_mode=research_mode,
            run_dir=row["run_dir"],
            stage_results=json.loads(row["stage_results_json"]),
            package=json.loads(package_json) if package_json else None,
            failures=json.loads(row["failures_json"]),
            events=json.loads(row["events_json"]),
            runtime_state=json.loads(row["runtime_state_json"]) if row["runtime_state_json"] else None,
            failure_details=json.loads(row["failure_details_json"] if "failure_details_json" in row.keys() else "[]"),
            cancel_requested=bool(row["cancel_requested"] if "cancel_requested" in row.keys() else 0),
            retry_of=(row["retry_of"] if "retry_of" in row.keys() else "") or None,
        )

    def _corpus_job_values(self, job: CorpusImportJob) -> tuple:
        return (
            job.id,
            job.source_type,
            job.source_name,
            job.query,
            job.domain,
            job.version_name,
            job.status,
            json.dumps(job.input_paths, ensure_ascii=False),
            job.total_files,
            job.processed_files,
            job.imported_documents,
            job.duplicate_documents,
            job.filtered_documents,
            job.failed_documents,
            json.dumps(job.errors, ensure_ascii=False),
            json.dumps(job.quality_report.model_dump(mode="json"), ensure_ascii=False) if job.quality_report else None,
        )

    def _corpus_job_from_row(self, row: sqlite3.Row) -> CorpusImportJob:
        report_json: str | None = row["quality_report_json"]
        return CorpusImportJob(
            id=row["id"],
            source_type=row["source_type"],
            source_name=row["source_name"],
            query=row["query"],
            domain=row["domain"],
            version_name=row["version_name"],
            status=row["status"],
            input_paths=json.loads(row["input_paths_json"]),
            total_files=row["total_files"],
            processed_files=row["processed_files"],
            imported_documents=row["imported_documents"],
            duplicate_documents=row["duplicate_documents"],
            filtered_documents=row["filtered_documents"],
            failed_documents=row["failed_documents"],
            errors=json.loads(row["errors_json"]),
            quality_report=CorpusQualityReport(**json.loads(report_json)) if report_json else None,
        )

    def _corpus_version_from_row(self, row: sqlite3.Row) -> CorpusVersion:
        report_json: str | None = row["quality_report_json"]
        return CorpusVersion(
            id=row["id"],
            name=row["name"],
            domain=row["domain"],
            source_type=row["source_type"],
            source_name=row["source_name"],
            query=row["query"],
            document_count=row["document_count"],
            chunk_count=row["chunk_count"],
            quality_report=CorpusQualityReport(**json.loads(report_json)) if report_json else None,
        )

    def _section_coverage(self, documents: list[PatentDocument]) -> dict[str, float]:
        coverage: dict[str, float] = {}
        for section_type in [
            SectionType.ABSTRACT,
            SectionType.CLAIMS,
            SectionType.DESCRIPTION,
            SectionType.TECHNICAL_FIELD,
            SectionType.BACKGROUND,
            SectionType.SUMMARY,
            SectionType.DRAWINGS,
            SectionType.EMBODIMENTS,
        ]:
            if not documents:
                coverage[section_type.value] = 0.0
                continue
            count = sum(1 for document in documents if any(section.type == section_type for section in document.sections))
            coverage[section_type.value] = round(count / len(documents), 4)
        return coverage


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def model_dump_jsonable(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


class _LockedCursor:
    def __init__(self, cursor: sqlite3.Cursor, lock: threading.RLock) -> None:
        self._cursor = cursor
        self._lock = lock

    def fetchone(self) -> sqlite3.Row | None:
        with self._lock:
            return self._cursor.fetchone()

    def fetchall(self) -> list[sqlite3.Row]:
        with self._lock:
            return self._cursor.fetchall()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class _LockedConnection:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def execute(self, *args: Any, **kwargs: Any) -> _LockedCursor:
        with self._lock:
            return _LockedCursor(self._connection.execute(*args, **kwargs), self._lock)

    def executemany(self, *args: Any, **kwargs: Any) -> _LockedCursor:
        with self._lock:
            return _LockedCursor(self._connection.executemany(*args, **kwargs), self._lock)

    def executescript(self, *args: Any, **kwargs: Any) -> _LockedCursor:
        with self._lock:
            return _LockedCursor(self._connection.executescript(*args, **kwargs), self._lock)

    def __enter__(self) -> "_LockedConnection":
        self._lock.acquire()
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Any:
        try:
            return self._connection.__exit__(exc_type, exc, traceback)
        finally:
            self._lock.release()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)
