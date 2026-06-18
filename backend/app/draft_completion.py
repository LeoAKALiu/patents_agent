from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from backend.app.claim_defense import generate_claim_defense_worksheet
from backend.app.evidence_binding import build_evidence_bindings
from backend.app.filing_readiness import assess_filing_readiness
from backend.app.patch_generator import PatchGenerationContext, generate_evidence_backed_patches
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    ClaimSupportMatrixRow,
    CompletionIssue,
    CompletionScoreCard,
    CompletionTask,
    DisclosureRun,
    DraftCompletionRun,
    DraftPackage,
    EvidenceBinding,
    EvidenceBindingSourceType,
    FeatureRecord,
    FilingReadinessReport,
    PatentPointCandidate,
    ProjectMaterial,
    ProjectRecord,
    ProposedPatch,
)


SEVERITY_PENALTY = {"high": 12, "medium": 7, "low": 3}
PROCEDURAL_VERBS = ("采集", "获取", "接收", "解析", "生成", "计算", "确定", "判断", "更新", "输出", "训练", "识别", "匹配", "调度", "校验")
SUPPORT_DETAIL_MARKERS = ("数据结构", "字段", "参数", "伪代码", "步骤S", "算法", "公式", "矩阵", "阈值", "实施例")
DISTINCTION_CLASSIFICATIONS = {"differentiator", "core_combo", "support_needed"}
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
    evidence_bindings: list[EvidenceBinding] | None = None,
) -> DraftCompletionRun:
    snapshot_hash = _snapshot_hash(package, patent_points, materials)
    package_hash = _package_hash(package)
    if evidence_bindings is None:
        evidence_bindings = build_evidence_bindings(
            ProjectRecord(id=project_id, name="", draft_text="", package=package),
            materials=materials,
            disclosures=disclosures,
            patent_points=patent_points,
        )
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
        evidence_bindings=evidence_bindings,
    )

    issues = _issues_from_readiness(readiness)
    matrix = _support_matrix(worksheet, package, patent_points)
    issues.extend(_issues_from_support_matrix(matrix))
    issues.extend(_specification_sufficiency_issues(package, matrix))
    issues.extend(_unverified_scheme_issues(package, patent_points))
    issues = _dedupe_issues(issues)

    tasks = _tasks_from_issues(issues)
    patches = generate_evidence_backed_patches(
        PatchGenerationContext(
            package=package,
            issues=issues,
            tasks=tasks,
            support_matrix=matrix,
            evidence_bindings=evidence_bindings,
        )
    )
    patched_task_ids = {patch.task_id for patch in patches}
    patches.extend(
        _patches_from_tasks(
            [task for task in tasks if task.id not in patched_task_ids],
            start_index=len(patches) + 1,
        )
    )
    scorecard = _scorecard(issues, matrix, package)

    return DraftCompletionRun(
        id=uuid.uuid4().hex,
        project_id=project_id,
        snapshot_hash=snapshot_hash,
        draft_package_hash=package_hash,
        status="completed",
        issues=issues,
        tasks=tasks,
        patches=patches,
        support_matrix=matrix,
        scorecard=scorecard,
        notes=[
            "completion-run is an internal improvement report; official export still requires official compile and post-draft review gates."
        ],
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def completion_run_to_markdown(run: DraftCompletionRun) -> str:
    lines = [
        "# DRAFT_COMPLETION_REPORT",
        "",
        "本报告为内部侧车文件，用于补强正式文本；正式导出仍需通过正式稿编译和成稿后多 Agent 会审。",
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
        details = []
        if row.evidence_refs:
            details.append(f"evidence_refs={', '.join(row.evidence_refs)}")
        if row.missing_evidence_reason:
            details.append(f"missing_evidence={row.missing_evidence_reason}")
        suffix = f" | {' | '.join(details)}" if details else ""
        lines.append(f"- {row.claim_ref}: {row.completion_status} | {row.feature_classification} | {row.feature_text}{suffix}")

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
        "support_gap": "format_pollution",
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
        data_refs = ["description:data-structure"] if _data_structure_relevant(record.text) and _has_data_support(
            record.text, package.description
        ) else []
        pseudo_refs = ["description:pseudo-code"] if _pseudo_code_relevant(record.text) and _has_pseudo_support(
            record.text, package.description
        ) else []
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
                evidence_refs=record.evidence_refs,
                source_refs=record.source_refs,
                support_explanation=record.support_explanation,
                missing_evidence_reason=_missing_evidence_reason(
                    record,
                    description_refs,
                    data_refs,
                    pseudo_refs,
                    formula_refs,
                ),
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


def _missing_evidence_reason(
    record: FeatureRecord,
    description_refs: list[str],
    data_refs: list[str],
    pseudo_refs: list[str],
    formula_refs: list[str],
) -> str:
    has_structural_support = bool(description_refs or data_refs or pseudo_refs or formula_refs)
    if (
        record.evidence_refs
        and record.support_explanation
        and "不升级为已验证支撑" in record.support_explanation
        and "可作为已验证/已检索支撑" not in record.support_explanation
    ):
        return "仅有低置信或未验证证据，不能作为已验证支撑。"
    if record.evidence_refs and has_structural_support:
        return ""
    if not record.evidence_refs and record.classification in DISTINCTION_CLASSIFICATIONS:
        return "核心/区别特征缺少用户材料、专利点或现有技术证据绑定。"
    if not has_structural_support:
        return "说明书缺少对应实施例、数据结构、公式或伪代码支撑。"
    return ""


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
                source_refs=list(
                    dict.fromkeys(
                        [
                            f"claim:{row.claim_ref}" if row.claim_ref else "claim",
                            *row.source_refs,
                            *[f"evidence:{ref}" for ref in row.evidence_refs],
                        ]
                    )
                ),
                message=f"权利要求特征缺少充分支撑：{row.feature_text}",
                why_it_matters="权利要求特征缺少说明书、实施例、公式或数据结构支撑，会增加充分公开和支持性风险。",
                suggested_action=_support_issue_suggestion(row),
                blocks_submission=True,
            )
        )
    return issues


