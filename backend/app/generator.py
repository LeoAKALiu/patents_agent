from __future__ import annotations

import json

from backend.app.llm import LLMClient
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
        claims = self.llm.complete_stage("claims", SYSTEM_PROMPT, _claims_prompt(brief, context, strategy_context, disclosure_context, formula_context))
        description = self.llm.complete_stage(
            "description", SYSTEM_PROMPT, _description_prompt(brief, claims, context, strategy_context, disclosure_context, formula_context)
        )
        abstract = self.llm.complete_stage("abstract", SYSTEM_PROMPT, _abstract_prompt(brief, claims, description))
        drawings = self.llm.complete_stage("drawings", SYSTEM_PROMPT, _drawings_prompt(brief, claims))
        mermaid = self.llm.complete_stage("diagram", SYSTEM_PROMPT, _diagram_prompt(brief, claims))
        image_prompt = self.llm.complete_stage("image_prompt", SYSTEM_PROMPT, _image_prompt(brief, mermaid))
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
            "请审查以下中国发明专利初稿，输出JSON数组。每项包含category、severity、message、suggestion、evidence。"
            "\n\n"
            f"题名：{package.title}\n摘要：{package.abstract}\n权利要求：{package.claims}\n说明书：{package.description}"
        )
        raw = self.llm.complete_stage("review", SYSTEM_PROMPT, prompt)
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


SYSTEM_PROMPT = (
    "你是中国发明专利撰写助手，熟悉CNIPA申请文件范式。"
    "输出应为专利初稿辅助文本，不得声称替代专利代理师。"
    "优先使用技术特征、步骤、模块、数据流、技术效果等专利语言，避免营销表述。"
)


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
    return f"""
请输出专利说明书的附图说明，至少包含图1方法流程图、图2系统结构图。每行用“图X为……”格式。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""


def _diagram_prompt(brief: InventionBrief, claims: str) -> str:
    return f"""
请根据该AI/软件方法发明生成可渲染的Mermaid flowchart TD代码，只输出Mermaid代码。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}
"""


def _image_prompt(brief: InventionBrief, mermaid: str) -> str:
    return f"""
请为专利摘要图/流程图生成绘图提示词。要求黑白线稿、无装饰、模块和箭头清晰、适合专利附图。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

流程图：
{mermaid}
"""
