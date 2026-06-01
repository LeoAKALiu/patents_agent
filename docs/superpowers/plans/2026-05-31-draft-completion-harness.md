# Draft Completion Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build v0.4 `Draft Completion Harness`, adding a patent-draft improvement loop that produces scorecards, claim-support matrices, prioritized gaps, patch suggestions, and a sidecar completion report while preserving warning-mode official export.

**Architecture:** Add focused completion models and a rules-first backend engine in `backend/app/draft_completion.py`, persist full completion runs as JSON in SQLite, expose FastAPI endpoints, and add a compact `初稿完善` workbench tab in the existing React app. Reuse v0.3 Clean Filing Gate and Claim Defense Worksheet outputs; do not replace official export behavior.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, React 19, Vite, TypeScript, Vitest, pytest.

---

## Current Constraints

- CodeGraph is not initialized in `/Users/leo/Projects/patents_agent`; use direct file reads during execution unless the user explicitly asks to initialize CodeGraph.
- The project directory is not a git repository. Checkpoint commands use `git rev-parse --is-inside-work-tree && ... || true`; no commit is expected in the current directory.
- v0.3 already has `backend/app/filing_readiness.py`, `backend/app/claim_defense.py`, official/internal export split, and warning-mode export. Preserve these semantics.
- Existing frontend structure is a single `frontend/src/App.tsx` workbench with tab definitions in `frontend/src/domain.ts`.
- The `初稿完善` tab should appear after `权利要求防线` and before `审查修改`.

## File Structure

- Modify `backend/app/schemas.py`: add `CompletionIssue`, `CompletionTask`, `ProposedPatch`, `CompletionScoreCard`, `ClaimSupportMatrixRow`, and `DraftCompletionRun`.
- Create `backend/app/draft_completion.py`: rules-first completion engine, scorecard computation, support matrix generation, patch/task generation, Markdown rendering.
- Modify `backend/app/storage.py`: add `draft_completion_runs` table plus create/list/get/update-patch-status methods.
- Modify `backend/app/main.py`: add completion run endpoints and wire engine inputs from project package, patent points, disclosure runs, readiness reports, worksheets, and materials.
- Modify `frontend/src/api.ts`: add completion types, run/list/report URL helpers, and accept/reject API calls.
- Modify `frontend/src/domain.ts`: add `completion` tab and labels/helpers for completion status, target, category, and score.
- Modify `frontend/src/domain.test.ts`: update tab-order and helper tests.
- Modify `frontend/src/App.tsx`: add completion state loading, run action, and `DraftCompletionView`.
- Modify `frontend/src/styles.css`: add compact scorecard, matrix, task, and patch styles.
- Modify `README.md`: document v0.4 initial draft completion workflow and warning-mode export.
- Create `tests/test_draft_completion.py`: engine, Markdown, and edge-case unit tests.
- Create `tests/test_draft_completion_api.py`: persistence and API tests.

---

### Task 1: Add Draft Completion Domain Models

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `tests/test_draft_completion.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_draft_completion.py` with:

```python
from backend.app.schemas import (
    ClaimSupportMatrixRow,
    CompletionIssue,
    CompletionScoreCard,
    CompletionTask,
    DraftCompletionRun,
    ProposedPatch,
)


def test_draft_completion_models_capture_support_and_patch_state():
    issue = CompletionIssue(
        id="i1",
        category="claim_support_gap",
        severity="high",
        target="claim",
        source_refs=["claim:1"],
        message="核心权利要求特征缺少说明书支撑。",
        why_it_matters="缺少支撑会提高充分公开和支持性风险。",
        suggested_action="补充数据结构和实施例。",
        blocks_submission=True,
    )
    task = CompletionTask(
        id="t1",
        issue_id="i1",
        task_type="add_data_structure",
        priority=100,
        input_refs=["claim:1"],
        expected_output="BillTraceRecord 数据结构",
        draft_section_target="description",
    )
    patch = ProposedPatch(
        id="p1",
        task_id="t1",
        target_section="description",
        patch_kind="insert",
        before_text="",
        after_text="BillTraceRecord包括item_id、ifc_guid_list和confidence_score。",
        rationale="补充清单回链的可计算表示。",
        risk_delta="降低充分公开风险。",
        evidence_refs=["task:t1"],
        can_enter_official_draft=True,
    )
    row = ClaimSupportMatrixRow(
        claim_ref="1",
        feature_text="工程量清单回链",
        feature_classification="core_combo",
        description_refs=[],
        evidence_status="feasible_unverified",
        completion_status="missing",
    )
    run = DraftCompletionRun(
        id="r1",
        project_id="project-1",
        snapshot_hash="hash-1",
        status="completed",
        issues=[issue],
        tasks=[task],
        patches=[patch],
        support_matrix=[row],
        scorecard=CompletionScoreCard(
            authorization_stability=60,
            protection_scope=78,
            support_strength=45,
            prior_art_distinction=65,
            filing_maturity=55,
            official_hygiene=80,
            overall=64,
        ),
    )

    assert run.issues[0].category == "claim_support_gap"
    assert run.tasks[0].status == "open"
    assert run.patches[0].status == "proposed"
    assert run.support_matrix[0].completion_status == "missing"
    assert run.scorecard.overall == 64
```

