import json

import pytest

from backend.app.generator import render_claims, render_description, render_drawings
from backend.app.llm import ConfigError, FakeLLMClient, MissingLLMClient, StructuredOutputError
from backend.app.schemas import (
    AbstractOutput,
    ClaimItem,
    ClaimsOutput,
    DescriptionOutput,
    DraftPackage,
    DrawingsOutput,
    FigureItem,
)


def test_render_claims_inserts_semicolons_and_period():
    output = ClaimsOutput(
        claims=[
            ClaimItem(
                number=1,
                kind="independent",
                category="method",
                preamble="一种方法，其特征在于，包括：",
                features=["获取待采集区域的证据状态", "求解最优传感器组合", "封装为任务包"],
            )
        ]
    )
    text = render_claims(output)
    assert text.startswith("1. 一种方法，其特征在于，包括：")
    assert "获取待采集区域的证据状态；" in text
    assert text.rstrip().endswith("。")
    # No accidental double terminators on the last feature.
    assert "。。" not in text


def test_render_claims_orders_by_number_and_skips_empty():
    output = ClaimsOutput(
        claims=[
            ClaimItem(number=2, kind="dependent", depends_on=1, preamble="根据权利要求1所述的方法", features=["其中A为B"]),
            ClaimItem(number=1, kind="independent", preamble="一种系统", features=[]),
        ]
    )
    text = render_claims(output)
    assert text.index("1. ") < text.index("2. ")
    assert "1. 一种系统。" in text


def test_render_drawings_single_source():
    output = DrawingsOutput(
        figures=[FigureItem(figure_no="图1", title="方法流程图"), FigureItem(figure_no="图2", title="系统结构图。")]
    )
    text = render_drawings(output)
    assert "图1为方法流程图。" in text
    assert "图2为系统结构图。" in text
    assert "图2为系统结构图。。" not in text


def test_render_description_uses_single_drawings_source():
    description = DescriptionOutput(technical_field="本发明属于A领域。", background="B。", summary="C。", embodiments="D。")
    drawings_text = render_drawings(DrawingsOutput(figures=[FigureItem(figure_no="图1", title="流程图")]))
    text = render_description(description, drawings_text)
    for heading in ("技术领域", "背景技术", "发明内容", "附图说明", "具体实施方式"):
        assert heading in text
    # Drawing description is single-sourced -> appears exactly once.
    assert text.count("图1为流程图。") == 1


def test_fake_complete_stage_json_parses_object():
    fake = FakeLLMClient({"abstract": json.dumps({"abstract": "本发明公开了一种方法。"})})
    payload = fake.complete_stage_json("abstract", "system", "user")
    assert payload == {"abstract": "本发明公开了一种方法。"}
    assert AbstractOutput.model_validate(payload).abstract.startswith("本发明")


def test_fake_complete_stage_json_strips_code_fence():
    fake = FakeLLMClient({"claims": "```json\n{\"claims\": []}\n```"})
    assert fake.complete_stage_json("claims", "s", "u") == {"claims": []}


def test_fake_complete_stage_json_rejects_non_json():
    fake = FakeLLMClient({"abstract": "好的，下面是摘要：本发明……"})
    with pytest.raises(StructuredOutputError):
        fake.complete_stage_json("abstract", "s", "u")


def test_missing_llm_complete_stage_json_raises_config_error():
    with pytest.raises(ConfigError):
        MissingLLMClient().complete_stage_json("abstract", "s", "u")


def test_draft_package_accepts_optional_struct_fields():
    package = DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法。",
        description="说明书",
        drawing_description="图1为流程图。",
        mermaid="",
        image_prompt="",
        claims_struct=ClaimsOutput(claims=[ClaimItem(number=1, preamble="一种方法", features=["步骤A"])]),
        abstract_struct=AbstractOutput(abstract="摘要"),
    )
    assert package.claims_struct is not None
    assert package.claims_struct.claims[0].number == 1
    assert package.abstract_struct is not None
    assert package.abstract_struct.abstract == "摘要"
    # Backward compatibility: struct fields default to None when omitted.
    assert DraftPackage(
        title="t", abstract="a", claims="c", description="d", drawing_description="e", mermaid="", image_prompt=""
    ).claims_struct is None
