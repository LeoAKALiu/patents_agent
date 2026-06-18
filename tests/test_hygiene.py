"""Unit tests for the package-save hygiene module (PR-10)."""

import pytest

from backend.app.hygiene import (
    clean_draft_package,
    _clean_text,
    _clean_title,
    _should_remove_line,
)
from backend.app.schemas import DraftPackage, PatentStrategyBrief, Citation


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种无人机主动采集方法。",
        "claims": "1. 一种方法，包括生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域。",
        "drawing_description": "图1为方法流程图。",
        "mermaid": "flowchart TD",
        "image_prompt": "黑白线稿",
        "review_findings": [],
        "citations": [],
        "generation_logs": ["claims generated"],
    }
    data.update(overrides)
    return DraftPackage(**data)


# ── _should_remove_line and _clean_text ───────────────────────────────────────


def test_removes_conversational_preface():
    assert _should_remove_line("好的，下面撰写权利要求书。", in_fence=False) == (
        True,
        "conversational_preface",
    )


def test_removes_support_gap_markers():
    for line in (
        "support_gap: 需要补矩阵。",
        "support_gaps: 权利要求3支撑不足。",
        "支撑不足提示：第5条。",
        "撰写说明：本段需要调整。",
    ):
        assert _should_remove_line(line, in_fence=False)[0] is True, f"should remove: {line!r}"


def test_removes_internal_field_lines():
    for line in (
        'image_prompt: 黑白线稿',
        'prompt: 输出专利摘要',
        'generation_logs: claims generated',
        'attorney_memo: 代理人复核',
        'system_trace: deliberation',
        'official_safe_patches: patch-1',
        '  "image_prompt": "黑白线稿"',
    ):
        assert _should_remove_line(line, in_fence=False)[0] is True, f"should remove: {line!r}"


def test_removes_json_wrapper_lines():
    assert _should_remove_line("{}", in_fence=False)[0] is True
    assert _should_remove_line("[]", in_fence=False)[0] is True
    assert _should_remove_line("{", in_fence=False)[0] is True
    assert _should_remove_line("}", in_fence=False)[0] is True
    assert _should_remove_line(",", in_fence=False)[0] is True


def test_removes_empty_official_field_lines():
    assert _should_remove_line('"title": ""', in_fence=False)[0] is True
    assert _should_remove_line('abstract: ""', in_fence=False)[0] is True


def test_removes_internal_trace_lines():
    for line in (
        "根据会审策略补充。",
        "多 agent 会审结果如下：",
        "多Agent会审已完成。",
        "主席汇总意见：通过。",
        "deliberation: 多模型会审完成。",
    ):
        assert _should_remove_line(line, in_fence=False)[0] is True, f"should remove: {line!r}"


def test_removes_unfavorable_statements():
    for line in (
        "可能不具备创造性。",
        "禁止直接提交。",
        "存在充分公开风险。",
    ):
        assert _should_remove_line(line, in_fence=False)[0] is True, f"should remove: {line!r}"


def test_removes_mermaid_lines():
    assert _should_remove_line("flowchart TD", in_fence=False)[0] is True
    assert _should_remove_line("A --> B", in_fence=False)[0] is True
    assert _should_remove_line("graph LR", in_fence=False)[0] is True


def test_strips_markdown_headings():
    text, sidecar = _clean_text("## 说明书\n本发明涉及无人机采集。")
    assert "说明书" in text
    assert "##" not in text
    assert len(sidecar) == 0  # markdown heading is stripped inline, not removed


def test_removes_fence_content():
    text, sidecar = _clean_text("正常文本。\n```mermaid\nflowchart TD\nA-->B\n```\n继续。")
    assert "继续。" in text
    assert "flowchart" not in text
    assert "A-->B" not in text
    assert any(item["category"] == "markdown_fence" for item in sidecar)


