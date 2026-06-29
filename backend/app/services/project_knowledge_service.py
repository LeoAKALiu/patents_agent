from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from backend.app.schemas import (
    AgentSearchPlan,
    CorpusQualityReport,
    PatentPointCandidate,
    PriorArtCandidate,
    ProjectCorpusVersion,
    ProjectKnowledgeOverview,
    ProjectKnowledgeState,
    ProjectRecord,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore


ZH_STOPWORDS = {"一种", "方法", "系统", "装置", "基于", "用于", "通过", "以及", "进行", "生成"}


class ProjectKnowledgeConflictError(ValueError):
    """Raised when a knowledge mutation targets a stale or inactive artifact."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hex(*parts: str) -> str:
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_snapshot_hash(project: ProjectRecord, patent_points: list[PatentPointCandidate] | None = None) -> str:
    parts = [
        project.name,
        project.draft_text,
        project.technical_field,
        project.background,
        project.pain_point,
        project.technical_solution,
        project.innovation,
        project.beneficial_effects,
    ]
    for point in patent_points or []:
        if point.selected:
            parts.extend([point.title, point.technical_problem, point.innovation, point.technical_solution])
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _selected_patent_points(patent_points: list[PatentPointCandidate] | None = None) -> list[PatentPointCandidate]:
    return [point for point in patent_points or [] if point.selected]


def _extract_keywords(text: str, *, limit: int = 8) -> list[str]:
    normalized = re.sub(r"[，。、“”《》；：:,.()\[\]{}]", " ", text)
    tokens: list[str] = []
    fallback_phrases = ["城市体检", "智能体", "任务编排", "证据链", "可信复核"]
    for phrase in fallback_phrases:
        if phrase in text and phrase not in tokens:
            tokens.append(phrase)
    for raw in normalized.split():
        cleaned = raw.strip()
        if not cleaned or cleaned in ZH_STOPWORDS:
            continue
        if len(cleaned) >= 2 and cleaned not in tokens:
            tokens.append(cleaned)
        if len(tokens) >= limit:
            break
    return tokens[:limit]


def _build_intent(
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate] | None = None,
) -> SearchIntent:
    selected_points = _selected_patent_points(patent_points)
    point_parts: list[str] = []
    for point in selected_points:
        point_parts.extend(
            [
                point.title,
                point.technical_problem,
                point.innovation,
                point.technical_solution,
            ]
        )
    source_text = "\n".join(
        [
            project.name,
            project.draft_text,
            project.technical_field,
            project.pain_point,
            project.technical_solution,
            project.innovation,
            project.beneficial_effects,
            *point_parts,
        ]
    )
    keywords_zh = _extract_keywords(source_text)
    primary_point = selected_points[0] if selected_points else None
    primary_point_problem = primary_point.technical_problem if primary_point else ""
    primary_point_solution = primary_point.technical_solution if primary_point else ""
    primary_point_innovation = primary_point.innovation if primary_point else ""
    return SearchIntent(
        id=uuid.uuid4().hex,
        project_id=project.id,
        source_project_hash=project_snapshot_hash(project, patent_points),
        technical_object=project.name,
        technical_problem=(
            project.pain_point
            or primary_point_problem
            or project.background
            or "现有方案缺少自动化任务拆解和可信复核。"
        ),
        technical_means=(
            project.technical_solution
            or primary_point_solution
            or project.innovation
            or primary_point_innovation
            or project.draft_text
        ),
        technical_effect=project.beneficial_effects or "提高处理效率和结果可信度。",
        keywords_zh=keywords_zh,
        keywords_en=["urban health", "agent", "task orchestration", "evidence review"],
        synonyms=["城市诊断", "城市运行体检", "多智能体编排", *[point.title for point in selected_points[:2]]],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q", "G06F"],
        cpc_candidates=["G06Q10/063", "G06F16/35"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
        created_by="agent",
        created_at=_now(),
    )


def _build_plan(intent: SearchIntent) -> AgentSearchPlan:
    core_query = " ".join(intent.keywords_zh[:4]) or intent.technical_object
    closest_query = " ".join([*intent.keywords_zh[:2], "证据链", "复核"]).strip()
    return AgentSearchPlan(
        id=uuid.uuid4().hex,
        project_id=intent.project_id,
        intent_id=intent.id,
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全相关技术方向的公开和授权专利。",
                queries=[core_query],
                sources=["fake"],
            ),
            SearchPlanStrategyGroup(
                id="closest-prior-art",
                label="最接近现有技术检索",
                purpose="寻找可用于新颖性和创造性对比的高相关文献。",
                queries=[closest_query or core_query],
                sources=["fake"],
            ),
        ],
        target_sources=["fake"],
        target_result_count=20,
        filters={"jurisdictions": intent.jurisdictions, "date_range": intent.date_range},
        created_at=_now(),
    )


def _get_active_plan(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
) -> tuple[ProjectKnowledgeState, AgentSearchPlan]:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    plan = store.get_agent_search_plan(project_id, plan_id)
    if plan is None:
        raise ValueError("Agent search plan not found.")
    if not state.active_plan_id or state.active_plan_id != plan_id:
        raise ProjectKnowledgeConflictError("Agent search plan is no longer active for this project.")
    return state, plan


def knowledge_overview(store: SQLiteStore, project_id: str) -> ProjectKnowledgeOverview:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    latest_plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, latest_plan.id if latest_plan else None)
    latest_corpus_version = None
    if state.active_corpus_version_id:
        latest_corpus_version = store.get_project_corpus_version(project_id, state.active_corpus_version_id)
    return ProjectKnowledgeOverview(
        state=state,
        latest_intent=store.get_latest_search_intent(project_id),
        latest_plan=latest_plan,
        candidates=candidates,
        latest_corpus_version=latest_corpus_version,
    )


def regenerate_project_knowledge(
    store: SQLiteStore,
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate] | None = None,
) -> ProjectKnowledgeOverview:
    intent = store.create_search_intent(_build_intent(project, patent_points))
    plan = store.create_agent_search_plan(_build_plan(intent))
    existing = store.get_project_knowledge_state(project.id) or ProjectKnowledgeState(project_id=project.id)
    state = existing.model_copy(
        update={
            "status": "search_plan_pending",
            "active_intent_id": intent.id,
            "active_plan_id": plan.id,
            "active_corpus_version_id": "",
            "last_search_at": "",
            "last_indexed_at": "",
            "staleness_reason": "",
            "document_count": 0,
            "candidate_count": 0,
            "claim_coverage": 0.0,
            "fulltext_coverage": 0.0,
            "quality_flags": ["needs_search"],
        }
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project.id)


def ensure_project_knowledge_initialized(store: SQLiteStore, project: ProjectRecord) -> ProjectKnowledgeOverview:
    existing = store.get_project_knowledge_state(project.id)
    if existing and existing.status != "not_started":
        return knowledge_overview(store, project.id)
    return regenerate_project_knowledge(store, project, [])


def run_agent_search_plan(store: SQLiteStore, project_id: str, plan_id: str) -> ProjectKnowledgeOverview:
    _state, plan = _get_active_plan(store, project_id, plan_id)
    running = plan.model_copy(update={"status": "running", "run_started_at": _now()})
    store.update_agent_search_plan(running)
    candidates: list[PriorArtCandidate] = []
    for index, group in enumerate(running.strategy_groups, start=1):
        query = group.queries[0] if group.queries else group.label
        publication_number = f"CN{100000000 + index}A"
        candidate = PriorArtCandidate(
            id=_stable_hex(project_id, plan_id, group.id),
            project_id=project_id,
            plan_id=plan_id,
            source="fake",
            title=f"{group.label}候选文献{index}",
            publication_number=publication_number,
            applicant="示例申请人",
            publication_date="2024-01-01",
            abstract=f"围绕{query}公开了相关技术方案。",
            url=f"https://patents.google.com/patent/{publication_number}",
            relevance_score=0.82,
            matched_terms=query.split(),
            fulltext_status="available",
            recommended_action="include",
            recommendation_reason="命中检索计划中的核心查询。",
            metadata={"query": query, "strategy_group": group.id},
        )
        candidates.append(store.upsert_prior_art_candidate(candidate))
    completed = running.model_copy(update={"status": "completed", "run_finished_at": _now()})
    store.update_agent_search_plan(completed)
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="candidates_pending",
        active_intent_id=completed.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(store.list_prior_art_candidates(project_id, plan_id)),
        quality_flags=["candidates_need_confirmation"],
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project_id)


def create_project_corpus_from_included_candidates(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
) -> ProjectKnowledgeOverview:
    _state, _plan = _get_active_plan(store, project_id, plan_id)
    included = [
        candidate
        for candidate in store.list_prior_art_candidates(project_id, plan_id)
        if candidate.user_decision == "include"
    ]
    all_synthetic = bool(included) and all(candidate.source == "fake" for candidate in included)
    claim_coverage = 0.0 if all_synthetic else (1.0 if included else 0.0)
    fulltext_coverage = 0.0 if all_synthetic else (1.0 if included else 0.0)
    quality_flags = ["synthetic_evidence"] if all_synthetic else []
    version = ProjectCorpusVersion(
        id=uuid.uuid4().hex,
        project_id=project_id,
        name=f"{project_id}-prior-art-v1",
        source_plan_id=plan_id,
        status="ready" if included else "failed",
        document_count=len(included),
        chunk_count=len(included) * 3,
        claim_coverage=claim_coverage,
        fulltext_coverage=fulltext_coverage,
        quality_report=CorpusQualityReport(
            total_files=len(included),
            processed_files=len(included),
            imported_documents=len(included),
            indexed_chunks=len(included) * 3,
            fulltext_extractable_rate=0.0 if all_synthetic else (1.0 if included else 0.0),
            section_coverage={"claims": claim_coverage, "fulltext": fulltext_coverage},
            low_quality_documents=[candidate.id for candidate in included] if all_synthetic else [],
            failures=(
                [{"code": "synthetic_evidence", "message": "Corpus built from synthetic fake-source candidates only."}]
                if all_synthetic
                else []
            ),
        ),
        created_at=_now(),
    )
    store.create_project_corpus_version(version)
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="ready" if included else "needs_supplemental_search",
        active_plan_id=plan_id,
        active_corpus_version_id=version.id,
        last_indexed_at=_now(),
        document_count=version.document_count,
        candidate_count=len(store.list_prior_art_candidates(project_id, plan_id)),
        claim_coverage=version.claim_coverage,
        fulltext_coverage=version.fulltext_coverage,
        quality_flags=quality_flags if included else ["empty_corpus"],
    )
    store.upsert_project_knowledge_state(state)
    return knowledge_overview(store, project_id)


def mark_stale_if_project_changed(
    store: SQLiteStore,
    project: ProjectRecord,
    patent_points: list[PatentPointCandidate],
) -> ProjectKnowledgeState:
    state = store.get_project_knowledge_state(project.id) or ProjectKnowledgeState(project_id=project.id)
    intent = store.get_latest_search_intent(project.id)
    if not intent:
        return state
    current_hash = project_snapshot_hash(project, patent_points)
    if current_hash == intent.source_project_hash:
        return state
    updated = state.model_copy(
        update={
            "status": "stale",
            "staleness_reason": "项目技术描述已变化，需要重新生成检索计划或补充检索。",
            "quality_flags": sorted(set([*state.quality_flags, "stale_project_snapshot"])),
        }
    )
    return store.upsert_project_knowledge_state(updated)
