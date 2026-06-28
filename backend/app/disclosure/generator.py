from __future__ import annotations

import json
import uuid
from typing import Any

from backend.app.disclosure.prior_art import PriorArtProvider, dedupe_prior_art_hits
from backend.app.llm import LLMClient
from backend.app.patent_mode import is_utility_model_project
from backend.app.project_metadata import format_project_metadata_block
from backend.app.research.deep_research_intake import (
    packet_prior_art_hits,
    parse_deep_research_materials,
)
from backend.app.research.ledger import SourceLedger, citation_snapshot
from backend.app.runtime import RuntimeContext
from backend.app.schemas import (
    ClaimChartItem,
    DisclosurePackage,
    DisclosureSelfCheckFinding,
    PatentChunk,
    PatentPointCandidate,
    PriorArtHit,
    ProjectMaterial,
    ProjectRecord,
)


class DisclosureGenerator:
    def __init__(self, llm: LLMClient, prior_art_provider: PriorArtProvider) -> None:
        self.llm = llm
        self.prior_art_provider = prior_art_provider

    def generate(
        self,
        *,
        project: ProjectRecord,
        materials: list[ProjectMaterial],
        context_chunks: list[PatentChunk],
        max_prior_art_results: int,
        user_candidates: list[PatentPointCandidate] | None = None,
        ledger: SourceLedger | None = None,
        pre_diagnostics: list[dict[str, Any]] | None = None,
        runtime: RuntimeContext | None = None,
        on_stage_result: Any | None = None,
    ) -> tuple[DisclosurePackage, list[dict[str, Any]], list[str]]:
        stage_results: list[dict[str, Any]] = []
        logs: list[str] = []
        user_candidates = user_candidates or []
        strategic_context = _format_user_candidates(user_candidates)
        material_context = _format_materials(project, materials)
        deep_research_packets = parse_deep_research_materials(materials)
        deep_research_context = _format_deep_research_prompt_context(deep_research_packets)
        strategic_context = _merge_context_blocks(strategic_context, deep_research_context)
        material_context = _merge_context_blocks(material_context, deep_research_context)
        markdown_hits = [hit for packet in deep_research_packets for hit in packet_prior_art_hits(packet)]
        rag_context = _format_context(context_chunks)
        system_prompt = _system_prompt(project)
        ledger = ledger or SourceLedger()

        stage_results.append(
            {
                "phase": "deep_research_material_intake",
                "payload": {
                    "packets": [packet.model_dump(mode="json") for packet in deep_research_packets],
                    "prior_art_hit_count": len(markdown_hits),
                    "warnings": [warning for packet in deep_research_packets for warning in packet.warnings],
                },
            }
        )
        _checkpoint_stage(stage_results, runtime, on_stage_result)
        logs.extend(log for packet in deep_research_packets for log in packet.generation_logs)

        if runtime:
            runtime.begin_stage("disclosure_scan", provider="llm", subtask="project/material scan")
        scan_raw = self.llm.complete_stage("disclosure_scan", system_prompt, _scan_prompt(project, material_context))
        scan = _json_object(scan_raw, _fallback_scan(project, materials))
        stage_results.append({"phase": "project_scan", "payload": scan})
        _checkpoint_stage(stage_results, runtime, on_stage_result)
        logs.append("project_scan: summarized draft and uploaded materials")

        if runtime:
            runtime.begin_stage("patent_points", provider="llm", subtask="candidate generation")
        points_raw = self.llm.complete_stage(
            "patent_points",
            system_prompt,
            _points_prompt(project, material_context, scan, rag_context, strategic_context),
        )
        generated_candidates, generated_selected_id = _parse_candidates(
            points_raw,
            project,
            utility_model=is_utility_model_project(project),
        )
        candidates, selected_id = _merge_candidates(user_candidates, generated_candidates, generated_selected_id)
        stage_results.append(
            {
                "phase": "patent_points",
                "payload": {
                    "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                    "selected_candidate_id": selected_id,
                },
            }
        )
        _checkpoint_stage(stage_results, runtime, on_stage_result)
        logs.append("patent_points: generated candidates and selected recommended point")

        if runtime:
            runtime.begin_stage("prior_art_terms", provider="llm", subtask="search term planning")
        terms_raw = self.llm.complete_stage(
            "prior_art_terms",
            system_prompt,
            _terms_prompt(project, candidates, selected_id, scan, strategic_context),
        )
        terms = _parse_terms(terms_raw, project)
        stage_results.append({"phase": "prior_art_terms", "payload": {"terms": terms}})
        _checkpoint_stage(stage_results, runtime, on_stage_result)
        logs.append("prior_art_terms: generated semantic search chunks")

        try:
            if runtime:
                runtime.begin_stage("prior_art_search", provider="prior_art", query=", ".join(terms[:3]))
            prior_art_hits, provider_warnings = _search_prior_art_with_ledger(
                self.prior_art_provider,
                terms,
                max_prior_art_results,
                ledger,
            )
        except Exception as exc:
            search_entry = ledger.start(provider="prior_art", kind="prior_art", query="; ".join(terms[:4]))
            search_entry.mark_failed(str(exc))
            prior_art_hits = []
            provider_warnings = [f"prior_art search failed: {exc}"]

        prior_art_hits = dedupe_prior_art_hits([*prior_art_hits, *markdown_hits])

        stage_results.append(
            {
                "phase": "prior_art_search",
                "payload": {
                    "hits": [hit.model_dump(mode="json") for hit in prior_art_hits],
                    "warnings": provider_warnings,
                    "ledger": ledger.to_stage_payload(),
                },
            }
        )
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append(f"prior_art_search: collected {len(prior_art_hits)} public references")

        if runtime:
            runtime.begin_stage("prior_art_relevance", provider="llm", subtask="claim chart enrichment")
        prior_art_hits, prior_art_differences, charts_by_candidate = self._enrich_prior_art(
            project,
            candidates,
            selected_id,
            prior_art_hits,
            deep_research_context,
        )
        candidates = [
            candidate.model_copy(update={"claim_chart": charts_by_candidate.get(candidate.id, candidate.claim_chart)})
            for candidate in candidates
        ]
        stage_results.append(
            {
                "phase": "prior_art_relevance",
                "payload": {
                    "hits": [hit.model_dump(mode="json") for hit in prior_art_hits],
                    "prior_art_differences": prior_art_differences,
                    "claim_charts": [
                        {"candidate_id": candidate_id, **chart.model_dump(mode="json")}
                        for candidate_id, charts in charts_by_candidate.items()
                        for chart in charts
                    ],
                },
            }
        )
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append("prior_art_relevance: summarized differences against public references")

        if runtime:
            runtime.begin_stage("disclosure_body", provider="llm", subtask="technical disclosure markdown")
        body = self.llm.complete_stage(
            "disclosure_body",
            system_prompt,
            _body_prompt(project, material_context, scan, candidates, selected_id, prior_art_hits, prior_art_differences),
        ).strip()
        stage_results.append({"phase": "disclosure_body", "payload": {"chars": len(body)}})
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append("disclosure_body: generated technical disclosure markdown")

        if runtime:
            runtime.begin_stage("disclosure_mermaid", provider="llm", subtask="diagram generation")
        mermaid = self.llm.complete_stage(
            "disclosure_mermaid",
            system_prompt,
            _mermaid_prompt(project, candidates, selected_id, body),
        ).strip()
        stage_results.append({"phase": "disclosure_mermaid", "payload": {"chars": len(mermaid)}})
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append("disclosure_mermaid: generated Mermaid diagrams")

        if runtime:
            runtime.begin_stage("disclosure_image_prompt", provider="llm", subtask="drawing prompt")
        image_prompt = self.llm.complete_stage(
            "disclosure_image_prompt",
            system_prompt,
            _image_prompt(project, mermaid),
        ).strip()
        stage_results.append({"phase": "disclosure_image_prompt", "payload": {"chars": len(image_prompt)}})
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append("disclosure_image_prompt: generated patent drawing prompt")

        if runtime:
            runtime.begin_stage("disclosure_self_check", provider="llm", subtask="consistency check")
        self_check_raw = self.llm.complete_stage(
            "disclosure_self_check",
            system_prompt,
            _self_check_prompt(project, body, mermaid, prior_art_hits),
        )
        findings = _parse_self_check(self_check_raw)
        stage_results.append(
            {"phase": "disclosure_self_check", "payload": [finding.model_dump(mode="json") for finding in findings]}
        )
        _checkpoint_stage(stage_results, runtime, on_stage_result, warning_count=len(provider_warnings))
        logs.append("disclosure_self_check: checked disclosure consistency and support")

        package = DisclosurePackage(
            title=_disclosure_title(project, candidates, selected_id),
            summary=str(scan.get("summary") or project.draft_text[:300]),
            materials_summary=str(scan.get("materials_summary") or _materials_summary(materials)),
            candidates=candidates,
            selected_candidate_id=selected_id,
            prior_art_hits=prior_art_hits,
            prior_art_differences=prior_art_differences,
            body_markdown=body,
            mermaid=mermaid,
            image_prompt=image_prompt,
            self_check_findings=findings,
            generation_logs=[*logs, *[f"warning: {warning}" for warning in provider_warnings]],
            research_ledger=ledger.to_stage_payload(),
            provider_diagnostics=pre_diagnostics or [],
            research_confidence=ledger.research_confidence(),
        )

        # Append a low-evidence warning when research confidence is low
        if package.research_confidence == "low" and not any(
            log.startswith("low_research_confidence:") for log in package.generation_logs
        ):
            package.generation_logs.append(
                f"low_research_confidence: 0 references collected ({len(ledger.entries)} provider attempts); "
                "交底书不隐含高专利性置信度。"
            )

        if runtime:
            runtime.begin_stage("disclosure_package", provider="system", subtask="artifact assembly")
            runtime.complete_stage(partial_artifact_count=len(stage_results), warning_count=len(provider_warnings))
        return package, stage_results, provider_warnings

    def _enrich_prior_art(
        self,
        project: ProjectRecord,
        candidates: list[PatentPointCandidate],
        selected_id: str | None,
        hits: list[PriorArtHit],
        deep_research_context: str,
    ) -> tuple[list[PriorArtHit], str, dict[str, list[ClaimChartItem]]]:
        if not hits:
            return hits, "未获得可用公开现有技术结果；交底书仅基于本地材料和授权专利语料生成。", {}
        raw = self.llm.complete_stage(
            "prior_art_relevance",
            _system_prompt(project),
            _relevance_prompt(project, candidates, selected_id, hits, deep_research_context),
        )
        data = _json_object(raw, {})
        charts_by_candidate: dict[str, list[ClaimChartItem]] = {}
        known_candidate_ids = {candidate.id for candidate in candidates}
        hits_by_id = {hit.id: hit for hit in hits}
        for item in data.get("claim_charts", []):
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "")
            prior_art_id = str(item.get("prior_art_id") or "")
            hit = hits_by_id.get(prior_art_id)
            if candidate_id not in known_candidate_ids or hit is None:
                continue
            chart = ClaimChartItem(
                prior_art_id=prior_art_id,
                prior_art_title=_prior_art_title(hit),
                overlapping_features=_string_list(item.get("overlapping_features")),
                differentiating_features=_string_list(item.get("differentiating_features")),
                claim_drafting_advice=str(item.get("claim_drafting_advice") or ""),
            )
            charts_by_candidate.setdefault(candidate_id, []).append(chart)
        by_id = {str(item.get("id")): item for item in data.get("hits", []) if isinstance(item, dict)}
        enriched: list[PriorArtHit] = []
        for hit in hits:
            patch = by_id.get(hit.id, {})
            enriched.append(
                hit.model_copy(
                    update={
                        "relevance_summary": str(patch.get("relevance_summary") or hit.relevance_summary),
                        "differentiators": _string_list(patch.get("differentiators")) or hit.differentiators,
                    }
                )
            )
        if not any(charts_by_candidate.values()):
            unverified_note = (
                "已检索到公开现有技术，但模型未形成可绑定 Claim Chart；"
                "差异结论需人工复核后才能用于查新判断。"
            )
            return [
                hit.model_copy(update={"differentiators": []})
                for hit in enriched
            ], unverified_note, {}
        return enriched, str(data.get("prior_art_differences") or "与公开文献的区别已在交底书正文中进一步展开。"), charts_by_candidate


