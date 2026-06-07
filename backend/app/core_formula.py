from __future__ import annotations

import json
import uuid
from typing import Iterable

from backend.app.llm import LLMClient
from backend.app.schemas import (
    CoreFormulaPackage,
    DisclosurePackage,
    FormulaBlock,
    FormulaNeedAssessment,
    FormulaRun,
    FormulaVariableDefinition,
    PatentPointCandidate,
    PatentStrategyBrief,
    ProjectRecord,
)


FORMULA_SIGNALS = (
    "置信度",
    "置信区间",
    "贡献矩阵",
    "矩阵",
    "权重",
    "增益",
    "后验",
    "优化",
    "概率",
    "函数",
    "坐标",
    "阈值",
    "协方差",
    "梯度",
    "损失",
    "评分",
)


def assess_formula_need(
    *,
    project: ProjectRecord,
    patent_points: Iterable[PatentPointCandidate] = (),
    disclosure: DisclosurePackage | None = None,
    strategy_brief: PatentStrategyBrief | None = None,
) -> FormulaNeedAssessment:
    text = _formula_context_text(project, patent_points, disclosure, strategy_brief)
    signals = [signal for signal in FORMULA_SIGNALS if signal in text]
    reasons: list[str] = []
    if signals:
        reasons.append("项目文本包含计算关系、置信度、矩阵或优化目标等公式型信号。")
    if strategy_brief and any(signal in strategy_brief.model_dump_json(ensure_ascii=False) for signal in FORMULA_SIGNALS):
        reasons.append("会审策略包含需要用公式固定的算法或目标函数。")
    return FormulaNeedAssessment(required=bool(signals), signals=signals, reasons=reasons)


def generate_formula_run(
    *,
    project_id: str,
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate],
    disclosure: DisclosurePackage | None,
    strategy_brief: PatentStrategyBrief | None,
    llm: LLMClient,
) -> FormulaRun:
    requirement = assess_formula_need(
        project=project,
        patent_points=patent_points,
        disclosure=disclosure,
        strategy_brief=strategy_brief,
    )
    run_id = uuid.uuid4().hex
    if not requirement.required:
        package = CoreFormulaPackage(
            summary="系统未检测到必须凝练为核心公式的计算型技术特征。",
            formula_blocks=[],
            variable_definitions=[],
            derivation_notes=[],
            claim_hooks=[],
            description_insert="",
            latex_markdown="# 核心公式\n\n本项目当前无需公式型凝练。",
            generation_logs=["formula: requirement not detected; skipped formula condensation"],
        )
        return FormulaRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            requirement=requirement,
            package=package,
            events=["formula package skipped: not required"],
        )

    prompt = _formula_prompt(project, patent_points, disclosure, strategy_brief, requirement)
    raw = llm.complete_stage("core_formula", SYSTEM_PROMPT, prompt)
    package = _parse_formula_package(raw, requirement)
    return FormulaRun(
        id=run_id,
        project_id=project_id,
        status="completed",
        requirement=requirement,
        package=package,
        events=["formula package generated"],
    )


def formula_package_to_markdown(package: CoreFormulaPackage) -> str:
    if package.latex_markdown.strip():
        return package.latex_markdown
    lines = ["# 核心公式", "", package.summary, ""]
    for block in package.formula_blocks:
        lines.extend(
            [
                f"## {block.id} {block.name}",
                "",
                f"目的：{block.purpose}",
                "",
                "```latex",
                block.latex,
                "```",
                "",
                f"权利要求落点：{block.claim_hook or '待映射'}",
                "",
            ]
        )
    if package.variable_definitions:
        lines.extend(["## 变量定义", ""])
        for item in package.variable_definitions:
            unit = f"（{item.unit}）" if item.unit else ""
            lines.append(f"- `{item.symbol}`：{item.meaning}{unit}")
        lines.append("")
    if package.derivation_notes:
        lines.extend(["## 推导说明", ""])
        lines.extend(f"- {note}" for note in package.derivation_notes)
        lines.append("")
    if package.claim_hooks:
        lines.extend(["## 权利要求落点", ""])
        lines.extend(f"- {hook}" for hook in package.claim_hooks)
        lines.append("")
    if package.description_insert:
        lines.extend(["## 说明书插入建议", "", package.description_insert, ""])
    return "\n".join(lines).strip() + "\n"