- [ ] **Step 2: Run schema test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_draft_completion.py::test_draft_completion_models_capture_support_and_patch_state -q
```

Expected: FAIL with import errors for the new completion models.

- [ ] **Step 3: Add Pydantic models**

Add these classes in `backend/app/schemas.py` after `ClaimDefenseWorksheet`:

```python
class CompletionIssue(BaseModel):
    id: str
    category: str = Field(
        pattern=(
            "^(claim_support_gap|specification_sufficiency_gap|figure_consistency_gap|"
            "term_definition_gap|prior_art_distinction_gap|unverified_scheme_gap|"
            "unfavorable_statement|format_pollution|subject_matter_risk|claim_scope_risk)$"
        )
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    target: str = Field(pattern="^(claim|description|drawing|embodiment|term|evidence|prior_art|export)$")
    source_refs: list[str] = Field(default_factory=list)
    message: str
    why_it_matters: str
    suggested_action: str
    blocks_submission: bool = False


class CompletionTask(BaseModel):
    id: str
    issue_id: str
    task_type: str
    priority: int = 0
    input_refs: list[str] = Field(default_factory=list)
    expected_output: str
    draft_section_target: str
    status: str = Field(default="open", pattern="^(open|proposed|accepted|rejected|superseded)$")


class ProposedPatch(BaseModel):
    id: str
    task_id: str
    target_section: str
    patch_kind: str = Field(pattern="^(insert|replace|delete|rewrite|sidecar_only)$")
    before_text: str = ""
    after_text: str = ""
    rationale: str
    risk_delta: str
    evidence_refs: list[str] = Field(default_factory=list)
    can_enter_official_draft: bool = False
    status: str = Field(default="proposed", pattern="^(proposed|accepted|rejected|superseded)$")


class CompletionScoreCard(BaseModel):
    authorization_stability: int = Field(ge=0, le=100)
    protection_scope: int = Field(ge=0, le=100)
    support_strength: int = Field(ge=0, le=100)
    prior_art_distinction: int = Field(ge=0, le=100)
    filing_maturity: int = Field(ge=0, le=100)
    official_hygiene: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


class ClaimSupportMatrixRow(BaseModel):
    claim_ref: str
    feature_text: str
    feature_classification: str = Field(
        pattern="^(known_base|differentiator|core_combo|dependent_fallback|support_needed)$"
    )
    description_refs: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)
    embodiment_refs: list[str] = Field(default_factory=list)
    formula_refs: list[str] = Field(default_factory=list)
    data_structure_refs: list[str] = Field(default_factory=list)
    pseudo_code_refs: list[str] = Field(default_factory=list)
    prior_art_refs: list[str] = Field(default_factory=list)
    evidence_status: str = Field(
        default="model_generated",
        pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$",
    )
    risk_tags: list[str] = Field(default_factory=list)
    completion_status: str = Field(pattern="^(supported|partial|missing)$")


class DraftCompletionRun(BaseModel):
    id: str
    project_id: str
    snapshot_hash: str = ""
    status: str = Field(default="completed", pattern="^(completed|failed)$")
    issues: list[CompletionIssue] = Field(default_factory=list)
    tasks: list[CompletionTask] = Field(default_factory=list)
    patches: list[ProposedPatch] = Field(default_factory=list)
    support_matrix: list[ClaimSupportMatrixRow] = Field(default_factory=list)
    scorecard: CompletionScoreCard
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""
```

- [ ] **Step 4: Run schema test**

Run:

```bash
python3 -m pytest tests/test_draft_completion.py::test_draft_completion_models_capture_support_and_patch_state -q
```

Expected: `1 passed`.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/schemas.py tests/test_draft_completion.py && git commit -m "feat: add draft completion models" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 2: Implement Rules-First Completion Engine

**Files:**
- Create: `backend/app/draft_completion.py`
- Modify: `tests/test_draft_completion.py`

- [ ] **Step 1: Add failing engine tests**

Append to `tests/test_draft_completion.py`:

```python
from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    DraftPackage,
    FeatureRecord,
    PatentPointCandidate,
)


def _completion_package() -> DraftPackage:
    return DraftPackage(
        title="一种既有建筑外立面逆建模与工程量清单生成方法",
        abstract="本发明公开一种外立面逆建模方法。",
        claims=(
            "1. 一种既有建筑外立面逆建模与工程量清单生成方法，其特征在于，"
            "生成IfcRelVoidsElement洞口扣减关系，建立工程量清单回链，并基于GUID依赖图进行增量更新。"
        ),
        description="本实施例获取点云和多视角影像，生成IFC模型，并输出工程量清单。",
        drawing_description="图1为方法流程图。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿 prompt",
        review_findings=[],
        citations=[],
        generation_logs=["deliberation: no completed multi-agent deliberation injected"],
    )


def test_completion_engine_finds_support_gaps_and_patch_suggestions():
    worksheet = ClaimDefenseWorksheet(
        id="w1",
        project_id="project-1",
        feature_records=[
            FeatureRecord(
                feature_id="f1",
                text="IfcRelVoidsElement洞口扣减关系、工程量清单回链和GUID依赖图增量更新",
                classification="core_combo",
                claim_refs=["1"],
                description_refs=[],
                figure_refs=["图1"],
                risk_tags=["组合创造性"],
            )
        ],
    )
    point = PatentPointCandidate(
        id="p1",
        title="IFC洞口扣减与清单回链",
        technical_problem="洞口扣减与工程量清单缺少可追溯关系。",
        innovation="建立IFC洞口扣减拓扑与清单回链。",
        technical_solution="生成IfcRelVoidsElement并建立清单回链。",
        evidence_status="feasible_unverified",
    )

    run = run_draft_completion(
        project_id="project-1",
        package=_completion_package(),
        filing_reports=[],
        worksheets=[worksheet],
        patent_points=[point],
        disclosures=[],
        materials=[],
    )

    categories = {issue.category for issue in run.issues}
    task_outputs = "\n".join(task.expected_output for task in run.tasks)
    patch_text = "\n".join(patch.after_text for patch in run.patches)
    assert "claim_support_gap" in categories
    assert "format_pollution" in categories
    assert "BillTraceRecord" in task_outputs
    assert "IfcRelVoidsElement" in patch_text
    assert run.support_matrix[0].completion_status == "missing"
    assert run.scorecard.support_strength < 70


def test_completion_report_is_sidecar_and_mentions_warning_mode():
    run = run_draft_completion(
        project_id="project-1",
        package=_completion_package(),
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
    )
    markdown = completion_run_to_markdown(run)

    assert "# DRAFT_COMPLETION_REPORT" in markdown
    assert "警告但允许导出" in markdown
    assert "## Scorecard" in markdown
    assert "## Proposed Patches" in markdown
```

- [ ] **Step 2: Run engine tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_draft_completion.py::test_completion_engine_finds_support_gaps_and_patch_suggestions tests/test_draft_completion.py::test_completion_report_is_sidecar_and_mentions_warning_mode -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.draft_completion'`.

- [ ] **Step 3: Add engine implementation**

Create `backend/app/draft_completion.py` with:

```python
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.filing_readiness import assess_filing_readiness
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    ClaimSupportMatrixRow,
    CompletionIssue,
    CompletionScoreCard,
    CompletionTask,
    DisclosureRun,
    DraftCompletionRun,
    DraftPackage,
    FilingReadinessReport,
    PatentPointCandidate,
    ProjectMaterial,
    ProposedPatch,
)


CORE_TERMS = ("IfcRelVoidsElement", "工程量清单回链", "BillTraceRecord", "GUID依赖图", "增量更新")
SEVERITY_PENALTY = {"high": 12, "medium": 7, "low": 3}


def run_draft_completion(
    *,
    project_id: str,
    package: DraftPackage,
    filing_reports: list[FilingReadinessReport],
    worksheets: list[ClaimDefenseWorksheet],
    patent_points: list[PatentPointCandidate],
    disclosures: list[DisclosureRun],
    materials: list[ProjectMaterial],
) -> DraftCompletionRun:
    snapshot_hash = _snapshot_hash(package, patent_points, materials)
    readiness = filing_reports[0] if filing_reports else assess_filing_readiness(
        project_id,
        package,
        verified_effects=any(point.evidence_status == "verified" for point in patent_points),
    )
    worksheet = worksheets[0] if worksheets else generate_claim_defense_worksheet(
        project_id=project_id,
        package=package,
        disclosures=disclosures,
        patent_points=patent_points,
        llm=None,
    )

    issues = _issues_from_readiness(readiness)
    matrix = _support_matrix(worksheet, package, patent_points)
    issues.extend(_issues_from_support_matrix(matrix))
    issues.extend(_specification_sufficiency_issues(package, matrix))
    issues.extend(_unverified_scheme_issues(package, patent_points))
    issues = _dedupe_issues(issues)
    tasks = _tasks_from_issues(issues, package)
    patches = _patches_from_tasks(tasks)
    scorecard = _scorecard(issues, matrix, package)

    return DraftCompletionRun(
        id=uuid.uuid4().hex,
        project_id=project_id,
        snapshot_hash=snapshot_hash,
        status="completed",
        issues=issues,
        tasks=tasks,
        patches=patches,
        support_matrix=matrix,
        scorecard=scorecard,
        notes=["completion-run uses warning-mode export: risks are sidecar guidance, not export blockers."],
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def completion_run_to_markdown(run: DraftCompletionRun) -> str:
    lines = [
        "# DRAFT_COMPLETION_REPORT",
        "",
        "本报告为内部侧车文件。系统采用警告但允许导出：高风险不会硬性阻止正式稿导出。",
        "",
        f"- run_id: {run.id}",
        f"- project_id: {run.project_id}",
        f"- status: {run.status}",
        f"- snapshot_hash: {run.snapshot_hash}",
        "",
        "## Scorecard",
        "",
        f"- authorization_stability: {run.scorecard.authorization_stability}",
        f"- protection_scope: {run.scorecard.protection_scope}",
        f"- support_strength: {run.scorecard.support_strength}",
        f"- prior_art_distinction: {run.scorecard.prior_art_distinction}",
        f"- filing_maturity: {run.scorecard.filing_maturity}",
        f"- official_hygiene: {run.scorecard.official_hygiene}",
        f"- overall: {run.scorecard.overall}",
        "",
        "## Issues",
    ]
    if not run.issues:
        lines.append("无明显初稿完善缺口。")
    for issue in run.issues:
        lines.extend(
            [
                "",
                f"### {issue.id} {issue.category}",
                f"- severity: {issue.severity}",
                f"- target: {issue.target}",
                f"- source_refs: {', '.join(issue.source_refs)}",
                f"- message: {issue.message}",
                f"- why_it_matters: {issue.why_it_matters}",
                f"- suggested_action: {issue.suggested_action}",
                f"- blocks_submission: {issue.blocks_submission}",
            ]
        )
    lines.extend(["", "## Claim Support Matrix"])
    for row in run.support_matrix:
        lines.append(
            f"- {row.claim_ref}: {row.completion_status} | {row.feature_classification} | {row.feature_text}"
        )
    lines.extend(["", "## Completion Tasks"])
    for task in run.tasks:
        lines.append(f"- [{task.status}] {task.priority} {task.task_type}: {task.expected_output}")
    lines.extend(["", "## Proposed Patches"])
    for patch in run.patches:
        lines.extend(
            [
                f"### {patch.id} {patch.patch_kind} -> {patch.target_section}",
                f"- status: {patch.status}",
                f"- can_enter_official_draft: {patch.can_enter_official_draft}",
                f"- rationale: {patch.rationale}",
                "",
                patch.after_text,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _snapshot_hash(package: DraftPackage, patent_points: list[PatentPointCandidate], materials: list[ProjectMaterial]) -> str:
    payload = package.model_dump_json() + "".join(point.model_dump_json() for point in patent_points)
    payload += "".join(material.id + material.file_name for material in materials)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _issues_from_readiness(report: FilingReadinessReport) -> list[CompletionIssue]:
    issues: list[CompletionIssue] = []
    mapping = {
        "format_pollution": "format_pollution",
        "internal_trace": "unfavorable_statement",
        "unfavorable_statement": "unfavorable_statement",
        "unverified_effect": "unverified_scheme_gap",
        "subject_matter_risk": "subject_matter_risk",
        "support_gap": "claim_support_gap",
    }
    for index, item in enumerate(report.issues, start=1):
        issues.append(
            CompletionIssue(
                id=f"i-readiness-{index}",
                category=mapping.get(item.category, "format_pollution"),
                severity=item.severity,
                target="export" if item.target == "export" else "description",
                source_refs=[f"filing_readiness:{item.target}"],
                message=item.message,
                why_it_matters="正式稿污染或不利表述会降低提交成熟度。",
                suggested_action=item.suggestion,
                blocks_submission=False,
            )
        )
    return issues


def _support_matrix(
    worksheet: ClaimDefenseWorksheet,
    package: DraftPackage,
    patent_points: list[PatentPointCandidate],
) -> list[ClaimSupportMatrixRow]:
    rows: list[ClaimSupportMatrixRow] = []
    for record in worksheet.feature_records:
        text = record.text
        description_refs = list(record.description_refs)
        if not description_refs and _appears_in_description(text, package.description):
            description_refs = ["description:auto-match"]
        formula_refs = ["description:formula"] if any(symbol in package.description for symbol in ["=", "∑", "矩阵", "射线"]) else []
        data_refs = ["description:BillTraceRecord"] if "BillTraceRecord" in package.description else []
        pseudo_refs = ["description:IFC pseudo-code"] if any(term in package.description for term in ["RelatingBuildingElement", "RelatedOpeningElement"]) else []
        status = "supported" if description_refs and (data_refs or pseudo_refs or formula_refs) else "partial" if description_refs else "missing"
        rows.append(
            ClaimSupportMatrixRow(
                claim_ref=record.claim_refs[0] if record.claim_refs else "",
                feature_text=text,
                feature_classification=record.classification,
                description_refs=description_refs,
                figure_refs=record.figure_refs,
                data_structure_refs=data_refs,
                pseudo_code_refs=pseudo_refs,
                prior_art_refs=record.prior_art_refs,
                evidence_status=_evidence_status(text, patent_points),
                risk_tags=record.risk_tags,
                completion_status=status,
            )
        )
    return rows


def _issues_from_support_matrix(matrix: list[ClaimSupportMatrixRow]) -> list[CompletionIssue]:
    issues: list[CompletionIssue] = []
    for index, row in enumerate(matrix, start=1):
        if row.completion_status == "supported":
            continue
        severity = "high" if row.feature_classification in {"core_combo", "support_needed"} else "medium"
        issues.append(
            CompletionIssue(
                id=f"i-support-{index}",
                category="claim_support_gap",
                severity=severity,
                target="claim",
                source_refs=[f"claim:{row.claim_ref}" if row.claim_ref else "claim"],
                message=f"权利要求特征缺少充分支撑：{row.feature_text}",
                why_it_matters="权利要求特征缺少说明书、实施例、公式或数据结构支撑，会增加充分公开和支持性风险。",
                suggested_action="补充对应公式、数据结构、伪代码、附图说明或端到端实施例。",
                blocks_submission=True,
            )
        )
    return issues


def _specification_sufficiency_issues(package: DraftPackage, matrix: list[ClaimSupportMatrixRow]) -> list[CompletionIssue]:
    text = "\n".join([package.claims, package.description, *(row.feature_text for row in matrix)])
    description = package.description
    checks = [
        ("BillTraceRecord", "补充BillTraceRecord字段、字段含义和清单项回链示例。"),
        ("IfcRelVoidsElement", "补充IfcWall、IfcOpeningElement、IfcRelVoidsElement的伪IFC关联片段。"),
        ("GUID依赖图", "补充人工修正事件触发后的GUID依赖图遍历和局部重算算法。"),
    ]
    issues = []
    for index, (term, action) in enumerate(checks, start=1):
        if term in text and term not in description:
            issues.append(
                CompletionIssue(
                    id=f"i-sufficiency-{index}",
                    category="specification_sufficiency_gap",
                    severity="high",
                    target="description",
                    source_refs=[f"term:{term}"],
                    message=f"核心术语 {term} 出现在权利要求或特征中，但说明书缺少具体实现。",
                    why_it_matters="核心组合特征需要工程化支撑，不能只停留在流程罗列。",
                    suggested_action=action,
                    blocks_submission=True,
                )
            )
    return issues


def _unverified_scheme_issues(package: DraftPackage, patent_points: list[PatentPointCandidate]) -> list[CompletionIssue]:
    if not any(point.evidence_status in {"feasible_unverified", "needs_experiment"} for point in patent_points):
        return []
    text = "\n".join([package.abstract, package.claims, package.description])
    risky = any(marker in text for marker in ["已验证", "实测", "效率提升", "误差降低", "提升30%", "降低30%"])
    if not risky:
        return []
    return [
        CompletionIssue(
            id="i-unverified-1",
            category="unverified_scheme_gap",
            severity="medium",
            target="evidence",
            source_refs=["patent_points"],
            message="可行未验证方案被写成已验证效果或确定工程结果。",
            why_it_matters="项目允许纳入可行未验证方案，但正式稿不能把未验证效果写成事实。",
            suggested_action="改写为可选实施方式、替代方案、变形例或机理性有益效果。",
            blocks_submission=False,
        )
    ]


def _tasks_from_issues(issues: list[CompletionIssue], package: DraftPackage) -> list[CompletionTask]:
    tasks: list[CompletionTask] = []
    for index, issue in enumerate(issues, start=1):
        if issue.category == "format_pollution":
            task_type = "clean_official_text"
            expected = "删除 Mermaid、prompt、Markdown 代码块和内部生成日志。"
            target = "export"
        elif issue.category == "specification_sufficiency_gap" and "BillTraceRecord" in issue.suggested_action:
            task_type = "add_data_structure"
            expected = "BillTraceRecord 数据结构及字段解释。"
            target = "description"
        elif issue.category == "specification_sufficiency_gap" and "IfcWall" in issue.suggested_action:
            task_type = "add_pseudo_ifc"
            expected = "IfcWall、IfcOpeningElement、IfcRelVoidsElement 伪IFC片段。"
            target = "description"
        elif issue.category == "specification_sufficiency_gap" and "GUID" in issue.suggested_action:
            task_type = "add_incremental_algorithm"
            expected = "GUID依赖图遍历和受影响清单项局部重算伪代码。"
            target = "description"
        else:
            task_type = "revise_draft_support"
            expected = issue.suggested_action
            target = issue.target
        tasks.append(
            CompletionTask(
                id=f"t{index}",
                issue_id=issue.id,
                task_type=task_type,
                priority=_priority(issue),
                input_refs=issue.source_refs,
                expected_output=expected,
                draft_section_target=target,
            )
        )
    return tasks


def _patches_from_tasks(tasks: list[CompletionTask]) -> list[ProposedPatch]:
    patches: list[ProposedPatch] = []
    for index, task in enumerate(tasks, start=1):
        after_text = _patch_text(task)
        patches.append(
            ProposedPatch(
                id=f"patch-{index}",
                task_id=task.id,
                target_section=task.draft_section_target,
                patch_kind="sidecar_only" if task.draft_section_target == "export" else "insert",
                after_text=after_text,
                rationale=f"响应补强任务：{task.expected_output}",
                risk_delta="降低提交成熟度、充分公开或格式污染风险。",
                evidence_refs=[f"task:{task.id}", *task.input_refs],
                can_enter_official_draft=task.draft_section_target in {"description", "claim", "drawing", "embodiment"},
            )
        )
    return patches


def _patch_text(task: CompletionTask) -> str:
    if task.task_type == "add_data_structure":
        return (
            "在一个实施例中，工程量清单回链记录 BillTraceRecord 包括 item_id、formula_id、"
            "ifc_guid_list、void_relation_guid_list、image_frame_ids、pixel_regions、"
            "point_cloud_indices、confidence_score 和 update_version。"
        )
    if task.task_type == "add_pseudo_ifc":
        return (
            "在一个实施例中，墙体实体 IfcWall 通过 IfcRelVoidsElement.RelatingBuildingElement "
            "关联至墙体GUID，并通过 IfcRelVoidsElement.RelatedOpeningElement 关联至 "
            "IfcOpeningElement 的洞口GUID，以形成洞口扣减拓扑。"
        )
    if task.task_type == "add_incremental_algorithm":
        return (
            "在一个实施例中，人工修正事件记录被修改构件GUID，系统沿GUID依赖图查找受影响的"
            "IfcRelVoidsElement和清单项，仅对受影响清单项执行局部重算并更新update_version。"
        )
    if task.task_type == "clean_official_text":
        return "该项仅进入侧车报告：正式稿导出时删除内部痕迹、Mermaid、prompt和生成日志。"
    return task.expected_output


def _scorecard(issues: list[CompletionIssue], matrix: list[ClaimSupportMatrixRow], package: DraftPackage) -> CompletionScoreCard:
    high = sum(1 for issue in issues if issue.severity == "high")
    medium = sum(1 for issue in issues if issue.severity == "medium")
    support_missing = sum(1 for row in matrix if row.completion_status == "missing")
    support_partial = sum(1 for row in matrix if row.completion_status == "partial")
    support_strength = _clamp(100 - support_missing * 18 - support_partial * 9)
    official_hygiene = _clamp(100 - sum(SEVERITY_PENALTY[issue.severity] for issue in issues if issue.target == "export"))
    authorization = _clamp(100 - high * 10 - medium * 5)
    distinction = _clamp(85 if any(term in package.claims for term in CORE_TERMS) else 60)
    protection = _clamp(78 if "工程量" in package.claims and "IFC" in package.claims.upper() else 62)
    maturity = _clamp((support_strength + official_hygiene + authorization) // 3)
    overall = _clamp((authorization + protection + support_strength + distinction + maturity + official_hygiene) // 6)
    return CompletionScoreCard(
        authorization_stability=authorization,
        protection_scope=protection,
        support_strength=support_strength,
        prior_art_distinction=distinction,
        filing_maturity=maturity,
        official_hygiene=official_hygiene,
        overall=overall,
    )


def _priority(issue: CompletionIssue) -> int:
    base = {"high": 100, "medium": 60, "low": 30}[issue.severity]
    return base + (10 if issue.blocks_submission else 0)


def _appears_in_description(feature: str, description: str) -> bool:
    terms = [term for term in CORE_TERMS if term in feature]
    if terms:
        return any(term in description for term in terms)
    return feature[:12] in description


def _evidence_status(feature: str, patent_points: list[PatentPointCandidate]) -> str:
    for point in patent_points:
        haystack = "\n".join([point.title, point.innovation, point.technical_solution])
        if any(term in haystack for term in CORE_TERMS if term in feature):
            return point.evidence_status
    return "model_generated"


def _dedupe_issues(issues: list[CompletionIssue]) -> list[CompletionIssue]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[CompletionIssue] = []
    for issue in issues:
        key = (issue.category, issue.target, issue.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))
```