def _search_prior_art_with_ledger(
    prior_art_provider: PriorArtProvider,
    terms: list[str],
    max_prior_art_results: int,
    ledger: SourceLedger,
) -> tuple[list[PriorArtHit], list[str]]:
    search_with_ledger = getattr(prior_art_provider, "search_with_ledger", None)
    if callable(search_with_ledger):
        return search_with_ledger(terms, max_prior_art_results, ledger)

    search_entry = ledger.start(provider="prior_art", kind="prior_art", query="; ".join(terms[:4]))
    hits, warnings = prior_art_provider.search(terms, max_prior_art_results)
    search_entry.mark_ok(
        hit_count=len(hits),
        parsed_count=len(hits),
        dedupe_count=0,
        retained_count=len(hits),
        citations=[citation_snapshot(hit) for hit in hits],
    )
    return hits, warnings


def _checkpoint_stage(
    stage_results: list[dict[str, Any]],
    runtime: RuntimeContext | None,
    on_stage_result: Any | None,
    *,
    warning_count: int = 0,
) -> None:
    if on_stage_result:
        on_stage_result(list(stage_results))
    if runtime:
        runtime.complete_stage(partial_artifact_count=len(stage_results), warning_count=warning_count)


INVENTION_SYSTEM_PROMPT = (
    "你是中国发明专利技术交底书撰写助手，面向AI/软件方法类中国发明专利。"
    "输出用于代理人/律师进一步审查，不替代正式法律意见。"
    "必须使用技术特征、步骤、模块、数据流和技术效果表达，避免商业宣传。"
)

