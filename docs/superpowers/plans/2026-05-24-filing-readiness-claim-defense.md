# Filing Readiness + Claim Defense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build v0.3 dual-core filing readiness and claim defense foundations: warning-mode clean filing reports, clean official exports, and persisted human-in-loop claim defense worksheets.

**Architecture:** Add two focused backend modules, `backend/app/filing_readiness.py` and `backend/app/claim_defense.py`, plus Pydantic models, SQLite persistence, FastAPI endpoints, and compact React views. Keep existing generated draft exports backward-compatible as internal exports, while adding clean official exports and sidecar readiness reports.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, python-docx, React 19, Vite, TypeScript, Vitest, pytest.

---

## Current Constraints

- CodeGraph is not initialized in `/Users/leo/Projects/patents_agent`; use direct file reads during execution unless the user explicitly asks to initialize CodeGraph.
- The project directory is not a git repository. Checkpoint commands include `git rev-parse --is-inside-work-tree && ... || true`; no commit is expected.
- Existing draft export endpoints `/api/projects/{project_id}/export.md` and `/api/projects/{project_id}/export.docx` currently include internal content. Keep them working for compatibility, but label new frontend export choices clearly.
- Existing frontend structure is a single `App.tsx` workbench with `workspaceTabs` defined in `frontend/src/domain.ts`.

## File Structure

- Create `backend/app/filing_readiness.py`: rule-based scanner, readiness status aggregation, official/internal/readiness Markdown rendering, official DOCX rendering.
- Create `backend/app/claim_defense.py`: claim feature rule extraction, LLM-assisted worksheet generation, validation fallback, recommendation generation.
- Modify `backend/app/schemas.py`: add readiness report and claim defense worksheet Pydantic models.
- Modify `backend/app/storage.py`: add SQLite tables and CRUD methods for readiness reports and worksheets.
- Modify `backend/app/main.py`: add readiness and worksheet endpoints plus official/internal export endpoints.
- Modify `backend/app/exporter.py`: expose clean official export helpers while keeping existing internal export helpers.
- Modify `frontend/src/api.ts`: add frontend types and API methods.
- Modify `frontend/src/domain.ts`: add workspace tabs and status/label helpers.
- Modify `frontend/src/domain.test.ts`: update tab order and helper tests.
- Modify `frontend/src/App.tsx`: load readiness/worksheets by selected project, add views and export actions.
- Modify `frontend/src/styles.css`: add compact table/status styles if not already reusable.
- Create `tests/test_filing_readiness.py`: backend unit/API/export tests.
- Create `tests/test_claim_defense.py`: backend unit/API/fallback tests.
- Modify `tests/test_export.py`: official export cleanliness tests.
- Modify `README.md`: document v0.3 filing readiness and claim defense workflow.

---

### Task 1: Add Backend Domain Models

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `tests/test_filing_readiness.py`
- Create: `tests/test_claim_defense.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_filing_readiness.py` with:

```python
from backend.app.schemas import FilingReadinessIssue, FilingReadinessReport


def test_filing_readiness_report_status_and_issue_shape():
    issue = FilingReadinessIssue(
        category="internal_trace",
        severity="high",
        target="claims",
        matched_text="根据会审策略撰写",
        message="正式稿包含内部过程痕迹。",
        suggestion="删除过程性表述，仅保留权利要求内容。",
        can_auto_clean=True,
    )
    report = FilingReadinessReport(
        id="r1",
        project_id="p1",
        draft_package_hash="hash-1",
        status="high_risk",
        rules_version="filing-readiness-v1",
        issues=[issue],
    )

    assert report.status == "high_risk"
    assert report.issues[0].category == "internal_trace"
    assert report.issues[0].target == "claims"
```

Create `tests/test_claim_defense.py` with:

```python
from backend.app.schemas import ClaimDefenseWorksheet, FeatureRecord


def test_claim_defense_worksheet_records_feature_classifications():
    feature = FeatureRecord(
        feature_id="f1",
        text="IFC洞口扣减拓扑与工程量清单回链",
        classification="core_combo",
        claim_refs=["1"],
        description_refs=["说明书第5段"],
        figure_refs=["图4"],
        prior_art_refs=["CN119131262A"],
        risk_tags=["组合创造性"],
    )
    worksheet = ClaimDefenseWorksheet(
        id="w1",
        project_id="p1",
        status="draft",
        source="generated_package",
        feature_records=[feature],
        defense_recommendations=["独权中应组合主张IFC洞口扣减与清单回链。"],
        support_gaps=["缺少IfcRelVoidsElement伪代码片段。"],
    )

    assert worksheet.feature_records[0].classification == "core_combo"
    assert worksheet.support_gaps == ["缺少IfcRelVoidsElement伪代码片段。"]
```

- [ ] **Step 2: Run schema tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_filing_readiness_report_status_and_issue_shape tests/test_claim_defense.py::test_claim_defense_worksheet_records_feature_classifications -q
```

Expected: FAIL with import errors for `FilingReadinessIssue`, `FilingReadinessReport`, `FeatureRecord`, and `ClaimDefenseWorksheet`.

- [ ] **Step 3: Add Pydantic models**

In `backend/app/schemas.py`, add these classes after `ProjectRecord`:

```python
class FilingReadinessIssue(BaseModel):
    category: str = Field(
        pattern="^(format_pollution|internal_trace|unfavorable_statement|unverified_effect|subject_matter_risk|support_gap)$"
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    target: str = Field(pattern="^(claims|description|abstract|drawings|export)$")
    matched_text: str
    message: str
    suggestion: str
    can_auto_clean: bool = False


class FilingReadinessReport(BaseModel):
    id: str
    project_id: str
    draft_package_hash: str = ""
    status: str = Field(pattern="^(clean|warning|high_risk)$")
    rules_version: str = "filing-readiness-v1"
    issues: list[FilingReadinessIssue] = Field(default_factory=list)
    created_at: str = ""


class FeatureRecord(BaseModel):
    feature_id: str
    text: str
    classification: str = Field(
        pattern="^(known_base|differentiator|core_combo|dependent_fallback|support_needed)$"
    )
    claim_refs: list[str] = Field(default_factory=list)
    description_refs: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)
    prior_art_refs: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)


class ClaimDefenseWorksheet(BaseModel):
    id: str
    project_id: str
    status: str = Field(default="draft", pattern="^(draft|reviewed|superseded)$")
    source: str = Field(default="draft", pattern="^(draft|disclosure|generated_package|manual)$")
    feature_records: list[FeatureRecord] = Field(default_factory=list)
    defense_recommendations: list[str] = Field(default_factory=list)
    support_gaps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_filing_readiness_report_status_and_issue_shape tests/test_claim_defense.py::test_claim_defense_worksheet_records_feature_classifications -q
```

Expected: `2 passed`.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/schemas.py tests/test_filing_readiness.py tests/test_claim_defense.py && git commit -m "feat: add filing readiness and claim defense models" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 2: Implement Clean Filing Gate Rules

**Files:**
- Create: `backend/app/filing_readiness.py`
- Modify: `tests/test_filing_readiness.py`

- [ ] **Step 1: Add failing rule scanner tests**

Append to `tests/test_filing_readiness.py`:

```python
from backend.app.filing_readiness import assess_filing_readiness, readiness_report_to_markdown
from backend.app.schemas import DraftPackage, PatentStrategyBrief