def test_removes_opening_fence_marker():
    """Regression: opening ```mermaid fence line must NOT leak into the
    patent field. The opening fence toggle itself is part of the pollution
    and must be recorded in the sidecar so the audit trail is complete.
    """
    text, sidecar = _clean_text(
        "正常文本。\n"
        "```mermaid\n"
        "flowchart TD\n"
        "A --> B\n"
        "```\n"
        "继续文本。"
    )

    # No fence marker of any kind should survive
    assert "```" not in text
    assert "mermaid" not in text
    assert "flowchart" not in text
    assert "A --> B" not in text

    # Patent prose preserved
    assert "正常文本。" in text
    assert "继续文本。" in text

    # Sidecar must include the opening fence toggle itself
    fence_items = [item for item in sidecar if item["category"] == "markdown_fence"]
    assert len(fence_items) >= 3  # opening, flowchart, A-->B, closing
    assert any(item["text"] == "```mermaid" for item in fence_items)
    assert any(item["text"] == "```" for item in fence_items)


def test_preserves_normal_prose_with_support_gap_phrase():
    """Regression: normal background prose that merely *mentions* the
    phrase 支撑不足提示 must NOT be dropped as a support_gap annotation.
    Only label-style markers (支撑不足提示：, support_gap:, 撰写说明：, etc.)
    are removed. Coordinate with the PR-5 scanner precision work.
    """
    prose_lines = (
        "背景技术中存在传感器数据支撑不足提示的问题。",
        "本发明解决该问题。",
        "现有系统中存在 支撑不足提示 现象，但并非注释行。",
        "传感器数据 支撑不足提示：仍是描述，不应被识别。",  # 'still description'—内嵌的不是label
    )

    for prose in prose_lines:
        cleaned, sidecar = _clean_text(prose)
        assert prose in cleaned, (
            f"PROSE FALSE POSITIVE: normal prose dropped — input: {prose!r}\n"
            f"got: {cleaned!r}"
        )
        # None of the lines above is a label-style support_gap marker
        assert not any(
            item["category"] == "support_gap" for item in sidecar
        ), f"false positive on: {prose!r}"


def test_clean_draft_package_does_not_mutate_input():
    """Regression: clean_draft_package must return a NEW DraftPackage
    instance and leave the caller's package untouched. Mutating in place
    was a reviewer-flagged anti-pattern.
    """
    package = _make_package(
        title="QA-测试标题",
        abstract="本发明涉及传感器数据支撑不足提示的处理。",
    )
    original_title = package.title
    original_abstract = package.abstract

    cleaned, sidecar = clean_draft_package(package)

    # Input package is untouched
    assert package.title == original_title
    assert package.abstract == original_abstract

    # Cleaned package is a separate instance
    assert cleaned is not package
    assert cleaned.title != original_title  # QA prefix stripped
    assert cleaned.abstract == original_abstract  # background prose preserved


def test_cleans_complex_polluted_text():
    """Simulate a real LLM output that leaked conversational text and metadata."""
    polluted = (
        "好的，下面撰写权利要求书。\n\n"
        "1. 一种方法，包括步骤A。\n\n"
        "撰写说明与支撑不足提示 support_gap: 权利要求3需要补充实验数据。\n"
        "image_prompt: 黑白线稿展示流程。\n"
        "根据会审策略补充的实施例。\n\n"
        "本发明通过技术方案提升效率。"
    )
    cleaned, sidecar = _clean_text(polluted)

    # Cleaned text should be patent-like
    assert "1. 一种方法，包括步骤A。" in cleaned
    assert "本发明通过技术方案提升效率。" in cleaned

    # Conversation/support-gap/prompt/trace should be removed
    assert "好的" not in cleaned
    assert "support_gap" not in cleaned.lower()
    assert "image_prompt" not in cleaned.lower()
    assert "会审策略" not in cleaned

    assert len(sidecar) >= 4


# ── _clean_title ──────────────────────────────────────────────────────────────


def test_clean_title_removes_qa_prefix():
    title, sidecar = _clean_title("QA-TAURI-20260618-多模态检索专利草案生成方法")
    assert "QA-TAURI" not in title
    assert "多模态检索专利草案生成方法" in title
    assert any(item["category"] == "qa_title_marker" for item in sidecar)


def test_clean_title_removes_conversational_title():
    title, sidecar = _clean_title("好的，下面撰写一种方法")
    assert "好的" not in title
    assert any(item["category"] == "conversational_preface" for item in sidecar)


def test_clean_title_preserves_normal_title():
    title, sidecar = _clean_title("一种城市体检指标驱动无人机主动采集方法")
    assert title == "一种城市体检指标驱动无人机主动采集方法"
    assert sidecar == []