UTILITY_MODEL_SYSTEM_PROMPT = (
    "你是中国实用新型专利技术交底书撰写助手，面向产品结构、装置构造、部件连接关系和空间布局。"
    "输出用于代理人/律师进一步审查，不替代正式法律意见。"
    "必须使用结构件、连接/安装/配合关系、附图标号和结构效果表达，避免商业宣传。"
    "不得把纯方法步骤、算法流程、软件介质或商业规则作为独立保护主题。"
)


def _system_prompt(project: ProjectRecord) -> str:
    return UTILITY_MODEL_SYSTEM_PROMPT if is_utility_model_project(project) else INVENTION_SYSTEM_PROMPT


def _scan_prompt(project: ProjectRecord, materials: str) -> str:
    return f"""请扫描项目 draft 与补充材料，输出 JSON object：
{{
  "summary": "项目技术摘要",
  "materials_summary": "材料覆盖情况",
  "technical_keywords": ["关键词"],
  "implementation_gaps": ["缺口"]
}}

项目：{project.name}
结构化项目元数据：
{format_project_metadata_block(project)}
Draft：
{project.draft_text}

材料：
{materials}
"""


def _points_prompt(project: ProjectRecord, materials: str, scan: dict, context: str, strategic_context: str) -> str:
    if is_utility_model_project(project):
        return f"""请生成 3-5 个可申请中国实用新型专利的候选结构点，并推荐一个最适合作为交底书主线的方案。
候选必须落在产品/装置/组件结构、部件连接关系、安装位置、空间布局或结构改进上；不得把纯算法、纯方法流程或业务规则作为独立保护主题。
如果存在用户指定专利点，必须保留这些专利点，但应把可保护主线提炼为结构件及连接/配合关系，并补充 support_gaps、drawing_needed 和 rationale。
严格输出 JSON object：
{{
  "candidates": [
    {{
      "id": "p1",
      "title": "候选结构名称",
      "technical_problem": "结构类技术问题",
      "innovation": "结构改进点",
      "technical_solution": "部件组成、连接关系、安装位置和配合方式",
      "beneficial_effects": ["结构效果"],
      "protection_focus": ["结构", "部件", "连接关系", "附图"],
      "grantability_score": 0.8,
      "rationale": "推荐理由"
    }}
  ],
  "selected_candidate_id": "p1"
}}

项目：{project.name}
结构化项目元数据：
{format_project_metadata_block(project)}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
用户指定专利点：
{strategic_context}
材料：{materials}
相似授权专利片段：{context}
"""
    return f"""请生成 3-5 个可申请中国发明专利的候选专利点，并推荐一个最适合作为交底书主线的方案。
如果存在用户指定专利点，必须保留这些专利点，不得因为证据状态为 feasible_unverified 而删除；可以补充 support_gaps、experiment_needed 和 rationale。
严格输出 JSON object：
{{
  "candidates": [
    {{
      "id": "p1",
      "title": "候选名称",
      "technical_problem": "技术问题",
      "innovation": "创新点",
      "technical_solution": "技术方案",
      "beneficial_effects": ["技术效果"],
      "protection_focus": ["方法", "系统"],
      "grantability_score": 0.8,
      "rationale": "推荐理由"
    }}
  ],
  "selected_candidate_id": "p1"
}}

项目：{project.name}
结构化项目元数据：
{format_project_metadata_block(project)}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
用户指定专利点：
{strategic_context}
材料：{materials}
相似授权专利片段：{context}
"""