def _dirty_package() -> DraftPackage:
    return DraftPackage(
        title="一种外立面逆建模方法",
        abstract="本发明公开了一种方法，效率提升30%。",
        claims="根据会审策略撰写\n```mermaid\nflowchart TD\nA-->B\n```",
        description="本发明属于人工智能软件方法领域，可能不具备创造性。",
        drawing_description="图1为流程图。",
        mermaid="flowchart TD\nA[点云] --> B[IFC]",
        image_prompt="黑白线稿 prompt",
        review_findings=[],
        citations=[],
        generation_logs=["generation_logs: claims, description, image_prompt"],
        strategy_brief=PatentStrategyBrief(
            summary="多Agent会审指出存在充分公开风险。",
            claim_strategy=["根据技术交底书补强独权。"],
            description_strategy=[],
            risk_controls=[],
            agent_consensus="deliberation complete",
        ),
    )


def test_clean_gate_detects_internal_and_format_pollution():
    report = assess_filing_readiness("project-1", _dirty_package(), verified_effects=False)

    categories = {issue.category for issue in report.issues}
    assert report.status == "high_risk"
    assert "format_pollution" in categories
    assert "internal_trace" in categories
    assert "unfavorable_statement" in categories
    assert "unverified_effect" in categories
    assert "subject_matter_risk" in categories


def test_readiness_report_markdown_contains_matches_and_suggestions():
    report = assess_filing_readiness("project-1", _dirty_package(), verified_effects=False)
    markdown = readiness_report_to_markdown(report)

    assert "# FILING_READINESS_REPORT" in markdown
    assert "根据会审策略撰写" in markdown
    assert "正式稿包含内部过程痕迹" in markdown
    assert "建筑信息模型、三维点云处理" in markdown
```

- [ ] **Step 2: Run rule scanner tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_clean_gate_detects_internal_and_format_pollution tests/test_filing_readiness.py::test_readiness_report_markdown_contains_matches_and_suggestions -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.filing_readiness'`.

- [ ] **Step 3: Create rule scanner module**

Create `backend/app/filing_readiness.py`:

```python
from __future__ import annotations

import hashlib
import re
import uuid

from docx import Document

from backend.app.schemas import DraftPackage, FilingReadinessIssue, FilingReadinessReport, PatentStrategyBrief

RULES_VERSION = "filing-readiness-v1"
TECHNICAL_FIELD_SUGGESTION = "建筑信息模型、三维点云处理、计算机视觉与计算机辅助工程量计算技术领域"


def assess_filing_readiness(
    project_id: str,
    package: DraftPackage,
    *,
    verified_effects: bool = False,
    report_id: str | None = None,
) -> FilingReadinessReport:
    issues: list[FilingReadinessIssue] = []
    sections = _package_sections(package)
    for target, text in sections.items():
        issues.extend(_scan_format_pollution(target, text))
        issues.extend(_scan_internal_traces(target, text))
        issues.extend(_scan_unfavorable_statements(target, text))
        issues.extend(_scan_subject_matter_risk(target, text))
        if not verified_effects:
            issues.extend(_scan_unverified_effects(target, text))
    status = _status_for_issues(issues)
    return FilingReadinessReport(
        id=report_id or uuid.uuid4().hex,
        project_id=project_id,
        draft_package_hash=_package_hash(package),
        status=status,
        rules_version=RULES_VERSION,
        issues=issues,
    )


def readiness_report_to_markdown(report: FilingReadinessReport) -> str:
    issue_lines = []
    for index, issue in enumerate(report.issues, start=1):
        issue_lines.append(
            "\n".join(
                [
                    f"### {index}. {issue.severity.upper()} / {issue.category} / {issue.target}",
                    f"- 命中内容：{issue.matched_text}",
                    f"- 问题：{issue.message}",
                    f"- 建议：{issue.suggestion}",
                    f"- 可自动清理：{'是' if issue.can_auto_clean else '否'}",
                ]
            )
        )
    return "\n\n".join(
        [
            "# FILING_READINESS_REPORT",
            f"- Report ID: {report.id}",
            f"- Project ID: {report.project_id}",
            f"- Status: {report.status}",
            f"- Rules: {report.rules_version}",
            "",
            "## Issues",
            "\n\n".join(issue_lines) if issue_lines else "暂无命中项。",
        ]
    )


def official_package_to_markdown(package: DraftPackage) -> str:
    return "\n\n".join(
        [
            f"# {package.title}",
            "## 摘要",
            package.abstract.strip(),
            "## 权利要求书",
            package.claims.strip(),
            "## 说明书",
            package.description.strip(),
            "## 附图说明",
            package.drawing_description.strip(),
        ]
    ) + "\n"


def export_official_docx(package: DraftPackage, output_path) -> object:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(package.title, level=0)
    _add_docx_section(doc, "摘要", package.abstract)
    _add_docx_section(doc, "权利要求书", package.claims)
    _add_docx_section(doc, "说明书", package.description)
    _add_docx_section(doc, "附图说明", package.drawing_description)
    doc.save(output_path)
    return output_path


def _package_sections(package: DraftPackage) -> dict[str, str]:
    strategy_text = _strategy_text(package.strategy_brief)
    return {
        "abstract": package.abstract or "",
        "claims": package.claims or "",
        "description": package.description or "",
        "drawings": package.drawing_description or "",
        "export": "\n".join(
            [
                package.mermaid or "",
                package.image_prompt or "",
                "\n".join(package.generation_logs),
                strategy_text,
                package.disclosure_summary or "",
                package.patent_point_summary or "",
            ]
        ),
    }


def _strategy_text(strategy: PatentStrategyBrief | None) -> str:
    if not strategy:
        return ""
    return "\n".join(
        [
            strategy.summary,
            "\n".join(strategy.claim_strategy),
            "\n".join(strategy.description_strategy),
            "\n".join(strategy.risk_controls),
            strategy.agent_consensus,
        ]
    )


def _scan_format_pollution(target: str, text: str) -> list[FilingReadinessIssue]:
    patterns = [r"```", r"(^|\n)#{1,6}\s+", r"\bflowchart\b", r"\bgraph\s+TD\b", r"\bsequenceDiagram\b", r"\bimage_prompt\b", r"\bdiagram\b"]
    return [
        _issue("format_pollution", "high", target, match.group(0), "正式稿包含Markdown、Mermaid或字段名残留。", "删除格式控制内容，只保留专利正文。", True)
        for pattern in patterns
        for match in re.finditer(pattern, text, flags=re.I)
    ]


def _scan_internal_traces(target: str, text: str) -> list[FilingReadinessIssue]:
    phrases = ["多Agent会审", "deliberation", "generation_logs", "根据技术交底书", "根据会审策略", "主席汇总失败", "prompt"]
    return [
        _issue("internal_trace", "high", target, phrase, "正式稿包含内部过程痕迹。", "删除过程性表述，仅保留正式申请文本。", True)
        for phrase in phrases
        if phrase in text
    ]