def _support_issue_suggestion(row: ClaimSupportMatrixRow) -> str:
    base = "补充对应公式、数据结构、伪代码、附图说明或端到端实施例。"
    if row.missing_evidence_reason:
        return f"{base} 缺失原因：{row.missing_evidence_reason}"
    return base


def _specification_sufficiency_issues(
    package: DraftPackage,
    matrix: list[ClaimSupportMatrixRow],
) -> list[CompletionIssue]:
    issues: list[CompletionIssue] = []
    seen_terms: set[str] = set()
    for row in matrix:
        if row.completion_status != "missing":
            continue
        for term in _candidate_core_terms(row.feature_text):
            if term in seen_terms or term in package.description:
                continue
            seen_terms.add(term)
            issues.append(
                CompletionIssue(
                    id=f"i-sufficiency-{len(issues) + 1}",
                    category="specification_sufficiency_gap",
                    severity="high" if row.feature_classification in {"core_combo", "support_needed"} else "medium",
                    target="description",
                    source_refs=[f"term:{term}"],
                    message=f"权利要求中的技术术语“{term}”在说明书中缺少定义或实施方式。",
                    why_it_matters="审查员会从清楚性、支持性和充分公开角度检查权利要求术语是否能在说明书中找到对应实现。",
                    suggested_action=f"在说明书中补充“{term}”的含义、输入输出、处理步骤和可替代实施例。",
                    blocks_submission=row.feature_classification in {"core_combo", "support_needed"},
                )
            )
            break
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
    if issue.category == "claim_support_gap":
        feature = _feature_from_issue(issue)
        return (
            "add_claim_support",
            f"补充权利要求特征“{feature}”的实施例、数据结构或伪代码支撑。",
            "description",
        )
    if issue.category == "specification_sufficiency_gap":
        return "add_term_definition", issue.suggested_action, "description"
    return "revise_draft_support", issue.suggested_action, issue.target