- [ ] **Step 4: Run engine tests**

Run:

```bash
python3 -m pytest tests/test_draft_completion.py -q
```

Expected: all tests in `tests/test_draft_completion.py` pass.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/draft_completion.py tests/test_draft_completion.py && git commit -m "feat: add draft completion engine" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 3: Persist Completion Runs

**Files:**
- Modify: `backend/app/storage.py`
- Create: `tests/test_draft_completion_api.py`

- [ ] **Step 1: Add failing storage tests**

Create `tests/test_draft_completion_api.py` with:

```python
from backend.app.schemas import CompletionScoreCard, DraftCompletionRun
from backend.app.storage import SQLiteStore


def _stored_completion_run(project_id: str = "project-1") -> DraftCompletionRun:
    return DraftCompletionRun(
        id="run-1",
        project_id=project_id,
        snapshot_hash="hash-1",
        status="completed",
        scorecard=CompletionScoreCard(
            authorization_stability=80,
            protection_scope=75,
            support_strength=70,
            prior_art_distinction=65,
            filing_maturity=72,
            official_hygiene=90,
            overall=75,
        ),
    )


def test_store_persists_and_updates_completion_runs(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    run = store.create_draft_completion_run(_stored_completion_run())

    assert store.get_draft_completion_run("project-1", run.id) is not None
    assert store.list_draft_completion_runs("project-1")[0].id == "run-1"

    updated = store.update_completion_patch_status("project-1", "run-1", "missing", "accepted")
    assert updated is None
```