def _formula_context_text(
    project: ProjectRecord,
    patent_points: Iterable[PatentPointCandidate],
    disclosure: DisclosurePackage | None,
    strategy_brief: PatentStrategyBrief | None,
) -> str:
    parts = [project.name, project.draft_text]
    points = list(patent_points)
    selected_points = [point for point in points if point.selected]
    scoped_points = selected_points or points
    for point in scoped_points:
        parts.extend(
            [
                point.title,
                point.technical_problem,
                point.innovation,
                point.technical_solution,
                point.feasibility_basis,
                " ".join(point.support_gaps),
            ]
        )
    if disclosure:
        parts.extend([disclosure.summary, disclosure.body_markdown, disclosure.prior_art_differences])
    if strategy_brief:
        parts.append(strategy_brief.model_dump_json(ensure_ascii=False))
    return "\n".join(part for part in parts if part)


SYSTEM_PROMPT = (
    "你是中国发明专利的算法公式凝练助手。"
    "只输出JSON，不输出Markdown解释；公式可用LaTeX字符串表示。"
    "不要声称实验已验证，未验证内容只能作为可行技术方案或实施例表达。"
)


def _formula_prompt(
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate],
    disclosure: DisclosurePackage | None,
    strategy_brief: PatentStrategyBrief | None,
    requirement: FormulaNeedAssessment,
) -> str:
    return f"""
请为下列专利项目凝练核心公式包，输出JSON对象，字段必须包含：
summary, formula_blocks, variable_definitions, derivation_notes, claim_hooks, description_insert, latex_markdown。
formula_blocks 每项包含 id、name、latex、purpose、claim_hook。
variable_definitions 每项包含 symbol、meaning、unit。

公式信号：
{requirement.model_dump_json(ensure_ascii=False, indent=2)}

项目：
{project.model_dump_json(ensure_ascii=False, indent=2)}

发明点：
{json.dumps([point.model_dump(mode="json") for point in patent_points], ensure_ascii=False, indent=2)}

交底书：
{disclosure.model_dump_json(ensure_ascii=False, indent=2) if disclosure else "无"}

会审策略：
{strategy_brief.model_dump_json(ensure_ascii=False, indent=2) if strategy_brief else "无"}
"""


def _parse_formula_package(raw: str, requirement: FormulaNeedAssessment) -> CoreFormulaPackage:
    payload = _extract_json(raw)
    try:
        package = CoreFormulaPackage(**payload)
    except Exception:
        package = _fallback_package(requirement)
    if not package.generation_logs:
        package.generation_logs = ["formula: generated core formula package"]
    if not package.latex_markdown:
        package.latex_markdown = formula_package_to_markdown(package)
    return package


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


def _fallback_package(requirement: FormulaNeedAssessment) -> CoreFormulaPackage:
    signal = requirement.signals[0] if requirement.signals else "技术指标"
    return CoreFormulaPackage(
        summary=f"围绕{signal}建立核心计算关系，用于支撑权利要求中的算法步骤。",
        formula_blocks=[
            FormulaBlock(
                id="F01",
                name=f"{signal}更新关系",
                latex=r"\Delta S_i = S_i^{post} - S_i^{prior}",
                purpose=f"描述采集或处理前后{signal}的变化量。",
                claim_hook=f"根据{signal}变化量确定后续处理或采集任务。",
            )
        ],
        variable_definitions=[
            FormulaVariableDefinition(symbol=r"S_i^{post}", meaning="处理后的指标状态", unit=""),
            FormulaVariableDefinition(symbol=r"S_i^{prior}", meaning="处理前的指标状态", unit=""),
        ],
        derivation_notes=["模型输出未能解析为完整JSON，系统生成保守公式包供人工复核。"],
        claim_hooks=[f"将{signal}更新关系写入从属权利要求或具体实施方式。"],
        description_insert=f"本实施例可通过公式F01计算{signal}更新量，并据此执行后续任务。",
        generation_logs=["formula: fallback package generated after parsing failure"],
    )
