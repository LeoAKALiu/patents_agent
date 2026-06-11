from __future__ import annotations

import json

from backend.app.llm import LLMClient
from backend.app.patent_mode import is_utility_model_text
from backend.app.schemas import (
    Citation,
    CoreFormulaPackage,
    DisclosurePackage,
    DraftPackage,
    InventionBrief,
    PatentChunk,
    PatentStrategyBrief,
    ReviewFinding,
)


class PatentDraftGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate(
        self,
        brief: InventionBrief,
        context_chunks: list[PatentChunk],
        strategy_brief: PatentStrategyBrief | None = None,
        disclosure: DisclosurePackage | None = None,
        formula_package: CoreFormulaPackage | None = None,
    ) -> DraftPackage:
        context = _format_context(context_chunks)
        strategy_context = _format_strategy(strategy_brief)
        disclosure_context = _format_disclosure(disclosure)
        formula_context = _format_formula(formula_package)
        system_prompt = _system_prompt(brief)
        claims = self.llm.complete_stage("claims", system_prompt, _claims_prompt(brief, context, strategy_context, disclosure_context, formula_context))
        description = self.llm.complete_stage(
            "description", system_prompt, _description_prompt(brief, claims, context, strategy_context, disclosure_context, formula_context)
        )
        abstract = self.llm.complete_stage("abstract", system_prompt, _abstract_prompt(brief, claims, description))
        drawings = self.llm.complete_stage("drawings", system_prompt, _drawings_prompt(brief, claims))
        mermaid = self.llm.complete_stage("diagram", system_prompt, _diagram_prompt(brief, claims))
        image_prompt = self.llm.complete_stage("image_prompt", system_prompt, _image_prompt(brief, mermaid))
        return DraftPackage(
            title=brief.title,
            abstract=abstract.strip(),
            claims=claims.strip(),
            description=description.strip(),
            drawing_description=drawings.strip(),
            mermaid=mermaid.strip(),
            image_prompt=image_prompt.strip(),
            review_findings=[],
            citations=[
                Citation(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    section_type=chunk.section_type,
                    text=chunk.text[:500],
                )
                for chunk in context_chunks
            ],
            generation_logs=[
                "claims: generated from invention brief and retrieved claim/description context",
                "description: generated to support claims",
                "abstract: generated under CNIPA-style 300-character constraint",
                "drawings: generated as figure descriptions",
                "diagram: generated as Mermaid flowchart",
                "image_prompt: generated for patent-style black-and-white drawing",
            ],
            strategy_brief=strategy_brief,
            agent_consensus=strategy_brief.agent_consensus if strategy_brief else None,
            disclosure_summary=disclosure.summary if disclosure else None,
            patent_point_summary=disclosure.selected_candidate.title if disclosure and disclosure.selected_candidate else None,
            core_formula_summary=formula_package.summary if formula_package else None,
        )

    def review(self, package: DraftPackage) -> list[ReviewFinding]:
        prompt = (
            "请审查以下中国专利初稿，输出JSON数组。每项包含category、severity、message、suggestion、evidence。"
            "\n\n"
            f"题名：{package.title}\n摘要：{package.abstract}\n权利要求：{package.claims}\n说明书：{package.description}"
        )
        raw = self.llm.complete_stage("review", _review_system_prompt(package), prompt)
        try:
            data = json.loads(raw)
            return [ReviewFinding(**item) for item in data]
        except Exception:
            return [
                ReviewFinding(
                    category="审查输出解析",
                    severity="medium",
                    message="模型未返回结构化JSON审查结果。",
                    suggestion=raw.strip()[:1000],
                )
            ]


INVENTION_SYSTEM_PROMPT = (
    "你是中国发明专利撰写助手，熟悉CNIPA申请文件范式。"
    "输出应为专利初稿辅助文本，不得声称替代专利代理师。"
    "优先使用技术特征、步骤、模块、数据流、技术效果等专利语言，避免营销表述。"
)

