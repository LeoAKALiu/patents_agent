from __future__ import annotations

import json
import re
import uuid
from typing import Iterable

from backend.app.llm import LLMClient
from backend.app.patent_mode import is_utility_model_project
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

STRONG_SIGNALS = {"矩阵", "权重", "优化", "概率", "阈值"}


def assess_formula_need(
    *,
    project: ProjectRecord,
    patent_points: Iterable[PatentPointCandidate] = (),
    disclosure: DisclosurePackage | None = None,
    strategy_brief: PatentStrategyBrief | None = None,
) -> FormulaNeedAssessment:
    if is_utility_model_project(project):
        return FormulaNeedAssessment(
            required=False,
            signals=[],
            reasons=["实用新型轻量版以结构、部件和连接关系为主，不强制凝练算法公式。"],
        )
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
    providers: list[str] | None = None,
) -> FormulaRun:
    requirement = assess_formula_need(
        project=project,
        patent_points=patent_points,
        disclosure=disclosure,
        strategy_brief=strategy_brief,
    )
    run_id = uuid.uuid4().hex
    if not requirement.required:
        selected_providers = providers or []
        package = CoreFormulaPackage(
            summary="系统未检测到必须凝练为核心公式的计算型技术特征。",
            formula_blocks=[],
            variable_definitions=[],
            derivation_notes=[],
            claim_hooks=[],
            description_insert="",
            latex_markdown="# 核心公式\n\n本项目当前无需公式型凝练。",
            generation_logs=[
                "formula: requirement not detected; skipped formula condensation",
                f"formula: selected providers {', '.join(selected_providers) or 'default'}",
            ],
        )
        return FormulaRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=selected_providers,
            requirement=requirement,
            package=package,
            events=["formula package skipped: not required"],
        )

    prompt = _formula_prompt(project, patent_points, disclosure, strategy_brief, requirement)
    raw = llm.complete_stage("core_formula", SYSTEM_PROMPT, prompt)
    package = _parse_formula_package(raw, requirement)
    selected_providers = providers or []
    package.generation_logs.append(f"formula: selected providers {', '.join(selected_providers) or 'default'}")
    return FormulaRun(
        id=run_id,
        project_id=project_id,
        status="completed",
        providers=selected_providers,
        requirement=requirement,
        package=package,
        events=[f"formula package generated with providers: {', '.join(providers or []) or 'default'}"],
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
    """Parse LLM output into a formula package, with repair and quality gating."""
    payload = _extract_json(raw)
    generation_logs = ["formula: generated core formula package"]

    # Attempt direct construction first
    try:
        package = CoreFormulaPackage(**payload)
    except Exception:
        # Attempt repair: fill missing required fields with sensible defaults
        repaired = _repair_formula_payload(payload, requirement)
        try:
            package = CoreFormulaPackage(**repaired)
            generation_logs.append("formula: package built after partial repair")
        except Exception:
            # Both direct parse and repair failed; fallback
            package = _fallback_package(requirement, raw)
            package.generation_logs = generation_logs + package.generation_logs
            return package

    # Quality validation
    quality = _validate_formula_quality(package, requirement)
    package.quality_severity = quality["severity"]
    if quality["severity"] in ("high", "critical"):
        package.is_fallback = True
        package.derivation_notes.insert(
            0,
            f"质量门检查未通过 ({quality['severity']}): {'; '.join(quality['warnings'])}",
        )
    package.raw_model_output = raw

    if not package.generation_logs:
        package.generation_logs = generation_logs
    if not package.latex_markdown:
        package.latex_markdown = formula_package_to_markdown(package)
    return package


def _extract_json(raw: str) -> dict:
    """Robust JSON extraction from LLM output with multiple repair strategies."""
    stripped = raw.strip()
    candidates: list[str] = []

    # Strategy 1: direct parse
    candidates.append(stripped)

    # Strategy 2: code-fence extraction (```json ... ``` / ``` ... ```)
    if "```" in stripped:
        fence_matches = re.findall(r"```(?:json)?\s*\n?(.*?)```", stripped, re.DOTALL)
        candidates.extend(m.strip() for m in fence_matches if "{" in m)

    # Strategy 3: extract outermost { ... } or [ ... ]
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])

    # Strategy 4: try to fix common JSON issues (trailing commas, unescaped)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
            # If it's a list, wrap it
            if isinstance(payload, list) and payload:
                return {"formula_blocks": payload}
        except json.JSONDecodeError:
            continue

    # Strategy 5: aggressive repair — fix trailing commas, missing quotes
    for candidate in candidates:
        repaired = _repair_json_syntax(candidate)
        try:
            payload = json.loads(repaired)
            if isinstance(payload, dict):
                return payload
            if isinstance(payload, list) and payload:
                return {"formula_blocks": payload}
        except json.JSONDecodeError:
            continue

    return {}


def _repair_json_syntax(text: str) -> str:
    """Attempt to fix common JSON syntax issues in LLM output."""
    # Remove trailing commas before ] or }
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix unquoted keys: {foo: bar} -> {"foo": bar}
    # Only match simple word-like keys (not already quoted, not numbers)
    text = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', text)
    # Fix invalid JSON escape sequences: \s, \m, etc. → \\s, \\m
    # Valid JSON escapes: " \ / b f n r t uXXXX
    # An invalid escape like \s should become \\s (literal backslash + s)
    text = re.sub(
        r'\\(?!["\\/bfnrtu])',
        r'\\\\',
        text,
    )
    return text