def _scan_unfavorable_statements(target: str, text: str) -> list[FilingReadinessIssue]:
    phrases = ["可能不具备创造性", "容易被现有技术组合", "尚未验证", "存在充分公开风险", "禁止直接提交"]
    return [
        _issue("unfavorable_statement", "high", target, phrase, "正式稿包含不利陈述。", "将风险判断移动到内部策略稿或readiness报告。", False)
        for phrase in phrases
        if phrase in text
    ]


def _scan_unverified_effects(target: str, text: str) -> list[FilingReadinessIssue]:
    return [
        _issue("unverified_effect", "medium", target, match.group(0), "正式稿包含未核验定量效果。", "没有验证证据时改为机理性有益效果。", False)
        for match in re.finditer(r"(提升|降低|提高)\s*\d+(?:\.\d+)?%", text)
    ]


def _scan_subject_matter_risk(target: str, text: str) -> list[FilingReadinessIssue]:
    phrases = ["人工智能软件方法领域", "智能管理方法", "造价规则"]
    return [
        _issue("subject_matter_risk", "medium", target, phrase, "技术领域或表述可能放大客体风险。", f"建议改为：{TECHNICAL_FIELD_SUGGESTION}", False)
        for phrase in phrases
        if phrase in text
    ]


def _issue(category: str, severity: str, target: str, matched_text: str, message: str, suggestion: str, can_auto_clean: bool) -> FilingReadinessIssue:
    return FilingReadinessIssue(
        category=category,
        severity=severity,
        target=target,
        matched_text=matched_text.strip(),
        message=message,
        suggestion=suggestion,
        can_auto_clean=can_auto_clean,
    )


def _status_for_issues(issues: list[FilingReadinessIssue]) -> str:
    if any(issue.severity == "high" for issue in issues):
        return "high_risk"
    if issues:
        return "warning"
    return "clean"


def _package_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def _add_docx_section(doc: Document, heading: str, text: str) -> None:
    doc.add_heading(heading, level=1)
    for line in text.splitlines() or [""]:
        doc.add_paragraph(line)
```

- [ ] **Step 4: Run focused rule tests**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_clean_gate_detects_internal_and_format_pollution tests/test_filing_readiness.py::test_readiness_report_markdown_contains_matches_and_suggestions -q
```

Expected: `2 passed`.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/filing_readiness.py tests/test_filing_readiness.py && git commit -m "feat: add clean filing gate rules" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 3: Persist Readiness Reports And Worksheets

**Files:**
- Modify: `backend/app/storage.py`
- Modify: `tests/test_filing_readiness.py`
- Modify: `tests/test_claim_defense.py`

- [ ] **Step 1: Add failing storage tests**

Append to `tests/test_filing_readiness.py`:

```python
from backend.app.storage import SQLiteStore


def test_store_persists_multiple_filing_readiness_reports(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    first = FilingReadinessReport(id="r1", project_id="p1", status="warning", issues=[])
    second = FilingReadinessReport(id="r2", project_id="p1", status="high_risk", issues=[])

    store.create_filing_readiness_report(first)
    store.create_filing_readiness_report(second)

    reports = store.list_filing_readiness_reports("p1")
    assert [report.id for report in reports] == ["r2", "r1"]
    assert store.get_filing_readiness_report("p1", "r1").status == "warning"
```

Append to `tests/test_claim_defense.py`:

```python
from backend.app.storage import SQLiteStore


def test_store_persists_multiple_claim_defense_worksheets(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    first = ClaimDefenseWorksheet(id="w1", project_id="p1", source="draft")
    second = ClaimDefenseWorksheet(id="w2", project_id="p1", source="generated_package")

    store.create_claim_defense_worksheet(first)
    store.create_claim_defense_worksheet(second)

    worksheets = store.list_claim_defense_worksheets("p1")
    assert [worksheet.id for worksheet in worksheets] == ["w2", "w1"]
    assert store.get_claim_defense_worksheet("p1", "w2").source == "generated_package"
```

- [ ] **Step 2: Run storage tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_store_persists_multiple_filing_readiness_reports tests/test_claim_defense.py::test_store_persists_multiple_claim_defense_worksheets -q
```

Expected: FAIL with missing `SQLiteStore` methods.

- [ ] **Step 3: Update storage imports**

In `backend/app/storage.py`, extend the schema import list:

```python
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    CorpusImportJob,
    CorpusQualityReport,
    CorpusVersion,
    DeliberationRun,
    DisclosureRun,
    DraftPackage,
    FeatureRecord,
    FilingReadinessReport,
    PatentAsset,
    PatentChunk,
    PatentPointCandidate,
    PatentDocument,
    ProjectMaterial,
    ProjectRecord,
    SectionType,
)
```

- [ ] **Step 4: Add SQLite tables**

In `_migrate()` after `disclosure_runs`, add:

```sql
create table if not exists filing_readiness_reports (
    id text primary key,
    project_id text not null,
    draft_package_hash text not null,
    status text not null,
    rules_version text not null,
    issues_json text not null,
    created_at text not null default current_timestamp,
    foreign key(project_id) references projects(id)
);