- [ ] **Step 2: Run storage test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_draft_completion_api.py::test_store_persists_and_updates_completion_runs -q
```

Expected: FAIL with missing `create_draft_completion_run`.

- [ ] **Step 3: Update storage imports**

In `backend/app/storage.py`, add `DraftCompletionRun` to the schemas import list:

```python
    DraftCompletionRun,
```

- [ ] **Step 4: Add storage methods**

Add these methods near the existing filing-readiness and claim-defense methods in `SQLiteStore`:

```python
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

    def update_completion_patch_status(
        self,
        project_id: str,
        run_id: str,
        patch_id: str,
        status: str,
    ) -> DraftCompletionRun | None:
        run = self.get_draft_completion_run(project_id, run_id)
        if not run:
            return None
        found = False
        patches = []
        for patch in run.patches:
            if patch.id == patch_id:
                patches.append(patch.model_copy(update={"status": status}))
                found = True
            else:
                patches.append(patch)
        if not found:
            return None
        updated = run.model_copy(update={"patches": patches})
        with self.connection:
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
```

- [ ] **Step 5: Add migration table**

In `_migrate`, after `claim_defense_worksheets`, add:

```sql
                create table if not exists draft_completion_runs (
                    id text primary key,
                    project_id text not null,
                    run_json text not null,
                    created_at text not null default current_timestamp,
                    foreign key(project_id) references projects(id)
                );
```

- [ ] **Step 6: Add row parser**

Add near `_claim_defense_worksheet_from_row`:

```python
    def _draft_completion_run_from_row(self, row: sqlite3.Row) -> DraftCompletionRun:
        run = DraftCompletionRun.model_validate(json.loads(row["run_json"]))
        if not run.created_at:
            run = run.model_copy(update={"created_at": row["created_at"]})
        return run
