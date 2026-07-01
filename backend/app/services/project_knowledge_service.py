from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.app.evidence_sources import evidence_source_views
from backend.app.knowledge.cnipa_export import CnipaExportImportContext, parse_cnipa_official_export_file
from backend.app.knowledge.non_patent_search import NonPatentSearchHit, NonPatentSearchProvider, WanfangLiteratureProvider
from backend.app.knowledge.patent_sources import (
    CNIPA_LEGACY_EPUB_SOURCE,
    CNIPA_OFFICIAL_EXPORT_SOURCE,
    GOOGLE_PATENTS_SOURCE,
    WIPO_PATENTSCOPE_SOURCE,
    build_cnipa_query_pack,
)
from backend.app.knowledge.patent_search import (
    PatentSearchProvider,
    default_project_patent_providers,
    patent_hit_to_candidate,
    run_provider_chain,
)
from backend.app.schemas import (
    AgentSearchPlan,
    CnipaQueryPack,
    CorpusQualityReport,
    EvidenceSourceConfig,
    PatentPointCandidate,
    PatentSearchFilters,
    PriorArtCandidate,
    ProviderAttempt,
    ProjectKnowledgeImportLedger,
    ProjectSearchLedger,
    ProjectCorpusVersion,
    ProjectKnowledgeOverview,
    ProjectKnowledgeState,
    ProjectRecord,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore
from backend.app.research.providers import sanitize_untrusted_text


ZH_STOPWORDS = {"一种", "方法", "系统", "装置", "基于", "用于", "通过", "以及", "进行", "生成"}
PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES = [
    "patsnap_api",
    "cnipa_official_export",
    "cnipa_epub",
    "wipo_patentscope",
    "google_patents",
]
PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES = ["wanfang_api"]
PROJECT_PATENT_PROVIDER_SOURCE_SET = frozenset(PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES)
LIVE_PROJECT_PATENT_PROVIDER_SOURCES = frozenset(
    {"patsnap_api", CNIPA_LEGACY_EPUB_SOURCE, WIPO_PATENTSCOPE_SOURCE, GOOGLE_PATENTS_SOURCE}
)
LIVE_PROJECT_NON_PATENT_PROVIDER_SOURCES = frozenset(PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES)
PUBLIC_PROJECT_PATENT_PROVIDER_SOURCES = frozenset({CNIPA_LEGACY_EPUB_SOURCE, WIPO_PATENTSCOPE_SOURCE, GOOGLE_PATENTS_SOURCE})
SOURCE_NOT_IMPLEMENTED_WARNINGS = {
    "patsnap_api": "patsnap_api_live_search_not_implemented",
    "wanfang_api": "wanfang_api_live_search_not_implemented",
}


class ProjectKnowledgeConflictError(ValueError):
    """Raised when a knowledge mutation targets a stale or inactive artifact."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_candidate_decision(decision: str) -> None:
    if decision not in {"pending", "include", "exclude"}:
        raise ValueError(f"invalid prior art candidate decision: {decision!r}")


def _candidate_has_claims(candidate: PriorArtCandidate) -> bool:
    if candidate.source == CNIPA_OFFICIAL_EXPORT_SOURCE and not _candidate_has_cnipa_official_provenance(candidate):
        return False
    return bool(str(candidate.metadata.get("claims") or "").strip())


def _candidate_has_explicit_fulltext_metadata(candidate: PriorArtCandidate) -> bool:
    return any(
        bool(str(candidate.metadata.get(key) or "").strip())
        for key in ("fulltext", "fulltext_text", "fulltext_content")
    )


def _candidate_has_cnipa_official_provenance(candidate: PriorArtCandidate) -> bool:
    metadata = candidate.metadata
    return (
        candidate.source == CNIPA_OFFICIAL_EXPORT_SOURCE
        and str(metadata.get("evidence_origin") or "").strip() == "official_export"
        and bool(str(metadata.get("import_ledger_id") or "").strip())
        and bool(str(metadata.get("raw_file_hash") or "").strip())
    )


def _candidate_has_fulltext(candidate: PriorArtCandidate) -> bool:
    if candidate.source == CNIPA_OFFICIAL_EXPORT_SOURCE and not _candidate_has_cnipa_official_provenance(candidate):
        return False
    has_description = bool(str(candidate.metadata.get("description") or "").strip())
    has_explicit_fulltext = _candidate_has_explicit_fulltext_metadata(candidate)
    return bool(
        has_description
        or has_explicit_fulltext
        or (
            candidate.fulltext_status == "available"
            and (has_description or has_explicit_fulltext)
        )
    )


def _ratio(count: int, total: int) -> float:
    return count / total if total else 0.0


def _stable_non_patent_candidate_id(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


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
                sources=list(PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES),
            ),
            SearchPlanStrategyGroup(
                id="closest-prior-art",
                label="最接近现有技术检索",
                purpose="寻找可用于新颖性和创造性对比的高相关文献。",
                queries=[closest_query or core_query],
                sources=list(PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES),
            ),
            SearchPlanStrategyGroup(
                id="supplemental-literature",
                label="非专利文献补强",
                purpose="补充论文、期刊、会议和科技文献线索，用于背景技术和创造性论证补强。",
                queries=[core_query],
                sources=list(PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES),
            ),
        ],
        target_sources=[*PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES, *PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES],
        target_result_count=20,
        filters={"jurisdictions": intent.jurisdictions, "date_range": intent.date_range},
        metadata={
            "primary_patent_sources": PROJECT_PRIMARY_PATENT_PROVIDER_SOURCES,
            "supplemental_literature_sources": PROJECT_SUPPLEMENTAL_LITERATURE_SOURCES,
            "fallback_sources": ["cnipa_official_export", "cnipa_epub", "wipo_patentscope", "google_patents"],
        },
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
            "patent_document_count": 0,
            "non_patent_document_count": 0,
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


def knowledge_overview(
    store: SQLiteStore,
    project_id: str,
    source_statuses: list[EvidenceSourceConfig] | None = None,
) -> ProjectKnowledgeOverview:
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
        source_statuses=source_statuses or [],
    )


def get_cnipa_query_pack(store: SQLiteStore, project_id: str) -> CnipaQueryPack:
    intent = store.get_latest_search_intent(project_id)
    plan = store.get_latest_agent_search_plan(project_id)
    return build_cnipa_query_pack(intent, plan)


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
            "patent_document_count": 0,
            "non_patent_document_count": 0,
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


def _non_patent_hit_to_candidate(
    hit: NonPatentSearchHit,
    *,
    project_id: str,
    plan_id: str,
    strategy_group_id: str,
) -> PriorArtCandidate:
    sanitized_title = sanitize_untrusted_text(hit.title, max_len=300) or hit.title
    sanitized_query = sanitize_untrusted_text(hit.query)
    sanitized_abstract = sanitize_untrusted_text(hit.abstract) if hit.abstract else None
    identity_seed = hit.url or sanitized_title or hit.id
    metadata = {
        "authors": [sanitize_untrusted_text(author, max_len=200) for author in hit.authors if author],
        "query": sanitized_query,
        "strategy_group": strategy_group_id,
    }
    if hit.provider_attempt_id:
        metadata["source_attempt_ids"] = [hit.provider_attempt_id]
    return PriorArtCandidate(
        id=_stable_non_patent_candidate_id(project_id, plan_id, strategy_group_id, hit.source, identity_seed),
        project_id=project_id,
        plan_id=plan_id,
        source=hit.source,
        title=sanitized_title,
        applicant=", ".join(metadata["authors"]),
        publication_date=hit.publication_year,
        abstract=sanitized_abstract,
        url=hit.url,
        relevance_score=0.0,
        matched_terms=sanitized_query.split(),
        fulltext_status="unknown",
        evidence_kind="non_patent_literature",
        can_satisfy_patent_gate=False,
        recommended_action="review",
        recommendation_reason="非专利文献线索可用于背景技术与创造性论证补强，不能替代专利证据门控。",
        metadata=metadata,
        created_at=_now(),
    )


def _planned_source_ids(plan: AgentSearchPlan) -> set[str]:
    return {
        source_id
        for source_id in (
            [*plan.target_sources, *(source for group in plan.strategy_groups for source in group.sources)]
        )
        if source_id
    }


def _planned_provider_source_ids(plan: AgentSearchPlan) -> set[str]:
    return _planned_source_ids(plan) & LIVE_PROJECT_PATENT_PROVIDER_SOURCES


def _planned_non_patent_provider_source_ids(plan: AgentSearchPlan) -> set[str]:
    return _planned_source_ids(plan) & LIVE_PROJECT_NON_PATENT_PROVIDER_SOURCES


def _strategy_group_id_for_source_and_query(plan: AgentSearchPlan, source_id: str, query: str) -> str:
    return next(
        (
            group.id
            for group in plan.strategy_groups
            if (not group.sources or source_id in group.sources) and query in (group.queries or [group.label])
        ),
        "supplemental-literature",
    )


def _default_provider_chain_for_plan(plan: AgentSearchPlan) -> list[PatentSearchProvider]:
    return _default_provider_chain_for_plan_with_data_dir(plan, data_dir=None)


def _default_provider_chain_for_plan_with_data_dir(
    plan: AgentSearchPlan,
    *,
    data_dir: str | Path | None,
) -> list[PatentSearchProvider]:
    provider_chain = (
        default_project_patent_providers()
        if data_dir is None
        else default_project_patent_providers(data_dir=data_dir)
    )
    planned_sources = _planned_source_ids(plan)
    if not planned_sources:
        return provider_chain
    planned_sources = _planned_provider_source_ids(plan)
    return [provider for provider in provider_chain if provider.source_id in planned_sources]


def _default_non_patent_provider_chain_for_plan_with_data_dir(
    plan: AgentSearchPlan,
    *,
    data_dir: str | Path | None,
) -> list[NonPatentSearchProvider]:
    if data_dir is None:
        return []
    sources = {source.source_id: source for source in evidence_source_views(Path(data_dir))}
    provider_chain: list[NonPatentSearchProvider] = [WanfangLiteratureProvider(sources["wanfang_api"])]
    planned_sources = _planned_non_patent_provider_source_ids(plan)
    if not planned_sources:
        return []
    return [provider for provider in provider_chain if provider.source_id in planned_sources]


def _run_non_patent_search_plan(
    provider_chain: list[NonPatentSearchProvider],
    project_id: str,
    plan: AgentSearchPlan,
) -> tuple[list[PriorArtCandidate], list[ProviderAttempt], list[str]]:
    filters = PatentSearchFilters.model_validate(plan.filters)
    all_hits: list[NonPatentSearchHit] = []
    attempts = []
    warnings: list[str] = []

    for provider in provider_chain:
        strategy_groups = [group for group in plan.strategy_groups if not group.sources or provider.source_id in group.sources]
        for group in strategy_groups:
            for query in (group.queries or [group.label]):
                attempt_id = uuid.uuid4().hex
                started_at = _now()
                available, skip_reason = provider.available()
                if not available:
                    attempt = ProviderAttempt(
                        id=attempt_id,
                        provider=provider.source_id,
                        query=query,
                        filters=filters.model_dump(mode="json"),
                        status="skipped",
                        warnings=[skip_reason or "provider unavailable"],
                        failure_reason=skip_reason or "provider unavailable",
                        started_at=started_at,
                        finished_at=_now(),
                    )
                    attempts.append(attempt)
                    warnings.extend(attempt.warnings)
                    continue
                try:
                    hits, provider_warnings = provider.search(query, limit=plan.target_result_count)
                    tagged_hits = [hit.model_copy(update={"provider_attempt_id": attempt_id, "query": query}) for hit in hits]
                    attempts.append(
                        ProviderAttempt(
                            id=attempt_id,
                            provider=provider.source_id,
                            query=query,
                            filters=filters.model_dump(mode="json"),
                            status="ok" if tagged_hits else "partial",
                            hit_count=len(tagged_hits),
                            warnings=provider_warnings,
                            started_at=started_at,
                            finished_at=_now(),
                        )
                    )
                    warnings.extend(provider_warnings)
                    all_hits.extend(tagged_hits)
                except TimeoutError as exc:
                    message = str(exc)
                    attempts.append(
                        ProviderAttempt(
                            id=attempt_id,
                            provider=provider.source_id,
                            query=query,
                            filters=filters.model_dump(mode="json"),
                            status="timed_out",
                            warnings=[message],
                            failure_reason=message,
                            started_at=started_at,
                            finished_at=_now(),
                        )
                    )
                    warnings.append(message)
                except Exception as exc:
                    message = str(exc)
                    attempts.append(
                        ProviderAttempt(
                            id=attempt_id,
                            provider=provider.source_id,
                            query=query,
                            filters=filters.model_dump(mode="json"),
                            status="failed",
                            warnings=[message],
                            failure_reason=message,
                            started_at=started_at,
                            finished_at=_now(),
                        )
                    )
                    warnings.append(message)

    retained_by_attempt: dict[str, int] = {}
    candidates = [
        _non_patent_hit_to_candidate(
            hit,
            project_id=project_id,
            plan_id=plan.id,
            strategy_group_id=_strategy_group_id_for_source_and_query(plan, hit.source, hit.query),
        )
        for hit in all_hits
    ]
    for candidate in candidates:
        for attempt_id in candidate.metadata.get("source_attempt_ids", []):
            retained_by_attempt[attempt_id] = retained_by_attempt.get(attempt_id, 0) + 1
    finalized_attempts = [
        attempt.model_copy(update={"retained_count": retained_by_attempt.get(attempt.id, 0)})
        for attempt in attempts
    ]
    return candidates, finalized_attempts, warnings


def _source_setup_quality_flags(
    plan: AgentSearchPlan,
    ledger: ProjectSearchLedger,
    *,
    data_dir: str | Path | None,
) -> list[str]:
    if data_dir is None:
        return []
    planned_sources = _planned_source_ids(plan) & frozenset({"patsnap_api", "wanfang_api"})
    if not planned_sources:
        return []
    source_views = {source.source_id: source for source in evidence_source_views(Path(data_dir))}
    flags: list[str] = []
    if any(source_views.get(source_id) and source_views[source_id].status == "not_configured" for source_id in planned_sources):
        flags.append("source_not_configured")
    if any(
        SOURCE_NOT_IMPLEMENTED_WARNINGS.get(attempt.provider, "") in attempt.warnings
        for attempt in ledger.attempts
        if attempt.provider in planned_sources
    ):
        flags.append("source_configured_not_implemented")
    return flags


def _ledger_has_public_no_hit_or_failure(ledger: ProjectSearchLedger) -> bool:
    return any(
        attempt.provider in PUBLIC_PROJECT_PATENT_PROVIDER_SOURCES and attempt.status in {"partial", "failed", "timed_out"}
        for attempt in ledger.attempts
    )


def _empty_search_result_state(ledger: ProjectSearchLedger, source_setup_flags: list[str]) -> tuple[str, list[str]]:
    public_no_hits = _ledger_has_public_no_hit_or_failure(ledger)
    if source_setup_flags:
        quality_flags = list(source_setup_flags)
        if public_no_hits:
            quality_flags.append("no_hits")
        return "search_plan_pending", quality_flags
    if public_no_hits:
        return "failed", ["no_hits"]
    return "failed", ["no_hits"]


def run_agent_search_plan(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
    providers: list[PatentSearchProvider] | None = None,
    data_dir: str | Path | None = None,
) -> ProjectKnowledgeOverview:
    _state, plan = _get_active_plan(store, project_id, plan_id)
    running = plan.model_copy(update={"status": "running", "run_started_at": _now()})
    store.update_agent_search_plan(running)
    provider_chain = (
        list(providers)
        if providers is not None
        else _default_provider_chain_for_plan_with_data_dir(running, data_dir=data_dir)
    )
    candidates, ledger = run_patent_search_plan(provider_chain, project_id, running)
    non_patent_provider_chain = [] if providers is not None else _default_non_patent_provider_chain_for_plan_with_data_dir(
        running,
        data_dir=data_dir,
    )
    non_patent_candidates, non_patent_attempts, non_patent_warnings = _run_non_patent_search_plan(
        non_patent_provider_chain,
        project_id,
        running,
    )
    all_candidates = [*candidates, *non_patent_candidates]
    ledger = ledger.model_copy(
        update={
            "attempts": [*ledger.attempts, *non_patent_attempts],
            "retained_candidate_ids": [candidate.id for candidate in all_candidates],
            "warnings": [*ledger.warnings, *non_patent_warnings],
        }
    )
    source_setup_flags = _source_setup_quality_flags(running, ledger, data_dir=data_dir)
    empty_state_status, empty_state_quality_flags = _empty_search_result_state(ledger, source_setup_flags)
    empty_run_is_setup_guidance = empty_state_status == "search_plan_pending"
    completed = running.model_copy(
        update={
            "status": "completed" if all_candidates or empty_run_is_setup_guidance else "failed",
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
        status="candidates_pending" if all_candidates else empty_state_status,
        active_intent_id=completed.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(all_candidates),
        quality_flags=["candidates_need_confirmation"] if all_candidates else empty_state_quality_flags,
    )
    stored_candidates, _stored_ledger = store.replace_agent_search_run(
        project_id=project_id,
        plan=completed,
        candidates=all_candidates,
        ledger=ledger,
        state=state,
    )
    return knowledge_overview(store, project_id)


def import_cnipa_official_export(
    store: SQLiteStore,
    project_id: str,
    plan_id: str,
    stored_path: Path,
    source_file_name: str | None = None,
) -> ProjectKnowledgeOverview:
    _state, plan = _get_active_plan(store, project_id, plan_id)
    ledger_id = uuid.uuid4().hex
    query = ""
    strategy_group_id = "cnipa-official-export"
    if plan.strategy_groups:
        first_group = plan.strategy_groups[0]
        strategy_group_id = first_group.id
        query = first_group.queries[0] if first_group.queries else first_group.label
    result = parse_cnipa_official_export_file(
        stored_path,
        context=CnipaExportImportContext(
            project_id=project_id,
            plan_id=plan_id,
            import_ledger_id=ledger_id,
            query=query,
            strategy_group_id=strategy_group_id,
        ),
    )
    candidates = [
        patent_hit_to_candidate(
            hit,
            project_id=project_id,
            plan_id=plan_id,
            strategy_group_id=str(hit.metadata.get("strategy_group") or strategy_group_id),
        )
        for hit in result.hits
    ]
    existing_candidates = store.list_prior_art_candidates(project_id, plan_id)
    store.apply_prior_art_candidate_updates(candidates)
    all_candidates = store.list_prior_art_candidates(project_id, plan_id)
    flags = ["candidates_need_confirmation"] if candidates else ["no_hits"]
    if result.warnings:
        flags.append("cnipa_export_parse_warnings")
    state = ProjectKnowledgeState(
        project_id=project_id,
        status="candidates_pending" if candidates else "failed",
        active_intent_id=plan.intent_id,
        active_plan_id=plan_id,
        last_search_at=_now(),
        candidate_count=len(all_candidates),
        quality_flags=flags,
    )
    store.upsert_project_knowledge_state(state)
    existing_ids = {candidate.id for candidate in existing_candidates}
    retained_ids = [
        candidate.id
        for candidate in all_candidates
        if (
            candidate.id not in existing_ids
            or str(candidate.metadata.get("import_ledger_id") or "").strip() == ledger_id
        )
        and str(candidate.metadata.get("import_ledger_id") or "").strip() == ledger_id
    ]
    ledger = ProjectKnowledgeImportLedger(
        id=ledger_id,
        project_id=project_id,
        plan_id=plan_id,
        source_id=CNIPA_OFFICIAL_EXPORT_SOURCE,
        source_file_name=source_file_name or stored_path.name,
        raw_file_hash=result.raw_file_hash,
        detected_schema=result.detected_schema,
        row_count=result.row_count,
        parsed_count=result.parsed_count,
        attachments=result.attachments,
        retained_candidate_ids=retained_ids,
        warnings=result.warnings,
        failures=result.failures,
        created_at=_now(),
    )
    store.create_project_knowledge_import_ledger(ledger)
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
    patent_included = [
        candidate
        for candidate in included
        if candidate.can_satisfy_patent_gate and candidate.evidence_kind == "patent"
    ]
    synthetic_included = [candidate for candidate in included if candidate.source == "fake"]
    non_patent_included = [
        candidate
        for candidate in included
        if candidate.evidence_kind == "non_patent_literature" or not candidate.can_satisfy_patent_gate
    ]
    all_synthetic = bool(included) and len(synthetic_included) == len(included)
    non_patent_only = bool(non_patent_included) and not patent_included
    includes_non_patent = bool(non_patent_included)
    if all_synthetic:
        claim_coverage = 0.0
        fulltext_coverage = 0.0
        quality_flags = ["synthetic_evidence"]
    else:
        claim_covered_count = sum(
            1
            for candidate in patent_included
            if candidate.source != CNIPA_OFFICIAL_EXPORT_SOURCE or _candidate_has_claims(candidate)
        )
        fulltext_covered_count = sum(
            1
            for candidate in patent_included
            if candidate.source != CNIPA_OFFICIAL_EXPORT_SOURCE or _candidate_has_fulltext(candidate)
        )
        claim_coverage = _ratio(
            claim_covered_count,
            len(included),
        )
        fulltext_coverage = _ratio(
            fulltext_covered_count,
            len(included),
        )
        quality_flags = []
        if includes_non_patent:
            quality_flags.append("non_patent_source")
        cnipa_included = [candidate for candidate in patent_included if candidate.source == CNIPA_OFFICIAL_EXPORT_SOURCE]
        invalid_cnipa_included = [
            candidate for candidate in cnipa_included if not _candidate_has_cnipa_official_provenance(candidate)
        ]
        valid_cnipa_included = [candidate for candidate in cnipa_included if _candidate_has_cnipa_official_provenance(candidate)]
        if invalid_cnipa_included:
            quality_flags.append("cnipa_export_missing_provenance")
        cnipa_claim_coverage = _ratio(
            sum(1 for candidate in valid_cnipa_included if _candidate_has_claims(candidate)),
            len(valid_cnipa_included),
        )
        cnipa_fulltext_coverage = _ratio(
            sum(1 for candidate in valid_cnipa_included if _candidate_has_fulltext(candidate)),
            len(valid_cnipa_included),
        )
        if valid_cnipa_included and cnipa_fulltext_coverage == 0.0 and cnipa_claim_coverage == 0.0:
            quality_flags.append("cnipa_export_metadata_only")
        elif valid_cnipa_included and cnipa_fulltext_coverage < 1.0:
            quality_flags.append("cnipa_export_partial_fulltext")
        if valid_cnipa_included and cnipa_claim_coverage < 1.0:
            quality_flags.append("cnipa_export_missing_claims")
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
    cnipa_failure_messages = {
        "cnipa_export_missing_provenance": "CNIPA official export corpus contains records missing official-export provenance metadata.",
        "cnipa_export_metadata_only": "CNIPA official export corpus contains metadata-only records without claims or fulltext.",
        "cnipa_export_partial_fulltext": "CNIPA official export corpus is missing fulltext coverage for one or more included records.",
        "cnipa_export_missing_claims": "CNIPA official export corpus is missing claims coverage for one or more included records.",
    }
    for flag in quality_flags:
        if flag in cnipa_failure_messages:
            quality_failures.append({"code": flag, "message": cnipa_failure_messages[flag]})
    partial_cnipa = any(flag.startswith("cnipa_export_") for flag in quality_flags)
    corpus_status = (
        "needs_supplemental_search"
        if (all_synthetic or includes_non_patent or partial_cnipa)
        else ("ready" if included else "failed")
    )
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
    if all_synthetic:
        state_quality_flags = ["synthetic_evidence"]
        state_status = "needs_supplemental_search"
    elif non_patent_only:
        state_quality_flags = ["non_patent_only"]
        state_status = "needs_supplemental_search"
    elif non_patent_included:
        state_quality_flags = quality_flags or ["non_patent_source"]
        state_status = "needs_supplemental_search"
    elif patent_included:
        state_quality_flags = quality_flags
        state_status = "needs_supplemental_search" if all_synthetic or partial_cnipa else "ready"
    else:
        state_quality_flags = ["empty_corpus"]
        state_status = "needs_supplemental_search"
    updated_state = state.model_copy(
        update={
            "status": state_status,
            "active_plan_id": plan_id,
            "active_corpus_version_id": version.id,
            "last_indexed_at": _now(),
            "document_count": version.document_count,
            "patent_document_count": len(patent_included),
            "non_patent_document_count": len(non_patent_included),
            "candidate_count": len(candidate_pool),
            "claim_coverage": version.claim_coverage,
            "fulltext_coverage": version.fulltext_coverage,
            "quality_flags": state_quality_flags,
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
            "patent_document_count": 0,
            "non_patent_document_count": 0,
            "claim_coverage": 0.0,
            "fulltext_coverage": 0.0,
            "quality_flags": sorted(set([*state.quality_flags, "stale_project_snapshot"])),
        }
    )
    return store.upsert_project_knowledge_state(updated)