UTILITY_MODEL_SYSTEM_PROMPT = (
    "你是中国实用新型专利撰写助手，熟悉CNIPA申请文件范式。"
    "输出应为专利初稿辅助文本，不得声称替代专利代理师。"
    "优先使用结构件、连接关系、安装位置、配合方式、附图标号和结构效果等专利语言，避免营销表述。"
    "不得把纯方法步骤、算法流程、软件介质或商业规则作为独立保护主题。"
)


def _is_utility_model_brief(brief: InventionBrief) -> bool:
    return is_utility_model_text(brief.raw_draft) or "实用新型" in brief.technical_field


def _system_prompt(brief: InventionBrief) -> str:
    return UTILITY_MODEL_SYSTEM_PROMPT if _is_utility_model_brief(brief) else INVENTION_SYSTEM_PROMPT


def _review_system_prompt(package: DraftPackage) -> str:
    text = f"{package.title}\n{package.claims}\n{package.description}"
    return UTILITY_MODEL_SYSTEM_PROMPT if is_utility_model_text(text) or "实用新型" in text else INVENTION_SYSTEM_PROMPT


def _format_context(chunks: list[PatentChunk]) -> str:
    if not chunks:
        return "无可用相似授权专利片段。"
    return "\n\n".join(
        f"[{index}] {chunk.section_type.value} / {chunk.metadata.get('title', chunk.document_id)}\n{chunk.text}"
        for index, chunk in enumerate(chunks, start=1)
    )


def _format_strategy(strategy_brief: PatentStrategyBrief | None) -> str:
    if not strategy_brief:
        return "无多 agent 会审策略。"
    return strategy_brief.model_dump_json(ensure_ascii=False, indent=2)


def _format_disclosure(disclosure: DisclosurePackage | None) -> str:
    if not disclosure:
        return "无前置技术交底书。"
    selected = disclosure.selected_candidate
    return json.dumps(
        {
            "summary": disclosure.summary,
            "selected_candidate": selected.model_dump(mode="json") if selected else None,
            "prior_art_differences": disclosure.prior_art_differences,
            "materials_summary": disclosure.materials_summary,
            "body_excerpt": disclosure.body_markdown[:3000],
        },
        ensure_ascii=False,
        indent=2,
    )


def _format_formula(formula_package: CoreFormulaPackage | None) -> str:
    if not formula_package:
        return "无核心公式包。"
    return formula_package.model_dump_json(ensure_ascii=False, indent=2)


