from __future__ import annotations

from backend.app.schemas import (
    AgentSearchPlan,
    PriorArtCandidate,
    ProjectCorpusVersion,
    ProjectKnowledgeState,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.storage import SQLiteStore


def test_project_knowledge_state_round_trips(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    state = ProjectKnowledgeState(
        project_id="project-1",
        status="search_plan_pending",
        active_plan_id="plan-1",
        document_count=0,
        candidate_count=0,
        claim_coverage=0.0,
        fulltext_coverage=0.0,
        quality_flags=["needs_search"],
    )

    stored = store.upsert_project_knowledge_state(state)
    loaded = store.get_project_knowledge_state("project-1")

    assert stored.project_id == "project-1"
    assert loaded == state


def test_search_plan_candidates_and_corpus_version_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    intent = SearchIntent(
        id="intent-1",
        project_id="project-1",
        source_project_hash="hash-1",
        technical_object="城市体检智能体",
        technical_problem="任务拆解和结果复核不足",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排"],
        keywords_en=["urban health", "agent", "task orchestration"],
        synonyms=["城市诊断"],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q"],
        cpc_candidates=["G06Q10/063"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
        created_by="agent",
    )
    store.create_search_intent(intent)

    plan = AgentSearchPlan(
        id="plan-1",
        project_id="project-1",
        intent_id="intent-1",
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全相关城市体检和智能体编排专利",
                queries=["城市体检 智能体 任务编排"],
                sources=["fake"],
            )
        ],
        target_sources=["fake"],
        target_result_count=20,
        filters={"jurisdictions": ["CN"]},
    )
    store.create_agent_search_plan(plan)

    candidate = PriorArtCandidate(
        id="candidate-1",
        project_id="project-1",
        plan_id="plan-1",
        source="fake",
        title="一种城市体检任务编排方法",
        publication_number="CN100000001A",
        abstract="公开了城市体检任务编排。",
        url="https://patents.google.com/patent/CN100000001A",
        relevance_score=0.87,
        matched_terms=["城市体检", "任务编排"],
        fulltext_status="available",
        recommended_action="include",
        recommendation_reason="命中核心技术对象和技术手段",
    )
    store.upsert_prior_art_candidate(candidate)
    updated = store.update_prior_art_candidate_decision("project-1", "candidate-1", "include")

    version = ProjectCorpusVersion(
        id="version-1",
        project_id="project-1",
        name="project-1-prior-art-v1",
        source_plan_id="plan-1",
        status="ready",
        document_count=1,
        chunk_count=3,
        claim_coverage=1.0,
        fulltext_coverage=1.0,
    )
    store.create_project_corpus_version(version)

    assert store.get_latest_search_intent("project-1") == intent
    assert store.get_latest_agent_search_plan("project-1") == plan
    assert updated is not None
    assert updated.user_decision == "include"
    assert store.list_prior_art_candidates("project-1") == [updated]
    assert store.get_latest_project_corpus_version("project-1") == version
