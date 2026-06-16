from __future__ import annotations

import json
import re
import uuid
from typing import Any

from backend.app.llm import LLMClient
from backend.app.schemas import (
    DeliberationLogEntry,
    DisclosureRun,
    KnowledgeReadinessRoleResult,
    KnowledgeReadinessRun,
    ProjectMaterial,
    ProjectRecord,
)


KNOWLEDGE_READINESS_THRESHOLD = 80
ROLE_STAGES = (
    ("deep_research_auditor", "knowledge_deep_research_auditor"),
    ("prior_art_auditor", "knowledge_prior_art_auditor"),
    ("drafting_support_auditor", "knowledge_drafting_support_auditor"),
)
SYSTEM_PROMPT = (
    "你是专利撰写前置知识完备度会审 agent。"
    "只输出 JSON，不输出 Markdown。"
    "评分为百分制，必须严格依据项目材料、DeepResearch 报告、论文/专利附件和本地语料覆盖度。"
)


def run_knowledge_readiness(
    *,
    project: ProjectRecord,
    materials: list[ProjectMaterial],
    disclosures: list[DisclosureRun],
    corpus_stats: dict[str, Any],
    llm: LLMClient,
    providers: list[str],
) -> KnowledgeReadinessRun:
    run_id = uuid.uuid4().hex
    processed_materials = [material for material in materials if material.status == "processed"]
    deep_research_uploaded = _has_deep_research_report(processed_materials)
    related_reference_count = _related_reference_count(processed_materials)
    corpus_document_count = int(corpus_stats.get("document_count") or 0)
    corpus_chunk_count = int(corpus_stats.get("chunk_count") or 0)
    dossier = _knowledge_dossier(
        project=project,
        materials=processed_materials,
        disclosures=disclosures,
        corpus_stats=corpus_stats,
        deep_research_uploaded=deep_research_uploaded,
        related_reference_count=related_reference_count,
    )
    logs: list[DeliberationLogEntry] = []
    role_results: list[KnowledgeReadinessRoleResult] = []
    try:
        for role, stage in ROLE_STAGES:
            raw = llm.complete_stage(stage, SYSTEM_PROMPT, _role_prompt(role, dossier))
            result = KnowledgeReadinessRoleResult.model_validate(_extract_json(raw))
            role_results.append(result)
            logs.append(
                DeliberationLogEntry(
                    level="info",
                    phase="knowledge_readiness",
                    provider_id=role,
                    message=f"{role} completed",
                    detail=json.dumps(result.model_dump(mode="json"), ensure_ascii=False)[:1200],
                )
            )
    except Exception as exc:
        logs.append(
            DeliberationLogEntry(
                level="error",
                phase="knowledge_readiness",
                provider_id="system",
                message="knowledge readiness failed",
                detail=str(exc)[:1200],
                repair_suggestion="检查知识完备度 agent 是否按 JSON schema 输出评分。",
            )
        )
        return KnowledgeReadinessRun(
            id=run_id,
            project_id=project.id,
            status="failed",
            providers=providers,
            blocking_issues=["知识完备度多智能体评分失败。"],
            logs=logs,
        )

    score_before_bonus = round(sum(result.score for result in role_results) / len(role_results))
    score = min(100, score_before_bonus + _reference_bonus(related_reference_count, corpus_document_count))
    blocking_issues = _blocking_issues(
        deep_research_uploaded=deep_research_uploaded,
        score=score,
    )
    proceed_allowed = deep_research_uploaded and score > KNOWLEDGE_READINESS_THRESHOLD and not blocking_issues
    recommendations = _dedupe([item for result in role_results for item in result.recommendations])
    return KnowledgeReadinessRun(
        id=run_id,
        project_id=project.id,
        status="completed",
        providers=providers,
        score=score,
        score_before_bonus=score_before_bonus,
        threshold=KNOWLEDGE_READINESS_THRESHOLD,
        proceed_allowed=proceed_allowed,
        deep_research_report_uploaded=deep_research_uploaded,
        processed_material_count=len(processed_materials),
        related_reference_count=related_reference_count,
        corpus_document_count=corpus_document_count,
        corpus_chunk_count=corpus_chunk_count,
        role_results=role_results,
        blocking_issues=blocking_issues,
        recommendations=recommendations,
        logs=logs,
    )


