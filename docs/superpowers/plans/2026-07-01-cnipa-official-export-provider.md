# CNIPA Official Export Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CNIPA official export files a real project evidence source, while adding a provider capability registry that can accept a future authorized CNIPA API without rewriting the knowledge workflow.

**Architecture:** Keep live web/API search behind the existing `PatentSearchProvider` contract, and add a separate `CnipaOfficialExportImporter` for user-supplied official export files. Project knowledge uses source capabilities to decide whether the next action is live search, manual official export import, or provider configuration.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLite JSON storage, existing `openpyxl` dependency for XLSX parsing, React/Vite/Vitest frontend.

## Global Constraints

- Worktree for this plan: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`.
- Branch for this plan: `codex/cnipa-official-export-design`.
- Do not modify `/Users/leo/Projects/patents_agent` dirty primary checkout.
- CNIPA official export source id must be exactly `cnipa_official_export`.
- Future authorized API source id must be exactly `cnipa_authorized_api`.
- Existing legacy helper source id remains `cnipa_epub`, but ordinary UI must not ask users to configure `CNIPA_EPUB_SEARCH_SCRIPT`.
- First phase supports CSV, XLSX, and ZIP files containing CSV/XLSX metadata.
- XML/PDF files inside ZIP are attachments or enhanced metadata inputs only when structured fields are present; scanned PDFs must not generate candidates by filename alone.
- No live CNIPA website calls in CI; tests use fixtures or generated temp files.
- Do not generate fake CNIPA candidates.
- Low-evidence grantability remains fail-closed through `ProjectKnowledgeState.status`, `document_count`, `claim_coverage`, `fulltext_coverage`, and `quality_flags`.

---

## File Structure

- Create `backend/app/knowledge/patent_sources.py`
  Owns patent source capabilities and CNIPA query pack generation.
- Create `backend/app/knowledge/cnipa_export.py`
  Parses CNIPA official export files into `PatentSearchHit` objects and import warnings/failures.
- Modify `backend/app/schemas.py`
  Adds source capability, CNIPA query pack, import failure, import ledger, and import response schemas.
- Modify `backend/app/storage.py`
  Adds JSON-backed project knowledge import ledger persistence.
- Modify `backend/app/services/project_knowledge_service.py`
  Adds CNIPA query pack retrieval, official export import service, candidate insertion, quality flags, and source whitelist.
- Modify `backend/app/api/project_knowledge.py`
  Adds patent source listing, query pack retrieval, CNIPA export upload, and import ledger listing endpoints.
- Modify `frontend/src/api.ts`
  Adds TypeScript types and API wrappers for source capabilities, query packs, import ledgers, and export upload.
- Modify `frontend/src/App.tsx`
  Loads source/query-pack data and wires CNIPA export upload into the knowledge workspace.
- Modify `frontend/src/features/corpus/CorpusWorkspace.tsx`
  Passes CNIPA source/import props through to `ProjectKnowledgeView`.
- Modify `frontend/src/views/projectKnowledgeView.tsx`
  Renders CNIPA official export workflow and source labels.
- Test files:
  - `tests/test_patent_sources.py`
  - `tests/test_cnipa_export_importer.py`
  - `tests/test_project_knowledge.py`
  - `tests/test_api.py`
  - `frontend/src/api.test.ts`
  - `frontend/src/projectKnowledgeView.test.tsx`
  - `frontend/src/features/corpus/CorpusWorkspace.test.tsx`

---

### Task 1: Patent Source Registry And CNIPA Query Pack

**Files:**
- Create: `backend/app/knowledge/patent_sources.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/project_knowledge_service.py`
- Test: `tests/test_patent_sources.py`
- Test: `tests/test_project_knowledge.py`

**Interfaces:**
- Consumes: `SearchIntent`, `AgentSearchPlan`, `SearchPlanStrategyGroup`.
- Produces:
  - `CNIPA_OFFICIAL_EXPORT_SOURCE: str`
  - `CNIPA_AUTHORIZED_API_SOURCE: str`
  - `PatentSourceCapability`
  - `CnipaQueryPackStrategy`
  - `CnipaQueryPack`
  - `list_patent_source_capabilities() -> list[PatentSourceCapability]`
  - `build_cnipa_query_pack(intent: SearchIntent | None, plan: AgentSearchPlan | None) -> CnipaQueryPack`
  - `get_cnipa_query_pack(store: SQLiteStore, project_id: str) -> CnipaQueryPack`

- [ ] **Step 1: Write failing source registry tests**

Add `tests/test_patent_sources.py`:

```python
from backend.app.knowledge.patent_sources import (
    CNIPA_AUTHORIZED_API_SOURCE,
    CNIPA_OFFICIAL_EXPORT_SOURCE,
    build_cnipa_query_pack,
    list_patent_source_capabilities,
)
from backend.app.schemas import AgentSearchPlan, SearchIntent, SearchPlanStrategyGroup


def test_patent_source_capabilities_include_manual_cnipa_export():
    capabilities = {source.source_id: source for source in list_patent_source_capabilities()}

    assert CNIPA_OFFICIAL_EXPORT_SOURCE in capabilities
    cnipa = capabilities[CNIPA_OFFICIAL_EXPORT_SOURCE]
    assert cnipa.display_name == "CNIPA 官方导出"
    assert cnipa.jurisdictions == ["CN"]
    assert cnipa.modes == ["official_export"]
    assert cnipa.availability == "manual_import"
    assert cnipa.trusted_patent_source is True
    assert cnipa.evidence_origin == "official_export"
    assert "CNIPA" in cnipa.setup_hint

    assert CNIPA_AUTHORIZED_API_SOURCE in capabilities
    assert capabilities[CNIPA_AUTHORIZED_API_SOURCE].availability == "unavailable"