create table if not exists claim_defense_worksheets (
    id text primary key,
    project_id text not null,
    status text not null,
    source text not null,
    feature_records_json text not null,
    defense_recommendations_json text not null,
    support_gaps_json text not null,
    notes_json text not null,
    created_at text not null default current_timestamp,
    foreign key(project_id) references projects(id)
);
```

- [ ] **Step 5: Add CRUD methods**

Add these methods to `SQLiteStore` near the disclosure run methods:

```python
    def create_filing_readiness_report(self, report: FilingReadinessReport) -> FilingReadinessReport:
        with self.connection:
            self.connection.execute(
                """
                insert into filing_readiness_reports(
                    id, project_id, draft_package_hash, status, rules_version, issues_json
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.id,
                    report.project_id,
                    report.draft_package_hash,
                    report.status,
                    report.rules_version,
                    json.dumps([issue.model_dump(mode="json") for issue in report.issues], ensure_ascii=False),
                ),
            )
        return report

    def list_filing_readiness_reports(self, project_id: str) -> list[FilingReadinessReport]:
        rows = self.connection.execute(
            "select * from filing_readiness_reports where project_id = ? order by created_at desc, id desc",
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
                insert into claim_defense_worksheets(
                    id, project_id, status, source, feature_records_json,
                    defense_recommendations_json, support_gaps_json, notes_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    worksheet.id,
                    worksheet.project_id,
                    worksheet.status,
                    worksheet.source,
                    json.dumps([record.model_dump(mode="json") for record in worksheet.feature_records], ensure_ascii=False),
                    json.dumps(worksheet.defense_recommendations, ensure_ascii=False),
                    json.dumps(worksheet.support_gaps, ensure_ascii=False),
                    json.dumps(worksheet.notes, ensure_ascii=False),
                ),
            )
        return worksheet

    def list_claim_defense_worksheets(self, project_id: str) -> list[ClaimDefenseWorksheet]:
        rows = self.connection.execute(
            "select * from claim_defense_worksheets where project_id = ? order by created_at desc, id desc",
            (project_id,),
        ).fetchall()
        return [self._claim_defense_worksheet_from_row(row) for row in rows]

    def get_claim_defense_worksheet(self, project_id: str, worksheet_id: str) -> ClaimDefenseWorksheet | None:
        row = self.connection.execute(
            "select * from claim_defense_worksheets where project_id = ? and id = ?",
            (project_id, worksheet_id),
        ).fetchone()
        return self._claim_defense_worksheet_from_row(row) if row else None
```

Add row helpers near existing `_disclosure_run_from_row` helpers:

```python
    def _filing_readiness_report_from_row(self, row: sqlite3.Row) -> FilingReadinessReport:
        return FilingReadinessReport(
            id=row["id"],
            project_id=row["project_id"],
            draft_package_hash=row["draft_package_hash"],
            status=row["status"],
            rules_version=row["rules_version"],
            issues=json.loads(row["issues_json"]),
            created_at=row["created_at"],
        )

    def _claim_defense_worksheet_from_row(self, row: sqlite3.Row) -> ClaimDefenseWorksheet:
        return ClaimDefenseWorksheet(
            id=row["id"],
            project_id=row["project_id"],
            status=row["status"],
            source=row["source"],
            feature_records=json.loads(row["feature_records_json"]),
            defense_recommendations=json.loads(row["defense_recommendations_json"]),
            support_gaps=json.loads(row["support_gaps_json"]),
            notes=json.loads(row["notes_json"]),
            created_at=row["created_at"],
        )
```

- [ ] **Step 6: Run storage tests**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_store_persists_multiple_filing_readiness_reports tests/test_claim_defense.py::test_store_persists_multiple_claim_defense_worksheets -q
```

Expected: `2 passed`.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/storage.py tests/test_filing_readiness.py tests/test_claim_defense.py && git commit -m "feat: persist filing readiness and claim defense runs" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 4: Add Filing Readiness API And Clean Exports

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/exporter.py`
- Modify: `tests/test_filing_readiness.py`
- Modify: `tests/test_export.py`

- [ ] **Step 1: Add failing API and official export tests**

Append to `tests/test_filing_readiness.py`:

```python
from fastapi.testclient import TestClient
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def test_filing_readiness_api_warns_but_allows_official_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "清稿测试", "draft_text": "一种建筑外立面逆建模方法。"},
    ).json()["id"]
    dirty_package = _dirty_package()
    client.app.state.store.update_project_package(project_id, dirty_package)

    report_response = client.post(f"/api/projects/{project_id}/filing-readiness")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["status"] == "high_risk"

    list_response = client.get(f"/api/projects/{project_id}/filing-readiness")
    assert list_response.json()["reports"][0]["id"] == report["id"]

    report_md = client.get(f"/api/projects/{project_id}/filing-readiness/{report['id']}/export.md")
    assert report_md.status_code == 200
    assert "FILING_READINESS_REPORT" in report_md.text
    assert "根据会审策略撰写" in report_md.text

    official_md = client.get(f"/api/projects/{project_id}/official-export.md")
    assert official_md.status_code == 200
    assert "权利要求书" in official_md.text
    assert "生成日志" not in official_md.text
    assert "多Agent会审" not in official_md.text
    assert "image_prompt" not in official_md.text
```

Append to `tests/test_export.py`:

```python
from backend.app.filing_readiness import official_package_to_markdown


def test_official_markdown_export_contains_only_filing_sections():
    package = DraftPackage(
        title="一种清洁导出方法",
        abstract="本发明公开了一种清洁导出方法。",
        claims="1. 一种清洁导出方法。",
        description="技术领域\n本发明涉及专利文本处理。",
        drawing_description="图1为流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="内部绘图提示词",
        generation_logs=["generation_logs: internal"],
        review_findings=[],
        citations=[],
    )

    markdown = official_package_to_markdown(package)

    assert "## 摘要" in markdown
    assert "## 权利要求书" in markdown
    assert "flowchart" not in markdown
    assert "内部绘图提示词" not in markdown
    assert "generation_logs" not in markdown
```

- [ ] **Step 2: Run API/export tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_filing_readiness_api_warns_but_allows_official_export tests/test_export.py::test_official_markdown_export_contains_only_filing_sections -q
```

Expected: FAIL because endpoints and official export helper are missing.

- [ ] **Step 3: Import readiness helpers and schema in `main.py`**

Add imports in `backend/app/main.py`:

```python
from backend.app.filing_readiness import (
    assess_filing_readiness,
    export_official_docx,
    official_package_to_markdown,
    readiness_report_to_markdown,
)
```

- [ ] **Step 4: Add readiness endpoints**

Add these endpoints after `review_project()` and before export endpoints:

```python
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
        return {"reports": [report.model_dump(mode="json") for report in store.list_filing_readiness_reports(project_id)]}

    @app.get("/api/projects/{project_id}/filing-readiness/{report_id}/export.md")
    def export_filing_readiness_report(project_id: str, report_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        report = store.get_filing_readiness_report(project_id, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Filing readiness report not found.")
        return PlainTextResponse(readiness_report_to_markdown(report), media_type="text/markdown; charset=utf-8")
```

- [ ] **Step 5: Add official export endpoints**

Add these endpoints near existing project export endpoints:

```python
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
```

Keep existing `/export.md` and `/export.docx` unchanged as internal exports.

- [ ] **Step 6: Run API/export tests**

Run:

```bash
python3 -m pytest tests/test_filing_readiness.py::test_filing_readiness_api_warns_but_allows_official_export tests/test_export.py::test_official_markdown_export_contains_only_filing_sections -q
```

Expected: `2 passed`.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/main.py backend/app/exporter.py backend/app/filing_readiness.py tests/test_filing_readiness.py tests/test_export.py && git commit -m "feat: add filing readiness api and official exports" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 5: Implement Claim Defense Worksheet Generator And API

**Files:**
- Create: `backend/app/claim_defense.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_claim_defense.py`

- [ ] **Step 1: Add failing generator and API tests**

Append to `tests/test_claim_defense.py`:

```python
from fastapi.testclient import TestClient

from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DraftPackage, PatentPointCreate


def _package_with_claims() -> DraftPackage:
    return DraftPackage(
        title="一种外立面逆建模方法",
        abstract="本发明公开了一种方法。",
        claims="1. 一种外立面逆建模方法，其特征在于，生成IFC洞口扣减拓扑并建立工程量清单回链。\n2. 根据权利要求1所述的方法，其中根据工程量影响排序人工复核。",
        description="说明书描述了IFC洞口扣减拓扑。",
        drawing_description="图1为方法流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿。",
        review_findings=[],
        citations=[],
    )


def test_claim_defense_rules_extract_feature_records_without_llm():
    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=_package_with_claims(),
        disclosures=[],
        patent_points=[],
        llm=None,
    )

    assert worksheet.source == "generated_package"
    assert worksheet.feature_records
    assert any("IFC洞口扣减拓扑" in record.text for record in worksheet.feature_records)
    assert worksheet.defense_recommendations


def test_claim_defense_api_persists_multiple_versions(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "防线测试", "draft_text": "一种外立面逆建模方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, _package_with_claims())
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "IFC洞口扣减拓扑与清单回链",
            "technical_problem": "洞口扣减与算量结果缺少可追溯关系",
            "innovation": "将IfcRelVoidsElement与清单条目回链",
            "technical_solution": "生成IFC洞口扣减关系并记录清单回链。",
            "selected": True,
        },
    )

    first = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")
    second = client.post(f"/api/projects/{project_id}/claim-defense-worksheets")

    assert first.status_code == 200
    assert second.status_code == 200
    list_response = client.get(f"/api/projects/{project_id}/claim-defense-worksheets")
    assert len(list_response.json()["worksheets"]) == 2
    detail = client.get(f"/api/projects/{project_id}/claim-defense-worksheets/{second.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["feature_records"]
```

- [ ] **Step 2: Run generator/API tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_claim_defense.py::test_claim_defense_rules_extract_feature_records_without_llm tests/test_claim_defense.py::test_claim_defense_api_persists_multiple_versions -q
```

Expected: FAIL because `backend.app.claim_defense` and worksheet endpoints are missing.

- [ ] **Step 3: Create claim defense generator module**

Create `backend/app/claim_defense.py`:

```python
from __future__ import annotations

import json
import re
import uuid

from pydantic import ValidationError

from backend.app.llm import LLMClient
from backend.app.schemas import ClaimDefenseWorksheet, DisclosureRun, DraftPackage, FeatureRecord, PatentPointCandidate


def generate_claim_defense_worksheet(
    *,
    project_id: str,
    package: DraftPackage | None,
    disclosures: list[DisclosureRun],
    patent_points: list[PatentPointCandidate],
    llm: LLMClient | None,
) -> ClaimDefenseWorksheet:
    source = "generated_package" if package else "draft"
    records = _rule_extract_features(package, patent_points)
    notes: list[str] = []
    llm_records = _llm_extract_features(package, patent_points, llm)
    if llm_records:
        records = _merge_records(records, llm_records)
    elif llm is not None:
        notes.append("LLM特征抽取失败，已降级为规则抽取。")
    records = _classify_records(records, patent_points, disclosures)
    return ClaimDefenseWorksheet(
        id=uuid.uuid4().hex,
        project_id=project_id,
        status="draft",
        source=source,
        feature_records=records,
        defense_recommendations=_defense_recommendations(records),
        support_gaps=_support_gaps(records),
        notes=notes,
    )


def _rule_extract_features(package: DraftPackage | None, patent_points: list[PatentPointCandidate]) -> list[FeatureRecord]:
    records: list[FeatureRecord] = []
    if package:
        for claim_number, claim_text in _claim_lines(package.claims):
            for fragment in _split_feature_fragments(claim_text):
                records.append(
                    FeatureRecord(
                        feature_id=f"claim-{claim_number}-{len(records) + 1}",
                        text=fragment,
                        classification="differentiator",
                        claim_refs=[claim_number],
                        description_refs=_description_refs(package.description, fragment),
                        risk_tags=[],
                    )
                )
    for point in patent_points:
        records.append(
            FeatureRecord(
                feature_id=f"point-{point.id}",
                text=f"{point.title}：{point.innovation or point.technical_solution}",
                classification="support_needed" if point.evidence_status != "verified" else "differentiator",
                risk_tags=[point.evidence_status],
                prior_art_refs=[chart.prior_art_id for chart in point.claim_chart],
            )
        )
    return _dedupe_records(records)


def _llm_extract_features(package: DraftPackage | None, patent_points: list[PatentPointCandidate], llm: LLMClient | None) -> list[FeatureRecord]:
    if not llm or not package:
        return []
    prompt = json.dumps(
        {
            "claims": package.claims,
            "description": package.description,
            "patent_points": [point.model_dump(mode="json") for point in patent_points],
            "instruction": "Return JSON object with feature_records. Each feature has feature_id, text, classification, claim_refs, description_refs, figure_refs, prior_art_refs, risk_tags.",
        },
        ensure_ascii=False,
    )
    try:
        raw = llm.complete_stage("claim_defense_features", "你是专利权利要求防线分析助手。只输出JSON。", prompt)
        data = json.loads(raw)
        return [FeatureRecord.model_validate(item) for item in data.get("feature_records", [])]
    except (KeyError, json.JSONDecodeError, ValidationError, RuntimeError):
        return []


def _classify_records(records: list[FeatureRecord], patent_points: list[PatentPointCandidate], disclosures: list[DisclosureRun]) -> list[FeatureRecord]:
    differentiators = _differentiator_terms(patent_points, disclosures)
    classified: list[FeatureRecord] = []
    for record in records:
        text = record.text
        classification = record.classification
        if any(term and term in text for term in differentiators):
            classification = "core_combo" if _looks_like_combo(text) else "differentiator"
        if not record.description_refs and classification in {"differentiator", "core_combo"}:
            classification = "support_needed"
        classified.append(record.model_copy(update={"classification": classification}))
    return classified


def _claim_lines(claims: str) -> list[tuple[str, str]]:
    matches = re.findall(r"(?m)^\\s*(\\d+)\\.\\s*(.+?)(?=\\n\\s*\\d+\\.|\\Z)", claims, flags=re.S)
    return [(number, text.strip()) for number, text in matches] or [("1", claims.strip())]


def _split_feature_fragments(text: str) -> list[str]:
    parts = re.split(r"[；;。]|，其中|其特征在于|包括", text)
    return [part.strip(" ，,。；;") for part in parts if len(part.strip(" ，,。；;")) >= 8]


def _description_refs(description: str, fragment: str) -> list[str]:
    keywords = [word for word in re.split(r"\\W+", fragment) if len(word) >= 4]
    return ["说明书"] if any(keyword in description for keyword in keywords) else []


def _differentiator_terms(patent_points: list[PatentPointCandidate], disclosures: list[DisclosureRun]) -> set[str]:
    terms: set[str] = set()
    for point in patent_points:
        terms.add(point.title)
        terms.add(point.innovation)
        for chart in point.claim_chart:
            terms.update(chart.differentiating_features)
    for run in disclosures:
        if run.package:
            terms.add(run.package.prior_art_differences)
    return {term for term in terms if term}


def _looks_like_combo(text: str) -> bool:
    markers = ["回链", "闭环", "增量", "IFC", "Ifc", "工程量", "置信度", "拓扑"]
    return sum(1 for marker in markers if marker in text) >= 2


def _dedupe_records(records: list[FeatureRecord]) -> list[FeatureRecord]:
    seen: set[str] = set()
    deduped: list[FeatureRecord] = []
    for record in records:
        key = record.text
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _merge_records(rule_records: list[FeatureRecord], llm_records: list[FeatureRecord]) -> list[FeatureRecord]:
    return _dedupe_records([*llm_records, *rule_records])


def _defense_recommendations(records: list[FeatureRecord]) -> list[str]:
    core = [record.text for record in records if record.classification in {"core_combo", "differentiator"}]
    if not core:
        return ["未识别到稳定区别特征；建议先补充技术交底或现有技术差异。"]
    return [
        f"独权建议围绕以下组合特征组织：{'；'.join(core[:4])}",
        "单点特征不宜单独作为创造性核心，应优先主张端到端闭环或可追溯数据结构。",
    ]


def _support_gaps(records: list[FeatureRecord]) -> list[str]:
    gaps = [f"{record.text}：缺少说明书明确支撑。" for record in records if record.classification == "support_needed"]
    return gaps or ["未发现阻断性说明书支撑缺口。"]
```

- [ ] **Step 4: Add worksheet endpoints**

In `backend/app/main.py`, import:

```python
from backend.app.claim_defense import generate_claim_defense_worksheet
```

Add endpoints after filing readiness endpoints:

```python
    @app.post("/api/projects/{project_id}/claim-defense-worksheets")
    def create_claim_defense_worksheet(project_id: str) -> dict:
        project = _require_project(store, project_id)
        disclosure_runs = store.list_disclosure_runs(project_id)
        patent_points = store.list_project_patent_points(project_id)
        worksheet = generate_claim_defense_worksheet(
            project_id=project_id,
            package=project.package,
            disclosures=disclosure_runs,
            patent_points=patent_points,
            llm=app.state.llm,
        )
        stored = store.create_claim_defense_worksheet(worksheet)
        return stored.model_dump(mode="json")

    @app.get("/api/projects/{project_id}/claim-defense-worksheets")
    def list_claim_defense_worksheets(project_id: str) -> dict:
        _require_project(store, project_id)
        return {"worksheets": [worksheet.model_dump(mode="json") for worksheet in store.list_claim_defense_worksheets(project_id)]}

    @app.get("/api/projects/{project_id}/claim-defense-worksheets/{worksheet_id}")
    def get_claim_defense_worksheet(project_id: str, worksheet_id: str) -> dict:
        _require_project(store, project_id)
        worksheet = store.get_claim_defense_worksheet(project_id, worksheet_id)
        if not worksheet:
            raise HTTPException(status_code=404, detail="Claim defense worksheet not found.")
        return worksheet.model_dump(mode="json")
```

- [ ] **Step 5: Add invalid LLM fallback test**

Append to `tests/test_claim_defense.py`:

```python
def test_claim_defense_invalid_llm_output_falls_back_to_rules():
    llm = FakeLLMClient({"claim_defense_features": "not-json"})
    worksheet = generate_claim_defense_worksheet(
        project_id="p1",
        package=_package_with_claims(),
        disclosures=[],
        patent_points=[],
        llm=llm,
    )

    assert worksheet.feature_records
    assert "LLM特征抽取失败" in worksheet.notes[0]
```

- [ ] **Step 6: Run claim defense tests**

Run:

```bash
python3 -m pytest tests/test_claim_defense.py -q
```

Expected: all tests in `tests/test_claim_defense.py` pass.

- [ ] **Step 7: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/claim_defense.py backend/app/main.py tests/test_claim_defense.py && git commit -m "feat: add claim defense worksheet api" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 6: Add Frontend Types, API Methods, And Tabs

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/domain.ts`
- Modify: `frontend/src/domain.test.ts`

- [ ] **Step 1: Add failing frontend helper/tab tests**

Update `frontend/src/domain.test.ts` workspace tab expectation to include the two new tabs between `分步撰写` and `审查修改`:

```ts
expect(workspaceTabs.map((tab) => tab.label)).toEqual([
  "语料库建设",
  "知识库",
  "创建专利项目",
  "护城河地图",
  "前置材料",
  "多 Agent 会审",
  "分步撰写",
  "提交成熟度",
  "权利要求防线",
  "审查修改",
  "导出",
]);
```

Add helper test:

```ts
describe("filing readiness helpers", () => {
  it("labels readiness status and feature classifications", async () => {
    const { readinessStatusLabel, featureClassificationLabel } = await import("./domain");
    expect(readinessStatusLabel("clean")).toBe("干净");
    expect(readinessStatusLabel("warning")).toBe("有警告");
    expect(readinessStatusLabel("high_risk")).toBe("高风险");
    expect(featureClassificationLabel("core_combo")).toBe("核心组合");
    expect(featureClassificationLabel("support_needed")).toBe("需支撑");
  });
});
```

- [ ] **Step 2: Run frontend tests to verify they fail**

Run:

```bash
cd frontend && npm test -- --run src/domain.test.ts
```

Expected: FAIL because new tabs/helpers do not exist.

- [ ] **Step 3: Add frontend types and API methods**

In `frontend/src/api.ts`, add these interfaces after `DraftPackage`:

```ts
export type FilingReadinessStatus = "clean" | "warning" | "high_risk";
export type FilingIssueSeverity = "low" | "medium" | "high";
export type FeatureClassification =
  | "known_base"
  | "differentiator"
  | "core_combo"
  | "dependent_fallback"
  | "support_needed";

export interface FilingReadinessIssue {
  category: string;
  severity: FilingIssueSeverity;
  target: "claims" | "description" | "abstract" | "drawings" | "export";
  matched_text: string;
  message: string;
  suggestion: string;
  can_auto_clean: boolean;
}

export interface FilingReadinessReport {
  id: string;
  project_id: string;
  draft_package_hash: string;
  status: FilingReadinessStatus;
  rules_version: string;
  issues: FilingReadinessIssue[];
  created_at: string;
}

export interface FeatureRecord {
  feature_id: string;
  text: string;
  classification: FeatureClassification;
  claim_refs: string[];
  description_refs: string[];
  figure_refs: string[];
  prior_art_refs: string[];
  risk_tags: string[];
}

export interface ClaimDefenseWorksheet {
  id: string;
  project_id: string;
  status: "draft" | "reviewed" | "superseded";
  source: "draft" | "disclosure" | "generated_package" | "manual";
  feature_records: FeatureRecord[];
  defense_recommendations: string[];
  support_gaps: string[];
  notes: string[];
  created_at: string;
}
```

Add API methods near existing project methods:

```ts
export async function createFilingReadinessReport(projectId: string): Promise<FilingReadinessReport> {
  return request<FilingReadinessReport>(`/api/projects/${projectId}/filing-readiness`, { method: "POST" });
}

export async function listFilingReadinessReports(projectId: string): Promise<FilingReadinessReport[]> {
  const data = await request<{ reports: FilingReadinessReport[] }>(`/api/projects/${projectId}/filing-readiness`);
  return data.reports;
}

export function filingReadinessReportUrl(projectId: string, reportId: string): string {
  return `/api/projects/${projectId}/filing-readiness/${reportId}/export.md`;
}

export async function createClaimDefenseWorksheet(projectId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets`, { method: "POST" });
}

export async function listClaimDefenseWorksheets(projectId: string): Promise<ClaimDefenseWorksheet[]> {
  const data = await request<{ worksheets: ClaimDefenseWorksheet[] }>(`/api/projects/${projectId}/claim-defense-worksheets`);
  return data.worksheets;
}

export async function getClaimDefenseWorksheet(projectId: string, worksheetId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets/${worksheetId}`);
}

export function officialExportUrl(projectId: string, kind: "docx" | "md"): string {
  return kind === "docx" ? `/api/projects/${projectId}/official-export.docx` : `/api/projects/${projectId}/official-export.md`;
}
```

- [ ] **Step 4: Add tabs and helper labels**

In `frontend/src/domain.ts`, import icons:

```ts
import {
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Database,
  Download,
  FilePlus2,
  PenLine,
  Scale,
  SearchCheck,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
```

Extend `WorkspaceTabId`:

```ts
  | "readiness"
  | "claimDefense"
```

Update `workspaceTabs` between `write` and `review`:

```ts
  { id: "readiness", label: "提交成熟度", icon: ClipboardCheck },
  { id: "claimDefense", label: "权利要求防线", icon: Scale },
```

Add helpers:

```ts
export function readinessStatusLabel(status: string): string {
  if (status === "clean") return "干净";
  if (status === "warning") return "有警告";
  return "高风险";
}

export function featureClassificationLabel(value: string): string {
  if (value === "known_base") return "已知基础";
  if (value === "differentiator") return "区别特征";
  if (value === "core_combo") return "核心组合";
  if (value === "dependent_fallback") return "从属兜底";
  return "需支撑";
}
```

- [ ] **Step 5: Run frontend helper tests**

Run:

```bash
cd frontend && npm test -- --run src/domain.test.ts
```

Expected: all domain tests pass.

- [ ] **Step 6: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add frontend/src/api.ts frontend/src/domain.ts frontend/src/domain.test.ts && git commit -m "feat: add filing readiness frontend contracts" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 7: Add Frontend Readiness And Claim Defense Views

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Wire imports and state**

In `frontend/src/App.tsx`, add imports from `./api`:

```ts
  ClaimDefenseWorksheet,
  FilingReadinessReport,
  createClaimDefenseWorksheet,
  createFilingReadinessReport,
  filingReadinessReportUrl,
  listClaimDefenseWorksheets,
  listFilingReadinessReports,
  officialExportUrl,
```

Add imports from `./domain`:

```ts
  featureClassificationLabel,
  readinessStatusLabel,
```

Add state in `App()`:

```ts
  const [filingReports, setFilingReports] = useState<FilingReadinessReport[]>([]);
  const [worksheets, setWorksheets] = useState<ClaimDefenseWorksheet[]>([]);
```

Add computed values:

```ts
  const latestFilingReport = filingReports[0] ?? null;
  const latestWorksheet = worksheets[0] ?? null;
```

- [ ] **Step 2: Add loaders and selected-project lifecycle**

Add loaders near existing `loadDisclosures`:

```ts
  async function loadFilingReports(projectId: string) {
    try {
      setFilingReports(await listFilingReadinessReports(projectId));
    } catch {
      setFilingReports([]);
    }
  }

  async function loadWorksheets(projectId: string) {
    try {
      setWorksheets(await listClaimDefenseWorksheets(projectId));
    } catch {
      setWorksheets([]);
    }
  }
```

Inside the selected project `useEffect`, when a project exists add:

```ts
      void loadFilingReports(selectedProject.id);
      void loadWorksheets(selectedProject.id);
```

Inside the `else` branch add:

```ts
      setFilingReports([]);
      setWorksheets([]);
```

- [ ] **Step 3: Add action handlers**

Add handlers in `App()`:

```ts
  async function handleRunFilingReadiness() {
    if (!selectedProject) return;
    await withStatus("filing-readiness", async () => {
      const report = await createFilingReadinessReport(selectedProject.id);
      setFilingReports(await listFilingReadinessReports(selectedProject.id));
      setMessage(`提交成熟度检查完成：${readinessStatusLabel(report.status)}`);
    });
  }

  async function handleCreateWorksheet() {
    if (!selectedProject) return;
    await withStatus("claim-defense", async () => {
      const worksheet = await createClaimDefenseWorksheet(selectedProject.id);
      setWorksheets(await listClaimDefenseWorksheets(selectedProject.id));
      setMessage(`权利要求防线工作表已生成：${worksheet.feature_records.length} 个特征`);
    });
  }
```

- [ ] **Step 4: Render new views**

Add render branches between `write` and `review`:

```tsx
        {activeTab === "readiness" && (
          <FilingReadinessView
            project={selectedProject}
            report={latestFilingReport}
            reports={filingReports}
            busy={busy}
            onRun={handleRunFilingReadiness}
          />
        )}
        {activeTab === "claimDefense" && (
          <ClaimDefenseView
            project={selectedProject}
            worksheet={latestWorksheet}
            worksheets={worksheets}
            busy={busy}
            onGenerate={handleCreateWorksheet}
          />
        )}
```

- [ ] **Step 5: Add `FilingReadinessView` component**

Add component before `ReviewView`:

```tsx
function FilingReadinessView({
  project,
  report,
  reports,
  busy,
  onRun,
}: {
  project: ProjectRecord | null;
  report: FilingReadinessReport | null;
  reports: FilingReadinessReport[];
  busy: string;
  onRun: () => void;
}) {
  const statusClass = report?.status === "high_risk" ? "status-badge danger" : report?.status === "warning" ? "status-badge warn" : "status-badge";
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>提交成熟度</h3>
          <p>{project ? "检查正式提交稿的格式污染、内部痕迹、不利陈述和未核验效果。" : "先创建并生成项目草稿后再检查。"}</p>
          {report && <span className={statusClass}>{readinessStatusLabel(report.status)}</span>}
        </div>
        <button className="primary" disabled={!project?.package || busy === "filing-readiness"} onClick={onRun} type="button">
          <SearchCheck size={18} />
          <span>运行检查</span>
        </button>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>导出</h3>
          {project?.package ? (
            <div className="button-row">
              <a className="export-link" href={officialExportUrl(project.id, "docx")}>
                <Download size={17} />
                <span>正式提交稿 DOCX</span>
              </a>
              <a className="export-link" href={officialExportUrl(project.id, "md")}>
                <Download size={17} />
                <span>正式提交稿 MD</span>
              </a>
              <a className="export-link" href={exportUrl(project.id, "md")}>
                <Download size={17} />
                <span>内部策略稿 MD</span>
              </a>
              {report && (
                <a className="export-link" href={filingReadinessReportUrl(project.id, report.id)}>
                  <Download size={17} />
                  <span>Readiness Report</span>
                </a>
              )}
            </div>
          ) : (
            <p className="empty">生成申请文本后才能导出正式稿。</p>
          )}
          {report?.status === "high_risk" && <p className="workflow-hint">高风险：仍允许导出，但建议先处理报告中的命中项。</p>}
        </div>

        <div className="panel">
          <h3>历史检查</h3>
          <div className="list">
            {reports.map((item) => (
              <article className="result-item" key={item.id}>
                <div className="result-meta">
                  <span className={item.status === "high_risk" ? "status-badge danger" : "status-badge"}>{readinessStatusLabel(item.status)}</span>
                  <span>{item.issues.length} 项</span>
                </div>
                <p>{item.rules_version}</p>
              </article>
            ))}
            {reports.length === 0 && <p className="empty">暂无提交成熟度检查。</p>}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>命中项</h3>
        <div className="list">
          {report?.issues.map((issue, index) => (
            <article className="result-item" key={`${issue.category}-${index}`}>
              <div className="result-meta">
                <span className={issue.severity === "high" ? "status-badge danger" : "status-badge warn"}>{severityLabel(issue.severity)}</span>
                <span>{issue.category}</span>
                <span>{issue.target}</span>
              </div>
              <p><strong>{issue.matched_text}</strong></p>
              <p>{issue.message}</p>
              <p className="workflow-hint">{issue.suggestion}</p>
            </article>
          ))}
          {!report && <p className="empty">运行检查后显示风险命中项。</p>}
          {report && report.issues.length === 0 && <p className="empty">未发现命中项。</p>}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 6: Add `ClaimDefenseView` component**

Add component after `FilingReadinessView`:

```tsx
function ClaimDefenseView({
  project,
  worksheet,
  worksheets,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  worksheet: ClaimDefenseWorksheet | null;
  worksheets: ClaimDefenseWorksheet[];
  busy: string;
  onGenerate: () => void;
}) {
  return (
    <div className="stack">
      <section className="panel action-band">
        <div>
          <h3>权利要求防线</h3>
          <p>{project ? "生成可持久化的特征分类、防线建议和说明书支撑缺口。" : "先创建项目后再生成防线工作表。"}</p>
        </div>
        <button className="primary" disabled={!project || busy === "claim-defense"} onClick={onGenerate} type="button">
          <ShieldCheck size={18} />
          <span>生成工作表</span>
        </button>
      </section>

      <section className="two-column">
        <div className="panel">
          <h3>防线建议</h3>
          <div className="list">
            {worksheet?.defense_recommendations.map((item) => (
              <article className="result-item" key={item}>
                <p>{item}</p>
              </article>
            ))}
            {!worksheet && <p className="empty">暂无权利要求防线工作表。</p>}
          </div>
        </div>
        <div className="panel">
          <h3>历史版本</h3>
          <div className="list">
            {worksheets.map((item) => (
              <article className="result-item" key={item.id}>
                <div className="result-meta">
                  <span>{item.status}</span>
                  <span>{item.source}</span>
                  <span>{item.feature_records.length} 特征</span>
                </div>
                <p>{item.created_at || item.id}</p>
              </article>
            ))}
            {worksheets.length === 0 && <p className="empty">暂无历史版本。</p>}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>特征记录</h3>
        <div className="feature-table">
          {worksheet?.feature_records.map((record) => (
            <article className="result-item" key={record.feature_id}>
              <div className="result-meta">
                <span className="status-badge">{featureClassificationLabel(record.classification)}</span>
                <span>{record.claim_refs.join("，") || "无权利要求引用"}</span>
              </div>
              <p>{record.text}</p>
              {record.risk_tags.length > 0 && <p className="workflow-hint">风险标签：{record.risk_tags.join("；")}</p>}
            </article>
          ))}
          {!worksheet && <p className="empty">生成工作表后显示技术特征。</p>}
        </div>
      </section>

      <section className="panel">
        <h3>说明书支撑缺口</h3>
        <div className="list">
          {worksheet?.support_gaps.map((gap) => (
            <article className="result-item" key={gap}>
              <p>{gap}</p>
            </article>
          ))}
          {!worksheet && <p className="empty">暂无支撑缺口。</p>}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 7: Add CSS helpers**

Add to `frontend/src/styles.css`:

```css
.status-badge.warn {
  background: #fff7ed;
  color: #9a3412;
}

.status-badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.feature-table {
  display: grid;
  gap: 10px;
}
```

- [ ] **Step 8: Run frontend build**

Run:

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: Vitest passes and Vite build succeeds.

- [ ] **Step 9: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add frontend/src/App.tsx frontend/src/styles.css && git commit -m "feat: add filing readiness and claim defense views" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 8: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- No code changes unless verification exposes a defect.

- [ ] **Step 1: Update README**

Add this section after the existing patent moat workflow section:

```markdown
## v0.3 提交成熟度与权利要求防线

v0.3 增加两个正式提交前的检查入口：

1. `提交成熟度`：生成 `FILING_READINESS_REPORT.md`，检查 Markdown/Mermaid/prompt/日志残留、内部会审痕迹、不利陈述、未核验定量效果和客体风险弱表述。系统采用“警告但允许导出”，不会阻止导出正式提交稿。
2. `权利要求防线`：生成可持久化、多版本的 Claim Defense Worksheet，列出技术特征、已知基础、区别特征、核心组合、从属兜底和说明书支撑缺口。

导出文件分为：

- 正式提交稿：只包含摘要、权利要求书、说明书、附图说明。
- 内部策略稿：可保留会审、现有技术、Claim Chart、护城河评分和生成日志。
- `FILING_READINESS_REPORT.md`：记录命中规则、风险级别和修改建议。
```

- [ ] **Step 2: Run full backend tests**

Run:

```bash
DEEPSEEK_API_KEY= python3 -m pytest -q
```

Expected: all backend tests pass without network calls.

- [ ] **Step 3: Run frontend tests and build**

Run:

```bash
cd frontend && npm test -- --run && npm run build
```

Expected: Vitest passes and Vite build succeeds.

- [ ] **Step 4: Start local services**

Run backend:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run frontend in `frontend/`:

```bash
npm run dev -- --port 5174
```

Expected:
- Backend health: `GET http://127.0.0.1:8000/api/health` returns `{"ok": true, ...}`.
- Frontend opens at `http://127.0.0.1:5174`.

- [ ] **Step 5: Browser smoke**

Open `http://127.0.0.1:5174` and verify:

1. Sidebar order includes `提交成熟度` and `权利要求防线` between `分步撰写` and `审查修改`.
2. Create or select a project with a generated package.
3. Run `提交成熟度`.
4. Confirm status renders as `干净`, `有警告`, or `高风险`.
5. Confirm `高风险` still leaves official export links enabled.
6. Export official Markdown and confirm it does not contain `Mermaid`, `image_prompt`, `生成日志`, or `多Agent会审`.
7. Export readiness report and confirm it contains matched issues and suggestions.
8. Run `权利要求防线`.
9. Confirm latest worksheet shows feature records, defense recommendations, support gaps, and history list.

- [ ] **Step 6: Final checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git status --short || true
```

Expected in the current directory: `fatal: not a git repository` or an equivalent non-git response.

---

## Self-Review

**Spec coverage:** Clean Gate warning mode, sidecar readiness report, official/internal export split, persisted multi-version worksheet, feature classification, support gaps, frontend views, and verification are all covered. Non-goals remain excluded.

**Placeholder scan:** This plan contains no `TBD`, `TODO`, or intentionally deferred implementation steps inside the v0.3 scope.

**Type consistency:** Backend and frontend use the same names for readiness (`FilingReadinessReport`, `FilingReadinessIssue`) and worksheet (`ClaimDefenseWorksheet`, `FeatureRecord`) concepts. API routes match the design spec.

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-24-filing-readiness-claim-defense.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
