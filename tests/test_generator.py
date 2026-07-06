import pytest

from backend.app.generator import PatentDraftGenerator
from backend.app.llm import ConfigError, FakeLLMClient, MissingLLMClient
from backend.app.schemas import InventionBrief, PatentChunk, PatentStrategyBrief, SectionType


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

    # claims must be generated before its dependents; the remaining stages run
    # concurrently so we assert the set of calls and the claims-first invariant
    # rather than a strict sequential order.
    assert [call.stage for call in llm.calls[:1]] == ["claims"]
    assert set(call.stage for call in llm.calls) == {
        "claims",
        "description",
        "abstract",
        "drawings",
        "diagram",
        "image_prompt",
    }
    assert len(llm.calls) == 6
    assert package.title == "专利撰写辅助"
    assert "权利要求1" in package.claims
    assert package.citations[0].chunk_id == "c1"


def test_generator_strips_assistant_prefaces_from_generated_sections():
    llm = FakeLLMClient(
        {
            "claims": (
                "好的,以下是根据您提供的技术交底材料、多智能体会审策略和核心公式包撰写的"
                "中国发明专利申请权利要求书初稿。\n"
                "---\n\n"
                "1. 一种城市体检智能体的任务编排与可信复核方法，其特征在于，包括任务编排。"
            ),
            "description": (
                "好的,基于您提供的技术交底书、权利要求书、多智能体会审策略以及核心公式包,"
                "我将为您撰写一份符合中国发明专利撰写规范的说明书正文初稿。\n\n"
                "技术领域\n"
                "本发明涉及城市体检智能体任务编排技术领域。"
            ),
            "abstract": "本发明公开一种城市体检智能体的任务编排与可信复核方法。",
            "drawings": "图1为任务编排流程图。",
            "diagram": "flowchart TD\nA[任务编排] --> B[可信复核]",
            "image_prompt": "黑白线稿，展示任务编排和可信复核流程。",
        }
    )
    generator = PatentDraftGenerator(llm)
    brief = InventionBrief(
        title="城市体检智能体",
        technical_field="AI软件",
        technical_problem="任务编排可信性不足",
        technical_solution="对任务进行编排并执行可信复核",
        beneficial_effects=["提升复核可信度"],
        key_steps=["任务编排", "可信复核"],
    )

    package = generator.generate(brief, [])

    assert package.claims.startswith("1. 一种城市体检智能体")
    assert package.description.startswith("技术领域")
    assert "好的" not in package.claims
    assert "好的" not in package.description
    assert "---" not in package.claims


def test_generator_reuses_cleaned_claims_for_dependent_prompts():
    llm = FakeLLMClient(
        {
            "claims": (
                "好的，下面撰写权利要求书。\n"
                "---\n"
                "1. 一种城市体检智能体的任务编排方法，其特征在于，包括生成任务包。"
            ),
            "description": "技术领域\n本发明涉及城市体检智能体任务编排技术领域。",
            "abstract": "本发明公开一种城市体检智能体的任务编排方法。",
            "drawings": "图1为任务编排流程图。",
            "diagram": "flowchart TD\nA[生成任务包] --> B[执行复核]",
            "image_prompt": "黑白线稿，展示任务包生成流程。",
        }
    )
    generator = PatentDraftGenerator(llm)
    brief = InventionBrief(
        title="城市体检智能体",
        technical_field="AI软件",
        technical_problem="任务编排可信性不足",
        technical_solution="生成任务包并执行复核",
        beneficial_effects=["提升复核可信度"],
        key_steps=["生成任务包"],
    )

    generator.generate(brief, [])

    dependent_prompts = [
        call.user_prompt
        for call in llm.calls
        if call.stage in {"description", "drawings", "diagram"}
    ]
    assert dependent_prompts
    assert all("好的" not in prompt for prompt in dependent_prompts)
    assert all("1. 一种城市体检智能体" in prompt for prompt in dependent_prompts)


def test_generator_only_passes_injectable_strategy_not_deliberation_transcript():
    llm = FakeLLMClient(
        {
            "claims": "1. 一种城市体检智能体的任务编排方法，其特征在于，包括生成任务包。",
            "description": "技术领域\n本发明涉及城市体检智能体任务编排技术领域。",
            "abstract": "本发明公开一种城市体检智能体的任务编排方法。",
            "drawings": "图1为任务编排流程图。",
            "diagram": "flowchart TD\nA[生成任务包] --> B[执行复核]",
            "image_prompt": "黑白线稿，展示任务包生成流程。",
        }
    )
    generator = PatentDraftGenerator(llm)
    brief = InventionBrief(
        title="城市体检智能体",
        technical_field="AI软件",
        technical_problem="任务编排可信性不足",
        technical_solution="生成任务包并执行复核",
        beneficial_effects=["提升复核可信度"],
        key_steps=["生成任务包"],
    )
    strategy = PatentStrategyBrief(
        summary="围绕任务包生成和可信复核撰写。",
        claim_strategy=["限定任务包生成步骤"],
        description_strategy=["补充任务包数据结构实施例"],
        risk_controls=["避免把未验证效果写成事实"],
        agent_consensus="codex 与 deepseek 交叉质询后认为 claude 的表述应收敛；resolved_recommendation=采用主席方案。",
    )

    generator.generate(brief, [], strategy_brief=strategy)

    generation_prompts = "\n".join(call.user_prompt for call in llm.calls if call.stage in {"claims", "description"})
    assert "限定任务包生成步骤" in generation_prompts
    assert "agent_consensus" not in generation_prompts
    assert "codex" not in generation_prompts
    assert "deepseek" not in generation_prompts
    assert "claude" not in generation_prompts
    assert "resolved_recommendation" not in generation_prompts
    assert "多 agent" not in generation_prompts
    assert "会审" not in generation_prompts


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