def test_build_cnipa_query_pack_uses_plan_queries_and_filters():
    intent = SearchIntent(
        id="intent-1",
        project_id="p-1",
        source_project_hash="hash",
        technical_object="城市体检智能体",
        technical_problem="任务编排缺少可信复核",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排", "证据链"],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q"],
        cpc_candidates=["G06Q10/063"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
    )
    plan = AgentSearchPlan(
        id="plan-1",
        project_id="p-1",
        intent_id="intent-1",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全公开和授权专利。",
                queries=["城市体检 智能体 任务编排 证据链"],
                sources=["cnipa_official_export"],
            )
        ],
        target_sources=["cnipa_official_export"],
        filters={"jurisdictions": ["CN"], "date_range": "2016-2026"},
    )

    pack = build_cnipa_query_pack(intent, plan)

    assert pack.project_id == "p-1"
    assert pack.plan_id == "plan-1"
    assert pack.source_id == "cnipa_official_export"
    assert pack.keywords_zh == ["城市体检", "智能体", "任务编排", "证据链"]
    assert pack.negative_keywords == ["医疗体检"]
    assert pack.ipc_candidates == ["G06Q"]
    assert pack.cpc_candidates == ["G06Q10/063"]
    assert pack.date_range == "2016-2026"
    assert pack.strategies[0].strategy_group_id == "broad-recall"
    assert pack.strategies[0].queries == ["城市体检 智能体 任务编排 证据链"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_patent_sources.py -q
```

Expected: FAIL with import errors for `backend.app.knowledge.patent_sources` and missing schema classes.

- [ ] **Step 3: Add schemas**

In `backend/app/schemas.py`, insert after `SearchPlanStrategyGroup`:

```python
class PatentSourceCapability(BaseModel):
    source_id: str
    display_name: str
    jurisdictions: list[str] = Field(default_factory=list)
    modes: list[Literal["live_search", "official_export", "assisted_capture", "authorized_api"]] = Field(default_factory=list)
    availability: Literal["available", "manual_import", "config_required", "unavailable"]
    trusted_patent_source: bool = False
    evidence_origin: Literal["official_export", "authorized_api", "public_web", "third_party", "legacy_helper"]
    setup_hint: str = ""


class CnipaQueryPackStrategy(BaseModel):
    strategy_group_id: str
    label: str
    purpose: str
    queries: list[str] = Field(default_factory=list)


class CnipaQueryPack(BaseModel):
    project_id: str
    plan_id: str
    intent_id: str
    source_id: str = "cnipa_official_export"
    technical_object: str = ""
    technical_problem: str = ""
    technical_means: str = ""
    keywords_zh: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    ipc_candidates: list[str] = Field(default_factory=list)
    cpc_candidates: list[str] = Field(default_factory=list)
    date_range: str = ""
    strategies: list[CnipaQueryPackStrategy] = Field(default_factory=list)
```

- [ ] **Step 4: Add source registry module**

Create `backend/app/knowledge/patent_sources.py`:

```python
from __future__ import annotations

from backend.app.schemas import (
    AgentSearchPlan,
    CnipaQueryPack,
    CnipaQueryPackStrategy,
    PatentSourceCapability,
    SearchIntent,
)

CNIPA_OFFICIAL_EXPORT_SOURCE = "cnipa_official_export"
CNIPA_AUTHORIZED_API_SOURCE = "cnipa_authorized_api"
CNIPA_LEGACY_EPUB_SOURCE = "cnipa_epub"
WIPO_PATENTSCOPE_SOURCE = "wipo_patentscope"
GOOGLE_PATENTS_SOURCE = "google_patents"


def list_patent_source_capabilities() -> list[PatentSourceCapability]:
    return [
        PatentSourceCapability(
            source_id=CNIPA_OFFICIAL_EXPORT_SOURCE,
            display_name="CNIPA 官方导出",
            jurisdictions=["CN"],
            modes=["official_export"],
            availability="manual_import",
            trusted_patent_source=True,
            evidence_origin="official_export",
            setup_hint="从 CNIPA 官方检索系统导出 CSV/XLSX/ZIP 后导入 GrantAtlas。",
        ),
        PatentSourceCapability(
            source_id=CNIPA_LEGACY_EPUB_SOURCE,
            display_name="CNIPA EPUB legacy helper",
            jurisdictions=["CN"],
            modes=["live_search"],
            availability="config_required",
            trusted_patent_source=True,
            evidence_origin="legacy_helper",
            setup_hint="高级模式：配置 CNIPA_EPUB_SEARCH_SCRIPT 后启用。",
        ),
        PatentSourceCapability(
            source_id=WIPO_PATENTSCOPE_SOURCE,
            display_name="WIPO Patentscope",
            jurisdictions=["WO"],
            modes=["live_search"],
            availability="available",
            trusted_patent_source=True,
            evidence_origin="public_web",
            setup_hint="用于国际公开文献补充检索。",
        ),
        PatentSourceCapability(
            source_id=GOOGLE_PATENTS_SOURCE,
            display_name="Google Patents",
            jurisdictions=["CN", "WO", "US", "EP"],
            modes=["live_search"],
            availability="config_required",
            trusted_patent_source=True,
            evidence_origin="public_web",
            setup_hint="通过 PATENT_ENABLE_GOOGLE_PATENTS_FALLBACK 显式启用。",
        ),
        PatentSourceCapability(
            source_id=CNIPA_AUTHORIZED_API_SOURCE,
            display_name="CNIPA 授权 API",
            jurisdictions=["CN"],
            modes=["authorized_api"],
            availability="unavailable",
            trusted_patent_source=True,
            evidence_origin="authorized_api",
            setup_hint="获得正式接口授权后接入。",
        ),
    ]


def build_cnipa_query_pack(intent: SearchIntent | None, plan: AgentSearchPlan | None) -> CnipaQueryPack:
    project_id = plan.project_id if plan else (intent.project_id if intent else "")
    plan_id = plan.id if plan else ""
    intent_id = intent.id if intent else (plan.intent_id if plan else "")
    filters = plan.filters if plan else {}
    strategies = [
        CnipaQueryPackStrategy(
            strategy_group_id=group.id,
            label=group.label,
            purpose=group.purpose,
            queries=list(group.queries),
        )
        for group in (plan.strategy_groups if plan else [])
    ]
    return CnipaQueryPack(
        project_id=project_id,
        plan_id=plan_id,
        intent_id=intent_id,
        technical_object=intent.technical_object if intent else "",
        technical_problem=intent.technical_problem if intent else "",
        technical_means=intent.technical_means if intent else "",
        keywords_zh=list(intent.keywords_zh if intent else []),
        negative_keywords=list(intent.negative_keywords if intent else []),
        ipc_candidates=list(intent.ipc_candidates if intent else []),
        cpc_candidates=list(intent.cpc_candidates if intent else []),
        date_range=str(filters.get("date_range") or (intent.date_range if intent else "")),
        strategies=strategies,
    )
```

- [ ] **Step 5: Wire default project sources**

In `backend/app/services/project_knowledge_service.py`, import constants:

```python
from backend.app.knowledge.patent_sources import (
    CNIPA_OFFICIAL_EXPORT_SOURCE,
    WIPO_PATENTSCOPE_SOURCE,
    build_cnipa_query_pack,
)
```

Replace source constants with:

```python
PROJECT_PATENT_PROVIDER_SOURCES = [CNIPA_OFFICIAL_EXPORT_SOURCE, WIPO_PATENTSCOPE_SOURCE]
PROJECT_PATENT_CORPUS_SOURCES = [*PROJECT_PATENT_PROVIDER_SOURCES, "cnipa_epub", "google_patents"]
PROJECT_PATENT_PROVIDER_SOURCE_SET = frozenset(PROJECT_PATENT_CORPUS_SOURCES)
```

Add this service function after `knowledge_overview`:

```python
def get_cnipa_query_pack(store: SQLiteStore, project_id: str) -> CnipaQueryPack:
    intent = store.get_latest_search_intent(project_id)
    plan = store.get_latest_agent_search_plan(project_id)
    return build_cnipa_query_pack(intent, plan)
```

Also add `CnipaQueryPack` to the `backend.app.schemas` import list in this file.

- [ ] **Step 6: Add service test for query pack retrieval**

In `tests/test_project_knowledge.py`, add:

```python
from backend.app.services.project_knowledge_service import get_cnipa_query_pack


def test_project_knowledge_cnipa_query_pack_uses_latest_plan(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])

    pack = get_cnipa_query_pack(store, project.id)

    assert pack.project_id == project.id
    assert pack.plan_id == overview.latest_plan.id
    assert pack.source_id == "cnipa_official_export"
    assert pack.strategies
    assert pack.strategies[0].queries