def _terms_prompt(
    project: ProjectRecord,
    candidates: list[PatentPointCandidate],
    selected_id: str | None,
    scan: dict,
    strategic_context: str,
) -> str:
    selected = _selected_candidate(candidates, selected_id)
    if is_utility_model_project(project):
        return f"""请把推荐结构点拆成 2-8 个用于公开专利检索的语义检索词，优先包含产品名称、结构件、连接关系和安装方式，避免整段长句。
只输出 JSON array，例如 ["外立面 挂接 连接结构", "传感器 模块 安装支架"]。

项目：{project.name}
结构化项目元数据：
{format_project_metadata_block(project)}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
用户指定专利点：
{strategic_context}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
"""
    return f"""请把推荐专利点拆成 2-8 个用于公开专利检索的语义检索词，优先短语，避免整段长句。
只输出 JSON array，例如 ["神经网络 缺陷 检测", "图像 质量 评估"]。

项目：{project.name}
结构化项目元数据：
{format_project_metadata_block(project)}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
用户指定专利点：
{strategic_context}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
"""


def _relevance_prompt(
    project: ProjectRecord,
    candidates: list[PatentPointCandidate],
    selected_id: str | None,
    hits: list[PriorArtHit],
    deep_research_context: str,
) -> str:
    selected = _selected_candidate(candidates, selected_id)
    return f"""请基于公开现有技术结果，概括每篇文献与推荐专利点的相关性和差异。
凡公开结果含 abstract，必须基于 abstract 概括方案要点、局限和区别，禁止仅凭标题判断。
严格输出 JSON object：
{{
  "prior_art_differences": "总体区别段落",
  "hits": [
    {{"id": "命中id", "relevance_summary": "相关性摘要", "differentiators": ["区别点"]}}
  ],
  "claim_charts": [
    {{
      "candidate_id": "候选专利点id",
      "prior_art_id": "命中id",
      "prior_art_title": "现有技术标题",
      "overlapping_features": ["重合技术特征"],
      "differentiating_features": ["区别技术特征"],
      "claim_drafting_advice": "权利要求规避建议"
    }}
  ]
}}

项目：{project.name}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
DeepResearch 内部材料：
{deep_research_context or "无"}
公开结果：
{json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False, indent=2)}
"""


