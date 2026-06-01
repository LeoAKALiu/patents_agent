import pytest

from backend.app.generator import PatentDraftGenerator
from backend.app.llm import ConfigError, FakeLLMClient, MissingLLMClient
from backend.app.schemas import InventionBrief, PatentChunk, SectionType


def test_generator_runs_ordered_pipeline_and_records_citations():
    llm = FakeLLMClient(
        {
            "brief": '{"title":"一种专利撰写辅助方法","technical_field":"AI软件","technical_problem":"初稿质量不稳定","technical_solution":"检索相似专利并分步生成","beneficial_effects":["提升结构完整性"],"key_steps":["导入语料","生成权利要求"]}',
            "claims": "1. 一种专利撰写辅助方法，其特征在于，包括导入语料并生成权利要求。\n2. 根据权利要求1所述的方法，其特征在于，还包括生成说明书。",
            "description": "技术领域\n本发明涉及AI软件技术领域。\n发明内容\n本发明通过RAG生成申请文本。",
            "abstract": "本发明公开了一种专利撰写辅助方法，能够提升申请文本结构完整性。",
            "drawings": "图1为专利撰写辅助方法流程图。",
            "diagram": "flowchart TD\nA[导入语料] --> B[生成权利要求]",
            "image_prompt": "黑白线稿，展示专利撰写辅助方法的数据处理流程。",
        }
    )
    generator = PatentDraftGenerator(llm)
    brief = InventionBrief(
        title="专利撰写辅助",
        technical_field="AI软件",
        technical_problem="初稿质量不稳定",
        technical_solution="检索相似专利并分步生成",
        beneficial_effects=["提升结构完整性"],
        key_steps=["导入语料", "生成权利要求"],
    )
    chunks = [
        PatentChunk(
            id="c1",
            document_id="d1",
            section_type=SectionType.CLAIMS,
            text="1. 一种文本生成方法，包括检索参考文本。",
            ordinal=1,
        )
    ]

    package = generator.generate(brief, chunks)

    assert [call.stage for call in llm.calls] == [
        "claims",
        "description",
        "abstract",
        "drawings",
        "diagram",
        "image_prompt",
    ]
    assert package.title == "专利撰写辅助"
    assert "权利要求1" in package.claims
    assert package.citations[0].chunk_id == "c1"


def test_generator_fails_closed_when_llm_is_not_configured():
    generator = PatentDraftGenerator(MissingLLMClient())
    brief = InventionBrief(
        title="专利撰写辅助",
        technical_field="AI软件",
        technical_problem="初稿质量不稳定",
        technical_solution="检索相似专利并分步生成",
        beneficial_effects=["提升结构完整性"],
        key_steps=["导入语料"],
    )

    with pytest.raises(ConfigError):
        generator.generate(brief, [])
