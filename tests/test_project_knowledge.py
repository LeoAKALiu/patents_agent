from __future__ import annotations

import pytest

from backend.app.schemas import (
    AgentSearchPlan,
    PatentPointCandidate,
    PatentType,
    PriorArtCandidate,
    ProjectCreate,
    ProjectCorpusVersion,
    ProjectKnowledgeState,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.services.project_knowledge_service import (
    ProjectKnowledgeConflictError,
    create_project_corpus_from_included_candidates,
    ensure_project_knowledge_initialized,
    knowledge_overview,
    mark_stale_if_project_changed,
    regenerate_project_knowledge,
    run_agent_search_plan,
)
from backend.app.services.project_service import build_project_record
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


def test_update_prior_art_candidate_decision_rejects_invalid_values(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
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

    with pytest.raises(ValueError, match="invalid prior art candidate decision"):
        store.update_prior_art_candidate_decision("project-1", "candidate-1", "bogus")

    stored = store.list_prior_art_candidates("project-1")
    assert len(stored) == 1
    assert stored[0].user_decision == "pending"


def test_knowledge_initialization_extracts_intent_and_plan(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
            patent_type=PatentType.INVENTION,
            technical_field="城市治理智能体",
            innovation="任务 DAG 与证据链复核",
        )
    )
    store.create_project(project)

    overview = ensure_project_knowledge_initialized(store, project)

    assert overview.state.status == "search_plan_pending"
    assert overview.latest_intent is not None
    assert "城市体检" in overview.latest_intent.keywords_zh
    assert "任务编排" in overview.latest_intent.keywords_zh
    assert overview.latest_plan is not None
    assert {group.id for group in overview.latest_plan.strategy_groups} >= {"broad-recall", "closest-prior-art"}


def test_run_plan_creates_fake_candidates_and_state(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        )
    )
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)

    assert after_run.state.status == "candidates_pending"
    assert len(after_run.candidates) >= 2
    assert all(candidate.source == "fake" for candidate in after_run.candidates)


def test_run_plan_rerun_keeps_candidate_count_stable(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    first_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    second_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)

    assert len(first_run.candidates) == len(second_run.candidates)
    assert second_run.state.candidate_count == len(second_run.candidates)
    assert [candidate.id for candidate in first_run.candidates] == [candidate.id for candidate in second_run.candidates]


def test_create_project_corpus_requires_explicit_include_decision(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    run_agent_search_plan(store, project.id, overview.latest_plan.id)

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "needs_supplemental_search"
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.document_count == 0
    assert after_build.state.document_count == 0


def test_create_project_corpus_uses_explicitly_included_candidates(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    for candidate in after_run.candidates[:2]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "ready"
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.document_count == 2
    assert after_build.state.document_count == 2
    assert after_build.state.quality_flags == ["synthetic_evidence"]
    assert after_build.state.claim_coverage == 0.0
    assert after_build.state.fulltext_coverage == 0.0
    assert after_build.latest_corpus_version.quality_report is not None
    assert after_build.latest_corpus_version.quality_report.failures == [
        {"code": "synthetic_evidence", "message": "Corpus built from synthetic fake-source candidates only."}
    ]


def test_superseded_plan_cannot_run_or_build_and_does_not_reactivate(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    initial = ensure_project_knowledge_initialized(store, project)
    original_plan_id = initial.latest_plan.id

    run_agent_search_plan(store, project.id, original_plan_id)
    for candidate in store.list_prior_art_candidates(project.id, original_plan_id)[:1]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")
    build = create_project_corpus_from_included_candidates(store, project.id, original_plan_id)
    assert build.state.active_corpus_version_id

    regenerated = regenerate_project_knowledge(store, project, [])
    replacement_plan_id = regenerated.latest_plan.id
    assert replacement_plan_id != original_plan_id
    assert regenerated.state.active_plan_id == replacement_plan_id
    assert regenerated.state.active_corpus_version_id == ""

    with pytest.raises(ProjectKnowledgeConflictError, match="no longer active"):
        run_agent_search_plan(store, project.id, original_plan_id)
    with pytest.raises(ProjectKnowledgeConflictError, match="no longer active"):
        create_project_corpus_from_included_candidates(store, project.id, original_plan_id)

    after = knowledge_overview(store, project.id)
    assert after.state.active_plan_id == replacement_plan_id
    assert after.state.active_corpus_version_id == ""
    assert store.get_agent_search_plan(project.id, original_plan_id).status == "completed"


def test_regeneration_hides_inactive_corpus_version_from_overview(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    store.update_prior_art_candidate_decision(project.id, after_run.candidates[0].id, "include")
    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)
    built_version_id = after_build.latest_corpus_version.id
    assert after_build.state.active_corpus_version_id == built_version_id
    assert store.get_latest_project_corpus_version(project.id).id == built_version_id

    regenerated = regenerate_project_knowledge(store, project, [])

    assert regenerated.state.active_corpus_version_id == ""
    assert regenerated.latest_corpus_version is None
    assert store.get_latest_project_corpus_version(project.id).id == built_version_id


def test_project_change_marks_knowledge_stale(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    store.update_prior_art_candidate_decision(project.id, after_run.candidates[0].id, "include")
    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)
    built_version_id = after_build.latest_corpus_version.id
    updated = project.model_copy(update={"draft_text": "改为桥梁裂缝检测和声学视觉复检。"})

    state = mark_stale_if_project_changed(store, updated, [])
    stale_overview = knowledge_overview(store, project.id)

    assert state.status == "stale"
    assert "项目技术描述已变化" in state.staleness_reason
    assert state.active_plan_id == overview.latest_plan.id
    assert state.active_corpus_version_id == ""
    assert state.document_count == 0
    assert state.claim_coverage == 0.0
    assert state.fulltext_coverage == 0.0
    assert stale_overview.latest_corpus_version is None
    assert store.get_latest_project_corpus_version(project.id).id == built_version_id
    with pytest.raises(ProjectKnowledgeConflictError, match="stale"):
        run_agent_search_plan(store, project.id, overview.latest_plan.id)
    with pytest.raises(ProjectKnowledgeConflictError, match="stale"):
        create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)


def test_selected_patent_points_mark_knowledge_stale_when_snapshot_changes(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    ensure_project_knowledge_initialized(store, project)

    state = mark_stale_if_project_changed(
        store,
        project,
        [
            PatentPointCandidate(
                id="point-1",
                title="一种证据链复核机制",
                technical_problem="复核过程不稳定",
                innovation="增加多智能体共识评分",
                technical_solution="按步骤回放审查证据",
                selected=True,
            )
        ],
    )

    assert state.status == "stale"
    assert "项目技术描述已变化" in state.staleness_reason


def test_stale_overview_hides_active_corpus_for_legacy_state(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id)
    store.update_prior_art_candidate_decision(project.id, after_run.candidates[0].id, "include")
    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    legacy_stale = after_build.state.model_copy(
        update={
            "status": "stale",
            "staleness_reason": "项目技术描述已变化，需要重新生成检索计划或补充检索。",
            "quality_flags": ["stale_project_snapshot"],
        }
    )
    store.upsert_project_knowledge_state(legacy_stale)

    stale_overview = knowledge_overview(store, project.id)

    assert stale_overview.state.active_corpus_version_id == after_build.latest_corpus_version.id
    assert stale_overview.latest_corpus_version is None