# ── clean_draft_package integration ────────────────────────────────────────────


def test_clean_draft_package_cleans_all_fields():
    package = _make_package(
        claims="好的，下面撰写权利要求书。\n1. 一种方法。\nsupport_gap: 需要补数据。",
        description=(
            "## 说明书\n"
            "本发明涉及无人机采集。\n"
            "根据会审策略补充实施例。\n"
            "```mermaid\nflowchart TD\nA-->B\n```\n"
            "可能不具备创造性。"
        ),
        drawing_description="图1为方法流程图。\nimage_prompt: 黑白线稿。",
    )
    cleaned, sidecar = clean_draft_package(package)

    # Patent-body fields should be clean
    assert "好的" not in cleaned.claims
    assert "support_gap" not in cleaned.claims.lower()
    assert "##" not in cleaned.description
    assert "会审策略" not in cleaned.description
    assert "flowchart" not in cleaned.description.lower()
    assert "可能不具备创造性" not in cleaned.description
    assert "image_prompt" not in cleaned.drawing_description.lower()

    # Non-patent sidecar fields should be untouched
    assert cleaned.generation_logs == ["claims generated"]

    # Sidecar should contain records
    assert any(
        k in sidecar for k in ("claims", "description", "drawing_description")
    )


def test_clean_draft_package_handles_empty_fields():
    package = _make_package(
        claims="support_gap: 需要补数据。\n撰写说明：待完善。\nimage_prompt: 图。",
    )
    cleaned, sidecar = clean_draft_package(package)

    # Claims may become empty after cleaning all internal lines
    # But the package should remain loadable
    assert cleaned.claims is not None
    assert len(sidecar) > 0


def test_clean_draft_package_handles_empty_title_fallback():
    """Title becomes empty after cleaning → fallback placeholder used."""
    package = _make_package(
        title="QA-",
    )
    cleaned, sidecar = clean_draft_package(package)
    assert cleaned.title == "(未命名发明)"
    assert any(
        item["category"] == "empty_title_fallback"
        for v in sidecar.values()
        for item in v
    )


def test_clean_draft_package_sidecar_removed_from_patent_fields_not_sidecar():
    """Strategy, disclosure, formula fields should remain untouched — only patent-body cleaned."""
    strategy = PatentStrategyBrief(
        summary="会审策略摘要",
        claim_strategy=["策略1"],
        agent_consensus="共识文本",
    )
    package = _make_package(
        title="一种方法。根据会审策略",
        claims="1. 一种方法。\n根据会审策略补充。",
        strategy_brief=strategy,
        agent_consensus="共识文本",
        disclosure_summary="交底摘要中包含会审信息",
        core_formula_summary="ΔS = S_post - S_prior",
    )
    cleaned, sidecar = clean_draft_package(package)

    # Title and claims cleaned of internal traces
    assert "会审策略" not in cleaned.title
    assert "会审策略" not in cleaned.claims
    # But "根据" was between the topic and the trace phrase, so the title
    # should still contain the invention part
    assert "一种方法" in cleaned.title

    # Strategy sidecar fields preserved (they're explicitly internal)
    assert cleaned.strategy_brief is not None
    assert "会审策略摘要" in cleaned.strategy_brief.summary
    assert cleaned.agent_consensus == "共识文本"
    assert cleaned.disclosure_summary == "交底摘要中包含会审信息"
    assert cleaned.core_formula_summary == "ΔS = S_post - S_prior"


def test_clean_draft_package_preserves_normal_text():
    """A clean package should pass through unchanged."""
    package = _make_package(
        title="一种无人机任务调整方法",
        abstract="本发明公开了一种无人机任务调整方法。",
        claims="1. 一种无人机任务调整方法，其特征在于，包括步骤A、B、C。",
        description="技术领域\n本发明涉及无人机技术领域。\n发明内容\n本发明通过动态推理调整任务。",
        drawing_description="图1为方法流程图；图2为系统结构图。",
    )
    cleaned, sidecar = clean_draft_package(package)

    assert cleaned.title == "一种无人机任务调整方法"
    assert "步骤A" in cleaned.claims
    assert "无人机技术领域" in cleaned.description
    assert sidecar == {}