```

- [ ] **Step 7: Run tests**

Run:

```bash
python3 -m pytest tests/test_patent_sources.py tests/test_project_knowledge.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/knowledge/patent_sources.py backend/app/services/project_knowledge_service.py tests/test_patent_sources.py tests/test_project_knowledge.py
git commit -m "feat: add patent source capabilities"
```

---

### Task 2: CNIPA Official Export Importer

**Files:**
- Create: `backend/app/knowledge/cnipa_export.py`
- Modify: `backend/app/schemas.py`
- Test: `tests/test_cnipa_export_importer.py`

**Interfaces:**
- Consumes:
  - `PatentSearchHit`
  - `normalize_publication_number(value: str | None) -> str`
  - `dedupe_patent_search_hits(hits: list[PatentSearchHit]) -> list[PatentSearchHit]`
- Produces:
  - `CnipaExportImportContext`
  - `CnipaExportImportFailure`
  - `CnipaExportImportResult`
  - `parse_cnipa_official_export_file(path: Path, context: CnipaExportImportContext) -> CnipaExportImportResult`

- [ ] **Step 1: Write failing importer tests**

Create `tests/test_cnipa_export_importer.py`:

```python
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from backend.app.knowledge.cnipa_export import (
    CnipaExportImportContext,
    parse_cnipa_official_export_file,
)


def _context() -> CnipaExportImportContext:
    return CnipaExportImportContext(
        project_id="p-1",
        plan_id="plan-1",
        import_ledger_id="ledger-1",
        query="城市体检 智能体",
        strategy_group_id="cnipa-official-export",
    )


def test_parse_cnipa_csv_export_maps_fields(tmp_path):
    path = tmp_path / "cnipa.csv"
    path.write_text(
        "公开公告号,专利名称,申请人,公开日,摘要,IPC\n"
        "CN112233445A,城市体检智能体任务编排方法,示例公司,2024-01-01,公开了一种任务编排方法。,G06Q\n",
        encoding="utf-8-sig",
    )

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 1
    assert result.raw_file_hash
    assert result.hits[0].source == "cnipa_official_export"
    assert result.hits[0].publication_number == "CN112233445A"
    assert result.hits[0].title == "城市体检智能体任务编排方法"
    assert result.hits[0].applicant == "示例公司"
    assert result.hits[0].ipc == ["G06Q"]
    assert result.hits[0].metadata["raw_file_hash"] == result.raw_file_hash
    assert result.hits[0].metadata["import_ledger_id"] == "ledger-1"
    assert result.hits[0].metadata["source_file_name"] == "cnipa.csv"
    assert result.hits[0].metadata["row_number"] == 2


def test_parse_cnipa_xlsx_export_maps_fields(tmp_path):
    path = tmp_path / "cnipa.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["申请公布号", "名称", "专利权人", "摘要"])
    sheet.append(["CN998877665A", "可信复核系统", "示例研究院", "公开了一种可信复核系统。"])
    workbook.save(path)

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 1
    assert result.hits[0].publication_number == "CN998877665A"
    assert result.hits[0].title == "可信复核系统"
    assert result.hits[0].applicant == "示例研究院"


def test_parse_cnipa_zip_export_reads_nested_tables_and_warns_on_pdf(tmp_path):
    csv_path = tmp_path / "inner.csv"
    csv_path.write_text(
        "申请号,题名,摘要\nCN202410000001,城市体检证据链方法,公开了一种证据链复核方法。\n",
        encoding="utf-8",
    )
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 scanned placeholder")
    zip_path = tmp_path / "cnipa.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.write(csv_path, "metadata/inner.csv")
        archive.write(pdf_path, "docs/scan.pdf")

    result = parse_cnipa_official_export_file(zip_path, context=_context())

    assert result.row_count == 1
    assert result.parsed_count == 1
    assert result.hits[0].application_number == "CN202410000001"
    assert any("scan.pdf" in warning for warning in result.warnings)


