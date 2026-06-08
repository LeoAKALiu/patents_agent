from __future__ import annotations

import json

from pydantic import ValidationError

from backend.app.llm import LLMClient, StructuredOutputError
from backend.app.schemas import (
    AbstractOutput,
    Citation,
    ClaimsOutput,
    CoreFormulaPackage,
    DescriptionOutput,
    DisclosurePackage,
    DraftPackage,
    DrawingsOutput,
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

        claims_struct = self._structured(
            "claims",
            _claims_prompt(brief, context, strategy_context, disclosure_context, formula_context),
            ClaimsOutput,
        )
        claims_text = render_claims(claims_struct)
        description_struct = self._structured(
            "description",
            _description_prompt(brief, claims_text, context, strategy_context, disclosure_context, formula_context),
            DescriptionOutput,
        )
        drawings_struct = self._structured("drawings", _drawings_prompt(brief, claims_text), DrawingsOutput)
        drawings_text = render_drawings(drawings_struct)
        description_text = render_description(description_struct, drawings_text)
        abstract_struct = self._structured(
            "abstract",
            _abstract_prompt(brief, claims_text, description_text),
            AbstractOutput,
        )
        mermaid = self.llm.complete_stage("diagram", SYSTEM_PROMPT, _diagram_prompt(brief, claims_text))
        image_prompt = self.llm.complete_stage("image_prompt", SYSTEM_PROMPT, _image_prompt(brief, mermaid))

        abstract_text, abstract_logs = _finalize_abstract(abstract_struct.abstract)

        return DraftPackage(
            title=brief.title,
            abstract=abstract_text,
            claims=claims_text,
            description=description_text,
            drawing_description=drawings_text,
            mermaid=mermaid.strip(),
            image_prompt=image_prompt.strip(),
            claims_struct=claims_struct,
            description_struct=description_struct,
            drawings_struct=drawings_struct,
            abstract_struct=abstract_struct,
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
                "claims: structured JSON rendered deterministically (features joined by 分号, 句号 terminator)",
                "description: structured JSON (四段) rendered deterministically",
                "abstract: structured JSON under CNIPA-style 300-character constraint",
                "drawings: structured JSON rendered as single-source 附图说明 and figure plan",
                "diagram: generated as Mermaid flowchart",
                "image_prompt: generated for patent-style black-and-white drawing",
                *abstract_logs,
            ],
            strategy_brief=strategy_brief,
            agent_consensus=strategy_brief.agent_consensus if strategy_brief else None,
            disclosure_summary=disclosure.summary if disclosure else None,
            patent_point_summary=disclosure.selected_candidate.title if disclosure and disclosure.selected_candidate else None,
            core_formula_summary=formula_package.summary if formula_package else None,
        )

    def _structured(self, stage: str, prompt: str, model):
        payload = self.llm.complete_stage_json(stage, SYSTEM_PROMPT, prompt)
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise StructuredOutputError(stage, f"{stage} JSON 不符合 schema：{exc}", raw=str(payload)) from exc

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
请为以下技术方案撰写中国发明专利权利要求，只返回一个 JSON 对象，结构为：
{{"claims": [{{"number": 1, "kind": "independent", "category": "method", "depends_on": null, "preamble": "一种……方法，其特征在于，包括：", "features": ["技术特征一", "技术特征二"]}}]}}
要求：
1. 至少1项独立权利要求和3项从属权利要求；category 取 method/system/device/medium/other；
2. 从属权利要求 kind 为 dependent，depends_on 为被引用权利要求号，preamble 形如“根据权利要求1所述的方法，其特征在于”；
3. preamble 仅写主题名与过渡语，技术特征逐条放入 features 数组，单条 feature 内不写分号或编号；
4. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形例、从属限定或待验证改进方向，不得写成已经完成验证的实施事实；
5. 对用户指定专利点，要保留其保护意图；
6. 如果存在核心公式包，权利要求必须吸收 formula_blocks 的计算目标、变量关系和 claim_hooks，但不得把未验证效果写成已验证事实；
7. 不要输出任何解释、Markdown 或开场白，只输出 JSON。

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
基于技术交底和权利要求，撰写说明书正文，只返回一个 JSON 对象，结构为：
{{"technical_field": "技术领域正文", "background": "背景技术正文", "summary": "发明内容正文", "embodiments": "具体实施方式正文"}}
说明书要支撑每一项权利要求，不引入权利要求无法对应的核心特征。各字段只写该部分正文、不写章节标题，且不要包含附图说明（附图说明单独生成）。
要求：
1. 对 evidence_status 为 feasible_unverified 或 needs_experiment 的方案，只能写成可选实施例、变形例、从属限定或待验证改进方向，不得写成已经完成验证的实施事实；
2. 对用户指定专利点，要保留其保护意图；
3. 如果存在核心公式包，必须在 summary 或 embodiments 给出公式编号、变量定义、计算流程和权利要求落点；
4. 不要输出任何解释、Markdown 或开场白，只输出 JSON。

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
请撰写中文专利摘要，只返回一个 JSON 对象，结构为：{{"abstract": "摘要正文"}}
要求：摘要不超过300字，包含技术领域、技术问题、技术方案要点和主要用途，不使用商业宣传语；不要输出解释、Markdown 或开场白，只输出 JSON。