```

- [ ] **Step 7: Run storage test**

Run:

```bash
python3 -m pytest tests/test_draft_completion_api.py::test_store_persists_and_updates_completion_runs -q
```

Expected: `1 passed`.

- [ ] **Step 8: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/storage.py tests/test_draft_completion_api.py && git commit -m "feat: persist draft completion runs" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 4: Add Completion API Endpoints

**Files:**
- Modify: `backend/app/main.py`
- Modify: `tests/test_draft_completion_api.py`

- [ ] **Step 1: Add failing API tests**

Append to `tests/test_draft_completion_api.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import create_app


def _client(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_completion_api_runs_lists_exports_and_updates_patch_status(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "name": "外立面逆建模",
            "draft_text": "一种生成IfcRelVoidsElement并建立工程量清单回链的方法。",
        },
    ).json()
    package_response = client.post(f"/api/projects/{project['id']}/generate")
    assert package_response.status_code == 503

    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种既有建筑外立面逆建模方法",
            abstract="本发明公开一种外立面逆建模方法。",
            claims="1. 一种方法，其特征在于生成IfcRelVoidsElement并建立工程量清单回链。",
            description="本实施例生成IFC模型。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="prompt",
            review_findings=[],
            citations=[],
            generation_logs=["deliberation: no completed multi-agent deliberation injected"],
        ),
    )

    run_response = client.post(f"/api/projects/{project['id']}/completion-runs")
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["scorecard"]["overall"] <= 100
    assert run["issues"]

    list_response = client.get(f"/api/projects/{project['id']}/completion-runs")
    assert list_response.status_code == 200
    assert list_response.json()["runs"][0]["id"] == run["id"]

    report_response = client.get(f"/api/projects/{project['id']}/completion-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "DRAFT_COMPLETION_REPORT" in report_response.text

    patch_id = run["patches"][0]["id"]
    accept_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/accept")
    assert accept_response.status_code == 200
    assert any(patch["id"] == patch_id and patch["status"] == "accepted" for patch in accept_response.json()["patches"])

    reject_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/reject")
    assert reject_response.status_code == 200
    assert any(patch["id"] == patch_id and patch["status"] == "rejected" for patch in reject_response.json()["patches"])
```

- [ ] **Step 2: Run API test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_draft_completion_api.py::test_completion_api_runs_lists_exports_and_updates_patch_status -q
```

Expected: FAIL with `404 Not Found` for `/completion-runs`.

- [ ] **Step 3: Add imports in main**

In `backend/app/main.py`, add:

```python
from backend.app.draft_completion import completion_run_to_markdown, run_draft_completion
```

- [ ] **Step 4: Add completion endpoints**

In `create_app`, add these routes after claim-defense routes and before export routes:

```python
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
```

- [ ] **Step 5: Run API tests**

Run:

```bash
python3 -m pytest tests/test_draft_completion_api.py -q
```

Expected: all tests in `tests/test_draft_completion_api.py` pass.

- [ ] **Step 6: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add backend/app/main.py tests/test_draft_completion_api.py && git commit -m "feat: add draft completion api" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 5: Add Frontend Completion Types And Helpers

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/domain.ts`
- Modify: `frontend/src/domain.test.ts`

- [ ] **Step 1: Add failing frontend helper tests**

Modify `frontend/src/domain.test.ts` tab-order expectation to include `初稿完善`:

Extend the existing import from `./domain`:

```ts
  completionCategoryLabel,
  completionScoreAverage,
  completionTargetLabel,
```

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
      "初稿完善",
      "审查修改",
      "导出",
    ]);
```

Append:

```ts
describe("draft completion helpers", () => {
  it("labels completion fields and averages scorecards", () => {
    expect(completionCategoryLabel("claim_support_gap")).toBe("权利要求支撑缺口");
    expect(completionTargetLabel("description")).toBe("说明书");
    expect(
      completionScoreAverage({
        authorization_stability: 80,
        protection_scope: 70,
        support_strength: 60,
        prior_art_distinction: 90,
        filing_maturity: 50,
        official_hygiene: 100,
        overall: 75,
      }),
    ).toBe(75);
  });
});
```

- [ ] **Step 2: Run frontend helper tests to verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/domain.test.ts
```

Expected: FAIL because the `completion` tab and helper functions do not exist.

- [ ] **Step 3: Add completion tab and helpers**

In `frontend/src/domain.ts`, import an icon:

```ts
  Gauge,
```

Add `"completion"` to `WorkspaceTabId` after `"claimDefense"`:

```ts
  | "completion"
```

Add the tab after `权利要求防线`:

```ts
  { id: "completion", label: "初稿完善", icon: Gauge },
```

Add helper functions:

```ts
export function completionCategoryLabel(category: string): string {
  if (category === "claim_support_gap") return "权利要求支撑缺口";
  if (category === "specification_sufficiency_gap") return "说明书充分公开缺口";
  if (category === "figure_consistency_gap") return "附图一致性缺口";
  if (category === "term_definition_gap") return "术语定义缺口";
  if (category === "prior_art_distinction_gap") return "现有技术差异缺口";
  if (category === "unverified_scheme_gap") return "未验证方案风险";
  if (category === "format_pollution") return "格式污染";
  if (category === "subject_matter_risk") return "客体风险";
  if (category === "claim_scope_risk") return "保护范围风险";
  return "不利表述";
}

export function completionTargetLabel(target: string): string {
  if (target === "claim") return "权利要求";
  if (target === "description") return "说明书";
  if (target === "drawing") return "附图";
  if (target === "embodiment") return "实施例";
  if (target === "term") return "术语";
  if (target === "evidence") return "证据";
  if (target === "prior_art") return "现有技术";
  return "导出";
}

export function completionScoreAverage(scorecard: { overall: number }): number {
  return scorecard.overall;
}
```

- [ ] **Step 4: Add TypeScript API types and functions**

In `frontend/src/api.ts`, add interfaces after `ClaimDefenseWorksheet`:

```ts
export interface CompletionIssue {
  id: string;
  category: string;
  severity: FilingIssueSeverity;
  target: "claim" | "description" | "drawing" | "embodiment" | "term" | "evidence" | "prior_art" | "export";
  source_refs: string[];
  message: string;
  why_it_matters: string;
  suggested_action: string;
  blocks_submission: boolean;
}

export interface CompletionTask {
  id: string;
  issue_id: string;
  task_type: string;
  priority: number;
  input_refs: string[];
  expected_output: string;
  draft_section_target: string;
  status: "open" | "proposed" | "accepted" | "rejected" | "superseded";
}

export interface ProposedPatch {
  id: string;
  task_id: string;
  target_section: string;
  patch_kind: "insert" | "replace" | "delete" | "rewrite" | "sidecar_only";
  before_text: string;
  after_text: string;
  rationale: string;
  risk_delta: string;
  evidence_refs: string[];
  can_enter_official_draft: boolean;
  status: "proposed" | "accepted" | "rejected" | "superseded";
}

export interface CompletionScoreCard {
  authorization_stability: number;
  protection_scope: number;
  support_strength: number;
  prior_art_distinction: number;
  filing_maturity: number;
  official_hygiene: number;
  overall: number;
}

export interface ClaimSupportMatrixRow {
  claim_ref: string;
  feature_text: string;
  feature_classification: FeatureClassification;
  description_refs: string[];
  figure_refs: string[];
  embodiment_refs: string[];
  formula_refs: string[];
  data_structure_refs: string[];
  pseudo_code_refs: string[];
  prior_art_refs: string[];
  evidence_status: EvidenceStatus;
  risk_tags: string[];
  completion_status: "supported" | "partial" | "missing";
}

export interface DraftCompletionRun {
  id: string;
  project_id: string;
  snapshot_hash: string;
  status: "completed" | "failed";
  issues: CompletionIssue[];
  tasks: CompletionTask[];
  patches: ProposedPatch[];
  support_matrix: ClaimSupportMatrixRow[];
  scorecard: CompletionScoreCard;
  notes: string[];
  created_at: string;
}
```

Add API functions near existing readiness/claim-defense functions:

```ts
export async function createDraftCompletionRun(projectId: string): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs`, { method: "POST" });
}

export async function listDraftCompletionRuns(projectId: string): Promise<DraftCompletionRun[]> {
  const data = await request<{ runs: DraftCompletionRun[] }>(`/api/projects/${projectId}/completion-runs`);
  return data.runs;
}

export function draftCompletionReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/completion-runs/${runId}/report.md`;
}