def _body_prompt(
    project: ProjectRecord,
    materials: str,
    scan: dict,
    candidates: list[PatentPointCandidate],
    selected_id: str | None,
    hits: list[PriorArtHit],
    differences: str,
) -> str:
    selected = _selected_candidate(candidates, selected_id)
    if is_utility_model_project(project):
        return f"""请生成完整中文实用新型技术交底书 Markdown。
必须包含：
1. 注意事项
2. 一、相关技术背景，包括 1.1 最接近现有结构和公开 URL、1.2 现有结构缺点
3. 二、要解决的结构类技术问题
4. 三、详细结构方案，包括部件组成、各部件连接/安装/配合关系、空间布局、可选材料或尺寸范围
5. 四、相对于现有技术的结构效果
6. 五、附图方案和建议标号，至少列出整体结构图、局部放大图或剖视/爆炸图
7. 六、建议保护点、可选实施例、变形结构和补充材料需求

正文应以装置/结构为主线，不得把方法流程、算法公式或软件介质写成独立保护主题。

项目：{project.name}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
材料：{materials}
公开现有技术：{json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False, indent=2)}
总体区别：{differences}
"""
    return f"""请生成完整中文技术交底书 Markdown。
必须包含：
1. 注意事项
2. 一、相关技术背景，包括 1.1 最接近现有技术和公开 URL、1.2 现有技术缺点
3. 二、要解决的技术问题
4. 三、详细技术方案，包括系统结构、模块功能、方法流程、关键参数/数据结构
5. 四、相对于现有技术的有益效果
6. 五、技术关键点和建议保护点
7. 六、可选实施例、变形例和补充材料需求

项目：{project.name}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
扫描摘要：{json.dumps(scan, ensure_ascii=False)}
材料：{materials}
公开现有技术：{json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False, indent=2)}
总体区别：{differences}
"""