技术交底：
{brief.model_dump_json(ensure_ascii=False, indent=2)}

权利要求：
{claims}

说明书：
{description[:3000]}
"""


def _drawings_prompt(brief: InventionBrief, claims: str) -> str:
    return f"""
请输出专利说明书的附图清单，只返回一个 JSON 对象，结构为：
{{"figures": [{{"figure_no": "图1", "title": "方法流程图"}}, {{"figure_no": "图2", "title": "系统结构图"}}]}}
要求：至少包含图1方法流程图与图2系统结构图；title 仅写图名，不含“图X为”前缀和句号；不要输出解释或 Markdown，只输出 JSON。

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


def _finalize_abstract(abstract: str) -> tuple[str, list[str]]:
    """Trim the abstract to the CNIPA 300-character limit; report truncation via generation logs."""
    text = (abstract or "").strip()
    if len(text) > 300:
        return text[:300], ["abstract: truncated to 300 characters to satisfy CNIPA abstract length limit"]
    return text, []


# --- Deterministic renderers (Component 1) -------------------------------------------------
# Canonical patent text is rendered from structured output, so AI prefaces / meta / headings
# cannot leak into claims/description/drawings, and claim formatting (分号/句号) is code-controlled.


def render_claims(claims_output: ClaimsOutput) -> str:
    """Render structured claims into canonical text: features joined by 中文分号, terminated by 句号."""
    lines: list[str] = []
    for item in sorted(claims_output.claims, key=lambda claim: claim.number):
        features = [feature.strip().rstrip("；;。") for feature in item.features if feature and feature.strip()]
        preamble = item.preamble.strip()
        if features:
            body = "；\n".join(features) + "。"
            text = f"{preamble}\n{body}" if preamble else body
        elif preamble:
            text = preamble if preamble.endswith("。") else f"{preamble}。"
        else:
            continue
        lines.append(f"{item.number}. {text}")
    return "\n".join(lines).strip()


def render_drawings(drawings_output: DrawingsOutput) -> str:
    """Single source of truth for 附图说明: render each figure as 「图X为……。」."""
    lines: list[str] = []
    for figure in drawings_output.figures:
        figure_no = figure.figure_no.strip()
        title = figure.title.strip().rstrip("。")
        if figure_no and title:
            lines.append(f"{figure_no}为{title}。")
    return "\n".join(lines).strip()


def render_description(description_output: DescriptionOutput, drawings_text: str) -> str:
    """Render the five canonical sections; 附图说明 is injected from the single drawings source."""
    sections = [
        ("技术领域", description_output.technical_field),
        ("背景技术", description_output.background),
        ("发明内容", description_output.summary),
        ("附图说明", drawings_text),
        ("具体实施方式", description_output.embodiments),
    ]
    blocks: list[str] = []
    for heading, body in sections:
        body = (body or "").strip()
        blocks.append(f"{heading}\n{body}" if body else heading)
    return "\n\n".join(blocks).strip()
