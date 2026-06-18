"""Evidence-backed local patch generation for draft completion runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.schemas import (
    ClaimSupportMatrixRow,
    CompletionIssue,
    CompletionTask,
    DraftPackage,
    EvidenceBinding,
    ProposedPatch,
)


@dataclass(frozen=True)
class PatchGenerationContext:
    package: DraftPackage
    issues: list[CompletionIssue]
    tasks: list[CompletionTask]
    support_matrix: list[ClaimSupportMatrixRow]
    evidence_bindings: list[EvidenceBinding] = field(default_factory=list)
    existing_patch_count: int = 0


def generate_evidence_backed_patches(context: PatchGenerationContext) -> list[ProposedPatch]:
    """Generate deterministic, reviewable patches backed by evidence refs."""

    issues_by_id = {issue.id: issue for issue in context.issues}
    patches: list[ProposedPatch] = []
    for task in context.tasks:
        issue = issues_by_id.get(task.issue_id)
        if issue is None:
            continue
        patch = _patch_for_task(context, issue, task, len(patches) + 1)
        if patch is not None:
            patches.append(patch)
    return patches


def _patch_for_task(
    context: PatchGenerationContext,
    issue: CompletionIssue,
    task: CompletionTask,
    index: int,
) -> ProposedPatch | None:
    if issue.category == "claim_support_gap" and task.draft_section_target == "description":
        return _claim_support_patch(context, issue, task, index)
    if issue.category == "unverified_scheme_gap":
        return _unverified_effect_patch(context, issue, task, index)
    if issue.category == "subject_matter_risk":
        return _sidecar_patch(context, issue, task, index, "该项需由代理人审阅后改写，暂不自动进入正式稿。")
    return None


def _claim_support_patch(
    context: PatchGenerationContext,
    issue: CompletionIssue,
    task: CompletionTask,
    index: int,
) -> ProposedPatch | None:
    row = _row_for_issue(issue, context.support_matrix)
    evidence_refs = _evidence_refs(row, issue, task)
    if row is None or not evidence_refs:
        return None
    feature = row.feature_text or _feature_from_issue(issue)
    after_text = _sanitize_patch_text(_description_support_text(feature, row))
    return ProposedPatch(
        id=_patch_id(context, index),
        task_id=task.id,
        target_section="description",
        patch_kind="insert",
        before_text=_description_anchor(context.package.description, feature),
        after_text=after_text,
        rationale=f"依据证据 {', '.join(evidence_refs)} 补充“{feature}”的说明书支撑。",
        risk_delta="降低权利要求支持性和充分公开风险。",
        evidence_refs=evidence_refs,
        can_enter_official_draft=True,
    )


def _unverified_effect_patch(
    context: PatchGenerationContext,
    issue: CompletionIssue,
    task: CompletionTask,
    index: int,
) -> ProposedPatch:
    text = _sanitize_patch_text(
        "该项仅作为侧车修订建议：将未验证的量化效果改写为可选实施方式、"
        "机理性有益效果或待实验验证的工程假设，避免写成已实测事实。"
    )
    return ProposedPatch(
        id=_patch_id(context, index),
        task_id=task.id,
        target_section=task.draft_section_target,
        patch_kind="sidecar_only",
        before_text="",
        after_text=text,
        rationale=issue.suggested_action or task.expected_output,
        risk_delta="避免未验证效果进入正式文本。",
        evidence_refs=[],
        can_enter_official_draft=False,
    )


def _sidecar_patch(
    context: PatchGenerationContext,
    issue: CompletionIssue,
    task: CompletionTask,
    index: int,
    text: str,
) -> ProposedPatch:
    return ProposedPatch(
        id=_patch_id(context, index),
        task_id=task.id,
        target_section=task.draft_section_target,
        patch_kind="sidecar_only",
        before_text="",
        after_text=_sanitize_patch_text(text),
        rationale=issue.suggested_action or task.expected_output,
        risk_delta="等待人工审阅，避免自动扩大正式稿风险。",
        evidence_refs=[],
        can_enter_official_draft=False,
    )


def _description_support_text(feature: str, row: ClaimSupportMatrixRow) -> str:
    parts = [
        f"在一个实施例中，针对“{feature}”，系统基于已获取的输入信号确定触发条件，"
        "并将触发条件、处理对象和输出结果写入可追溯记录。"
    ]
    if not row.data_structure_refs:
        parts.append(
            "所述可追溯记录包括特征标识、输入来源、触发时间窗、处理对象、输出结果和置信度字段。"
        )
    if not row.pseudo_code_refs:
        parts.append(
            "其伪代码包括：步骤S1，获取与该特征对应的输入信号；步骤S2，判断是否满足触发条件；"
            "步骤S3，执行局部处理并生成输出结果；步骤S4，记录输入、处理对象和输出结果之间的对应关系。"
        )
    if not row.formula_refs and any(marker in feature for marker in ("阈值", "置信", "概率", "权重", "矩阵")):
        parts.append("在可选实施例中，触发条件可由阈值函数或权重矩阵计算得到。")
    return "".join(parts)


def _row_for_issue(issue: CompletionIssue, rows: list[ClaimSupportMatrixRow]) -> ClaimSupportMatrixRow | None:
    feature = _feature_from_issue(issue)
    for row in rows:
        if row.feature_text == feature or feature in row.feature_text or row.feature_text in feature:
            return row
    return None


def _evidence_refs(
    row: ClaimSupportMatrixRow | None,
    issue: CompletionIssue,
    task: CompletionTask,
) -> list[str]:
    refs: list[str] = []
    if row is not None:
        refs.extend(row.evidence_refs)
    for value in [*issue.source_refs, *task.input_refs]:
        if value.startswith("evidence:"):
            refs.append(value.split("evidence:", 1)[1])
    return list(dict.fromkeys(ref for ref in refs if ref))


def _feature_from_issue(issue: CompletionIssue) -> str:
    marker = "权利要求特征缺少充分支撑："
    if marker in issue.message:
        return issue.message.split(marker, 1)[1].strip()
    return issue.message.strip("。")[:80]


def _description_anchor(description: str, feature: str) -> str:
    for sentence in _sentences(description):
        if any(marker and marker in sentence for marker in _feature_markers(feature)):
            return sentence[:240]
    stripped = description.strip()
    return stripped[-240:] if stripped else "说明书"


def _sentences(text: str) -> list[str]:
    normalized = text.replace("。", "。\n").replace("；", "；\n").replace(";", ";\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _feature_markers(feature: str) -> list[str]:
    markers = [part.strip() for part in feature.replace("，", "、").replace("并", "、").split("、") if len(part.strip()) >= 3]
    if len(feature) >= 6:
        markers.append(feature[:8])
    return list(dict.fromkeys(markers))


def _sanitize_patch_text(text: str) -> str:
    banned = ("prompt", "generation_logs", "system_trace", "attorney_memo", "internal", "任务:", "task:")
    sanitized = text
    for marker in banned:
        sanitized = sanitized.replace(marker, "")
        sanitized = sanitized.replace(marker.upper(), "")
    return " ".join(sanitized.split())


def _patch_id(context: PatchGenerationContext, index: int) -> str:
    return f"patch-evidence-{context.existing_patch_count + index}"