def _patches_from_tasks(tasks: list[CompletionTask], *, start_index: int = 1) -> list[ProposedPatch]:
    patches: list[ProposedPatch] = []
    for index, task in enumerate(tasks, start=start_index):
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
                can_enter_official_draft=(
                    task.draft_section_target in {"description", "claim", "drawing", "embodiment"}
                    and _task_has_evidence_refs(task)
                ),
            )
        )
    return patches


def _task_has_evidence_refs(task: CompletionTask) -> bool:
    return any(ref.startswith("evidence:") for ref in task.input_refs)


def _patch_text(task: CompletionTask) -> str:
    if task.task_type == "add_claim_support":
        feature = _quoted_feature(task.expected_output)
        return (
            f"在一个实施例中，针对权利要求特征“{feature}”，系统接收输入数据并形成中间状态记录，"
            "所述中间状态记录包括 input_data、processing_rule、intermediate_state、output_result "
            "和 confidence_record 字段。其伪代码包括：步骤S1，获取与该特征对应的输入数据；"
            "步骤S2，根据预设处理规则生成中间状态；步骤S3，输出处理结果并记录结果与输入之间的对应关系。"
        )
    if task.task_type == "add_term_definition":
        feature = _quoted_feature(task.expected_output)
        return (
            f"在一个实施例中，术语“{feature}”表示在权利要求技术方案中用于限定输入、处理过程、"
            "输出结果或状态更新关系的技术单元；其具体含义以说明书中的数据结构、处理步骤和附图流程为准。"
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
    claim_count = _claim_count(package.claims)
    category_count = _claim_category_count(package.claims)
    procedural_count = _procedural_verb_count(package.claims)
    differentiator_count = sum(1 for row in matrix if row.feature_classification in DISTINCTION_CLASSIFICATIONS)
    grounded_distinction_count = sum(
        1 for row in matrix if row.feature_classification in DISTINCTION_CLASSIFICATIONS and row.prior_art_refs
    )
    ungrounded_distinction_count = differentiator_count - grounded_distinction_count
    prior_art_ref_count = sum(1 for row in matrix if row.prior_art_refs)
    model_generated_core_count = sum(
        1
        for row in matrix
        if row.feature_classification in DISTINCTION_CLASSIFICATIONS and _row_has_only_model_generated_evidence(row)
    )
    verified_support_count = sum(1 for row in matrix if _row_has_verified_support(row))

    support_strength = _clamp(100 - support_missing * 35 - support_partial * 15 - model_generated_core_count * 8)
    official_hygiene = _clamp(
        100 - sum(SEVERITY_PENALTY[issue.severity] for issue in issues if issue.category in HYGIENE_CATEGORIES)
    )
    authorization = _clamp(
        100
        - high * 10
        - medium * 5
        - (12 if "其特征在于" not in package.claims else 0)
        - (8 if claim_count <= 1 else 0)
        + min(verified_support_count, 4) * 3
    )
    protection = _clamp(
        45
        + min(claim_count, 10) * 4
        + min(category_count, 4) * 5
        + min(procedural_count, 8) * 2
        - support_missing * 6
        - support_partial * 2
    )
    distinction = _clamp(
        55
        + min(grounded_distinction_count, 5) * 8
        + min(prior_art_ref_count, 3) * 4
        + min(ungrounded_distinction_count, 5) * 2
        - sum(5 for issue in issues if issue.category == "prior_art_distinction_gap")
    )
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


def _row_has_only_model_generated_evidence(row: ClaimSupportMatrixRow) -> bool:
    if _row_has_verified_support(row):
        return False
    if row.evidence_status == "model_generated":
        return True
    return "低置信或未验证证据" in row.missing_evidence_reason


def _row_has_verified_support(row: ClaimSupportMatrixRow) -> bool:
    if any(ref.startswith(f"{EvidenceBindingSourceType.PROJECT_MATERIAL.value}:") for ref in row.source_refs):
        return "低置信或未验证证据" not in row.missing_evidence_reason
    if row.evidence_status == "verified" and any(
        ref.startswith(f"{EvidenceBindingSourceType.PATENT_POINT.value}:") for ref in row.source_refs
    ):
        return True
    return False


def _priority(issue: CompletionIssue) -> int:
    base = {"high": 100, "medium": 60, "low": 30}[issue.severity]
    return base + (10 if issue.blocks_submission else 0)


def _appears_in_description(feature: str, description: str) -> bool:
    for marker in _feature_markers(feature):
        if marker in description:
            return True
        if len(marker) >= 5 and marker[:5] in description:
            return True
    return False


def _has_formula_support(description: str) -> bool:
    return any(symbol in description for symbol in ("=", "∑", "Σ", "矩阵", "公式", "函数"))


def _formula_relevant(feature: str) -> bool:
    return any(term in feature for term in ("计算", "公式", "函数", "矩阵", "坐标", "向量", "投影", "阈值", "权重", "置信", "概率", "面积"))


def _data_structure_relevant(feature: str) -> bool:
    return any(term in feature for term in ("数据", "参数", "矩阵", "记录", "关系", "映射", "集合", "索引", "列表", "表", "状态", "结果"))


def _pseudo_code_relevant(feature: str) -> bool:
    return any(term in feature for term in PROCEDURAL_VERBS)


def _has_data_support(feature: str, description: str) -> bool:
    if not _appears_in_description(feature, description):
        return False
    return any(term in description for term in ("数据结构", "字段", "参数", "记录", "映射", "索引", "集合", "状态记录"))


def _has_pseudo_support(feature: str, description: str) -> bool:
    if not _appears_in_description(feature, description):
        return False
    return any(term in description for term in ("伪代码", "步骤S", "算法", "执行如下", "处理规则"))


def _evidence_status(feature: str, patent_points: list[PatentPointCandidate]) -> str:
    markers = _feature_markers(feature)
    for point in patent_points:
        haystack = "\n".join([point.title, point.innovation, point.technical_solution])
        if markers and any(marker in haystack for marker in markers):
            return point.evidence_status
    return "model_generated"


def _feature_from_issue(issue: CompletionIssue) -> str:
    marker = "权利要求特征缺少充分支撑："
    if marker in issue.message:
        return issue.message.split(marker, 1)[1].strip()
    return issue.message.strip("。")[:80]


def _quoted_feature(text: str) -> str:
    if "“" in text and "”" in text:
        return text.split("“", 1)[1].split("”", 1)[0]
    return text[:80]


def _feature_markers(feature: str) -> list[str]:
    cleaned = feature.strip()
    raw_parts = [
        part.strip()
        for part in __import__("re").split(r"[\s,，、；;。:：()（）]+|并|以及|和", cleaned)
        if len(part.strip()) >= 3
    ]
    markers: list[str] = []
    for part in raw_parts:
        if part.startswith("一种") or part in {"其特征在于", "包括", "根据权利要求1所述的方法"}:
            continue
        markers.append(part)
        normalized = _strip_leading_action(part)
        if normalized and normalized != part and len(normalized) >= 3:
            markers.append(normalized)
    if len(cleaned) >= 6:
        markers.append(cleaned[:12])
    return list(dict.fromkeys(markers[:8]))


def _strip_leading_action(text: str) -> str:
    for verb in (*PROCEDURAL_VERBS, "建立", "基于"):
        if text.startswith(verb) and len(text) > len(verb) + 2:
            return text[len(verb):]
    return text


def _candidate_core_terms(feature: str) -> list[str]:
    return [
        marker
        for marker in _feature_markers(feature)
        if len(marker) >= 4 and not any(marker.startswith(prefix) for prefix in ("一种", "包括", "根据"))
    ]


def _claim_count(claims: str) -> int:
    count = sum(1 for line in claims.splitlines() if __import__("re").match(r"^\s*\d+[.、．]", line))
    return count or (1 if claims.strip() else 0)


def _claim_category_count(claims: str) -> int:
    categories = 0
    for marker in ("方法", "系统", "装置", "设备", "存储介质"):
        if marker in claims:
            categories += 1
    return categories


def _procedural_verb_count(claims: str) -> int:
    return sum(1 for verb in PROCEDURAL_VERBS if verb in claims)


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
