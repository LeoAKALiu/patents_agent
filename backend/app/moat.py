from __future__ import annotations

import json

from backend.app.llm import LLMClient
from backend.app.schemas import MoatScores, PatentPointCandidate, ProjectRecord


MOAT_DIMENSIONS = (
    "scope_width",
    "designaround_difficulty",
    "feasibility",
    "support_strength",
    "prior_art_distance",
    "strategic_value",
)


SYSTEM_PROMPT = (
    "你是中国发明专利的护城河评估助手。"
    "根据给定项目和专利点，从六个维度评估该专利点的护城河强度，每个维度输出 0.0 到 1.0 之间的浮点数。"
    "维度含义：scope_width（权利要求覆盖范围）、designaround_difficulty（竞争对手绕开难度）、"
    "feasibility（技术可实施性）、support_strength（说明书与证据支撑强度）、"
    "prior_art_distance（相对现有技术的距离/新颖性余量）、strategic_value（对该项目的战略价值）。"
    "只输出 JSON 对象，不输出 Markdown 解释；务必同时给出一段简洁的中文 rationale 说明打分依据。"
    "不要声称实验已验证，未验证内容只能作为可行技术方案表达。"
)


def _moat_prompt(project: ProjectRecord, point: PatentPointCandidate) -> str:
    claim_chart = point.claim_chart or []
    return f"""
请为下列专利点评估护城河六维分数，输出 JSON 对象，字段必须包含：
scope_width, designaround_difficulty, feasibility, support_strength, prior_art_distance, strategic_value, rationale。
每个分数为 0.0 到 1.0 之间的浮点数；rationale 为一段简洁中文说明（不超过 200 字）。

项目：
{project.model_dump_json(ensure_ascii=False, indent=2)}

专利点：
{point.model_dump_json(ensure_ascii=False, indent=2)}

现有技术对照（用于判断 prior_art_distance）：
{json.dumps([item.model_dump(mode="json") for item in claim_chart], ensure_ascii=False, indent=2) if claim_chart else "无"}
"""


def _extract_json(raw: str) -> dict:
    stripped = raw.strip()
    candidates = [stripped]
    if "```" in stripped:
        parts = stripped.split("```")
        candidates.extend(part.replace("json", "", 1).strip() for part in parts if "{" in part)
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    return {}


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _fallback_moat() -> tuple[MoatScores, str]:
    return MoatScores(feasibility=0.5, strategic_value=0.5), "评分解析失败，已使用占位分。"


def _parse_moat_result(raw: str) -> tuple[MoatScores, str]:
    payload = _extract_json(raw)
    if not payload:
        return _fallback_moat()
    try:
        scores = MoatScores(
            **{dimension: _clamp(float(payload.get(dimension, 0.0))) for dimension in MOAT_DIMENSIONS}
        )
    except (TypeError, ValueError):
        return _fallback_moat()
    rationale = str(payload.get("rationale") or "").strip()
    if not rationale:
        rationale = "评测完成，但未返回打分依据。"
    return scores, rationale


def score_moat(
    *,
    llm: LLMClient,
    project: ProjectRecord,
    point: PatentPointCandidate,
) -> tuple[MoatScores, str]:
    """调用 LLM 对单个专利点的护城河六维进行评测，返回 (分数, 打分依据)。"""
    raw = llm.complete_stage("moat_scoring", SYSTEM_PROMPT, _moat_prompt(project, point))
    return _parse_moat_result(raw)
