from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

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
READINESS_TARGET_MAP = {
    "claims": "claim",
    "drawings": "drawing",
    "description": "description",
    "abstract": "description",
    "export": "export",
}
HYGIENE_CATEGORIES = {
    "format_pollution",
    "unfavorable_statement",
    "subject_matter_risk",
    "unverified_scheme_gap",
}


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
    package_hash = _package_hash(package)
    readiness = next(
        (report for report in filing_reports if report.draft_package_hash == package_hash),
        None,
    )
    if readiness is None:
        readiness = assess_filing_readiness(
            project_id,
            package,
            verified_effects=any(point.evidence_status == "verified" for point in patent_points),
        )
    # Stored worksheets do not carry a package hash, so completion runs regenerate them.
    worksheet = generate_claim_defense_worksheet(
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

    tasks = _tasks_from_issues(issues)
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
    if not run.support_matrix:
        lines.append("暂无权利要求特征矩阵。")
    for row in run.support_matrix:
        lines.append(
            f"- {row.claim_ref}: {row.completion_status} | {row.feature_classification} | {row.feature_text}"
        )

    lines.extend(["", "## Completion Tasks"])
    if not run.tasks:
        lines.append("暂无补强任务。")
    for task in run.tasks:
        lines.append(f"- [{task.status}] {task.priority} {task.task_type}: {task.expected_output}")

    lines.extend(["", "## Proposed Patches"])
    if not run.patches:
        lines.append("暂无建议补丁。")
    for patch in run.patches:
        lines.extend(
            [
                "",
                f"### {patch.id} {patch.patch_kind} -> {patch.target_section}",
                f"- status: {patch.status}",
                f"- can_enter_official_draft: {patch.can_enter_official_draft}",
                f"- rationale: {patch.rationale}",
                "",
                patch.after_text,
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _snapshot_hash(
    package: DraftPackage,
    patent_points: list[PatentPointCandidate],
    materials: list[ProjectMaterial],
) -> str:
    payload = package.model_dump_json()
    payload += "".join(point.model_dump_json() for point in patent_points)
    payload += "".join(f"{material.id}:{material.file_name}" for material in materials)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _package_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def _issues_from_readiness(report: FilingReadinessReport) -> list[CompletionIssue]:
    category_map = {
        "format_pollution": "format_pollution",
        "internal_trace": "unfavorable_statement",
        "unfavorable_statement": "unfavorable_statement",
        "unverified_effect": "unverified_scheme_gap",
        "subject_matter_risk": "subject_matter_risk",
        "support_gap": "claim_support_gap",
    }
    issues: list[CompletionIssue] = []
    for index, item in enumerate(report.issues, start=1):
        issues.append(
            CompletionIssue(
                id=f"i-readiness-{index}",
                category=category_map.get(item.category, "format_pollution"),
                severity=item.severity,
                target=READINESS_TARGET_MAP[item.target],
                source_refs=[f"filing_readiness:{item.target}"],
                message=item.message,
                why_it_matters="正式稿污染、内部痕迹或不利表述会降低提交成熟度。",
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
        description_refs = list(record.description_refs)
        if not description_refs and _appears_in_description(record.text, package.description):
            description_refs = ["description:auto-match"]

        formula_refs = (
            ["description:formula"]
            if _formula_relevant(record.text) and _has_formula_support(package.description)
            else []
        )
        data_refs = (
            ["description:BillTraceRecord"]
            if _data_structure_relevant(record.text) and "BillTraceRecord" in package.description
            else []
        )
        pseudo_refs = (
            ["description:IFC pseudo-code"]
            if _pseudo_ifc_relevant(record.text)
            and "RelatingBuildingElement" in package.description
            and "RelatedOpeningElement" in package.description
            else []
        )
        completion_status = _completion_status(description_refs, data_refs, pseudo_refs, formula_refs)
        rows.append(
            ClaimSupportMatrixRow(
                claim_ref=record.claim_refs[0] if record.claim_refs else "",
                feature_text=record.text,
                feature_classification=record.classification,
                description_refs=description_refs,
                figure_refs=record.figure_refs,
                formula_refs=formula_refs,
                data_structure_refs=data_refs,
                pseudo_code_refs=pseudo_refs,
                prior_art_refs=record.prior_art_refs,
                evidence_status=_evidence_status(record.text, patent_points),
                risk_tags=record.risk_tags,
                completion_status=completion_status,
            )
        )
    return rows


def _completion_status(
    description_refs: list[str],
    data_refs: list[str],
    pseudo_refs: list[str],
    formula_refs: list[str],
) -> str:
    if description_refs and (data_refs or pseudo_refs or formula_refs):
        return "supported"
    if description_refs:
        return "partial"
    return "missing"


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


def _specification_sufficiency_issues(
    package: DraftPackage,
    matrix: list[ClaimSupportMatrixRow],
) -> list[CompletionIssue]:
    source_text = "\n".join([package.claims, *(row.feature_text for row in matrix)])
    checks = [
        (
            "BillTraceRecord",
            ("工程量清单回链" in source_text or "BillTraceRecord" in source_text)
            and "BillTraceRecord" not in package.description,
            "补充BillTraceRecord字段、字段含义和清单项回链示例。",
        ),
        (
            "IfcRelVoidsElement",
            "IfcRelVoidsElement" in source_text and "IfcRelVoidsElement" not in package.description,
            "补充IfcWall、IfcOpeningElement、IfcRelVoidsElement的伪IFC关联片段。",
        ),
        (
            "GUID依赖图",
            "GUID依赖图" in source_text and "GUID依赖图" not in package.description,
            "补充人工修正事件触发后的GUID依赖图遍历和局部重算算法。",
        ),
    ]

    issues: list[CompletionIssue] = []
    for index, (term, missing, action) in enumerate(checks, start=1):
        if not missing:
            continue
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


def _unverified_scheme_issues(
    package: DraftPackage,
    patent_points: list[PatentPointCandidate],
) -> list[CompletionIssue]:
    if not any(point.evidence_status in {"feasible_unverified", "needs_experiment"} for point in patent_points):
        return []
    draft_text = "\n".join([package.abstract, package.claims, package.description])
    if not any(marker in draft_text for marker in ["已验证", "实测", "效率提升", "误差降低", "提升30%", "降低30%"]):
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


def _tasks_from_issues(issues: list[CompletionIssue]) -> list[CompletionTask]:
    tasks: list[CompletionTask] = []
    for index, issue in enumerate(issues, start=1):
        task_type, expected_output, target = _task_spec(issue)
        tasks.append(
            CompletionTask(
                id=f"t{index}",
                issue_id=issue.id,
                task_type=task_type,
                priority=_priority(issue),
                input_refs=issue.source_refs,
                expected_output=expected_output,
                draft_section_target=target,
            )
        )
    return tasks


def _task_spec(issue: CompletionIssue) -> tuple[str, str, str]:
    if issue.category == "format_pollution":
        return "clean_official_text", "删除 Mermaid、prompt、Markdown 代码块和内部生成日志。", "export"
    if issue.category == "specification_sufficiency_gap" and "BillTraceRecord" in issue.suggested_action:
        return "add_data_structure", "BillTraceRecord 数据结构及字段解释。", "description"
    if issue.category == "specification_sufficiency_gap" and "IfcWall" in issue.suggested_action:
        return "add_pseudo_ifc", "IfcWall、IfcOpeningElement、IfcRelVoidsElement 伪IFC片段。", "description"
    if issue.category == "specification_sufficiency_gap" and "GUID" in issue.suggested_action:
        return "add_incremental_algorithm", "GUID依赖图遍历和受影响清单项局部重算伪代码。", "description"
    return "revise_draft_support", issue.suggested_action, issue.target


def _patches_from_tasks(tasks: list[CompletionTask]) -> list[ProposedPatch]:
    patches: list[ProposedPatch] = []
    for index, task in enumerate(tasks, start=1):
        patches.append(
            ProposedPatch(
                id=f"patch-{index}",
                task_id=task.id,
                target_section=task.draft_section_target,
                patch_kind="sidecar_only" if task.draft_section_target == "export" else "insert",
                after_text=_patch_text(task),
                rationale=f"响应补强任务：{task.expected_output}",
                risk_delta="降低提交成熟度、充分公开或格式污染风险。",
                evidence_refs=[f"task:{task.id}", *task.input_refs],
                can_enter_official_draft=task.draft_section_target
                in {"description", "claim", "drawing", "embodiment"},
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


def _scorecard(
    issues: list[CompletionIssue],
    matrix: list[ClaimSupportMatrixRow],
    package: DraftPackage,
) -> CompletionScoreCard:
    high = sum(1 for issue in issues if issue.severity == "high")
    medium = sum(1 for issue in issues if issue.severity == "medium")
    support_missing = sum(1 for row in matrix if row.completion_status == "missing")
    support_partial = sum(1 for row in matrix if row.completion_status == "partial")

    support_strength = _clamp(100 - support_missing * 35 - support_partial * 15)
    official_hygiene = _clamp(
        100 - sum(SEVERITY_PENALTY[issue.severity] for issue in issues if issue.category in HYGIENE_CATEGORIES)
    )
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


def _has_formula_support(description: str) -> bool:
    return any(symbol in description for symbol in ("=", "∑", "矩阵", "射线"))


def _formula_relevant(feature: str) -> bool:
    return any(term in feature for term in ("反投", "射线", "基面", "平面", "多视角", "相机"))


def _data_structure_relevant(feature: str) -> bool:
    return any(term in feature for term in ("BillTraceRecord", "清单", "回链", "工程量"))


def _pseudo_ifc_relevant(feature: str) -> bool:
    return any(term in feature for term in ("Ifc", "IFC", "洞口", "扣减"))


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
