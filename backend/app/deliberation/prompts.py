from __future__ import annotations

from backend.app.schemas import InventionBrief, PatentChunk


GUARDRAILS = """执行约束：
- 不要浏览网页，不要打开浏览器，不要调用 web/search/browser 类工具。
- 不要读取仓库、README、AGENTS.md、历史运行留痕目录或任何未在本 prompt 中提供的文件。
- 不要解释你将如何工作，不要输出元评论。
- 只基于本 prompt 中给出的 dossier、授权专利片段和前序发言完成任务。
- 严格返回可被 Python json.loads 解析的 JSON object，不要附加额外说明、Markdown 代码围栏、thinking 或前后缀。
- JSON 字符串内部不要使用英文双引号；引用术语时使用中文引号「」或直接省略引号。若必须使用英文双引号，必须写成 \\"。
"""


ROLE_PROMPTS = {
    "codex": "你是 Codex 侧专利工程专家，优先关注技术可交付性、权利要求边界、实施例支撑和失败模式。",
    "deepseek": "你是 DeepSeek 侧专利审查专家，优先关注现有技术差异、审查稳定性、创造性论证和风险压降。",
    "gemini": "你是 Gemini 侧专利策略专家，优先关注保护范围布局、创新点表达、审查说服力和摘要/附图叙事。",
    "claude": "你是 Claude 侧专利文本专家，优先关注说明书结构、术语一致性、支持性和整体自洽。",
    "kimicode": "你是 KimiCode 侧专利产品化专家，优先关注中文表达质量、方案可读性、审查员可理解性和权利要求叙事。",
    "mimo": "你是 MimoCode 侧工程实现专家，优先关注实现路径、模块边界、异常处理、可验证证据和交付风险。",
}


def build_dossier(brief: InventionBrief, context_chunks: list[PatentChunk]) -> str:
    chunks = "\n\n".join(
        f"[{index}] {chunk.section_type.value} / {chunk.metadata.get('title', chunk.document_id)}\n{chunk.text[:1200]}"
        for index, chunk in enumerate(context_chunks, start=1)
    )
    return f"""# 技术交底
{brief.model_dump_json(ensure_ascii=False, indent=2)}

# 相似授权专利片段
{chunks or "无。"}
"""


def opening_prompt(provider_id: str, dossier: str) -> str:
    return f"""{GUARDRAILS}
{ROLE_PROMPTS.get(provider_id, ROLE_PROMPTS["codex"])}

任务：给出生成中国发明专利初稿前的独立会审意见。

{dossier}

JSON schema:
{{
  "stance": "一句话总体判断",
  "claim_scope": ["建议保护的权利要求范围"],
  "risks": ["漏洞或审查风险"],
  "recommendations": ["写作策略建议"]
}}
"""


def pair_prompt(provider_a: str, provider_b: str, dossier: str, openings: dict) -> str:
    return f"""{GUARDRAILS}
你是交叉质询记录员，需要比较两个 agent 的初始立论并收敛冲突。

{dossier}

双方立论：
{openings}

比较对象：{provider_a} vs {provider_b}

JSON schema:
{{
  "conflict_level": 0.0,
  "agreements": ["共同结论"],
  "disagreements": ["关键分歧"],
  "resolved_recommendation": "会审后建议采用的处理方式"
}}
"""


def chair_prompt(dossier: str, openings: dict, pair_results: list[dict]) -> str:
    return f"""{GUARDRAILS}
你是 Codex 主席，负责汇总多智能体会审并生成可注入专利写作流水线的 strategy brief。

{dossier}

初始立论：
{openings}

两两交叉质询：
{pair_results}

JSON schema:
{{
  "summary": "总体写作策略摘要",
  "claim_strategy": ["权利要求布局建议"],
  "description_strategy": ["说明书支撑建议"],
  "risk_controls": ["漏洞与规避建议"],
  "agent_consensus": "多 agent 共识",
  "disclosure_summary": "若 dossier 中有前置交底书，则概括其可注入内容；否则为空字符串",
  "patent_point_summary": "若有推荐专利点，则概括保护重点；否则为空字符串",
  "prior_art_differences": "若有公开现有技术差异，则概括区别；否则为空字符串"
}}
"""