def _repair_formula_payload(
    payload: dict, requirement: FormulaNeedAssessment
) -> dict:
    """Fill missing required fields with sensible defaults so Pydantic can construct."""
    repaired = dict(payload)
    if "summary" not in repaired or not repaired.get("summary"):
        signal = requirement.signals[0] if requirement.signals else "技术指标"
        repaired["summary"] = f"围绕{signal}的算法关系凝练（经结构修复）。"
    # Normalize formula_blocks: ensure each has required fields
    blocks = repaired.get("formula_blocks")
    if not isinstance(blocks, list):
        repaired["formula_blocks"] = []
    else:
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                block.setdefault("id", block.get("id", f"F{i+1:02d}"))
                block.setdefault("name", block.get("name", f"公式{i+1}"))
                block.setdefault("latex", block.get("latex", block.get("expression", "")))
                block.setdefault("purpose", block.get("purpose", block.get("description", "")))
                block.setdefault("claim_hook", block.get("claim_hook", ""))
    return repaired


def _validate_formula_quality(
    package: CoreFormulaPackage, requirement: FormulaNeedAssessment
) -> dict:
    """Check formula package quality. Returns severity and warnings."""
    warnings: list[str] = []
    severity: str = "normal"

    # No formula blocks at all
    if not package.formula_blocks:
        if requirement.required:
            warnings.append("未生成任何公式。")
            severity = "critical"
        return {"severity": severity, "warnings": warnings}

    blocks = package.formula_blocks

    # Check for trivial/fallback-like formulas (simple difference relation)
    trivial_patterns = [
        r"\\Delta\s+\w+\s*=\s*\w+\^{post}\s*-\s*\w+\^{prior}",
        r"\\Delta\s+\w+\s*=\s*\w+\^{post}\s*-\s*\w+\^{prior}",
    ]
    trivial_count = 0
    for block in blocks:
        for pattern in trivial_patterns:
            if re.search(pattern, block.latex):
                trivial_count += 1
                break

    strong_signals = STRONG_SIGNALS & set(requirement.signals)

    # No meaningful formulas — only trivial difference equations
    if len(blocks) <= 1 and trivial_count >= len(blocks):
        if strong_signals:
            warnings.append(
                f"项目包含强公式信号 {', '.join(sorted(strong_signals))}，但仅生成平凡差值公式。"
            )
            severity = "high"
        else:
            warnings.append("仅生成平凡的差值公式，可能不足以支撑权利要求。")
            severity = "warning"

    # Rich signals but only one formula
    if strong_signals and len(blocks) == 1 and severity == "normal":
        warnings.append(
            f"项目包含 {len(strong_signals)} 个强公式信号 ({', '.join(sorted(strong_signals))})，但仅生成1个公式，可能未全覆盖。"
        )
        severity = "warning"

    # Check that variable definitions are substantive (not just generic post/prior)
    generic_vars = 0
    for vd in package.variable_definitions:
        if "处理前" in vd.meaning or "处理后" in vd.meaning or "指标状态" in vd.meaning:
            generic_vars += 1
    if generic_vars > 0 and len(package.variable_definitions) <= 2 and strong_signals:
        warnings.append("变量定义过于通用（仅区分处理前/后），未体现矩阵/权重/概率等具体量。")
        if severity == "normal":
            severity = "warning"

    # Check for empty or trivial purpose
    for block in blocks:
        if len(block.purpose) < 10 or block.purpose in (
            "描述采集或处理前后置信度的变化量。",
            "描述采集或处理前后技术指标的变化量。",
        ):
            warnings.append(f"公式 {block.id} 的目的说明过于简略，缺少技术含义。")
            if severity == "normal":
                severity = "warning"

    # Check formula_blocks have meaningful latex (not empty)
    for block in blocks:
        if not block.latex.strip() or block.latex.strip() in ("", "\\", "\\\\"):
            warnings.append(f"公式 {block.id} 的LaTeX表达式为空。")
            severity = "high"

    return {"severity": severity, "warnings": warnings}


def _fallback_package(
    requirement: FormulaNeedAssessment, raw_output: str = ""
) -> CoreFormulaPackage:
    signal = requirement.signals[0] if requirement.signals else "技术指标"
    strong_signals = STRONG_SIGNALS & set(requirement.signals)
    severity = "high" if strong_signals else "warning"

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
        derivation_notes=[
            "模型输出未能解析为完整JSON，系统生成保守公式包供人工复核。",
            *(
                [f"强公式信号检测: {', '.join(sorted(strong_signals))} — 回退公式严重不足"]
                if strong_signals
                else []
            ),
        ],
        claim_hooks=[f"将{signal}更新关系写入从属权利要求或具体实施方式。"],
        description_insert=f"本实施例可通过公式F01计算{signal}更新量，并据此执行后续任务。",
        generation_logs=["formula: fallback package generated after parsing failure"],
        is_fallback=True,
        quality_severity=severity,
        raw_model_output=raw_output,
    )
