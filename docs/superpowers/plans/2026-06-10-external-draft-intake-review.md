# External Draft Intake Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an external patent draft intake workflow that preserves the original draft, parses it into a working `DraftPackage`, runs the existing quality/improvement/review chain, and exports a cleaned higher-quality filing draft.

**Architecture:** Build a thin backend intake layer in `backend/app/external_drafts.py` that stores source drafts, parses sections, and emits `DraftPackage` working drafts. Reuse existing `filing_readiness`, `claim_defense`, `draft_completion`, `score-improvement`, `official_compile`, and `post_draft_review` modules for scoring, polishing, review, and official export. Add a focused guided-flow frontend entry for pasted text / Markdown first, then DOCX support as a separate task.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, SQLite, python-docx, pytest, TypeScript, React, Vitest, Vite.

---

## Current Constraints

- Execute implementation on a clean branch or worktree, preferably `codex/external-draft-intake-review` from `main`. The current observed checkout had unrelated untracked files, so do not mix this feature into an active UI-polish branch.
- The design spec is `docs/superpowers/specs/2026-06-10-external-draft-intake-review-design.md`.
- Existing official export boundaries must remain intact: official filing text is exported only from `OfficialDraftPackage`, not from the raw external draft, intake report, completion report, logs, or agent memo.
- Existing quality modules already exist. Do not duplicate their scoring or export gate behavior.
- The MVP supports pasted text and Markdown in the first backend/frontend pass. DOCX is implemented after the core intake flow is green.

## File Structure

- Create: `backend/app/external_drafts.py`
  - Responsibility: text extraction, Markdown/plain-text section parsing, DOCX text extraction, source hash helpers, intake issue generation, working draft conversion, Markdown review-bundle rendering.
- Create: `tests/test_external_drafts.py`
  - Responsibility: parser/model/report unit tests for text, Markdown, low-confidence sections, duplicate sections, malformed claim numbering, and DOCX text extraction.
- Create: `tests/test_external_drafts_api.py`
  - Responsibility: API and persistence tests for source creation, intake runs, confirmation, quality-chain compatibility, and review-bundle report export.
- Modify: `backend/app/schemas.py`
  - Add `ExternalDraftSource`, `ExternalDraftSourceCreate`, `SectionConfidence`, `SectionConfidenceItem`, `IntakeIssue`, `ExternalDraftIntakeRun`, `ExternalDraftIntakeConfirmRequest`, and `ExternalDraftReviewBundle`.
- Modify: `backend/app/storage.py`
  - Add `external_draft_sources` and `external_draft_intake_runs` tables, CRUD/list/get helpers, confirmation persistence, and project-delete cleanup.
- Modify: `backend/app/main.py`
  - Add external draft endpoints and wire confirmation to `store.update_project_package`.
- Modify: `frontend/src/api.ts`
  - Add external draft types and client helpers.
- Modify: `frontend/src/guidedFlow.ts`
  - Add mode state for `"idea"` vs `"externalDraft"` intake without changing the existing official compile / export gates.
- Modify: `frontend/src/guidedFlow.test.ts`
  - Add guided-flow tests for external-draft mode, intake completion, and needs-review blocking.
- Modify: `frontend/src/GuidedPatentFlow.tsx`
  - Add a first-step segmented control and external draft intake panel.
- Modify: `frontend/src/App.tsx`
  - Load external draft state for the selected project, wire create/intake/confirm actions, and pass props into `GuidedPatentFlowView`.
- Modify: `frontend/src/styles.css`
  - Add compact styles for source cards, section-confidence rows, intake issues, and the section confirmation editor.

---

### Task 1: Add External Draft Domain Models

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `tests/test_external_drafts.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_external_drafts.py` with:

```python
from backend.app.schemas import (
    DraftPackage,
    ExternalDraftIntakeRun,
    ExternalDraftSource,
    ExternalDraftSourceCreate,
    IntakeIssue,
    SectionConfidence,
    SectionConfidenceItem,
)


def test_external_draft_models_capture_source_intake_and_confidence():
    source = ExternalDraftSource(
        id="src-1",
        project_id="project-1",
        source_type="pasted_text",
        file_name="pasted.txt",
        content_hash="hash-raw",
        raw_text="权利要求书\n1. 一种方法。\n说明书\n本发明涉及数据处理。",
        raw_path="",
        metadata={"input": "paste"},
    )
    confidence = SectionConfidence(
        title=SectionConfidenceItem(score=0.4, source_markers=[], warnings=["未识别发明名称"]),
        abstract=SectionConfidenceItem(score=0.0, source_markers=[], warnings=["未识别摘要"]),
        claims=SectionConfidenceItem(score=0.95, source_markers=["权利要求书"], warnings=[]),
        description=SectionConfidenceItem(score=0.9, source_markers=["说明书"], warnings=[]),
        drawing_description=SectionConfidenceItem(score=0.0, source_markers=[], warnings=["未识别附图说明"]),
    )
    issue = IntakeIssue(
        id="intake-1",
        category="missing_section",
        severity="medium",
        section="abstract",
        message="未识别摘要章节。",
        suggested_action="在章节确认界面补充摘要。",
        blocks_quality_run=False,
    )
    run = ExternalDraftIntakeRun(
        id="run-1",
        project_id="project-1",
        source_id=source.id,
        status="needs_review",
        parser_version="external-draft-parser-v1",
        source_hash=source.content_hash,
        parsed_package=DraftPackage(
            title="未命名发明",
            abstract="",
            claims="1. 一种方法。",
            description="本发明涉及数据处理。",
            drawing_description="",
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=[],
        ),
        section_confidence=confidence,
        intake_issues=[issue],
        unassigned_fragments=[],
        working_draft_hash="hash-working",
    )

    create = ExternalDraftSourceCreate(source_type="pasted_text", text=source.raw_text, file_name="pasted.txt")

    assert create.source_type == "pasted_text"
    assert source.content_hash == "hash-raw"
    assert run.status == "needs_review"
    assert run.section_confidence.claims.score == 0.95
    assert run.intake_issues[0].category == "missing_section"
```

- [ ] **Step 2: Run schema test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py::test_external_draft_models_capture_source_intake_and_confidence -q
```

Expected: FAIL with import errors for the external draft models.

- [ ] **Step 3: Add external draft schemas**

Modify `backend/app/schemas.py` after `DraftCompletionRun`:

```python
class ExternalDraftSourceCreate(BaseModel):
    source_type: str = Field(pattern="^(pasted_text|markdown_file|docx_file)$")
    text: str = ""
    file_name: str = ""
    file_content: str = ""