def _mermaid_prompt(project: ProjectRecord, candidates: list[PatentPointCandidate], selected_id: str | None, body: str) -> str:
    selected = _selected_candidate(candidates, selected_id)
    if is_utility_model_project(project):
        return f"""请输出可渲染 Mermaid 代码，包含一个 flowchart TD，展示推荐结构点的部件组成、连接关系和安装位置。只输出 Mermaid 代码，不输出方法流程。

项目：{project.name}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
交底书正文摘录：
{body[:3000]}
"""
    return f"""请输出可渲染 Mermaid 代码，包含一个 flowchart TD，展示推荐专利点的方法流程或系统结构。只输出 Mermaid 代码。

项目：{project.name}
推荐专利点：{selected.model_dump_json(ensure_ascii=False) if selected else ""}
交底书正文摘录：
{body[:3000]}
"""


def _image_prompt(project: ProjectRecord, mermaid: str) -> str:
    if is_utility_model_project(project):
        return f"""请为实用新型专利附图生成绘图提示词，要求黑白线稿、无装饰，突出产品整体结构、局部连接关系、安装位置和必要标号，适合摘要附图或说明书附图。

项目：{project.name}
Mermaid：
{mermaid}
"""
    return f"""请为专利摘要图/流程图生成绘图提示词，要求黑白线稿、无装饰、模块和箭头清晰、适合专利附图。

项目：{project.name}
Mermaid：
{mermaid}
"""


def _self_check_prompt(project: ProjectRecord, body: str, mermaid: str, hits: list[PriorArtHit]) -> str:
    if is_utility_model_project(project):
        return f"""请对以下实用新型技术交底书做内部自检，仅输出 JSON array。
每项包含 category、severity(low|medium|high)、message、suggestion。
重点检查：是否以结构/装置为主线、部件连接关系是否清楚、附图标号是否可补、术语一致、现有结构 URL、结构效果、可选实施例缺口、Mermaid 是否表达结构关系。

项目：{project.name}
交底书：
{body[:8000]}

Mermaid：
{mermaid}

公开现有技术：
{json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False)}
"""
    return f"""请对以下技术交底书做内部自检，仅输出 JSON array。
每项包含 category、severity(low|medium|high)、message、suggestion。
重点检查：逻辑闭环、术语一致、现有技术 URL、摘要使用、技术效果、实施例缺口、Mermaid 可渲染性。

项目：{project.name}
交底书：
{body[:8000]}

Mermaid：
{mermaid}

公开现有技术：
{json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False)}
"""


def _format_materials(project: ProjectRecord, materials: list[ProjectMaterial]) -> str:
    blocks = [f"## Draft\n{project.draft_text}"]
    for material in materials:
        if material.status != "processed":
            blocks.append(f"## {material.file_name}\n材料解析失败：{'；'.join(material.warnings)}")
            continue
        blocks.append(f"## {material.file_name}\n{material.text[:6000]}")
    return "\n\n".join(blocks)