def _claims_prompt(brief: InventionBrief, context: str, strategy_context: str, disclosure_context: str, formula_context: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
请为以下技术方案撰写中国实用新型专利权利要求书。
要求：
1. 至少1项独立权利要求和3项从属权利要求；
2. 独立权利要求必须是产品、装置、设备、组件或结构，不得写成方法步骤、算法流程、软件介质或商业规则；
3. 独立权利要求写清必要结构件、连接/安装/配合关系、空间位置关系和结构闭环；
4. 从属权利要求限定可替换结构、局部连接方式、安装件、限位件、密封/支撑/导向/固定结构、传感器或控制单元的结构配合；
5. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形结构、从属限定或待补充结构样机方向，不得写成已经完成验证的实施事实；
6. 如方案包含算法或软件，其只能作为控制模块、传感器模块或处理单元与结构件配合的背景，不作为独立保护主题。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

相似授权专利片段：
{context}

多 agent 会审策略：
{strategy_context}

前置技术交底书：
{disclosure_context}

核心公式包：
{formula_context}
"""
    return f"""
请为以下技术方案撰写中国发明专利权利要求书。
要求：
1. 至少1项独立权利要求和3项从属权利要求；
2. 独立权利要求覆盖方法/系统的软件实现；
3. 从属权利要求限定关键步骤、模型、数据处理和输出；
4. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形例、从属限定或待验证改进方向，不得写成已经完成验证的实施事实；
5. 对用户指定专利点，要保留其保护意图，并用 support_gaps 指明提交前需补强的实验或工程材料。
6. 如果存在核心公式包，独立权利要求或从属权利要求必须吸收 formula_blocks 的计算目标、变量关系和 claim_hooks，但不要把未验证效果写成已验证事实。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

相似授权专利片段：
{context}

多 agent 会审策略：
{strategy_context}

前置技术交底书：
{disclosure_context}

核心公式包：
{formula_context}
"""


def _description_prompt(brief: InventionBrief, claims: str, context: str, strategy_context: str, disclosure_context: str, formula_context: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
基于技术交底和权利要求，撰写实用新型说明书正文，必须包含技术领域、背景技术、实用新型内容、附图说明、具体实施方式。
说明书要支撑每一项权利要求，不引入权利要求无法对应的核心结构。
要求：
1. 以结构组成、连接关系、安装位置、空间布局和配合方式展开，不把方法流程或算法公式作为主线；
2. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形结构、从属限定或待补充结构样机方向，不得写成已经完成验证的实施事实；
3. 附图说明和具体实施方式应包含可编号的部件名称，并解释各标号之间的连接或配合关系；
4. 如存在控制/传感/处理单元，只说明其与结构件的安装、连接或配合，不展开软件算法为独立发明点。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}

参考片段：
{context}

多 agent 会审策略：
{strategy_context}

前置技术交底书：
{disclosure_context}

核心公式包：
{formula_context}
"""
    return f"""
基于技术交底和权利要求，撰写说明书正文，必须包含技术领域、背景技术、发明内容、附图说明、具体实施方式。
说明书要支撑每一项权利要求，不引入权利要求无法对应的核心特征。
要求：
1. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形例、从属限定或待验证改进方向，不得写成已经完成验证的实施事实；
2. 对用户指定专利点，要保留其保护意图，并用 support_gaps 指明提交前需补强的实验或工程材料。
3. 如果存在核心公式包，必须给出公式编号、变量定义、计算流程、权利要求落点和说明书插入建议。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}

参考片段：
{context}

多 agent 会审策略：
{strategy_context}

前置技术交底书：
{disclosure_context}

核心公式包：
{formula_context}
"""


def _abstract_prompt(brief: InventionBrief, claims: str, description: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
请撰写不超过300字的中文实用新型专利摘要，包含技术领域、要解决的结构问题、核心结构组成/连接关系、主要结构效果和用途，不使用商业宣传语。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}

说明书：
{description[:3000]}
"""
    return f"""
请撰写不超过300字的中文专利摘要，包含技术领域、技术问题、技术方案要点和主要用途，不使用商业宣传语。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}

说明书：
{description[:3000]}
"""


def _drawings_prompt(brief: InventionBrief, claims: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
请输出实用新型专利说明书的附图说明，至少包含图1整体结构示意图、图2局部连接关系或剖视/爆炸结构图。每行用“图X为……”格式，并尽量列出可编号部件。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""
    return f"""
请输出专利说明书的附图说明，至少包含图1方法流程图、图2系统结构图。每行用“图X为……”格式。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""


def _diagram_prompt(brief: InventionBrief, claims: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
请根据该实用新型生成可渲染的 Mermaid flowchart TD 结构关系图，只输出 Mermaid 代码。图中表达部件组成、连接关系、安装位置和配合关系，不输出方法流程。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""
    return f"""
请根据该AI/软件方法发明生成可渲染的Mermaid flowchart TD代码，只输出Mermaid代码。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""


def _image_prompt(brief: InventionBrief, mermaid: str) -> str:
    if _is_utility_model_brief(brief):
        return f"""
请为实用新型专利摘要图/结构图生成绘图提示词。要求黑白线稿、无装饰，突出整体结构、局部连接关系、安装位置、剖视/爆炸视图和必要标号，适合专利附图。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

结构关系图：
{mermaid}
"""
    return f"""
请为专利摘要图/流程图生成绘图提示词。要求黑白线稿、无装饰、模块和箭头清晰、适合专利附图。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

流程图：
{mermaid}
"""
