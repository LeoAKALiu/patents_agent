from backend.app.official_compile import (
    OfficialDraftCompiler,
    official_package_to_markdown,
)
from backend.app.schemas import DraftPackage


def test_compiler_removes_internal_pollution_from_official_package():
    package = _draft_package(
        claims="好的，下面撰写权利要求书。\n1. 一种方法。\n\n撰写说明与支撑不足提示 support_gap: 需要补矩阵。",
        description=(
            "## 说明书\n"
            "本发明涉及无人机采集。\n"
            "```mermaid\nflowchart TD\nA-->B\n```\n"
            "generation_logs: claims generated\n"
            "根据会审策略补充。"
        ),
        drawing_description="图1为方法流程图。\nimage_prompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "completed"
    assert run.official_package is not None
    official_text = official_package_to_markdown(run.official_package)
    assert "好的" not in official_text
    assert "support_gap" not in official_text
    assert "```" not in official_text
    assert "flowchart TD" not in official_text
    assert "generation_logs" not in official_text
    assert "image_prompt" not in official_text
    assert "根据会审策略" not in official_text
    assert any(item["pattern"] == "support_gap" for item in run.contamination_removed)


def test_compiler_blocks_cross_project_title_contamination():
    package = _draft_package(
        description="本说明书还包括：基于边缘端动态推理的无人机飞行中任务调整方法。"
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "cross_project_contamination" for item in run.blocked_items)


def test_compiler_blocks_when_cleaning_empties_required_section():
    package = _draft_package(description="support_gap: 说明书待补充。")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "empty_required_section" for item in run.blocked_items)


def test_compiler_removes_json_style_prompt_internal_field():
    package = _draft_package(
        drawing_description='图1为方法流程图。\n"prompt": "黑白线稿"',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "completed"
    assert run.official_package is not None
    official_text = official_package_to_markdown(run.official_package)
    assert "prompt" not in official_text
    assert "黑白线稿" not in official_text
    assert any(item["pattern"] == "prompt" for item in run.contamination_removed)


def test_compiler_blocks_ai_preface_title_contamination():
    package = _draft_package(title="好的，下面撰写一种方法")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] in {"residual_internal_text", "empty_required_section"}
        and item["section"] == "title"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_drawing_description():
    package = _draft_package(drawing_description="图1为方法流程图。prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "drawing_description"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_title():
    package = _draft_package(title="一种方法 prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "title"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_json_wrapper_only_required_section():
    package = _draft_package(drawing_description='{\n  "prompt": "黑白线稿"\n}')

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "empty_required_section"
        and item["section"] == "drawing_description"
        for item in run.blocked_items
    )


def _draft_package(**overrides) -> DraftPackage:
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
