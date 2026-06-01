from __future__ import annotations

import hashlib
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from backend.app.corpus.filters import is_ai_software_invention
from backend.app.corpus.metadata import parse_metadata_table
from backend.app.patent_parser import chunk_document, extract_claims, make_patent_document, read_document_text
from backend.app.rag import LocalVectorIndex
from backend.app.schemas import CorpusImportJob, CorpusQualityReport, CorpusVersion, PatentAsset, PatentChunk, SectionType
from backend.app.storage import SQLiteStore


FULLTEXT_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".markdown", ".xml"}
METADATA_SUFFIXES = {".csv", ".xlsx", ".xlsm"}


class CorpusImportService:
    def __init__(self, store: SQLiteStore, index: LocalVectorIndex, data_dir: Path) -> None:
        self.store = store
        self.index = index
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_job(
        self,
        source_type: str,
        source_name: str = "",
        query: str = "",
        domain: str = "ai_software",
        version_name: str = "ai-software-v1",
    ) -> CorpusImportJob:
        job = CorpusImportJob(
            id=uuid.uuid4().hex,
            source_type=source_type,
            source_name=source_name,
            query=query,
            domain=domain,
            version_name=version_name,
        )
        self.store.create_corpus_job(job)
        return job

    def add_input(self, job_id: str, input_path: Path) -> CorpusImportJob:
        job = self._require_job(job_id)
        input_path = Path(input_path)
        target_dir = self.data_dir / "corpus-jobs" / job_id / "inputs"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / input_path.name
        if input_path.resolve() != target.resolve():
            if input_path.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(input_path, target)
            else:
                shutil.copy2(input_path, target)
        next_paths = [*job.input_paths, str(target)]
        updated = job.model_copy(update={"input_paths": next_paths, "total_files": len(next_paths)})
        self.store.update_corpus_job(updated)
        self.store.add_patent_asset(
            PatentAsset(
                id=uuid.uuid4().hex,
                job_id=job_id,
                file_name=target.name,
                path=str(target),
                file_type=target.suffix.lower().lstrip(".") or "directory",
                status="uploaded",
            )
        )
        return updated

    def run_job(self, job_id: str) -> CorpusImportJob:
        job = self._require_job(job_id)
        running = job.model_copy(update={"status": "running", "errors": []})
        self.store.update_corpus_job(running)
        work_dir = self.data_dir / "corpus-jobs" / job_id / "work"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        failures: list[dict[str, str]] = []
        imported_document_ids: list[str] = []
        indexed_chunks = 0
        duplicate_count = 0
        filtered_count = 0
        processed_count = 0
        extracted_text_count = 0
        seen_keys: set[str] = set()

        try:
            source_paths = self._expand_inputs(job.input_paths, work_dir)
            metadata_rows = self._load_metadata_rows(source_paths)
            candidates = self._build_candidates(source_paths, metadata_rows)
            total_files = len(candidates)

            for candidate in candidates:
                processed_count += 1
                metadata = dict(candidate["metadata"])
                path = candidate["path"]
                try:
                    text = read_document_text(path)
                    extracted_text_count += 1
                    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    metadata = self._enrich_metadata(job, metadata, path, content_hash)

                    if job.domain == "ai_software" and not is_ai_software_invention(metadata, text):
                        filtered_count += 1
                        continue

                    duplicate_key = self._dedup_key(metadata, content_hash)
                    if duplicate_key in seen_keys or self.store.find_duplicate_document(metadata, content_hash):
                        duplicate_count += 1
                        seen_keys.add(duplicate_key)
                        continue
                    seen_keys.add(duplicate_key)

                    document_id = self._document_id(job.version_name, duplicate_key)
                    document = make_patent_document(document_id, path.name, text)
                    document.title = metadata.get("title") or document.title
                    document.source_name = job.source_name or path.name
                    document.metadata = {**document.metadata, **metadata, "claims": self._claims_metadata(document)}
                    chunks = [PatentChunk(**chunk) for chunk in chunk_document(document)]
                    self.store.add_document(document, chunks)
                    self.index.add(chunks)
                    imported_document_ids.append(document.id)
                    indexed_chunks += len(chunks)
                    self.store.add_patent_asset(
                        PatentAsset(
                            id=uuid.uuid4().hex,
                            job_id=job.id,
                            file_name=path.name,
                            path=str(path),
                            file_type=path.suffix.lower().lstrip("."),
                            status="processed",
                            document_id=document.id,
                            metadata={"content_hash": content_hash},
                        )
                    )
                except Exception as exc:
                    failures.append({"file": str(path), "reason": str(exc)})
                    self.store.add_patent_asset(
                        PatentAsset(
                            id=uuid.uuid4().hex,
                            job_id=job.id,
                            file_name=path.name,
                            path=str(path),
                            file_type=path.suffix.lower().lstrip("."),
                            status="failed",
                            error=str(exc),
                        )
                    )

            report = self._quality_report(
                document_ids=imported_document_ids,
                total_files=total_files,
                processed_files=processed_count,
                extracted_text_count=extracted_text_count,
                duplicate_documents=duplicate_count,
                filtered_documents=filtered_count,
                failures=failures,
                indexed_chunks=indexed_chunks,
            )
            status = "completed" if not failures or imported_document_ids else "failed"
            completed = running.model_copy(
                update={
                    "status": status,
                    "total_files": total_files,
                    "processed_files": processed_count,
                    "imported_documents": report.imported_documents,
                    "duplicate_documents": duplicate_count,
                    "filtered_documents": filtered_count,
                    "failed_documents": len(failures),
                    "errors": [failure["reason"] for failure in failures],
                    "quality_report": report,
                }
            )
            self.store.update_corpus_job(completed)
            self._upsert_version(job, report)
            return completed
        except Exception as exc:
            failed = running.model_copy(update={"status": "failed", "errors": [str(exc)]})
            self.store.update_corpus_job(failed)
            return failed

    def _require_job(self, job_id: str) -> CorpusImportJob:
        job = self.store.get_corpus_job(job_id)
        if not job:
            raise ValueError(f"Corpus import job not found: {job_id}")
        return job

    def _expand_inputs(self, input_paths: list[str], work_dir: Path) -> list[Path]:
        expanded: list[Path] = []
        for raw_path in input_paths:
            path = Path(raw_path)
            if path.is_dir():
                expanded.extend(self._collect_supported_files(path))
            elif path.suffix.lower() == ".zip":
                target = work_dir / path.stem
                target.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(path) as archive:
                    archive.extractall(target)
                expanded.extend(self._collect_supported_files(target))
            else:
                expanded.append(path)
        return [path for path in expanded if path.suffix.lower() in FULLTEXT_SUFFIXES | METADATA_SUFFIXES]

    def _collect_supported_files(self, directory: Path) -> list[Path]:
        return sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in FULLTEXT_SUFFIXES | METADATA_SUFFIXES
        )

    def _load_metadata_rows(self, paths: list[Path]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in paths:
            if path.suffix.lower() in METADATA_SUFFIXES:
                parsed = parse_metadata_table(path)
                for row in parsed:
                    row["_metadata_table"] = str(path)
                rows.extend(parsed)
        return rows

    def _build_candidates(self, paths: list[Path], metadata_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fulltext_paths = [path for path in paths if path.suffix.lower() in FULLTEXT_SUFFIXES]
        by_name = {path.name.lower(): path for path in fulltext_paths}
        by_stem = {path.stem.lower(): path for path in fulltext_paths}
        used: set[Path] = set()
        candidates: list[dict[str, Any]] = []

        for row in metadata_rows:
            path = self._match_fulltext(row, by_name, by_stem)
            if path:
                used.add(path)
                candidates.append({"path": path, "metadata": row})
            else:
                candidates.append(
                    {
                        "path": Path(row.get("source_file_name") or row.get("title") or row.get("application_number") or "missing"),
                        "metadata": row,
                    }
                )
        for path in fulltext_paths:
            if path not in used:
                candidates.append({"path": path, "metadata": {}})
        return candidates

    def _match_fulltext(
        self,
        row: dict[str, Any],
        by_name: dict[str, Path],
        by_stem: dict[str, Path],
    ) -> Path | None:
        candidates = [
            str(row.get("source_file_name", "")),
            str(row.get("grant_number", "")),
            str(row.get("publication_number", "")),
            str(row.get("application_number", "")).replace(".", ""),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            name = Path(candidate).name.lower()
            stem = Path(candidate).stem.lower()
            if name in by_name:
                return by_name[name]
            if stem in by_stem:
                return by_stem[stem]
        return None

    def _enrich_metadata(
        self,
        job: CorpusImportJob,
        metadata: dict[str, Any],
        path: Path,
        content_hash: str,
    ) -> dict[str, Any]:
        return {
            **metadata,
            "source_type": job.source_type,
            "source_name": job.source_name,
            "source_query": job.query,
            "domain": job.domain,
            "version_name": job.version_name,
            "corpus_job_id": job.id,
            "raw_file_path": str(path),
            "source_file_name": path.name,
            "content_hash": content_hash,
        }

    def _claims_metadata(self, document) -> list[dict[str, Any]]:
        claims_text = "\n".join(section.text for section in document.sections if section.type == SectionType.CLAIMS)
        return [claim.model_dump(mode="json") for claim in extract_claims(claims_text)]

    def _dedup_key(self, metadata: dict[str, Any], content_hash: str) -> str:
        for key in ["grant_number", "publication_number", "application_number"]:
            value = str(metadata.get(key, "")).strip().upper()
            if value:
                return f"{key}:{value}"
        title = str(metadata.get("title", "")).strip()
        applicants = "|".join(str(value) for value in metadata.get("applicants", []) or [])
        date = str(metadata.get("application_date", "")).strip()
        if title and (applicants or date):
            return f"title:{title}|{applicants}|{date}"
        return f"hash:{content_hash}"

    def _document_id(self, version_name: str, duplicate_key: str) -> str:
        digest = hashlib.sha256(f"{version_name}:{duplicate_key}".encode("utf-8")).hexdigest()
        return digest[:32]

    def _quality_report(
        self,
        document_ids: list[str],
        total_files: int,
        processed_files: int,
        extracted_text_count: int,
        duplicate_documents: int,
        filtered_documents: int,
        failures: list[dict[str, str]],
        indexed_chunks: int,
    ) -> CorpusQualityReport:
        documents = [document for document in (self.store.get_document(document_id) for document_id in document_ids) if document]
        section_coverage: dict[str, float] = {}
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
                section_coverage[section_type.value] = 0.0
                continue
            count = sum(1 for document in documents if any(section.type == section_type for section in document.sections))
            section_coverage[section_type.value] = round(count / len(documents), 4)
        low_quality = [
            document.id
            for document in documents
            if not any(section.type == SectionType.CLAIMS for section in document.sections) or len(document.text) < 200
        ]
        return CorpusQualityReport(
            total_files=total_files,
            processed_files=processed_files,
            imported_documents=len(documents),
            duplicate_documents=duplicate_documents,
            filtered_documents=filtered_documents,
            failed_documents=len(failures),
            indexed_chunks=indexed_chunks,
            fulltext_extractable_rate=round(extracted_text_count / processed_files, 4) if processed_files else 0.0,
            section_coverage=section_coverage,
            low_quality_documents=low_quality,
            failures=failures,
        )

    def _upsert_version(self, job: CorpusImportJob, report: CorpusQualityReport) -> None:
        stats = self.store.get_corpus_stats(version_name=job.version_name)
        version = CorpusVersion(
            id=hashlib.sha256(job.version_name.encode("utf-8")).hexdigest()[:16],
            name=job.version_name,
            domain=job.domain,
            source_type=job.source_type,
            source_name=job.source_name,
            query=job.query,
            document_count=stats["document_count"],
            chunk_count=stats["chunk_count"],
            quality_report=report,
        )
        self.store.upsert_corpus_version(version)