def test_parse_cnipa_export_rejects_rows_without_identifier_or_title(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("申请人,公开日\n示例公司,2024-01-01\n", encoding="utf-8")

    result = parse_cnipa_official_export_file(path, context=_context())

    assert result.parsed_count == 0
    assert result.failures[0].code == "missing_required_fields"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_cnipa_export_importer.py -q
```

Expected: FAIL with import error for `backend.app.knowledge.cnipa_export`.

- [ ] **Step 3: Add import result schemas**

In `backend/app/schemas.py`, insert after `PatentSearchHit`:

```python
class CnipaExportImportFailure(BaseModel):
    source_file_name: str
    row_number: int = 0
    code: str
    message: str


class CnipaExportImportResult(BaseModel):
    import_ledger_id: str
    source_id: str = "cnipa_official_export"
    raw_file_hash: str = ""
    detected_schema: str = ""
    row_count: int = 0
    parsed_count: int = 0
    hits: list[PatentSearchHit] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[CnipaExportImportFailure] = Field(default_factory=list)
```

- [ ] **Step 4: Add importer module**

Create `backend/app/knowledge/cnipa_export.py`:

```python
from __future__ import annotations

import csv
import hashlib
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook

from backend.app.knowledge.patent_search import (
    dedupe_patent_search_hits,
    normalize_publication_number,
)
from backend.app.knowledge.patent_sources import CNIPA_OFFICIAL_EXPORT_SOURCE
from backend.app.research.providers import sanitize_untrusted_text
from backend.app.schemas import CnipaExportImportFailure, CnipaExportImportResult, PatentSearchHit

FIELD_ALIASES: dict[str, str] = {
    "公开公告号": "publication_number",
    "申请公布号": "publication_number",
    "公开号": "publication_number",
    "授权公告号": "publication_number",
    "Publication Number": "publication_number",
    "publication_number": "publication_number",
    "申请号": "application_number",
    "Application Number": "application_number",
    "application_number": "application_number",
    "专利名称": "title",
    "名称": "title",
    "题名": "title",
    "发明名称": "title",
    "Title": "title",
    "title": "title",
    "申请人": "applicant",
    "专利权人": "applicant",
    "Applicant": "applicant",
    "applicant": "applicant",
    "发明人": "inventor",
    "Inventor": "inventor",
    "公开日": "publication_date",
    "公开公告日": "publication_date",
    "Publication Date": "publication_date",
    "publication_date": "publication_date",
    "申请日": "application_date",
    "Application Date": "application_date",
    "摘要": "abstract",
    "Abstract": "abstract",
    "abstract": "abstract",
    "IPC": "ipc",
    "国际分类号": "ipc",
    "CPC": "cpc",
    "权利要求": "claims",
    "Claims": "claims",
    "说明书": "description",
    "Description": "description",
    "链接": "url",
    "详情页": "url",
    "URL": "url",
    "url": "url",
}

LIST_FIELDS = {"ipc", "cpc"}
TABLE_SUFFIXES = {".csv", ".txt", ".xlsx", ".xlsm"}
ATTACHMENT_SUFFIXES = {".pdf", ".xml"}


@dataclass(frozen=True)
class CnipaExportImportContext:
    project_id: str
    plan_id: str
    import_ledger_id: str
    query: str
    strategy_group_id: str


def parse_cnipa_official_export_file(path: Path, *, context: CnipaExportImportContext) -> CnipaExportImportResult:
    raw_file_hash = _file_hash(path)
    if path.suffix.lower() == ".zip":
        return _parse_zip(path, context=context, raw_file_hash=raw_file_hash)
    rows = _parse_table(path)
    return _rows_to_result(
        rows,
        context=context,
        raw_file_hash=raw_file_hash,
        detected_schema=path.suffix.lower().lstrip("."),
        source_file_name=path.name,
    )


def _parse_zip(path: Path, *, context: CnipaExportImportContext, raw_file_hash: str) -> CnipaExportImportResult:
    warnings: list[str] = []
    failures: list[CnipaExportImportFailure] = []
    hits: list[PatentSearchHit] = []
    row_count = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(path) as archive:
            for member in sorted(archive.infolist(), key=lambda item: item.filename):
                if member.is_dir():
                    continue
                member_name = Path(member.filename).name
                suffix = Path(member_name).suffix.lower()
                if suffix in TABLE_SUFFIXES:
                    child = Path(tmpdir) / f"{uuid4().hex}-{member_name}"
                    child.write_bytes(archive.read(member))
                    partial = _rows_to_result(
                        _parse_table(child),
                        context=context,
                        raw_file_hash=raw_file_hash,
                        detected_schema=f"zip:{suffix.lstrip('.')}",
                        source_file_name=member_name,
                    )
                    row_count += partial.row_count
                    hits.extend(partial.hits)
                    warnings.extend(partial.warnings)
                    failures.extend(partial.failures)
                elif suffix in ATTACHMENT_SUFFIXES:
                    warnings.append(f"{member_name} 已作为附件保留；未从该文件生成候选。")
    deduped = dedupe_patent_search_hits(hits)
    return CnipaExportImportResult(
        import_ledger_id=context.import_ledger_id,
        raw_file_hash=raw_file_hash,
        detected_schema="zip",
        row_count=row_count,
        parsed_count=len(deduped),
        hits=deduped,
        warnings=warnings,
        failures=failures,
    )


def _parse_table(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return _parse_csv(path)
    if suffix in {".xlsx", ".xlsm"}:
        return _parse_xlsx(path)
    raise ValueError(f"Unsupported CNIPA export table type: {suffix}")


def _parse_csv(path: Path) -> list[dict[str, Any]]:
    text = _read_text(path)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    return [_normalize_row(row) for row in reader if any((value or "").strip() for value in row.values())]


def _parse_xlsx(path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    parsed: list[dict[str, Any]] = []
    for raw_row in rows[1:]:
        row = {header: "" if value is None else str(value).strip() for header, value in zip(headers, raw_row)}
        if any(row.values()):
            parsed.append(_normalize_row(row))
    return parsed


def _rows_to_result(
    rows: list[dict[str, Any]],
    *,
    context: CnipaExportImportContext,
    raw_file_hash: str,
    detected_schema: str,
    source_file_name: str,
) -> CnipaExportImportResult:
    hits: list[PatentSearchHit] = []
    failures: list[CnipaExportImportFailure] = []
    for index, row in enumerate(rows, start=2):
        publication_number = normalize_publication_number(str(row.get("publication_number") or ""))
        application_number = normalize_publication_number(str(row.get("application_number") or ""))
        title = sanitize_untrusted_text(str(row.get("title") or ""), max_len=300)
        abstract = sanitize_untrusted_text(str(row.get("abstract") or "")) or None
        if not (publication_number or application_number) or not (title or abstract):
            failures.append(
                CnipaExportImportFailure(
                    source_file_name=source_file_name,
                    row_number=index,
                    code="missing_required_fields",
                    message="CNIPA export row requires publication/application number and title/abstract.",
                )
            )
            continue
        metadata = {
            "raw_file_hash": raw_file_hash,
            "import_ledger_id": context.import_ledger_id,
            "source_file_name": source_file_name,
            "row_number": index,
            "strategy_group": context.strategy_group_id,
            "evidence_origin": "official_export",
        }
        for key in ["claims", "description", "inventor", "application_date"]:
            if row.get(key):
                metadata[key] = row[key]
        hits.append(
            PatentSearchHit(
                id=uuid4().hex,
                source=CNIPA_OFFICIAL_EXPORT_SOURCE,
                query=context.query,
                title=title or publication_number or application_number,
                url=str(row.get("url") or ""),
                publication_number=publication_number or None,
                application_number=application_number or None,
                applicant=str(row.get("applicant") or ""),
                publication_date=str(row.get("publication_date") or ""),
                abstract=abstract,
                ipc=list(row.get("ipc") or []),
                cpc=list(row.get("cpc") or []),
                metadata=metadata,
            )
        )
    deduped = dedupe_patent_search_hits(hits)
    return CnipaExportImportResult(
        import_ledger_id=context.import_ledger_id,
        raw_file_hash=raw_file_hash,
        detected_schema=detected_schema,
        row_count=len(rows),
        parsed_count=len(deduped),
        hits=deduped,
        failures=failures,
    )


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in row.items():
        if raw_key is None:
            continue
        key = FIELD_ALIASES.get(str(raw_key).strip(), str(raw_key).strip())
        value = "" if raw_value is None else str(raw_value).strip()
        if not value:
            continue
        normalized[key] = _split_list(value) if key in LIST_FIELDS else value
    return normalized


def _split_list(value: str) -> list[str]:
    normalized = value.replace("；", ";").replace("，", ";").replace(",", ";").replace("、", ";").replace("|", ";")
    return [part.strip() for part in normalized.split(";") if part.strip()]


def _read_text(path: Path) -> str:
    for encoding in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CNIPA export table encoding is not supported. Please save it as UTF-8 or GB18030.")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 5: Run tests**

Run:

```bash
python3 -m pytest tests/test_cnipa_export_importer.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/knowledge/cnipa_export.py tests/test_cnipa_export_importer.py
git commit -m "feat: parse cnipa official exports"
```

---

### Task 3: Project Knowledge Import API And Ledger Storage

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/storage.py`
- Modify: `backend/app/services/project_knowledge_service.py`
- Modify: `backend/app/api/project_knowledge.py`
- Test: `tests/test_project_knowledge.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `parse_cnipa_official_export_file(path, context=...)`
  - `patent_hit_to_candidate(hit, project_id, plan_id, strategy_group_id)`
  - `ProjectKnowledgeState`
- Produces:
  - `ProjectKnowledgeImportLedger`
  - `CnipaExportImportResponse`
  - `SQLiteStore.create_project_knowledge_import_ledger(ledger)`
  - `SQLiteStore.list_project_knowledge_import_ledgers(project_id, plan_id=None)`
  - `import_cnipa_official_export(store, project_id, plan_id, stored_path) -> ProjectKnowledgeOverview`
  - `POST /api/projects/{project_id}/knowledge/cnipa-export-imports`

- [ ] **Step 1: Write failing service test**

In `tests/test_project_knowledge.py`, add:

```python
def test_import_cnipa_official_export_adds_real_candidates_and_ledger(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    export_path = tmp_path / "cnipa.csv"
    export_path.write_text(
        "公开公告号,专利名称,摘要\n"
        "CN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
        encoding="utf-8",
    )

    imported = import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path)

    assert imported.state.status == "candidates_pending"
    assert imported.state.candidate_count == 1
    assert imported.state.quality_flags == ["candidates_need_confirmation"]
    assert imported.candidates[0].source == "cnipa_official_export"
    assert imported.candidates[0].metadata["evidence_origin"] == "official_export"
    ledgers = store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id)
    assert len(ledgers) == 1
    assert ledgers[0].source_id == "cnipa_official_export"
    assert ledgers[0].parsed_count == 1
    assert ledgers[0].retained_candidate_ids == [imported.candidates[0].id]
```

- [ ] **Step 2: Run service test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py::test_import_cnipa_official_export_adds_real_candidates_and_ledger -q
```

Expected: FAIL with missing `import_cnipa_official_export` and storage ledger methods.

- [ ] **Step 3: Add ledger schemas**

In `backend/app/schemas.py`, insert after `ProjectSearchLedger`:

```python
class ProjectKnowledgeImportLedger(BaseModel):
    id: str
    project_id: str
    plan_id: str
    source_id: str
    source_file_name: str
    raw_file_hash: str = ""
    detected_schema: str = ""
    row_count: int = 0
    parsed_count: int = 0
    retained_candidate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[CnipaExportImportFailure] = Field(default_factory=list)
    created_at: str = ""


```

Insert this response schema immediately after `ProjectKnowledgeOverview` in `backend/app/schemas.py`:

```python
class CnipaExportImportResponse(BaseModel):
    overview: ProjectKnowledgeOverview
    ledger: ProjectKnowledgeImportLedger
```

- [ ] **Step 4: Add storage table and methods**

In `backend/app/storage.py`, add `ProjectKnowledgeImportLedger` to imports. Add this table next to `project_search_ledgers`:

```python
create table if not exists project_knowledge_import_ledgers (
    id text primary key,
    project_id text not null,
    plan_id text not null,
    ledger_json text not null,
    created_at text not null,
    foreign key(project_id) references projects(id)
);
```

Add methods near search ledger methods:

```python
def create_project_knowledge_import_ledger(self, ledger: ProjectKnowledgeImportLedger) -> ProjectKnowledgeImportLedger:
    with self.connection:
        self.connection.execute(
            """
            insert or replace into project_knowledge_import_ledgers(id, project_id, plan_id, ledger_json, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                ledger.id,
                ledger.project_id,
                ledger.plan_id,
                ledger.model_dump_json(),
                ledger.created_at,
            ),
        )
    return ledger


def list_project_knowledge_import_ledgers(
    self,
    project_id: str,
    plan_id: str | None = None,
) -> list[ProjectKnowledgeImportLedger]:
    if plan_id:
        rows = self.connection.execute(
            """
            select ledger_json from project_knowledge_import_ledgers
            where project_id = ? and plan_id = ?
            order by created_at desc, rowid desc
            """,
            (project_id, plan_id),
        ).fetchall()
    else:
        rows = self.connection.execute(
            """
            select ledger_json from project_knowledge_import_ledgers
            where project_id = ?
            order by created_at desc, rowid desc
            """,
            (project_id,),
        ).fetchall()
    return [ProjectKnowledgeImportLedger.model_validate_json(row["ledger_json"]) for row in rows]
```

- [ ] **Step 5: Add import service**

In `backend/app/services/project_knowledge_service.py`, import:

```python
from pathlib import Path
from backend.app.knowledge.cnipa_export import CnipaExportImportContext, parse_cnipa_official_export_file
from backend.app.schemas import ProjectKnowledgeImportLedger
```

Add after `run_agent_search_plan`:

```python
def import_cnipa_official_export(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
    stored_path: Path,
) -> ProjectKnowledgeOverview:
    _state, plan = _get_active_plan(store, project_id, plan_id)
    ledger_id = uuid.uuid4().hex
    query = ""
    strategy_group_id = "cnipa-official-export"
    if plan.strategy_groups:
        first_group = plan.strategy_groups[0]
        strategy_group_id = first_group.id
        query = first_group.queries[0] if first_group.queries else first_group.label
    result = parse_cnipa_official_export_file(
        stored_path,
        context=CnipaExportImportContext(
            project_id=project_id,
            plan_id=plan_id,
            import_ledger_id=ledger_id,
            query=query,
            strategy_group_id=strategy_group_id,
        ),
    )
    candidates = [
        patent_hit_to_candidate(
            hit,
            project_id=project_id,
            plan_id=plan_id,
            strategy_group_id=str(hit.metadata.get("strategy_group") or strategy_group_id),
        )
        for hit in result.hits
    ]
    existing_candidates = store.list_prior_art_candidates(project_id, plan_id)
    store.apply_prior_art_candidate_updates(candidates)
    all_candidates = store.list_prior_art_candidates(project_id, plan_id)
    flags = ["candidates_need_confirmation"] if candidates else ["no_hits"]
    if result.warnings:
        flags.append("cnipa_export_parse_warnings")
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="candidates_pending" if candidates else "failed",
        active_intent_id=plan.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(all_candidates),
        quality_flags=flags,
    )
    store.upsert_project_knowledge_state(state)
    existing_ids = {candidate.id for candidate in existing_candidates}
    retained_ids = [candidate.id for candidate in all_candidates if candidate.id not in existing_ids]
    ledger = ProjectKnowledgeImportLedger(
        id=ledger_id,
        project_id=project_id,
        plan_id=plan_id,
        source_id=CNIPA_OFFICIAL_EXPORT_SOURCE,
        source_file_name=stored_path.name,
        raw_file_hash=result.raw_file_hash,
        detected_schema=result.detected_schema,
        row_count=result.row_count,
        parsed_count=result.parsed_count,
        retained_candidate_ids=retained_ids,
        warnings=result.warnings,
        failures=result.failures,
        created_at=_now(),
    )
    store.create_project_knowledge_import_ledger(ledger)
    return knowledge_overview(store, project_id)
```

- [ ] **Step 6: Run service test**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py::test_import_cnipa_official_export_adds_real_candidates_and_ledger -q
```

Expected: PASS.

- [ ] **Step 7: Write failing API tests**

In `tests/test_api.py`, add imports if missing:

```python
from pathlib import Path
```

Add test:

```python
def test_project_knowledge_cnipa_export_upload_returns_overview(tmp_path):
    client = _test_app_without_env(tmp_path)
    created = client.post(
        "/api/projects",
        json={
            "name": "城市体检智能体",
            "draft_text": "通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        },
    ).json()
    project_id = created["id"]
    overview = client.post(f"/api/projects/{project_id}/knowledge/search-intent").json()
    plan_id = overview["latest_plan"]["id"]
    upload = client.post(
        f"/api/projects/{project_id}/knowledge/cnipa-export-imports",
        data={"plan_id": plan_id},
        files={
            "file": (
                "cnipa.csv",
                "公开公告号,专利名称,摘要\nCN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
                "text/csv",
            )
        },
    )

    assert upload.status_code == 200
    data = upload.json()
    assert data["overview"]["state"]["status"] == "candidates_pending"
    assert data["overview"]["candidates"][0]["source"] == "cnipa_official_export"
    assert data["ledger"]["parsed_count"] == 1

    ledgers = client.get(f"/api/projects/{project_id}/knowledge/import-ledgers").json()
    assert ledgers["ledgers"][0]["source_id"] == "cnipa_official_export"
```

- [ ] **Step 8: Add API endpoints**

In `backend/app/api/project_knowledge.py`, import:

```python
import shutil
import uuid
from pathlib import Path
from fastapi import File, Form, UploadFile
from backend.app.knowledge.patent_sources import list_patent_source_capabilities
from backend.app.services.project_knowledge_service import get_cnipa_query_pack, import_cnipa_official_export
```

Add endpoints:

```python
@router.get("/api/patent-sources")
def list_patent_sources() -> dict:
    return {"sources": [source.model_dump(mode="json") for source in list_patent_source_capabilities()]}


@router.get("/api/projects/{project_id}/knowledge/cnipa-query-pack")
def get_project_cnipa_query_pack(project_id: str, request: Request) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    return get_cnipa_query_pack(request.app.state.store, project_id).model_dump(mode="json")


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
    with stored_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    try:
        overview = import_cnipa_official_export(request.app.state.store, project_id, plan_id, stored_path)
    except ProjectKnowledgeConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ledgers = request.app.state.store.list_project_knowledge_import_ledgers(project_id, plan_id)
    return {"overview": overview.model_dump(mode="json"), "ledger": ledgers[0].model_dump(mode="json")}


@router.get("/api/projects/{project_id}/knowledge/import-ledgers")
def list_project_knowledge_import_ledgers(project_id: str, request: Request, plan_id: str | None = None) -> dict:
    repo = get_project_repository(request)
    require_project(project_id, repo)
    ledgers = request.app.state.store.list_project_knowledge_import_ledgers(project_id, plan_id)
    return {"ledgers": [ledger.model_dump(mode="json") for ledger in ledgers]}
```

- [ ] **Step 9: Run API and service tests**

Run:

```bash
python3 -m pytest tests/test_api.py tests/test_project_knowledge.py tests/test_cnipa_export_importer.py tests/test_patent_sources.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas.py backend/app/storage.py backend/app/services/project_knowledge_service.py backend/app/api/project_knowledge.py tests/test_project_knowledge.py tests/test_api.py
git commit -m "feat: import cnipa exports into project knowledge"
```

---

### Task 4: Corpus Quality Gates For CNIPA Official Evidence

**Files:**
- Modify: `backend/app/services/project_knowledge_service.py`
- Modify: `backend/app/grantability.py`
- Test: `tests/test_project_knowledge.py`
- Test: `tests/test_grantability.py`

**Interfaces:**
- Consumes: `PriorArtCandidate.source == "cnipa_official_export"` and candidate metadata keys `claims`, `description`, `abstract`.
- Produces:
  - `cnipa_export_metadata_only`
  - `cnipa_export_missing_claims`
  - `cnipa_export_partial_fulltext`
  - status `ready` only when coverage thresholds are sufficient.

- [ ] **Step 1: Write failing corpus quality tests**

In `tests/test_project_knowledge.py`, add:

```python
def test_cnipa_official_export_builds_ready_corpus_with_claims_and_fulltext(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    for number in ["CN112233445A", "CN112233446A"]:
        store.upsert_prior_art_candidate(
            PriorArtCandidate(
                id=f"candidate-{number}",
                project_id=project.id,
                plan_id=plan_id,
                source="cnipa_official_export",
                title=f"城市体检方法 {number}",
                publication_number=number,
                abstract="公开了一种城市体检方法。",
                url="",
                fulltext_status="available",
                user_decision="include",
                metadata={"claims": "1. 一种城市体检方法。", "description": "说明书全文。"},
            )
        )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=2,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "ready"
    assert result.state.document_count == 2
    assert result.state.claim_coverage == 1.0
    assert result.state.fulltext_coverage == 1.0
    assert result.state.quality_flags == []


def test_cnipa_metadata_only_corpus_needs_supplemental_search(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            url="",
            user_decision="include",
            metadata={"evidence_origin": "official_export"},
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=1,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert "cnipa_export_metadata_only" in result.state.quality_flags
    assert "synthetic_evidence" not in result.state.quality_flags
    assert "non_patent_source" not in result.state.quality_flags
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py::test_cnipa_official_export_builds_ready_corpus_with_claims_and_fulltext tests/test_project_knowledge.py::test_cnipa_metadata_only_corpus_needs_supplemental_search -q
```

Expected: FAIL because current coverage logic treats all real patent sources as full coverage.

- [ ] **Step 3: Add coverage helpers**

In `backend/app/services/project_knowledge_service.py`, add near constants:

```python
def _candidate_has_claims(candidate: PriorArtCandidate) -> bool:
    return bool(str(candidate.metadata.get("claims") or "").strip())


def _candidate_has_fulltext(candidate: PriorArtCandidate) -> bool:
    return bool(
        candidate.fulltext_status == "available"
        or candidate.abstract
        or str(candidate.metadata.get("description") or "").strip()
        or str(candidate.metadata.get("claims") or "").strip()
    )


def _ratio(count: int, total: int) -> float:
    return count / total if total else 0.0
```

In `create_project_corpus_from_included_candidates`, replace the real-patent `else` coverage branch with:

```python
    else:
        claim_coverage = _ratio(sum(1 for candidate in patent_included if _candidate_has_claims(candidate)), len(included))
        fulltext_coverage = _ratio(sum(1 for candidate in patent_included if _candidate_has_fulltext(candidate)), len(included))
        quality_flags = []
        cnipa_included = [candidate for candidate in patent_included if candidate.source == CNIPA_OFFICIAL_EXPORT_SOURCE]
        if cnipa_included and fulltext_coverage == 0.0:
            quality_flags.append("cnipa_export_metadata_only")
        elif cnipa_included and fulltext_coverage < 1.0:
            quality_flags.append("cnipa_export_partial_fulltext")
        if cnipa_included and claim_coverage < 1.0:
            quality_flags.append("cnipa_export_missing_claims")
```

Set status using:

```python
    partial_cnipa = any(flag.startswith("cnipa_export_") for flag in quality_flags)
    corpus_status = "needs_supplemental_search" if (all_synthetic or includes_non_patent or partial_cnipa) else ("ready" if included else "failed")
```

Use the same `partial_cnipa` value for `state_status`.

Replace the later state-quality reassignment block with this shape so CNIPA coverage flags are preserved:

```python
    if all_synthetic:
        quality_flags = ["synthetic_evidence"]
    elif includes_non_patent:
        quality_flags = ["non_patent_source"]
    elif not included:
        quality_flags = ["empty_corpus"]
```

- [ ] **Step 4: Add grantability copy for CNIPA quality flags**

In `backend/app/grantability.py`, after the existing `insufficient_corpus` block, add:

```python
    if any(flag.startswith("cnipa_export_") for flag in knowledge_flags):
        low_evidence_flags.append("CNIPA 官方导出文献已入库，但全文或权利要求覆盖不足，需补充导出全文后再确认授权前景。")
        fail_closed = True
```

- [ ] **Step 5: Add grantability test**

In `tests/test_grantability.py`, add a test near existing knowledge gate tests:

```python
def test_grantability_fails_closed_for_partial_cnipa_export_state():
    report = generate_grantability_report(
        project_id="proj-cnipa-partial",
        package=_sample_package(),
        disclosures=[_sample_disclosure()],
        patent_points=_sample_patent_points(),
        project_knowledge_state=ProjectKnowledgeState(
            project_id="proj-cnipa-partial",
            status="needs_supplemental_search",
            document_count=2,
            claim_coverage=0.0,
            fulltext_coverage=0.5,
            quality_flags=["cnipa_export_missing_claims"],
        ),
    )

    assert report.fail_closed is True
    assert any("CNIPA 官方导出文献已入库" in flag for flag in report.low_evidence_flags)
```

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_grantability.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/project_knowledge_service.py backend/app/grantability.py tests/test_project_knowledge.py tests/test_grantability.py
git commit -m "feat: gate cnipa export evidence quality"
```

---

### Task 5: Frontend CNIPA Export Workflow

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/features/corpus/CorpusWorkspace.tsx`
- Modify: `frontend/src/views/projectKnowledgeView.tsx`
- Test: `frontend/src/api.test.ts`
- Test: `frontend/src/projectKnowledgeView.test.tsx`
- Test: `frontend/src/features/corpus/CorpusWorkspace.test.tsx`

**Interfaces:**
- Consumes:
  - `GET /api/patent-sources`
  - `GET /api/projects/{project_id}/knowledge/cnipa-query-pack`
  - `POST /api/projects/{project_id}/knowledge/cnipa-export-imports`
- Produces:
  - `getPatentSources()`
  - `getProjectCnipaQueryPack(projectId)`
  - `listProjectKnowledgeImportLedgers(projectId, planId?)`
  - `uploadProjectCnipaExport(projectId, planId, file)`
  - UI copy that says CNIPA official export is the ordinary path when helper is not configured.

- [ ] **Step 1: Add API types and failing API tests**

In `frontend/src/api.ts`, plan to add these types near project knowledge types:

```ts
export interface PatentSourceCapability {
  source_id: string;
  display_name: string;
  jurisdictions: string[];
  modes: Array<"live_search" | "official_export" | "assisted_capture" | "authorized_api">;
  availability: "available" | "manual_import" | "config_required" | "unavailable";
  trusted_patent_source: boolean;
  evidence_origin: "official_export" | "authorized_api" | "public_web" | "third_party" | "legacy_helper";
  setup_hint: string;
}

export interface CnipaQueryPackStrategy {
  strategy_group_id: string;
  label: string;
  purpose: string;
  queries: string[];
}

export interface CnipaQueryPack {
  project_id: string;
  plan_id: string;
  intent_id: string;
  source_id: string;
  technical_object: string;
  technical_problem: string;
  technical_means: string;
  keywords_zh: string[];
  negative_keywords: string[];
  ipc_candidates: string[];
  cpc_candidates: string[];
  date_range: string;
  strategies: CnipaQueryPackStrategy[];
}

export interface ProjectKnowledgeImportLedger {
  id: string;
  project_id: string;
  plan_id: string;
  source_id: string;
  source_file_name: string;
  raw_file_hash: string;
  detected_schema: string;
  row_count: number;
  parsed_count: number;
  retained_candidate_ids: string[];
  warnings: string[];
  failures: Array<{ source_file_name: string; row_number: number; code: string; message: string }>;
  created_at: string;
}
```

In `frontend/src/api.test.ts`, add `getPatentSources`, `getProjectCnipaQueryPack`, `listProjectKnowledgeImportLedgers`, and `uploadProjectCnipaExport` to the import list. Then add this test:

```ts
it("calls patent source and CNIPA export endpoints", async () => {
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    requests.push({ url, init });
    if (url === "/api/patent-sources") {
      return new Response(JSON.stringify({ sources: [{ source_id: "cnipa_official_export", display_name: "CNIPA 官方导出" }] }), { status: 200 });
    }
    if (url.endsWith("/knowledge/cnipa-query-pack")) {
      return new Response(JSON.stringify({ project_id: "p-1", plan_id: "plan-1", intent_id: "intent-1", source_id: "cnipa_official_export", strategies: [] }), { status: 200 });
    }
    if (url.endsWith("/knowledge/import-ledgers?plan_id=plan-1")) {
      return new Response(JSON.stringify({ ledgers: [{ id: "ledger-1", source_id: "cnipa_official_export", parsed_count: 1 }] }), { status: 200 });
    }
    if (url.endsWith("/knowledge/cnipa-export-imports")) {
      return new Response(JSON.stringify({
        overview: { state: { project_id: "p-1", status: "candidates_pending" }, latest_intent: null, latest_plan: null, candidates: [], latest_corpus_version: null },
        ledger: { id: "ledger-2", source_id: "cnipa_official_export", parsed_count: 1 },
      }), { status: 200 });
    }
    return new Response(JSON.stringify({}), { status: 200 });
  }));
  const file = new File(["公开公告号,专利名称"], "cnipa.csv", { type: "text/csv" });

  const sources = await getPatentSources();
  const queryPack = await getProjectCnipaQueryPack("p-1");
  const ledgers = await listProjectKnowledgeImportLedgers("p-1", "plan-1");
  const result = await uploadProjectCnipaExport("p-1", "plan-1", file);

  expect(sources[0].source_id).toBe("cnipa_official_export");
  expect(queryPack.source_id).toBe("cnipa_official_export");
  expect(ledgers[0].source_id).toBe("cnipa_official_export");
  expect(result.ledger.source_id).toBe("cnipa_official_export");
  expect(requests.map((request) => request.url)).toEqual([
    "/api/patent-sources",
    "/api/projects/p-1/knowledge/cnipa-query-pack",
    "/api/projects/p-1/knowledge/import-ledgers?plan_id=plan-1",
    "/api/projects/p-1/knowledge/cnipa-export-imports",
  ]);
  expect(requests[3].init?.method).toBe("POST");
  expect(requests[3].init?.body).toBeInstanceOf(FormData);
});
```

- [ ] **Step 2: Implement API wrappers**

In `frontend/src/api.ts`, add:

```ts
export async function getPatentSources(): Promise<PatentSourceCapability[]> {
  const data = await request<{ sources: PatentSourceCapability[] }>("/api/patent-sources");
  return data.sources;
}

export async function getProjectCnipaQueryPack(projectId: string): Promise<CnipaQueryPack> {
  return request<CnipaQueryPack>(`/api/projects/${projectId}/knowledge/cnipa-query-pack`);
}

export async function listProjectKnowledgeImportLedgers(
  projectId: string,
  planId?: string,
): Promise<ProjectKnowledgeImportLedger[]> {
  const params = new URLSearchParams();
  if (planId) params.set("plan_id", planId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const data = await request<{ ledgers: ProjectKnowledgeImportLedger[] }>(
    `/api/projects/${projectId}/knowledge/import-ledgers${suffix}`,
  );
  return data.ledgers;
}

export async function uploadProjectCnipaExport(
  projectId: string,
  planId: string,
  file: File,
): Promise<{ overview: ProjectKnowledgeOverview; ledger: ProjectKnowledgeImportLedger }> {
  const form = new FormData();
  form.append("plan_id", planId);
  form.append("file", file);
  return request<{ overview: ProjectKnowledgeOverview; ledger: ProjectKnowledgeImportLedger }>(
    `/api/projects/${projectId}/knowledge/cnipa-export-imports`,
    { method: "POST", body: form },
  );
}
```

- [ ] **Step 3: Add view tests**

In `frontend/src/projectKnowledgeView.test.tsx`, add:

```tsx
it("renders CNIPA official export workflow instead of helper configuration", () => {
  render(
    <ProjectKnowledgeView
      selectedProject={project}
      knowledge={baseOverview}
      busy=""
      cnipaQueryPack={{
        project_id: "p-1",
        plan_id: "plan-1",
        intent_id: "intent-1",
        source_id: "cnipa_official_export",
        technical_object: "城市体检智能体",
        technical_problem: "任务编排缺少可信复核",
        technical_means: "多智能体任务编排",
        keywords_zh: ["城市体检", "智能体"],
        negative_keywords: ["医疗体检"],
        ipc_candidates: ["G06Q"],
        cpc_candidates: [],
        date_range: "2016-2026",
        strategies: [{ strategy_group_id: "broad", label: "宽召回检索", purpose: "找全相关专利", queries: ["城市体检 智能体"] }],
      }}
      importLedgers={[]}
      onGenerateKnowledgePlan={vi.fn()}
      onRunKnowledgeSearch={vi.fn()}
      onCandidateDecision={vi.fn()}
      onBuildProjectCorpus={vi.fn()}
      onImportCnipaExport={vi.fn()}
    />,
  );

  expect(screen.getByText("导入 CNIPA 官方导出物")).toBeInTheDocument();
  expect(screen.getByText("城市体检 智能体")).toBeInTheDocument();
  expect(screen.queryByText(/CNIPA_EPUB_SEARCH_SCRIPT/)).not.toBeInTheDocument();
});

it("labels imported CNIPA candidates as official export", () => {
  const knowledge: ProjectKnowledgeOverview = {
    ...baseOverview,
    candidates: [{ ...baseOverview.candidates[0], source: "cnipa_official_export" }],
  };

  render(
    <ProjectKnowledgeView
      selectedProject={project}
      knowledge={knowledge}
      busy=""
      importLedgers={[]}
      onGenerateKnowledgePlan={vi.fn()}
      onRunKnowledgeSearch={vi.fn()}
      onCandidateDecision={vi.fn()}
      onBuildProjectCorpus={vi.fn()}
      onImportCnipaExport={vi.fn()}
    />,
  );

  expect(screen.getByText(/CNIPA 官方导出/)).toBeInTheDocument();
});
```

- [ ] **Step 4: Implement view props and UI**

In `frontend/src/views/projectKnowledgeView.tsx`, update imports:

```ts
import type {
  CnipaQueryPack,
  PriorArtCandidate,
  ProjectKnowledgeImportLedger,
  ProjectKnowledgeOverview,
  ProjectRecord,
} from "@/api";
```

Add props:

```ts
  cnipaQueryPack?: CnipaQueryPack | null;
  importLedgers?: ProjectKnowledgeImportLedger[];
  onImportCnipaExport?: (file: File) => void;
```

Add source label helper near existing helpers:

```ts
function sourceLabel(source: string): string {
  if (source === "cnipa_official_export") return "CNIPA 官方导出";
  if (source === "cnipa_epub") return "CNIPA legacy helper";
  if (source === "wipo_patentscope") return "WIPO Patentscope";
  if (source === "google_patents") return "Google Patents";
  return source;
}
```

Replace `{candidate.source}` display with `{sourceLabel(candidate.source)}`.

Add a CNIPA import panel below the status card when `plan` exists:

```tsx
{plan && (
  <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-5">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <h3>CNIPA 官方导出</h3>
        <p className="text-sm text-[var(--text-primary)]/65">
          Agent 已生成 CNIPA 检索包。请在 CNIPA 官方系统执行检索并导出 CSV/XLSX/ZIP，再导入为真实中文专利候选。
        </p>
      </div>
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const file = new FormData(event.currentTarget).get("file");
          if (file instanceof File && file.size > 0) onImportCnipaExport?.(file);
          event.currentTarget.reset();
        }}
      >
        <input
          accept=".csv,.txt,.xlsx,.xlsm,.zip"
          className="text-sm"
          name="file"
          type="file"
        />
        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm font-medium"
          disabled={busy.startsWith("knowledge")}
          type="submit"
        >
          <Database size={16} />
          <span>导入 CNIPA 官方导出物</span>
        </button>
      </form>
    </div>
    {cnipaQueryPack?.strategies?.length ? (
      <div className="mt-4 grid gap-3">
        {cnipaQueryPack.strategies.map((strategy) => (
          <article className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-3" key={strategy.strategy_group_id}>
            <p className="font-semibold">{strategy.label}</p>
            <p className="text-sm text-[var(--text-primary)]/65">{strategy.purpose}</p>
            <p className="mt-2 text-xs text-[var(--text-primary)]/70">{strategy.queries.join(" / ")}</p>
          </article>
        ))}
      </div>
    ) : null}
    {importLedgers?.length ? (
      <div className="mt-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] p-3 text-sm">
        最近导入：{importLedgers[0].source_file_name}，解析 {importLedgers[0].parsed_count} 条候选。
      </div>
    ) : null}
  </section>
)}
```

- [ ] **Step 5: Wire App and CorpusWorkspace**

In `frontend/src/features/corpus/CorpusWorkspace.tsx`, add state fields:

```ts
  cnipaQueryPack?: CnipaQueryPack | null;
  importLedgers?: ProjectKnowledgeImportLedger[];
```

Add handler:

```ts
  onImportCnipaExport: (file: File) => Promise<void> | void;
```

Pass props to `ProjectKnowledgeView`:

```tsx
cnipaQueryPack={state.cnipaQueryPack ?? null}
importLedgers={state.importLedgers ?? []}
onImportCnipaExport={(file) => void handlers.onImportCnipaExport(file)}
```

In `frontend/src/App.tsx`, import:

```ts
getProjectCnipaQueryPack,
listProjectKnowledgeImportLedgers,
uploadProjectCnipaExport,
type CnipaQueryPack,
type ProjectKnowledgeImportLedger,
```

Add state:

```ts
const [cnipaQueryPack, setCnipaQueryPack] = useState<CnipaQueryPack | null>(null);
const [projectKnowledgeImportLedgers, setProjectKnowledgeImportLedgers] = useState<ProjectKnowledgeImportLedger[]>([]);
```

Update project knowledge loading after `getProjectKnowledge(projectId)`:

```ts
const [overview, queryPack] = await Promise.all([
  getProjectKnowledge(projectId),
  getProjectCnipaQueryPack(projectId),
]);
setProjectKnowledge(overview);
setCnipaQueryPack(queryPack);
if (overview.latest_plan) {
  setProjectKnowledgeImportLedgers(await listProjectKnowledgeImportLedgers(projectId, overview.latest_plan.id));
} else {
  setProjectKnowledgeImportLedgers([]);
}
```

Add handler:

```ts
async function handleImportCnipaExport(file: File): Promise<void> {
  const latestPlan = projectKnowledge?.latest_plan;
  if (!selectedProject || !latestPlan) return;
  const projectId = selectedProject.id;
  await withStatus("knowledge-cnipa-import", async () => {
    const result = await uploadProjectCnipaExport(projectId, latestPlan.id, file);
    if (selectedProjectIdRef.current !== projectId) {
      return;
    }
    setProjectKnowledge(result.overview);
    setProjectKnowledgeImportLedgers((current) => [result.ledger, ...current]);
    setMessage(`已导入 CNIPA 官方导出物：解析 ${result.ledger.parsed_count} 条候选。`);
  });
}
```

Pass `cnipaQueryPack`, `projectKnowledgeImportLedgers`, and `handleImportCnipaExport` into the corpus workspace state/handlers object.

- [ ] **Step 6: Update frontend tests and run them**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Build frontend**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api.ts frontend/src/App.tsx frontend/src/features/corpus/CorpusWorkspace.tsx frontend/src/views/projectKnowledgeView.tsx frontend/src/api.test.ts frontend/src/projectKnowledgeView.test.tsx frontend/src/features/corpus/CorpusWorkspace.test.tsx
git commit -m "feat: expose cnipa export import workflow"
```

---

## Final Verification

- [ ] Run backend tests:

```bash
python3 -m pytest tests/test_patent_sources.py tests/test_cnipa_export_importer.py tests/test_project_knowledge.py tests/test_api.py tests/test_grantability.py tests/test_patent_search_providers.py -q
```

Expected: PASS.

- [ ] Run frontend tests and build:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx
npm --prefix frontend run build
```

Expected: PASS.

- [ ] Run status check:

```bash
git status --short --branch
```

Expected: clean branch ahead of `origin/main` by the implementation commits.