class ExternalDraftSource(BaseModel):
    id: str
    project_id: str
    source_type: str = Field(pattern="^(pasted_text|markdown_file|docx_file)$")
    file_name: str = ""
    content_hash: str
    raw_text: str
    raw_path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class SectionConfidenceItem(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    source_markers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SectionConfidence(BaseModel):
    title: SectionConfidenceItem
    abstract: SectionConfidenceItem
    claims: SectionConfidenceItem
    description: SectionConfidenceItem
    drawing_description: SectionConfidenceItem


class IntakeIssue(BaseModel):
    id: str
    category: str = Field(
        pattern=(
            "^(missing_section|duplicate_section|low_confidence_section|format_noise|"
            "unsupported_attachment|suspected_internal_text|malformed_claim_numbering)$"
        )
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    section: str = Field(pattern="^(title|abstract|claims|description|drawing_description|raw_text)$")
    message: str
    suggested_action: str
    blocks_quality_run: bool = False


class ExternalDraftIntakeRun(BaseModel):
    id: str
    project_id: str
    source_id: str
    status: str = Field(pattern="^(completed|needs_review|failed)$")
    parser_version: str = "external-draft-parser-v1"
    source_hash: str = ""
    parsed_package: DraftPackage | None = None
    section_confidence: SectionConfidence | None = None
    intake_issues: list[IntakeIssue] = Field(default_factory=list)
    unassigned_fragments: list[str] = Field(default_factory=list)
    working_draft_hash: str = ""
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""


class ExternalDraftIntakeConfirmRequest(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str


class ExternalDraftReviewBundle(BaseModel):
    project_id: str
    source_id: str = ""
    intake_run_id: str = ""
    initial_score: int | None = None
    latest_score: int | None = None
    accepted_patch_ids: list[str] = Field(default_factory=list)
    completion_run_ids: list[str] = Field(default_factory=list)
    official_compile_run_id: str = ""
    post_draft_review_run_id: str = ""
    export_allowed: bool = False
    report_hash: str = ""
```

- [ ] **Step 4: Run schema test**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py::test_external_draft_models_capture_source_intake_and_confidence -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas.py tests/test_external_drafts.py
git commit -m "feat: add external draft intake models"
```

Expected: commit succeeds on the clean feature branch.

---

### Task 2: Implement Plain Text and Markdown Intake Parser

**Files:**
- Create: `backend/app/external_drafts.py`
- Modify: `tests/test_external_drafts.py`

- [ ] **Step 1: Add failing parser tests**

Append to `tests/test_external_drafts.py`:

```python
from backend.app.external_drafts import (
    create_external_draft_source,
    external_draft_review_bundle_to_markdown,
    parse_external_draft_source,
    working_draft_hash,
)


def test_markdown_external_draft_parses_into_working_package():
    source = create_external_draft_source(
        project_id="project-1",
        source_type="markdown_file",
        text=(
            "# 一种指标缺口驱动的无人机采集方法\n\n"
            "## 摘要\n"
            "本发明公开一种按指标缺口生成无人机采集任务的方法。\n\n"
            "## 权利要求书\n"
            "1. 一种无人机采集方法，其特征在于，计算指标证据缺失度并生成采集任务包。\n"
            "2. 根据权利要求1所述的方法，其特征在于，按置信度增益排序任务。\n\n"
            "## 说明书\n"
            "技术领域\n"
            "本发明涉及城市体检数据采集。\n"
            "具体实施方式\n"
            "系统计算指标证据缺失度、传感器可达性和采集窗口。\n\n"
            "## 附图说明\n"
            "图1为方法流程图。\n"
        ),
        file_name="draft.md",
    )

    run = parse_external_draft_source(project_id="project-1", source=source)

    assert run.status == "completed"
    assert run.parsed_package is not None
    assert run.parsed_package.title == "一种指标缺口驱动的无人机采集方法"
    assert "指标证据缺失度" in run.parsed_package.claims
    assert run.section_confidence is not None
    assert run.section_confidence.claims.score >= 0.9
    assert run.working_draft_hash == working_draft_hash(run.parsed_package)


def test_external_draft_needs_review_when_claims_are_missing():
    source = create_external_draft_source(
        project_id="project-1",
        source_type="pasted_text",
        text="发明名称\n一种数据处理方法\n说明书\n本发明涉及数据处理。",
        file_name="pasted.txt",
    )

    run = parse_external_draft_source(project_id="project-1", source=source)

    assert run.status == "needs_review"
    assert any(issue.category == "missing_section" and issue.section == "claims" for issue in run.intake_issues)
    assert any(issue.blocks_quality_run for issue in run.intake_issues)


def test_external_draft_flags_duplicate_sections_and_malformed_claim_numbering():
    source = create_external_draft_source(
        project_id="project-1",
        source_type="pasted_text",
        text=(
            "发明名称\n一种处理方法\n"
            "摘要\n摘要一。\n"
            "摘要\n摘要二。\n"
            "权利要求书\n一、一种处理方法。\n"
            "说明书\n本发明涉及数据处理。\n"
        ),
        file_name="pasted.txt",
    )

    run = parse_external_draft_source(project_id="project-1", source=source)

    assert any(issue.category == "duplicate_section" and issue.section == "abstract" for issue in run.intake_issues)
    assert any(issue.category == "malformed_claim_numbering" for issue in run.intake_issues)
```

- [ ] **Step 2: Run parser tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py -q
```

Expected: FAIL because `backend.app.external_drafts` does not exist.

- [ ] **Step 3: Create parser module**

Create `backend/app/external_drafts.py` with:

```python
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Iterable

from backend.app.schemas import (
    DeliberationLogEntry,
    DraftPackage,
    ExternalDraftIntakeRun,
    ExternalDraftReviewBundle,
    ExternalDraftSource,
    IntakeIssue,
    SectionConfidence,
    SectionConfidenceItem,
)


PARSER_VERSION = "external-draft-parser-v1"

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("发明名称", "名称", "题名"),
    "abstract": ("摘要", "摘要附图"),
    "claims": ("权利要求书", "权利要求", "权利要求书正文"),
    "description": ("说明书", "技术领域", "背景技术", "发明内容", "具体实施方式", "实施例"),
    "drawing_description": ("附图说明", "图面说明", "附图简要说明"),
}

REQUIRED_SECTIONS = ("claims", "description")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def working_draft_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def create_external_draft_source(
    *,
    project_id: str,
    source_type: str,
    text: str,
    file_name: str = "",
    raw_path: str = "",
    metadata: dict | None = None,
) -> ExternalDraftSource:
    normalized = normalize_text(text)
    return ExternalDraftSource(
        id=uuid.uuid4().hex,
        project_id=project_id,
        source_type=source_type,
        file_name=file_name or "external-draft.txt",
        content_hash=content_hash(normalized),
        raw_text=normalized,
        raw_path=raw_path,
        metadata=metadata or {},
        created_at=utc_now_iso(),
    )


def parse_external_draft_source(*, project_id: str, source: ExternalDraftSource) -> ExternalDraftIntakeRun:
    logs = [
        DeliberationLogEntry(
            level="info",
            phase="external_draft_intake",
            provider_id="system",
            message="external draft intake started",
            detail=f"source_id={source.id}; source_type={source.source_type}",
        )
    ]
    try:
        sections, duplicate_sections, unassigned = parse_sections(source.raw_text)
        issues = intake_issues_from_sections(sections, duplicate_sections, source.raw_text)
        package = package_from_sections(sections)
        confidence = section_confidence_from_sections(sections)
        status = "needs_review" if any(issue.blocks_quality_run for issue in issues) else "completed"
        return ExternalDraftIntakeRun(
            id=uuid.uuid4().hex,
            project_id=project_id,
            source_id=source.id,
            status=status,
            parser_version=PARSER_VERSION,
            source_hash=source.content_hash,
            parsed_package=package,
            section_confidence=confidence,
            intake_issues=issues,
            unassigned_fragments=unassigned,
            working_draft_hash=working_draft_hash(package),
            logs=logs,
            created_at=utc_now_iso(),
        )
    except Exception as exc:
        logs.append(
            DeliberationLogEntry(
                level="error",
                phase="external_draft_intake",
                provider_id="system",
                message="external draft intake failed",
                detail=f"{type(exc).__name__}: {exc}",
                repair_suggestion="改用纯文本粘贴或 Markdown 文件重新导入。",
            )
        )
        return ExternalDraftIntakeRun(
            id=uuid.uuid4().hex,
            project_id=project_id,
            source_id=source.id,
            status="failed",
            parser_version=PARSER_VERSION,
            source_hash=source.content_hash,
            logs=logs,
            created_at=utc_now_iso(),
        )


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_sections(text: str) -> tuple[dict[str, str], set[str], list[str]]:
    lines = normalize_text(text).splitlines()
    sections: dict[str, list[str]] = {key: [] for key in SECTION_ALIASES}
    duplicate_sections: set[str] = set()
    unassigned: list[str] = []
    current = ""
    seen: set[str] = set()
    pending_title_from_markdown = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current:
                sections[current].append("")
            continue
        heading = detect_heading(line)
        if heading:
            current = heading
            if heading in seen:
                duplicate_sections.add(heading)
            seen.add(heading)
            heading_text = strip_heading_marker(line)
            if heading == "title" and heading_text not in SECTION_ALIASES["title"]:
                sections["title"].append(heading_text)
            continue
        if line.startswith("# ") and not pending_title_from_markdown:
            pending_title_from_markdown = line[2:].strip()
            if not sections["title"]:
                sections["title"].append(pending_title_from_markdown)
            continue
        if current:
            sections[current].append(raw_line)
        else:
            unassigned.append(raw_line)

    compacted = {key: normalize_text("\n".join(value)) for key, value in sections.items()}
    if not compacted["title"] and pending_title_from_markdown:
        compacted["title"] = pending_title_from_markdown
    return compacted, duplicate_sections, [fragment for fragment in unassigned if fragment.strip()]


def detect_heading(line: str) -> str:
    cleaned = strip_heading_marker(line)
    cleaned = cleaned.rstrip("：:")
    for section, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return section
    return ""


def strip_heading_marker(line: str) -> str:
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^\*\*(.+)\*\*$", r"\1", line)
    return line.strip()


def package_from_sections(sections: dict[str, str]) -> DraftPackage:
    return DraftPackage(
        title=sections.get("title") or "未命名发明",
        abstract=sections.get("abstract", ""),
        claims=sections.get("claims", ""),
        description=sections.get("description", ""),
        drawing_description=sections.get("drawing_description", ""),
        mermaid="",
        image_prompt="",
        review_findings=[],
        citations=[],
        generation_logs=["external_draft_intake: parsed from external source"],
    )


def section_confidence_from_sections(sections: dict[str, str]) -> SectionConfidence:
    return SectionConfidence(
        title=confidence_item(sections, "title"),
        abstract=confidence_item(sections, "abstract"),
        claims=confidence_item(sections, "claims"),
        description=confidence_item(sections, "description"),
        drawing_description=confidence_item(sections, "drawing_description"),
    )


def confidence_item(sections: dict[str, str], section: str) -> SectionConfidenceItem:
    text = sections.get(section, "")
    if not text.strip():
        return SectionConfidenceItem(score=0.0, source_markers=[], warnings=[f"未识别{section}章节"])
    score = 0.95 if section in {"claims", "description"} else 0.85
    return SectionConfidenceItem(score=score, source_markers=list(SECTION_ALIASES[section]), warnings=[])


def intake_issues_from_sections(sections: dict[str, str], duplicate_sections: Iterable[str], raw_text: str) -> list[IntakeIssue]:
    issues: list[IntakeIssue] = []
    for section in REQUIRED_SECTIONS:
        if not sections.get(section, "").strip():
            issues.append(
                IntakeIssue(
                    id=f"intake-missing-{section}",
                    category="missing_section",
                    severity="high",
                    section=section,
                    message=f"未识别{section}章节。",
                    suggested_action="在章节确认界面补充该章节后再运行质量检查。",
                    blocks_quality_run=True,
                )
            )
    for section in sorted(duplicate_sections):
        issues.append(
            IntakeIssue(
                id=f"intake-duplicate-{section}",
                category="duplicate_section",
                severity="medium",
                section=section,
                message=f"检测到重复的{section}章节标题。",
                suggested_action="确认重复章节是否应合并为同一章节。",
                blocks_quality_run=False,
            )
        )
    claims = sections.get("claims", "")
    if claims.strip() and not re.search(r"(?m)^\s*(?:权利要求)?\s*1[\.、．]", claims):
        issues.append(
            IntakeIssue(
                id="intake-malformed-claim-numbering",
                category="malformed_claim_numbering",
                severity="medium",
                section="claims",
                message="权利要求书未检测到标准的权利要求1编号。",
                suggested_action="将第一项权利要求改为“1.”或“权利要求1”开头。",
                blocks_quality_run=False,
            )
        )
    if re.search(r"(?i)(prompt|generation_logs|attorney_memo|system_trace)", raw_text):
        issues.append(
            IntakeIssue(
                id="intake-suspected-internal-text",
                category="suspected_internal_text",
                severity="medium",
                section="raw_text",
                message="外部稿中疑似包含内部过程文本。",
                suggested_action="运行正式稿编译前确认该类文本不会进入正式提交稿。",
                blocks_quality_run=False,
            )
        )
    return issues


def external_draft_review_bundle_to_markdown(bundle: ExternalDraftReviewBundle) -> str:
    lines = [
        "# EXTERNAL_DRAFT_REVIEW_BUNDLE",
        "",
        f"- project_id: {bundle.project_id}",
        f"- source_id: {bundle.source_id or '无'}",
        f"- intake_run_id: {bundle.intake_run_id or '无'}",
        f"- initial_score: {bundle.initial_score if bundle.initial_score is not None else '无'}",
        f"- latest_score: {bundle.latest_score if bundle.latest_score is not None else '无'}",
        f"- accepted_patch_ids: {', '.join(bundle.accepted_patch_ids) or '无'}",
        f"- completion_run_ids: {', '.join(bundle.completion_run_ids) or '无'}",
        f"- official_compile_run_id: {bundle.official_compile_run_id or '无'}",
        f"- post_draft_review_run_id: {bundle.post_draft_review_run_id or '无'}",
        f"- export_allowed: {str(bundle.export_allowed).lower()}",
        f"- report_hash: {bundle.report_hash or '无'}",
        "",
        "本报告是内部提质侧车文件，不进入正式申请正文。",
    ]
    return "\n".join(lines).strip() + "\n"
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py -q
```

Expected: all external draft tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/external_drafts.py tests/test_external_drafts.py
git commit -m "feat: parse external patent drafts"
```

Expected: commit succeeds.

---

### Task 3: Persist External Draft Sources and Intake Runs

**Files:**
- Modify: `backend/app/storage.py`
- Create: `tests/test_external_drafts_api.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_external_drafts_api.py` with:

```python
from backend.app.external_drafts import create_external_draft_source, parse_external_draft_source
from backend.app.storage import SQLiteStore


def test_store_persists_external_draft_sources_and_intake_runs(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    source = create_external_draft_source(
        project_id="project-1",
        source_type="pasted_text",
        text="权利要求书\n1. 一种方法。\n说明书\n本发明涉及数据处理。",
        file_name="pasted.txt",
    )
    stored_source = store.create_external_draft_source(source)
    run = parse_external_draft_source(project_id="project-1", source=stored_source)
    stored_run = store.create_external_draft_intake_run(run)

    assert store.get_external_draft_source("project-1", source.id).content_hash == source.content_hash
    assert store.list_external_draft_sources("project-1")[0].id == source.id
    assert store.get_external_draft_intake_run("project-1", run.id).working_draft_hash == run.working_draft_hash
    assert store.list_external_draft_intake_runs("project-1", source.id)[0].id == stored_run.id

    updated = stored_run.model_copy(update={"status": "completed"})
    store.update_external_draft_intake_run(updated)
    assert store.get_external_draft_intake_run("project-1", run.id).status == "completed"

    reopened = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    assert reopened.get_external_draft_source("project-1", source.id).raw_text == source.raw_text
    assert reopened.get_external_draft_intake_run("project-1", run.id).status == "completed"
```

- [ ] **Step 2: Run storage test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_store_persists_external_draft_sources_and_intake_runs -q
```

Expected: FAIL because store methods do not exist.

- [ ] **Step 3: Add imports and deletion cleanup**

Modify `backend/app/storage.py` imports:

```python
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
    OfficialCompileRun,
    OfficialDraftPackage,
    PatentAsset,
    PatentChunk,
    PatentPointCandidate,
    PatentDocument,
    PostDraftReviewRun,
    ProjectMaterial,
    ProjectRecord,
    SectionType,
)
```

Modify the table list in `delete_project` to include:

```python
                "external_draft_intake_runs",
                "external_draft_sources",
```

- [ ] **Step 4: Add CRUD methods**

Add these methods near project/draft-completion methods in `backend/app/storage.py`:

```python
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

    def update_external_draft_intake_run(self, run: ExternalDraftIntakeRun) -> None:
        with self.connection:
            self.connection.execute(
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
                    json.dumps(run.parsed_package.model_dump(mode="json"), ensure_ascii=False) if run.parsed_package else None,
                    json.dumps(run.section_confidence.model_dump(mode="json"), ensure_ascii=False) if run.section_confidence else None,
                    json.dumps([issue.model_dump(mode="json") for issue in run.intake_issues], ensure_ascii=False),
                    json.dumps(run.unassigned_fragments, ensure_ascii=False),
                    run.working_draft_hash,
                    json.dumps([entry.model_dump(mode="json") for entry in run.logs], ensure_ascii=False),
                    run.project_id,
                    run.id,
                ),
            )

    def list_external_draft_intake_runs(self, project_id: str, source_id: str | None = None) -> list[ExternalDraftIntakeRun]:
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
```

- [ ] **Step 5: Add migration tables**

Modify `_migrate` in `backend/app/storage.py` before `filing_readiness_reports`:

```sql
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
```

- [ ] **Step 6: Add row/value helpers**

Add to `backend/app/storage.py` near other row helpers:

```python
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
            json.dumps(run.parsed_package.model_dump(mode="json"), ensure_ascii=False) if run.parsed_package else None,
            json.dumps(run.section_confidence.model_dump(mode="json"), ensure_ascii=False) if run.section_confidence else None,
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
```

- [ ] **Step 7: Run storage test**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_store_persists_external_draft_sources_and_intake_runs -q
```