def _format_deep_research_prompt_context(packets: list[Any]) -> str:
    if not packets:
        return ""
    packet_blocks: list[str] = []
    for index, packet in enumerate(packets, start=1):
        packet_hits = packet_prior_art_hits(packet)
        lines = [f"## DeepResearch 补充线索 {index}"]
        if packet_hits:
            lines.append("现有技术线索：")
            for hit in packet_hits:
                detail_parts = [
                    part
                    for part in (
                        hit.publication_number,
                        hit.title,
                        hit.url,
                        hit.abstract or hit.relevance_summary,
                    )
                    if part
                ]
                lines.append(f"- {' | '.join(detail_parts)}")
        if packet.differentiators:
            lines.append("关键差异点：")
            lines.extend(f"- {item}" for item in packet.differentiators)
        if packet.claim_drafting_constraints:
            lines.append("权利要求约束：")
            lines.extend(f"- {item}" for item in packet.claim_drafting_constraints)
        if packet.suggested_completion_tasks:
            lines.append("技术补充待办：")
            lines.extend(f"- {item}" for item in packet.suggested_completion_tasks)
        if len(lines) > 1:
            packet_blocks.append("\n".join(lines))
    return "\n\n".join(packet_blocks)


def _merge_context_blocks(base: str, extra: str) -> str:
    if not extra.strip():
        return base
    if not base.strip():
        return extra
    return f"{base}\n\n{extra}"


def _format_context(chunks: list[PatentChunk]) -> str:
    if not chunks:
        return "无可用相似授权专利片段。"
    return "\n\n".join(
        f"[{index}] {chunk.section_type.value} / {chunk.metadata.get('title', chunk.document_id)}\n{chunk.text[:1200]}"
        for index, chunk in enumerate(chunks, start=1)
    )


def _format_user_candidates(candidates: list[PatentPointCandidate]) -> str:
    if not candidates:
        return "无用户指定专利点。"
    return json.dumps([candidate.model_dump(mode="json") for candidate in candidates], ensure_ascii=False, indent=2)


def _fallback_scan(project: ProjectRecord, materials: list[ProjectMaterial]) -> dict[str, Any]:
    return {
        "summary": project.draft_text[:300],
        "materials_summary": _materials_summary(materials),
        "technical_keywords": _fallback_keywords(project.draft_text),
        "implementation_gaps": [],
    }


def _materials_summary(materials: list[ProjectMaterial]) -> str:
    if not materials:
        return "未上传补充项目材料，仅基于项目 draft。"
    ok = sum(1 for material in materials if material.status == "processed")
    return f"已上传 {len(materials)} 份材料，其中 {ok} 份可解析。"


def _parse_candidates(raw: str, project: ProjectRecord, *, utility_model: bool = False) -> tuple[list[PatentPointCandidate], str | None]:
    data = _json_object(raw, {})
    items = data.get("candidates") if isinstance(data, dict) else None
    candidates: list[PatentPointCandidate] = []
    if isinstance(items, list):
        for index, item in enumerate(items[:5], start=1):
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("id") or f"p{index}")
            candidates.append(
                PatentPointCandidate(
                    id=candidate_id,
                    title=str(item.get("title") or f"{project.name}相关专利点{index}"),
                    technical_problem=str(item.get("technical_problem") or "现有技术存在处理效率或准确性不足的问题。"),
                    innovation=str(item.get("innovation") or item.get("technical_solution") or project.draft_text[:200]),
                    technical_solution=str(item.get("technical_solution") or project.draft_text[:400]),
                    beneficial_effects=_string_list(item.get("beneficial_effects")),
                    protection_focus=_string_list(item.get("protection_focus")) or (
                        ["结构", "部件", "连接关系"] if utility_model else []
                    ),
                    grantability_score=_float(item.get("grantability_score")),
                    rationale=str(item.get("rationale") or ""),
                )
            )
    if not candidates:
        if utility_model:
            candidates = [
                PatentPointCandidate(
                    id="p1",
                    title=f"{project.name}结构",
                    technical_problem="现有结构中部件连接、安装或维护便利性不足。",
                    innovation=project.draft_text[:200],
                    technical_solution=project.draft_text[:500],
                    beneficial_effects=["提高结构稳定性", "降低装配和维护难度"],
                    protection_focus=["结构", "部件", "连接关系", "附图"],
                    grantability_score=0.5,
                    rationale="基于项目 draft 自动生成的保守实用新型候选。",
                )
            ]
        else:
            candidates = [
                PatentPointCandidate(
                    id="p1",
                    title=f"{project.name}方法及系统",
                    technical_problem="现有技术中相关处理流程自动化和专利表达支撑不足。",
                    innovation=project.draft_text[:200],
                    technical_solution=project.draft_text[:500],
                    beneficial_effects=["提升处理流程完整性", "降低人工整理遗漏风险"],
                    protection_focus=["方法", "系统"],
                    grantability_score=0.5,
                    rationale="基于项目 draft 自动生成的保守候选。",
                )
            ]
    selected_id = str(data.get("selected_candidate_id") or candidates[0].id)
    if selected_id not in {candidate.id for candidate in candidates}:
        selected_id = candidates[0].id
    return candidates, selected_id


