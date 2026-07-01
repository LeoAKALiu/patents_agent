from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from backend.app.knowledge.patent_search import (
    PatentSearchProvider,
    default_project_patent_providers,
    patent_hit_to_candidate,
    run_provider_chain,
)
from backend.app.schemas import (
    AgentSearchPlan,
    CorpusQualityReport,
    PatentPointCandidate,
    PatentSearchFilters,
    PriorArtCandidate,
    ProjectSearchLedger,
    ProjectCorpusVersion,
    ProjectKnowledgeOverview,
    ProjectKnowledgeState,
    ProjectRecord,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore


ZH_STOPWORDS = {"一种", "方法", "系统", "装置", "基于", "用于", "通过", "以及", "进行", "生成"}
PROJECT_PATENT_PROVIDER_SOURCES = ["cnipa_epub", "wipo_patentscope"]
PROJECT_PATENT_CORPUS_SOURCES = [*PROJECT_PATENT_PROVIDER_SOURCES, "google_patents"]
PROJECT_PATENT_PROVIDER_SOURCE_SET = frozenset(PROJECT_PATENT_CORPUS_SOURCES)


class ProjectKnowledgeConflictError(ValueError):
    """Raised when a knowledge mutation targets a stale or inactive artifact."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_candidate_decision(decision: str) -> None:
    if decision not in {"pending", "include", "exclude"}:
        raise ValueError(f"invalid prior art candidate decision: {decision!r}")


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
                sources=list(PROJECT_PATENT_PROVIDER_SOURCES),
            ),
            SearchPlanStrategyGroup(
                id="closest-prior-art",
                label="最接近现有技术检索",
                purpose="寻找可用于新颖性和创造性对比的高相关文献。",
                queries=[closest_query or core_query],
                sources=list(PROJECT_PATENT_PROVIDER_SOURCES),
            ),
        ],
        target_sources=list(PROJECT_PATENT_PROVIDER_SOURCES),
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
    if state.status == "stale":
        raise ProjectKnowledgeConflictError(
            "Project knowledge is stale and must be regenerated before reusing this search plan."
        )
    if not state.active_plan_id or state.active_plan_id != plan_id:
        raise ProjectKnowledgeConflictError("Agent search plan is no longer active for this project.")
    return state, plan


def _get_mutable_candidate_set(
    store: SQLiteStore,
    project_id: str,
    candidate_ids: list[str],
) -> tuple[ProjectKnowledgeState, list[PriorArtCandidate]]:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    if state.status == "stale":
        raise ProjectKnowledgeConflictError(
            "Project knowledge is stale and must be regenerated before changing candidate decisions."
        )
    if state.status not in {"candidates_pending", "needs_supplemental_search", "ready"} or not state.active_plan_id:
        raise ProjectKnowledgeConflictError(
            "Project knowledge is not active for candidate decisions and must be regenerated or rerun first."
        )

    candidates_by_id = {
        candidate.id: candidate
        for candidate in store.list_prior_art_candidates(project_id)
    }
    missing_id = next((candidate_id for candidate_id in candidate_ids if candidate_id not in candidates_by_id), "")
    if missing_id:
        raise ValueError(f"Prior-art candidate not found: {missing_id}")

    candidates = [candidates_by_id[candidate_id] for candidate_id in candidate_ids]
    stale_id = next(
        (candidate.id for candidate in candidates if candidate.plan_id != state.active_plan_id),
        "",
    )
    if stale_id:
        raise ProjectKnowledgeConflictError(
            "Prior-art candidate no longer belongs to the active search plan for this project."
        )
    return state, candidates


def _candidate_mutation_followup_state(
    state: ProjectKnowledgeState,
    *,
    candidate_count: int,
    decision_changed: bool,
) -> ProjectKnowledgeState | None:
    if not decision_changed or not state.active_corpus_version_id:
        return None
    return state.model_copy(
        update={
            "status": "candidates_pending",
            "active_corpus_version_id": "",
            "last_indexed_at": "",
            "staleness_reason": "",
            "document_count": 0,
            "candidate_count": candidate_count,
            "claim_coverage": 0.0,
            "fulltext_coverage": 0.0,
            "quality_flags": ["candidates_need_confirmation"],
        }
    )


def update_project_candidate_decision(
    store: SQLiteStore,
    project_id: str,
    candidate_id: str,
    decision: str,
) -> PriorArtCandidate:
    _validate_candidate_decision(decision)
    state, candidates = _get_mutable_candidate_set(store, project_id, [candidate_id])
    candidate = candidates[0]
    updated = candidate.model_copy(update={"user_decision": decision})
    followup_state = _candidate_mutation_followup_state(
        state,
        candidate_count=len(store.list_prior_art_candidates(project_id, state.active_plan_id)),
        decision_changed=candidate.user_decision != decision,
    )
    store.apply_prior_art_candidate_updates([updated], followup_state)
    return updated


def bulk_update_project_candidate_decisions(
    store: SQLiteStore,
    project_id: str,
    candidate_ids: list[str],
    decision: str,
) -> list[PriorArtCandidate]:
    _validate_candidate_decision(decision)
    state, candidates = _get_mutable_candidate_set(store, project_id, candidate_ids)
    updated = [candidate.model_copy(update={"user_decision": decision}) for candidate in candidates]
    followup_state = _candidate_mutation_followup_state(
        state,
        candidate_count=len(store.list_prior_art_candidates(project_id, state.active_plan_id)),
        decision_changed=any(candidate.user_decision != decision for candidate in candidates),
    )
    store.apply_prior_art_candidate_updates(updated, followup_state)
    return updated


def knowledge_overview(store: SQLiteStore, project_id: str) -> ProjectKnowledgeOverview:
    state = store.get_project_knowledge_state(project_id) or ProjectKnowledgeState(project_id=project_id)
    latest_plan = store.get_latest_agent_search_plan(project_id)
    candidates = store.list_prior_art_candidates(project_id, latest_plan.id if latest_plan else None)
    latest_corpus_version = None
    if state.status != "stale" and state.active_corpus_version_id:
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


def run_patent_search_plan(
    provider_chain: list[PatentSearchProvider],
    project_id: str,
    plan: AgentSearchPlan,
) -> tuple[list[PriorArtCandidate], ProjectSearchLedger]:
    queries = [
        (group.id, query)
        for group in plan.strategy_groups
        for query in (group.queries or [group.label])
    ]
    filters = PatentSearchFilters.model_validate(plan.filters)
    hits, attempts, warnings = run_provider_chain(
        providers=provider_chain,
        queries=queries,
        filters=filters,
        limit=plan.target_result_count,
    )
    candidates = [
        patent_hit_to_candidate(
            hit,
            project_id=project_id,
            plan_id=plan.id,
            strategy_group_id=str(hit.metadata.get("strategy_group") or "search"),
        )
        for hit in hits
    ]
    ledger = ProjectSearchLedger(
        id=uuid.uuid4().hex,
        project_id=project_id,
        plan_id=plan.id,
        attempts=attempts,
        retained_candidate_ids=[candidate.id for candidate in candidates],
        warnings=warnings,
        created_at=_now(),
    )
    return candidates, ledger


def run_agent_search_plan(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
    providers: list[PatentSearchProvider] | None = None,
) -> ProjectKnowledgeOverview:
    _state, plan = _get_active_plan(store, project_id, plan_id)
    running = plan.model_copy(update={"status": "running", "run_started_at": _now()})
    store.update_agent_search_plan(running)
    provider_chain = list(providers) if providers is not None else default_project_patent_providers()
    candidates, ledger = run_patent_search_plan(provider_chain, project_id, running)
    completed = running.model_copy(
        update={
            "status": "completed" if candidates else "failed",
            "run_finished_at": _now(),
            "warnings": ledger.warnings,
            "metadata": {
                **running.metadata,
                "latest_search_ledger_id": ledger.id,
            },
        }
    )
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="candidates_pending" if candidates else "failed",
        active_intent_id=completed.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(candidates),
        quality_flags=["candidates_need_confirmation"] if candidates else ["no_hits"],
    )
    stored_candidates, _stored_ledger = store.replace_agent_search_run(
        project_id=project_id,
        plan=completed,
        candidates=candidates,
        ledger=ledger,
        state=state,
    )
    return knowledge_overview(store, project_id)


def create_project_corpus_from_included_candidates(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
) -> ProjectKnowledgeOverview:
    state, _plan = _get_active_plan(store, project_id, plan_id)
    candidate_pool = store.list_prior_art_candidates(project_id, plan_id)
    if (
        state.status not in {"candidates_pending", "needs_supplemental_search", "ready"}
        or not state.last_search_at
        or not candidate_pool
    ):
        raise ProjectKnowledgeConflictError(
            "Project knowledge is not ready for corpus build. Run candidate search for the active plan first."
        )
    included = [
        candidate
        for candidate in candidate_pool
        if candidate.user_decision == "include"
    ]
    patent_included = [candidate for candidate in included if candidate.source in PROJECT_PATENT_PROVIDER_SOURCE_SET]
    synthetic_included = [candidate for candidate in included if candidate.source == "fake"]
    non_patent_included = [
        candidate
        for candidate in included
        if candidate.source not in PROJECT_PATENT_PROVIDER_SOURCE_SET and candidate.source != "fake"
    ]
    all_synthetic = bool(included) and len(synthetic_included) == len(included)
    includes_non_patent = bool(non_patent_included)
    patent_ratio = (len(patent_included) / len(included)) if included else 0.0
    if all_synthetic:
        claim_coverage = 0.0
        fulltext_coverage = 0.0
        quality_flags = ["synthetic_evidence"]
    elif includes_non_patent:
        claim_coverage = patent_ratio
        fulltext_coverage = patent_ratio
        quality_flags = ["non_patent_source"]
    else:
        claim_coverage = 1.0 if included else 0.0
        fulltext_coverage = 1.0 if included else 0.0
        quality_flags = []
    non_patent_sources = sorted({candidate.source for candidate in non_patent_included})
    quality_failures: list[dict[str, str]] = []
    if all_synthetic:
        quality_failures.append(
            {"code": "synthetic_evidence", "message": "Corpus built from synthetic fake-source candidates only."}
        )
    if includes_non_patent:
        quality_failures.append(
            {
                "code": "non_patent_source",
                "message": "Corpus includes non-patent sources: " + ", ".join(non_patent_sources),
            }
        )
    corpus_status = "needs_supplemental_search" if (all_synthetic or includes_non_patent) else ("ready" if included else "failed")
    version = ProjectCorpusVersion(
        id=uuid.uuid4().hex,
        project_id=project_id,
        name=f"{project_id}-prior-art-v1",
        source_plan_id=plan_id,
        status=corpus_status,
        document_count=len(included),
        chunk_count=len(included) * 3,
        claim_coverage=claim_coverage,
        fulltext_coverage=fulltext_coverage,
        quality_report=CorpusQualityReport(
            total_files=len(included),
            processed_files=len(included),
            imported_documents=len(included),
            indexed_chunks=len(included) * 3,
            fulltext_extractable_rate=fulltext_coverage,
            section_coverage={"claims": claim_coverage, "fulltext": fulltext_coverage},
            low_quality_documents=(
                [candidate.id for candidate in included]
                if all_synthetic
                else [candidate.id for candidate in non_patent_included]
            ),
            failures=quality_failures,
        ),
        created_at=_now(),
    )
    store.create_project_corpus_version(version)
    state_status = "needs_supplemental_search" if all_synthetic or includes_non_patent or not included else "ready"
    if all_synthetic:
        quality_flags = ["synthetic_evidence"]
    elif includes_non_patent:
        quality_flags = ["non_patent_source"]
    elif included:
        quality_flags = []
    else:
        quality_flags = ["empty_corpus"]
    updated_state = state.model_copy(
        update={
            "status": state_status,
            "active_plan_id": plan_id,
            "active_corpus_version_id": version.id,
            "last_indexed_at": _now(),
            "document_count": version.document_count,
            "candidate_count": len(candidate_pool),
            "claim_coverage": version.claim_coverage,
            "fulltext_coverage": version.fulltext_coverage,
            "quality_flags": quality_flags,
        }
    )
    store.upsert_project_knowledge_state(updated_state)
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
            "active_corpus_version_id": "",
            "staleness_reason": "项目技术描述已变化，需要重新生成检索计划或补充检索。",
            "document_count": 0,
            "claim_coverage": 0.0,
            "fulltext_coverage": 0.0,
            "quality_flags": sorted(set([*state.quality_flags, "stale_project_snapshot"])),
        }
    )
    return store.upsert_project_knowledge_state(updated)