def is_deep_research_report_material(material: ProjectMaterial) -> bool:
    haystack = f"{material.file_name}\n{material.text[:5000]}".lower()
    return any(
        pattern in haystack
        for pattern in (
            "deepresearch",
            "deep research",
            "deep-research",
            "深度研究",
            "深度检索",
            "深度调研",
            "现有技术调研报告",
            "检索报告",
        )
    )


def require_knowledge_ready(run: KnowledgeReadinessRun | None) -> None:
    if run and run.status == "completed" and run.proceed_allowed:
        return
    raise ValueError("Knowledge readiness score must be greater than 80 with an uploaded DeepResearch report before generating a draft.")


def _has_deep_research_report(materials: list[ProjectMaterial]) -> bool:
    return any(is_deep_research_report_material(material) for material in materials)


def _related_reference_count(materials: list[ProjectMaterial]) -> int:
    count = 0
    for material in materials:
        if is_deep_research_report_material(material):
            continue
        haystack = f"{material.file_name}\n{material.text[:3000]}".lower()
        if any(token in haystack for token in ("论文", "paper", "article", "arxiv", "专利", "patent", "cn", "us", "wo")):
            count += 1
    return count


def _reference_bonus(related_reference_count: int, corpus_document_count: int) -> int:
    return min(10, related_reference_count * 3 + min(4, corpus_document_count))


def _blocking_issues(
    *,
    deep_research_uploaded: bool,
    score: int,
) -> list[str]:
    issues: list[str] = []
    if not deep_research_uploaded:
        issues.append("必须先上传 DeepResearch 报告材料。")
    if score <= KNOWLEDGE_READINESS_THRESHOLD:
        issues.append("知识完备度评分需大于 80 分。")
    return _dedupe(issues)


def _knowledge_dossier(
    *,
    project: ProjectRecord,
    materials: list[ProjectMaterial],
    disclosures: list[DisclosureRun],
    corpus_stats: dict[str, Any],
    deep_research_uploaded: bool,
    related_reference_count: int,
) -> str:
    latest_disclosure = next((run for run in disclosures if run.status == "completed" and run.package), None)
    material_lines = [
        f"- {material.file_name} ({material.file_type}, {len(material.text)} chars)"
        for material in materials[:12]
    ]
    return "\n".join(
        [
            f"项目名称：{project.name}",
            f"项目想法：{project.draft_text[:1500]}",
            f"已上传 DeepResearch 报告：{deep_research_uploaded}",
            f"可解析材料数：{len(materials)}",
            f"相关论文/专利附件数：{related_reference_count}",
            f"本地语料文档数：{corpus_stats.get('document_count', 0)}",
            f"本地语料片段数：{corpus_stats.get('chunk_count', 0)}",
            "材料清单：",
            *material_lines,
            "最近交底摘要：",
            latest_disclosure.package.summary[:1500] if latest_disclosure and latest_disclosure.package else "无 completed 交底书。",
        ]
    )


def _role_prompt(role: str, dossier: str) -> str:
    focus = {
        "deep_research_auditor": "检查 DeepResearch 报告是否上传、是否覆盖关键现有技术、是否有可引用结论。",
        "prior_art_auditor": "检查相关论文/专利文件和本地语料是否足以支撑现有技术差异。",
        "drafting_support_auditor": "检查材料是否足以支撑发明点、实施例、权利要求边界和技术效果。",
    }[role]
    return f"""
角色：{role}
任务：{focus}
只输出 JSON object，字段必须包含：
{{
  "role": "{role}",
  "score": 0-100,
  "strengths": ["已有支撑"],
  "issues": ["缺口"],
  "recommendations": ["下一步建议"]
}}

知识材料摘要：
{dossier}
"""


def _extract_json(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    candidates = [stripped]
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    if "```" in stripped:
        candidates.extend(part.replace("json", "", 1).strip() for part in stripped.split("```") if "{" in part)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    raise ValueError("invalid_json: knowledge readiness output is not JSON")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