Expected: `1 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/storage.py tests/test_external_drafts_api.py
git commit -m "feat: persist external draft intake runs"
```

Expected: commit succeeds.

---

### Task 4: Add External Draft API and Confirmation Flow

**Files:**
- Modify: `backend/app/main.py`
- Modify: `tests/test_external_drafts_api.py`

- [ ] **Step 1: Add failing API tests**

Append to `tests/test_external_drafts_api.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_external_draft_api_creates_source_runs_intake_and_confirms_package(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "外部稿项目", "draft_text": "外部初稿导入项目。"},
    ).json()

    source_response = client.post(
        f"/api/projects/{project['id']}/external-drafts",
        json={
            "source_type": "pasted_text",
            "file_name": "draft.txt",
            "text": (
                "发明名称\n一种外部稿处理方法\n"
                "说明书\n本发明涉及专利初稿处理。\n"
            ),
        },
    )
    assert source_response.status_code == 200
    source = source_response.json()
    assert source["content_hash"]

    intake_response = client.post(f"/api/projects/{project['id']}/external-drafts/{source['id']}/intake-runs")
    assert intake_response.status_code == 200
    intake = intake_response.json()
    assert intake["status"] == "needs_review"
    assert intake["parsed_package"]["title"] == "一种外部稿处理方法"

    confirm_response = client.post(
        f"/api/projects/{project['id']}/external-draft-intake-runs/{intake['id']}/confirm",
        json={
            "title": "一种外部稿处理方法",
            "abstract": "本发明公开一种外部稿处理方法。",
            "claims": "1. 一种外部稿处理方法，其特征在于，解析外部专利初稿并生成工作稿。",
            "description": "本发明涉及专利初稿处理。系统保存原始稿并生成内部工作稿。",
            "drawing_description": "图1为外部稿处理流程图。",
        },
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "completed"

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["package"]["title"] == "一种外部稿处理方法"
    assert "保存原始稿" in project_after["package"]["description"]

    list_sources = client.get(f"/api/projects/{project['id']}/external-drafts").json()
    assert list_sources["sources"][0]["id"] == source["id"]

    list_runs = client.get(f"/api/projects/{project['id']}/external-drafts/{source['id']}/intake-runs").json()
    assert list_runs["runs"][0]["id"] == intake["id"]
```