export async function acceptCompletionPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/${patchId}/accept`, {
    method: "POST",
  });
}

export async function rejectCompletionPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/${patchId}/reject`, {
    method: "POST",
  });
}
```

- [ ] **Step 5: Run frontend helper tests**

Run:

```bash
cd frontend
npm test -- --run src/domain.test.ts
```

Expected: `src/domain.test.ts` passes.

- [ ] **Step 6: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add frontend/src/api.ts frontend/src/domain.ts frontend/src/domain.test.ts && git commit -m "feat: add draft completion frontend types" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 6: Add Draft Completion Workbench UI

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add imports and state**

In `frontend/src/App.tsx`, extend imports from `frontend/src/api.ts`:

```ts
  acceptCompletionPatch,
  createDraftCompletionRun,
  draftCompletionReportUrl,
  listDraftCompletionRuns,
  rejectCompletionPatch,
  type DraftCompletionRun,
```

Extend imports from `frontend/src/domain.ts`:

```ts
  completionCategoryLabel,
  completionTargetLabel,
```

Add state near existing readiness/claim-defense state:

```ts
  const [completionRuns, setCompletionRuns] = useState<DraftCompletionRun[]>([]);
```

- [ ] **Step 2: Load completion runs on project change**

In the existing selected-project loading effect, add:

```ts
        const completion = await listDraftCompletionRuns(selectedProject.id);
        if (!cancelled && selectedProject.id === selectedProjectRef.current?.id) {
          setCompletionRuns(completion);
        }
```

If the app uses separate async loaders for readiness and worksheets, add a small helper instead:

```ts
  async function refreshCompletionRuns(projectId = selectedProject?.id) {
    if (!projectId) return;
    const runs = await listDraftCompletionRuns(projectId);
    setCompletionRuns(runs);
  }
```

Call `setCompletionRuns([])` wherever project-specific readiness and worksheet state are cleared.

- [ ] **Step 3: Add run and patch handlers**

Add handlers near existing readiness/claim-defense handlers:

```ts
  async function handleRunDraftCompletion() {
    if (!selectedProject) return;
    await withStatus("completion", async () => {
      const run = await createDraftCompletionRun(selectedProject.id);
      setCompletionRuns((items) => [run, ...items.filter((item) => item.id !== run.id)]);
      setMessage(`初稿完善完成：整体评分 ${run.scorecard.overall}/100`);
    });
  }

  async function handleCompletionPatch(runId: string, patchId: string, action: "accept" | "reject") {
    if (!selectedProject) return;
    await withStatus(`completion-${action}-${patchId}`, async () => {
      const run =
        action === "accept"
          ? await acceptCompletionPatch(selectedProject.id, runId, patchId)
          : await rejectCompletionPatch(selectedProject.id, runId, patchId);
      setCompletionRuns((items) => items.map((item) => (item.id === run.id ? run : item)));
      setMessage(action === "accept" ? "修订建议已标记为采纳。" : "修订建议已标记为拒绝。");
    });
  }
```

- [ ] **Step 4: Render completion tab**

Add this branch near `readiness` and `claimDefense` tab branches:

```tsx
        {activeTab === "completion" && (
          <DraftCompletionView
            project={selectedProject}
            packageValue={currentPackage}
            runs={completionRuns}
            busy={busy}
            onRun={handleRunDraftCompletion}
            onPatch={handleCompletionPatch}
          />
        )}
