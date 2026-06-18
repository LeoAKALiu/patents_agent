from __future__ import annotations

from backend.app.patch_generator import PatchGenerationContext, generate_evidence_backed_patches
from backend.app.schemas import (
    ClaimSupportMatrixRow,
    CompletionIssue,
    CompletionTask,
    DraftPackage,
)


def _package() -> DraftPackage:
    return DraftPackage(
        title="声学视觉融合巡检方法",
        abstract="通过声学异常窗口触发视觉局部复检。",
        claims="1. 一种巡检方法，其特征在于，声学异常窗口触发视觉局部复检。",
        description="本实施例描述巡检机器人采集声学信号。",
        drawing_description="图1示出巡检流程。",
        mermaid="",
        image_prompt="",
    )


def test_claim_support_gap_with_strong_evidence_creates_description_insert_patch() -> None:
    issue = CompletionIssue(
        id="i-support-1",
        category="claim_support_gap",
        severity="high",
        target="claim",
        source_refs=["claim:1", "project_material:material-1", "evidence:E100"],
        message="权利要求特征缺少充分支撑：声学异常窗口触发视觉局部复检",
        why_it_matters="缺少支撑。",
        suggested_action="补充实施例。",
        blocks_submission=True,
    )
    task = CompletionTask(
        id="t1",
        issue_id=issue.id,
        task_type="add_claim_support",
        priority=110,
        input_refs=issue.source_refs,
        expected_output="补充权利要求特征“声学异常窗口触发视觉局部复检”的实施例、数据结构或伪代码支撑。",
        draft_section_target="description",
    )
    row = ClaimSupportMatrixRow(
        claim_ref="1",
        feature_text="声学异常窗口触发视觉局部复检",
        feature_classification="core_combo",
        evidence_refs=["E100"],
        source_refs=["project_material:material-1"],
        completion_status="missing",
    )

    patches = generate_evidence_backed_patches(
        PatchGenerationContext(package=_package(), issues=[issue], tasks=[task], support_matrix=[row])
    )

    assert len(patches) == 1
    patch = patches[0]
    assert patch.patch_kind == "insert"
    assert patch.target_section == "description"
    assert patch.can_enter_official_draft is True
    assert patch.evidence_refs == ["E100"]
    assert patch.before_text
    assert "声学异常窗口触发视觉局部复检" in patch.after_text
    assert "伪代码" in patch.after_text
    assert "input_data" not in patch.after_text
    assert "processing_rule" not in patch.after_text
    assert "prompt" not in patch.after_text.lower()
    assert "generation_logs" not in patch.after_text


def test_unverified_quantitative_effect_creates_sidecar_only_patch() -> None:
    issue = CompletionIssue(
        id="i-unverified-1",
        category="unverified_scheme_gap",
        severity="medium",
        target="evidence",
        source_refs=["patent_points"],
        message="可行未验证方案被写成已验证效果或确定工程结果。",
        why_it_matters="未验证效果不能写成事实。",
        suggested_action="改写为可选实施方式或机理性有益效果。",
    )
    task = CompletionTask(
        id="t1",
        issue_id=issue.id,
        task_type="revise_draft_support",
        priority=60,
        input_refs=issue.source_refs,
        expected_output=issue.suggested_action,
        draft_section_target="evidence",
    )

    patches = generate_evidence_backed_patches(
        PatchGenerationContext(package=_package(), issues=[issue], tasks=[task], support_matrix=[])
    )

    assert len(patches) == 1
    patch = patches[0]
    assert patch.patch_kind == "sidecar_only"
    assert patch.can_enter_official_draft is False
    assert patch.evidence_refs == []
    assert "可选实施方式" in patch.after_text


def test_patch_generator_skips_official_patch_without_evidence_refs() -> None:
    issue = CompletionIssue(
        id="i-support-1",
        category="claim_support_gap",
        severity="high",
        target="claim",
        source_refs=["claim:1"],
        message="权利要求特征缺少充分支撑：声学异常窗口触发视觉局部复检",
        why_it_matters="缺少支撑。",
        suggested_action="补充实施例。",
        blocks_submission=True,
    )
    task = CompletionTask(
        id="t1",
        issue_id=issue.id,
        task_type="add_claim_support",
        priority=110,
        input_refs=issue.source_refs,
        expected_output="补充权利要求特征“声学异常窗口触发视觉局部复检”的实施例。",
        draft_section_target="description",
    )
    row = ClaimSupportMatrixRow(
        claim_ref="1",
        feature_text="声学异常窗口触发视觉局部复检",
        feature_classification="core_combo",
        completion_status="missing",
    )

    patches = generate_evidence_backed_patches(
        PatchGenerationContext(package=_package(), issues=[issue], tasks=[task], support_matrix=[row])
    )

    assert patches == []