- [ ] **Step 2: Run API test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_external_draft_api_creates_source_runs_intake_and_confirms_package -q
```

Expected: FAIL with 404 for `/external-drafts`.

- [ ] **Step 3: Add imports to `backend/app/main.py`**

Modify imports:

```python
from backend.app.external_drafts import (
    create_external_draft_source,
    external_draft_review_bundle_to_markdown,
    parse_external_draft_source,
    working_draft_hash,
)
```

Add schema imports:

```python
    ExternalDraftIntakeConfirmRequest,
    ExternalDraftReviewBundle,
    ExternalDraftSourceCreate,
```

- [ ] **Step 4: Add API routes**

Add these routes near project material/disclosure routes in `backend/app/main.py`:

```python
    @app.post("/api/projects/{project_id}/external-drafts")
    def create_external_draft(project_id: str, payload: ExternalDraftSourceCreate) -> dict:
        _require_project(store, project_id)
        text = payload.text
        if payload.source_type in {"markdown_file", "docx_file"} and payload.file_content:
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
        package = DraftPackage(
            title=payload.title,
            abstract=payload.abstract,
            claims=payload.claims,
            description=payload.description,
            drawing_description=payload.drawing_description,
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
        store.update_external_draft_intake_run(updated)
        store.update_project_package(project_id, package)
        return updated.model_dump(mode="json")
```

- [ ] **Step 5: Run API test**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_external_draft_api_creates_source_runs_intake_and_confirms_package -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py tests/test_external_drafts_api.py
git commit -m "feat: add external draft intake API"
```

Expected: commit succeeds.

---

### Task 5: Add Review Bundle Report and Quality-Chain Compatibility

**Files:**
- Modify: `backend/app/main.py`
- Modify: `tests/test_external_drafts_api.py`
- Modify: `backend/app/external_drafts.py`

- [ ] **Step 1: Add failing bundle and quality-chain test**

Append to `tests/test_external_drafts_api.py`:

```python
from backend.app.schemas import DraftPackage


def test_external_draft_confirmed_package_runs_quality_and_bundle_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "外部稿提质", "draft_text": "外部初稿导入项目。"},
    ).json()
    client.app.state.store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种外部稿提质方法",
            abstract="本发明公开一种外部稿提质方法。",
            claims="1. 一种方法，其特征在于，接收外部初稿并生成修改建议。",
            description="本实施例接收外部初稿。",
            drawing_description="图1为流程图。",
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=["external_draft_intake: confirmed from run run-1"],
        ),
    )

    completion_response = client.post(f"/api/projects/{project['id']}/completion-runs")
    assert completion_response.status_code == 200

    score_response = client.post(f"/api/projects/{project['id']}/score-improvement", json={"max_rounds": 1})
    assert score_response.status_code == 200

    compile_response = client.post(f"/api/projects/{project['id']}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    assert compile_response.json()["status"] in {"completed", "blocked"}

    report_response = client.get(f"/api/projects/{project['id']}/external-draft-review-bundle/report.md")
    assert report_response.status_code == 200
    assert "EXTERNAL_DRAFT_REVIEW_BUNDLE" in report_response.text
    assert "initial_score" in report_response.text
    assert "official_compile_run_id" in report_response.text
```

- [ ] **Step 2: Run bundle test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_external_draft_confirmed_package_runs_quality_and_bundle_report -q
```

Expected: FAIL with 404 for the review-bundle report endpoint.

- [ ] **Step 3: Add bundle hash helper**

Modify `backend/app/external_drafts.py`:

```python
def review_bundle_hash(bundle: ExternalDraftReviewBundle) -> str:
    canonical = bundle.model_copy(update={"report_hash": ""})
    return hashlib.sha256(canonical.model_dump_json().encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Add report endpoint**

Add to `backend/app/main.py` near external draft routes:

```python
    @app.get("/api/projects/{project_id}/external-draft-review-bundle/report.md")
    def export_external_draft_review_bundle(project_id: str) -> PlainTextResponse:
        _require_project(store, project_id)
        sources = store.list_external_draft_sources(project_id)
        intake_runs = store.list_external_draft_intake_runs(project_id)
        completion_runs = store.list_draft_completion_runs(project_id)
        official_runs = store.list_official_compile_runs(project_id)
        review_runs = store.list_post_draft_review_runs(project_id)
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
            source_id=sources[0].id if sources else "",
            intake_run_id=intake_runs[0].id if intake_runs else "",
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
```

Add `review_bundle_hash` to the `external_drafts` import in `backend/app/main.py`.

- [ ] **Step 5: Run bundle test**

Run:

```bash
python3 -m pytest tests/test_external_drafts_api.py::test_external_draft_confirmed_package_runs_quality_and_bundle_report -q
```

Expected: `1 passed`.

- [ ] **Step 6: Run focused backend suite**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py tests/test_external_drafts_api.py tests/test_draft_completion_api.py tests/test_official_compile.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/external_drafts.py backend/app/main.py tests/test_external_drafts_api.py
git commit -m "feat: add external draft review bundle report"
```

Expected: commit succeeds.

---

### Task 6: Add Frontend API Types and Guided Flow State

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/guidedFlow.ts`
- Modify: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add failing frontend state/API tests**

Append to `frontend/src/guidedFlow.test.ts`:

```ts
import type { ExternalDraftIntakeRun, ExternalDraftSource } from "./api";

const externalDraftSource: ExternalDraftSource = {
  id: "src1",
  project_id: "p1",
  source_type: "pasted_text",
  file_name: "draft.txt",
  content_hash: "source-hash",
  raw_text: "权利要求书\n1. 一种方法。",
  raw_path: "",
  metadata: {},
  created_at: "2026-06-10T00:00:00Z",
};

const completedExternalDraftIntakeRun: ExternalDraftIntakeRun = {
  id: "intake1",
  project_id: "p1",
  source_id: "src1",
  status: "completed",
  parser_version: "external-draft-parser-v1",
  source_hash: "source-hash",
  parsed_package: null,
  section_confidence: null,
  intake_issues: [],
  unassigned_fragments: [],
  working_draft_hash: "working-hash",
  logs: [],
  created_at: "2026-06-10T00:00:00Z",
};

it("tracks external draft intake state without bypassing quality gates", () => {
  const state = deriveGuidedFlowState({
    project: { ...projectWithIdea, package: null },
    materials: [],
    disclosures: [],
    deliberations: [],
    patentPoints: [],
    filingReports: [],
    worksheets: [],
    completionRuns: [],
    externalDraftSources: [externalDraftSource],
    externalDraftIntakeRuns: [completedExternalDraftIntakeRun],
  });

  expect(state.hasExternalDraftSource).toBe(true);
  expect(state.hasCompletedExternalDraftIntake).toBe(true);
  expect(state.draftReady).toBe(false);
  expect(state.qualityChecked).toBe(false);
});
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run:

```bash
npm --prefix frontend test -- --run guidedFlow.test.ts
```

Expected: FAIL because external draft types/state fields do not exist.

- [ ] **Step 3: Add API types and helpers**

Modify `frontend/src/api.ts` after `DraftCompletionRun`:

```ts
export type ExternalDraftSourceType = "pasted_text" | "markdown_file" | "docx_file";

export interface ExternalDraftSource {
  id: string;
  project_id: string;
  source_type: ExternalDraftSourceType;
  file_name: string;
  content_hash: string;
  raw_text: string;
  raw_path: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SectionConfidenceItem {
  score: number;
  source_markers: string[];
  warnings: string[];
}

export interface SectionConfidence {
  title: SectionConfidenceItem;
  abstract: SectionConfidenceItem;
  claims: SectionConfidenceItem;
  description: SectionConfidenceItem;
  drawing_description: SectionConfidenceItem;
}

export interface IntakeIssue {
  id: string;
  category:
    | "missing_section"
    | "duplicate_section"
    | "low_confidence_section"
    | "format_noise"
    | "unsupported_attachment"
    | "suspected_internal_text"
    | "malformed_claim_numbering";
  severity: FilingIssueSeverity;
  section: "title" | "abstract" | "claims" | "description" | "drawing_description" | "raw_text";
  message: string;
  suggested_action: string;
  blocks_quality_run: boolean;
}

export interface ExternalDraftIntakeRun {
  id: string;
  project_id: string;
  source_id: string;
  status: "completed" | "needs_review" | "failed";
  parser_version: string;
  source_hash: string;
  parsed_package: DraftPackage | null;
  section_confidence: SectionConfidence | null;
  intake_issues: IntakeIssue[];
  unassigned_fragments: string[];
  working_draft_hash: string;
  logs: DeliberationLogEntry[];
  created_at: string;
}
```

Add API functions near project functions:

```ts
export async function createExternalDraftSource(
  projectId: string,
  payload: { source_type: ExternalDraftSourceType; text: string; file_name?: string; file_content?: string },
): Promise<ExternalDraftSource> {
  return request<ExternalDraftSource>(`/api/projects/${projectId}/external-drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listExternalDraftSources(projectId: string): Promise<ExternalDraftSource[]> {
  const data = await request<{ sources: ExternalDraftSource[] }>(`/api/projects/${projectId}/external-drafts`);
  return data.sources;
}

export async function startExternalDraftIntakeRun(projectId: string, sourceId: string): Promise<ExternalDraftIntakeRun> {
  return request<ExternalDraftIntakeRun>(`/api/projects/${projectId}/external-drafts/${sourceId}/intake-runs`, {
    method: "POST",
  });
}

export async function listExternalDraftIntakeRuns(
  projectId: string,
  sourceId: string,
): Promise<ExternalDraftIntakeRun[]> {
  const data = await request<{ runs: ExternalDraftIntakeRun[] }>(
    `/api/projects/${projectId}/external-drafts/${sourceId}/intake-runs`,
  );
  return data.runs;
}

export async function confirmExternalDraftIntakeRun(
  projectId: string,
  runId: string,
  payload: Pick<DraftPackage, "title" | "abstract" | "claims" | "description" | "drawing_description">,
): Promise<ExternalDraftIntakeRun> {
  return request<ExternalDraftIntakeRun>(`/api/projects/${projectId}/external-draft-intake-runs/${runId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function externalDraftReviewBundleReportUrl(projectId: string): string {
  return `/api/projects/${projectId}/external-draft-review-bundle/report.md`;
}
```

- [ ] **Step 4: Add guided flow state fields**

Modify `frontend/src/guidedFlow.ts` imports to include:

```ts
  ExternalDraftIntakeRun,
  ExternalDraftSource,
```

Extend `GuidedFlowInput`:

```ts
  externalDraftSources?: ExternalDraftSource[];
  externalDraftIntakeRuns?: ExternalDraftIntakeRun[];
```

Extend `GuidedFlowState`:

```ts
  hasExternalDraftSource: boolean;
  hasCompletedExternalDraftIntake: boolean;
  hasExternalDraftIntakeNeedsReview: boolean;
```

Inside `deriveGuidedFlowState`, compute:

```ts
  const externalDraftSources = input.externalDraftSources ?? [];
  const externalDraftIntakeRuns = input.externalDraftIntakeRuns ?? [];
  const hasExternalDraftSource = externalDraftSources.length > 0;
  const hasCompletedExternalDraftIntake = externalDraftIntakeRuns.some((run) => run.status === "completed");
  const hasExternalDraftIntakeNeedsReview = externalDraftIntakeRuns.some((run) => run.status === "needs_review");
```

Return these fields in the `GuidedFlowState` object:

```ts
    hasExternalDraftSource,
    hasCompletedExternalDraftIntake,
    hasExternalDraftIntakeNeedsReview,
```

- [ ] **Step 5: Run frontend state tests**

Run:

```bash
npm --prefix frontend test -- --run guidedFlow.test.ts
```

Expected: guided flow tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api.ts frontend/src/guidedFlow.ts frontend/src/guidedFlow.test.ts
git commit -m "feat: add external draft frontend API state"
```

Expected: commit succeeds.

---

### Task 7: Add External Draft Guided UI

**Files:**
- Modify: `frontend/src/GuidedPatentFlow.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/guidedFlow.test.ts`

- [ ] **Step 1: Add failing prop/render test**

Add this test to `frontend/src/guidedFlow.test.ts`:

```ts
it("keeps idea mode as the default main generation entry", () => {
  expect(guidedStepLabels[0]).toBe("想法与材料");
  expect(defaultMainSectionId).toBe("generate");
});
```

Run:

```bash
npm --prefix frontend test -- --run guidedFlow.test.ts
```

Expected: PASS before UI work; this locks the existing default flow.

- [ ] **Step 2: Extend guided props and imports**

Modify `frontend/src/GuidedPatentFlow.tsx` imports from `./api` to include:

```ts
  type ExternalDraftIntakeRun,
  type ExternalDraftSource,
```

Extend `GuidedPatentFlowProps`:

```ts
  externalDraftSources: ExternalDraftSource[];
  externalDraftIntakeRuns: ExternalDraftIntakeRun[];
  onCreateExternalDraft: (payload: { text: string; fileName: string }) => Promise<void>;
  onStartExternalDraftIntake: (sourceId: string) => Promise<void>;
  onConfirmExternalDraftIntake: (
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) => Promise<void>;
```

- [ ] **Step 3: Add intake mode UI**

In `IdeaIntakePanel`, add local mode state:

```tsx
  const [intakeMode, setIntakeMode] = useState<"idea" | "external">("idea");
```

Add a segmented control at the top of the panel:

```tsx
      <div className="segmented-control" role="tablist" aria-label="专利生成入口">
        <button
          aria-selected={intakeMode === "idea"}
          className={intakeMode === "idea" ? "selected" : ""}
          onClick={() => setIntakeMode("idea")}
          role="tab"
          type="button"
        >
          从想法生成
        </button>
        <button
          aria-selected={intakeMode === "external"}
          className={intakeMode === "external" ? "selected" : ""}
          onClick={() => setIntakeMode("external")}
          role="tab"
          type="button"
        >
          导入外部初稿
        </button>
      </div>
```

Render the existing idea form only when `intakeMode === "idea"`. Render the new panel when `intakeMode === "external"`.

- [ ] **Step 4: Add `ExternalDraftIntakePanel` component**

Add this component in `frontend/src/GuidedPatentFlow.tsx`:

```tsx
function ExternalDraftIntakePanel({
  project,
  sources,
  runs,
  busy,
  busyElapsedSeconds,
  onCreateExternalDraft,
  onStartExternalDraftIntake,
  onConfirmExternalDraftIntake,
}: {
  project: ProjectRecord | null;
  sources: ExternalDraftSource[];
  runs: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  onCreateExternalDraft: GuidedPatentFlowProps["onCreateExternalDraft"];
  onStartExternalDraftIntake: GuidedPatentFlowProps["onStartExternalDraftIntake"];
  onConfirmExternalDraftIntake: GuidedPatentFlowProps["onConfirmExternalDraftIntake"];
}) {
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("external-draft.txt");
  const latestRun = runs[0] ?? null;
  const draft = latestRun?.parsed_package ?? null;

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!project || !text.trim()) return;
    await onCreateExternalDraft({ text: text.trim(), fileName: fileName.trim() || "external-draft.txt" });
    setText("");
  }

  async function handleConfirm() {
    if (!latestRun || !draft) return;
    await onConfirmExternalDraftIntake(latestRun.id, {
      title: draft.title,
      abstract: draft.abstract,
      claims: draft.claims,
      description: draft.description,
      drawing_description: draft.drawing_description,
    });
  }

  return (
    <section className="external-draft-panel">
      {!project && <p className="workflow-hint">请先创建或选择一个项目，再导入外部初稿。</p>}
      <form className="guided-intake" onSubmit={handleCreate}>
        <label>
          <span>文件名</span>
          <input value={fileName} onChange={(event) => setFileName(event.target.value)} disabled={!project} />
        </label>
        <label>
          <span>粘贴外部专利初稿</span>
          <textarea
            className="idea-input"
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={!project}
            placeholder="粘贴发明名称、摘要、权利要求书、说明书和附图说明。"
          />
        </label>
        <button className="primary" disabled={!project || !text.trim() || busy === "external-draft-create"} type="submit">
          <FileText size={17} />
          <span>保存原始外部稿</span>
        </button>
      </form>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy.startsWith("external-draft")} />
      <div className="guided-summary-list">
        {sources.map((source) => (
          <article className="guided-summary-row" key={source.id}>
            <FileText size={18} />
            <div>
              <strong>{source.file_name}</strong>
              <span>{source.source_type} / {source.content_hash.slice(0, 12)}</span>
            </div>
            <button
              className="icon-button"
              disabled={busy === "external-draft-intake"}
              onClick={() => onStartExternalDraftIntake(source.id)}
              type="button"
            >
              解析章节
            </button>
          </article>
        ))}
        {sources.length === 0 && <p className="empty">保存外部稿后，系统会解析章节并生成内部工作稿。</p>}
      </div>
      {latestRun && (
        <article className="guided-choice selected">
          <div className="result-meta">
            <span className={latestRun.status === "needs_review" ? "status-badge warn" : "status-badge"}>
              {latestRun.status === "completed" ? "解析完成" : latestRun.status === "needs_review" ? "需要确认" : "解析失败"}
            </span>
            <span>{latestRun.working_draft_hash.slice(0, 12) || "无工作稿 hash"}</span>
          </div>
          <h4>{draft?.title || "外部初稿解析结果"}</h4>
          <p>{latestRun.intake_issues.map((issue) => issue.message).join("；") || "未发现导入阶段阻断问题。"}</p>
          {draft && (
            <button className="primary" disabled={busy === "external-draft-confirm"} onClick={handleConfirm} type="button">
              <CheckCircle2 size={17} />
              <span>确认为内部工作稿</span>
            </button>
          )}
        </article>
      )}
    </section>
  );
}
```

Pass the new props from `IdeaIntakePanel` to `ExternalDraftIntakePanel`.

- [ ] **Step 5: Wire state and actions in `App.tsx`**

Modify imports from `./api`:

```ts
  confirmExternalDraftIntakeRun,
  createExternalDraftSource,
  listExternalDraftIntakeRuns,
  listExternalDraftSources,
  startExternalDraftIntakeRun,
  type ExternalDraftIntakeRun,
  type ExternalDraftSource,
```

Add state:

```tsx
  const [externalDraftSources, setExternalDraftSources] = useState<ExternalDraftSource[]>([]);
  const [externalDraftIntakeRuns, setExternalDraftIntakeRuns] = useState<ExternalDraftIntakeRun[]>([]);
```

Add loader:

```tsx
  async function refreshExternalDrafts(projectId: string) {
    const sources = await listExternalDraftSources(projectId);
    setExternalDraftSources(sources);
    if (sources[0]) {
      setExternalDraftIntakeRuns(await listExternalDraftIntakeRuns(projectId, sources[0].id));
    } else {
      setExternalDraftIntakeRuns([]);
    }
  }
```

Modify the selected-project `useEffect` so it resets and loads external draft state with the other project-scoped state:

```tsx
  useEffect(() => {
    setOfficialCompileRuns([]);
    setCurrentSourceDraftHash("");
    setPostDraftReviews([]);
    setCurrentDraftHash("");
    setExternalDraftSources([]);
    setExternalDraftIntakeRuns([]);
    if (selectedProject?.id) {
      void loadDeliberations(selectedProject.id);
      void loadMaterials(selectedProject.id);
      void loadDisclosures(selectedProject.id);
      void loadFormulaState(selectedProject.id);
      void loadOfficialCompileRuns(selectedProject.id);
      void loadPostDraftReviews(selectedProject.id);
      void refreshExternalDrafts(selectedProject.id);
      setPatentPoints([]);
      setPatentPointsProjectId("");
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      void loadPatentPoints(selectedProject.id);
      void loadFilingReports(selectedProject.id);
      void loadWorksheets(selectedProject.id);
      void loadCompletionRuns(selectedProject.id);
    } else {
      setDeliberationRuns([]);
      setProjectMaterials([]);
      setDisclosureRuns([]);
      setFormulaRequirement(null);
      setFormulaRuns([]);
      setPatentPoints([]);
      setFilingReports([]);
      setWorksheets([]);
      setCompletionRuns([]);
      setExternalDraftSources([]);
      setExternalDraftIntakeRuns([]);
      setPatentPointsProjectId("");
    }
  }, [selectedProject?.id]);
```

Add actions:

```tsx
  async function handleCreateExternalDraft(payload: { text: string; fileName: string }) {
    if (!selectedProject) return;
    await withBusy("external-draft-create", async () => {
      await createExternalDraftSource(selectedProject.id, {
        source_type: "pasted_text",
        text: payload.text,
        file_name: payload.fileName,
      });
      await refreshExternalDrafts(selectedProject.id);
      setMessage("已保存外部初稿原文。");
    });
  }

  async function handleStartExternalDraftIntake(sourceId: string) {
    if (!selectedProject) return;
    await withBusy("external-draft-intake", async () => {
      await startExternalDraftIntakeRun(selectedProject.id, sourceId);
      await refreshExternalDrafts(selectedProject.id);
      await refreshProjects();
      setMessage("外部初稿解析完成。");
    });
  }

  async function handleConfirmExternalDraftIntake(
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) {
    if (!selectedProject) return;
    await withBusy("external-draft-confirm", async () => {
      await confirmExternalDraftIntakeRun(selectedProject.id, runId, payload);
      await refreshExternalDrafts(selectedProject.id);
      await refreshProjects();
      setMessage("已确认外部稿为内部工作稿。");
    });
  }
```

Pass props into `GuidedPatentFlowView`:

```tsx
        externalDraftSources={externalDraftSources}
        externalDraftIntakeRuns={externalDraftIntakeRuns}
        onCreateExternalDraft={handleCreateExternalDraft}
        onStartExternalDraftIntake={handleStartExternalDraftIntake}
        onConfirmExternalDraftIntake={handleConfirmExternalDraftIntake}
```

- [ ] **Step 6: Add CSS**

Add to `frontend/src/styles.css`:

```css
.segmented-control {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-muted);
}

.segmented-control button {
  border: 0;
  border-radius: 6px;
  padding: 8px 12px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.segmented-control button.selected {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.external-draft-panel {
  display: grid;
  gap: 16px;
}
```

- [ ] **Step 7: Run frontend tests and build**

Run:

```bash
npm --prefix frontend test -- --run guidedFlow.test.ts
npm --prefix frontend run build
```

Expected: tests and build pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/GuidedPatentFlow.tsx frontend/src/App.tsx frontend/src/styles.css frontend/src/guidedFlow.test.ts
git commit -m "feat: add external draft guided intake UI"
```

Expected: commit succeeds.

---

### Task 8: Add DOCX Intake Support

**Files:**
- Modify: `backend/app/external_drafts.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_external_drafts.py`

- [ ] **Step 1: Add failing DOCX extraction test**

Append to `tests/test_external_drafts.py`:

```python
from docx import Document

from backend.app.external_drafts import extract_docx_text


def test_docx_external_draft_text_extraction(tmp_path):
    docx_path = tmp_path / "external-draft.docx"
    document = Document()
    document.add_heading("一种DOCX外部稿处理方法", level=1)
    document.add_paragraph("摘要")
    document.add_paragraph("本发明公开一种DOCX外部稿处理方法。")
    document.add_paragraph("权利要求书")
    document.add_paragraph("1. 一种方法，其特征在于，读取DOCX段落并生成工作稿。")
    document.add_paragraph("说明书")
    document.add_paragraph("本发明涉及文档解析。")
    document.save(docx_path)

    text = extract_docx_text(docx_path)

    assert "一种DOCX外部稿处理方法" in text
    assert "权利要求书" in text
    assert "读取DOCX段落" in text
```

- [ ] **Step 2: Run DOCX test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py::test_docx_external_draft_text_extraction -q
```

Expected: FAIL because `extract_docx_text` does not exist.

- [ ] **Step 3: Implement DOCX extraction helper**

Modify `backend/app/external_drafts.py`:

```python
from pathlib import Path

from docx import Document
```

Add:

```python
def extract_docx_text(path: Path) -> str:
    document = Document(path)
    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return normalize_text("\n".join(parts))
```

- [ ] **Step 4: Run DOCX unit test**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py::test_docx_external_draft_text_extraction -q
```

Expected: `1 passed`.

- [ ] **Step 5: Add DOCX upload endpoint path**

In `backend/app/main.py`, add a multipart route:

```python
    @app.post("/api/projects/{project_id}/external-drafts/upload")
    async def upload_external_draft(project_id: str, file: UploadFile = File(...)) -> dict:
        _require_project(store, project_id)
        suffix = Path(file.filename or "external-draft").suffix.lower()
        raw_bytes = await file.read()
        source_type = "docx_file" if suffix == ".docx" else "markdown_file"
        raw_path = settings.data_dir / "external-drafts" / project_id / f"{uuid.uuid4().hex}{suffix or '.txt'}"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_bytes)
        if suffix == ".docx":
            text = extract_docx_text(raw_path)
        else:
            text = raw_bytes.decode("utf-8", errors="replace")
        source = create_external_draft_source(
            project_id=project_id,
            source_type=source_type,
            text=text,
            file_name=file.filename or raw_path.name,
            raw_path=str(raw_path),
            metadata={"uploaded": True, "content_type": file.content_type or ""},
        )
        stored = store.create_external_draft_source(source)
        return stored.model_dump(mode="json")
```

Ensure `backend/app/main.py` imports `Path`, `uuid`, `UploadFile`, `File`, and `extract_docx_text` if they are not already imported.

- [ ] **Step 6: Add API upload test**

Append to `tests/test_external_drafts_api.py`:

```python
def test_external_draft_docx_upload_creates_source(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project = client.post(
        "/api/projects",
        json={"name": "DOCX外部稿", "draft_text": "DOCX外部稿导入。"},
    ).json()
    docx_path = tmp_path / "external.docx"
    document = Document()
    document.add_paragraph("权利要求书")
    document.add_paragraph("1. 一种DOCX导入方法。")
    document.add_paragraph("说明书")
    document.add_paragraph("本发明涉及DOCX解析。")
    document.save(docx_path)

    response = client.post(
        f"/api/projects/{project['id']}/external-drafts/upload",
        files={"file": ("external.docx", docx_path.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "docx_file"
    assert "DOCX导入方法" in response.json()["raw_text"]
```

- [ ] **Step 7: Run DOCX tests**

Run:

```bash
python3 -m pytest tests/test_external_drafts.py::test_docx_external_draft_text_extraction tests/test_external_drafts_api.py::test_external_draft_docx_upload_creates_source -q
```

Expected: both tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/external_drafts.py backend/app/main.py tests/test_external_drafts.py tests/test_external_drafts_api.py
git commit -m "feat: support docx external draft intake"
```

Expected: commit succeeds.

---

### Task 9: Final Verification and Browser Smoke

**Files:**
- No code files unless verification exposes defects.

- [ ] **Step 1: Run backend regression**

Run:

```bash
python3 -m pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend regression**

Run:

```bash
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: Vitest and Vite build pass.

- [ ] **Step 3: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Start local app for smoke**

Run backend:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Expected: backend starts and serves `/api/health`.

Run frontend:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

Expected: Vite serves `http://127.0.0.1:5174/`.

- [ ] **Step 5: Browser smoke the external draft path**

Use Browser or Playwright to visit `http://127.0.0.1:5174/` and verify:

1. `专利生成` is the default main section.
2. The first panel offers `从想法生成` and `导入外部初稿`.
3. Selecting `导入外部初稿` reveals the pasted-draft textarea.
4. Saving a pasted external draft creates a source card with a hash prefix.
5. Running `解析章节` displays either `解析完成` or `需要确认`.
6. Confirming the parsed draft updates the current project package.
7. Existing `质量检查 -> 正式稿编译 -> 成稿会审 -> 导出` gates remain visible.

- [ ] **Step 6: Capture screenshots**

Capture:

```text
/tmp/patents-external-draft-desktop.png
/tmp/patents-external-draft-mobile.png
```

Expected: no overlapping text, the segmented control is readable, and the source card / run status are visible.

- [ ] **Step 7: Commit final fixes**

If verification required code fixes:

```bash
git add backend/app frontend/src tests
git commit -m "fix: polish external draft intake verification"
```

If no fixes were needed, no commit is required.

---

## Self-Review

- Spec coverage: source preservation, parsing, confidence, needs-review confirmation, quality-chain reuse, review bundle, official export boundary, frontend entry, DOCX support, and verification each have an implementation task.
- Scope check: PDF OCR, complex diff/merge UI, legal-status verification, and automatic filing are intentionally out of scope.
- Type consistency: backend and frontend names use `ExternalDraftSource`, `ExternalDraftIntakeRun`, `SectionConfidence`, `IntakeIssue`, and `ExternalDraftReviewBundle` consistently.
- Boundary check: raw external draft, intake report, completion report, and post-draft review output remain internal sidecar material; official export continues to use `OfficialDraftPackage`.