```

- [ ] **Step 5: Add DraftCompletionView component**

Add this component before `ExportView`:

```tsx
function DraftCompletionView({
  project,
  packageValue,
  runs,
  busy,
  onRun,
  onPatch,
}: {
  project: ProjectRecord | null;
  packageValue: DraftPackage | null;
  runs: DraftCompletionRun[];
  busy: string | null;
  onRun: () => void;
  onPatch: (runId: string, patchId: string, action: "accept" | "reject") => void;
}) {
  const latest = runs[0] ?? null;
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Draft Completion Harness</p>
          <h3>初稿完善循环</h3>
          <p className="muted">生成支撑矩阵、补强任务和侧车完善报告。高风险只提示，不阻止正式稿导出。</p>
        </div>
        <button type="button" onClick={onRun} disabled={!project || !packageValue || busy === "completion"}>
          {busy === "completion" ? "完善中..." : "运行初稿完善"}
        </button>
      </div>

      {!packageValue && <p className="empty">请先完成分步撰写，生成初稿后再运行完善审计。</p>}
      {latest && (
        <>
          <div className="score-grid">
            {[
              ["授权稳定性", latest.scorecard.authorization_stability],
              ["保护范围", latest.scorecard.protection_scope],
              ["支撑强度", latest.scorecard.support_strength],
              ["差异清晰度", latest.scorecard.prior_art_distinction],
              ["提交成熟度", latest.scorecard.filing_maturity],
              ["正式稿清洁度", latest.scorecard.official_hygiene],
              ["整体", latest.scorecard.overall],
            ].map(([label, value]) => (
              <div className="score-card" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          <div className="split-grid">
            <div>
              <h4>高优先级缺口</h4>
              <div className="stack-list">
                {latest.issues.map((issue) => (
                  <article className="compact-card" key={issue.id}>
                    <div className="row">
                      <span className={`status-badge ${issue.severity}`}>{issue.severity}</span>
                      <strong>{completionCategoryLabel(issue.category)}</strong>
                      <span className="muted">{completionTargetLabel(issue.target)}</span>
                    </div>
                    <p>{issue.message}</p>
                    <p className="muted">{issue.suggested_action}</p>
                  </article>
                ))}
              </div>
            </div>
            <div>
              <h4>补强任务</h4>
              <div className="stack-list">
                {latest.tasks.map((task) => (
                  <article className="compact-card" key={task.id}>
                    <div className="row">
                      <strong>{task.task_type}</strong>
                      <span className="muted">优先级 {task.priority}</span>
                    </div>
                    <p>{task.expected_output}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>

          <h4>权利要求-支撑矩阵</h4>
          <div className="matrix-table">
            <table>
              <thead>
                <tr>
                  <th>权利要求</th>
                  <th>特征</th>
                  <th>支撑状态</th>
                  <th>证据状态</th>
                </tr>
              </thead>
              <tbody>
                {latest.support_matrix.map((row) => (
                  <tr key={`${row.claim_ref}-${row.feature_text}`}>
                    <td>{row.claim_ref || "-"}</td>
                    <td>{row.feature_text}</td>
                    <td>{row.completion_status}</td>
                    <td>{row.evidence_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h4>修订建议</h4>
          <div className="stack-list">
            {latest.patches.map((patch) => (
              <article className="compact-card" key={patch.id}>
                <div className="row">
                  <strong>{patch.patch_kind} / {patch.target_section}</strong>
                  <span className="muted">{patch.status}</span>
                </div>
                <p>{patch.rationale}</p>
                <pre className="patch-preview">{patch.after_text}</pre>
                <div className="button-row">
                  <button
                    type="button"
                    onClick={() => onPatch(latest.id, patch.id, "accept")}
                    disabled={patch.status === "accepted" || busy === `completion-accept-${patch.id}`}
                  >
                    采纳标记
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => onPatch(latest.id, patch.id, "reject")}
                    disabled={patch.status === "rejected" || busy === `completion-reject-${patch.id}`}
                  >
                    拒绝标记
                  </button>
                </div>
              </article>
            ))}
          </div>

          {project && (
            <a className="export-link" href={draftCompletionReportUrl(project.id, latest.id)}>
              导出 DRAFT_COMPLETION_REPORT.md
            </a>
          )}
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Add CSS**

Append to `frontend/src/styles.css`:

```css
.score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.score-card {
  border: 1px solid #d9dee8;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.score-card span {
  display: block;
  color: #667085;
  font-size: 12px;
}

.score-card strong {
  display: block;
  font-size: 24px;
  margin-top: 4px;
}

.matrix-table {
  overflow-x: auto;
  margin: 12px 0 20px;
}

.matrix-table table {
  width: 100%;
  border-collapse: collapse;
}

.matrix-table th,
.matrix-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px;
  text-align: left;
  vertical-align: top;
}

.patch-preview {
  white-space: pre-wrap;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
  font-size: 13px;
}

.button-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
```

- [ ] **Step 7: Run frontend tests and build**

Run:

```bash
cd frontend
npm test -- --run
npm run build
```

Expected: Vitest passes and Vite build succeeds.

- [ ] **Step 8: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add frontend/src/App.tsx frontend/src/styles.css && git commit -m "feat: add draft completion workbench" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.

---

### Task 7: Update Documentation And Run Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

In `README.md`, after the v0.3 section, add:

```markdown
## v0.4 初稿完善循环

v0.4 增加 `初稿完善` 工作台，用于把专利初稿拆成可审计、可补强、可复查的工作对象。它会生成：

1. `DRAFT_COMPLETION_REPORT.md`：内部侧车完善报告。
2. 多维评分：授权稳定性、保护范围、支撑强度、现有技术差异清晰度、提交成熟度和正式稿清洁度。
3. 权利要求-支撑矩阵：把权利要求特征映射到说明书、附图、实施例、公式、数据结构、伪代码和证据状态。
4. 补强任务队列：把缺口转化为可执行任务，例如补充 `BillTraceRecord`、伪 IFC 片段或 GUID 依赖图算法。
5. 局部修订建议：默认只作为建议，不自动覆盖正式稿。

本功能延续“警告但允许导出”的原则。红色风险不会禁用正式稿导出；风险、未验证方案和修订建议保存在内部报告中。可行但未验证方案可以进入护城河，但必须保留 `可行未验证` 或 `需实验` 状态，不能在正式稿中写成已验证工程效果。
```

- [ ] **Step 2: Run backend verification**

Run:

```bash
python3 -m pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run
npm run build
```

Expected: all frontend tests pass and production build succeeds.

- [ ] **Step 4: Optional local smoke**

If a browser smoke is needed, start the backend and frontend in separate sessions:

```bash
DEEPSEEK_API_KEY= uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

Expected browser behavior:

- Sidebar includes `初稿完善` after `权利要求防线`.
- Running the completion check creates a scorecard and issue list.
- `DRAFT_COMPLETION_REPORT.md` downloads from the completion tab.
- Official export remains available even when scorecard or issues are high risk.

- [ ] **Step 5: Checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree && git add README.md && git commit -m "docs: describe draft completion harness" || true
```

Expected in the current directory: no commit is created because the project is not a git repository.