def _merge_candidates(
    user_candidates: list[PatentPointCandidate],
    generated: list[PatentPointCandidate],
    generated_selected_id: str | None,
) -> tuple[list[PatentPointCandidate], str | None]:
    merged: list[PatentPointCandidate] = []
    seen: set[str] = set()
    for candidate in user_candidates:
        if candidate.id in seen:
            continue
        patched = candidate
        if candidate.evidence_status in {"feasible_unverified", "needs_experiment"} and not candidate.support_gaps:
            patched = candidate.model_copy(update={"support_gaps": ["提交前需补充实验或工程样例。"]})
        merged.append(patched)
        seen.add(patched.id)
    for candidate in generated:
        if candidate.id not in seen:
            merged.append(candidate)
            seen.add(candidate.id)
    selected_user = next((candidate for candidate in merged if candidate.selected), None)
    if selected_user:
        return merged, selected_user.id
    if generated_selected_id in seen:
        return merged, generated_selected_id
    return merged, merged[0].id if merged else None


def _parse_terms(raw: str, project: ProjectRecord) -> list[str]:
    parsed: Any
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, dict):
        parsed = parsed.get("terms", [])
    terms = [str(item).strip() for item in parsed if str(item).strip()] if isinstance(parsed, list) else []
    if len(terms) < 2:
        terms = _fallback_keywords(f"{project.name} {project.draft_text}")
    return terms[:8]


def _parse_self_check(raw: str) -> list[DisclosureSelfCheckFinding]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = []
    if isinstance(parsed, dict):
        parsed = parsed.get("findings", [])
    findings: list[DisclosureSelfCheckFinding] = []
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "medium")
            if severity not in {"low", "medium", "high"}:
                severity = "medium"
            findings.append(
                DisclosureSelfCheckFinding(
                    category=str(item.get("category") or "自检"),
                    severity=severity,
                    message=str(item.get("message") or "模型未给出明确说明。"),
                    suggestion=str(item.get("suggestion") or "请人工复核。"),
                )
            )
    return findings


def _json_object(raw: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return fallback
    return parsed if isinstance(parsed, dict) else fallback


def _fallback_keywords(text: str) -> list[str]:
    keywords: list[str] = []
    for keyword in ["神经网络", "图像", "缺陷", "检索", "生成", "训练", "审核", "流程", "模型", "数据"]:
        if keyword in text:
            keywords.append(keyword)
    if len(keywords) < 2:
        words = [word for word in re_split_words(text) if len(word) >= 2]
        keywords.extend(words[:4])
    terms = [" ".join(keywords[index : index + 3]) for index in range(0, min(len(keywords), 6), 3)]
    terms = [term for term in terms if term.strip()]
    if len(terms) >= 2:
        return terms
    seed = text[:30] or "人工智能 软件 方法"
    return [seed, "人工智能 软件 方法"]


def re_split_words(text: str) -> list[str]:
    return [part for part in "".join(char if char.isalnum() else " " for char in text).split() if part]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _prior_art_title(hit: PriorArtHit) -> str:
    return hit.title or hit.publication_number or hit.id


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _selected_candidate(candidates: list[PatentPointCandidate], selected_id: str | None) -> PatentPointCandidate | None:
    for candidate in candidates:
        if candidate.id == selected_id:
            return candidate
    return candidates[0] if candidates else None


def _disclosure_title(project: ProjectRecord, candidates: list[PatentPointCandidate], selected_id: str | None) -> str:
    selected = _selected_candidate(candidates, selected_id)
    if selected:
        return selected.title
    return f"{project.name}技术交底书"
