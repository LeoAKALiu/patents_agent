from __future__ import annotations

import textwrap
from zipfile import ZipFile

import pytest

from backend.app.evidence_sources import update_evidence_source_config
from backend.app.knowledge.patent_search import (
    CnipaEpubPatentProvider,
    GooglePatentsProvider,
    PatSnapPatentProvider,
    StaticPatentSearchProvider,
    patent_hit_to_candidate,
)
from backend.app.schemas import (
    AgentSearchPlan,
    EvidenceSourceConfigPatch,
    PatentSearchHit,
    PatentPointCandidate,
    PatentType,
    PriorArtCandidate,
    ProjectCreate,
    ProjectCorpusVersion,
    ProjectKnowledgeState,
    ProjectRecord,
    ProjectSearchLedger,
    SearchIntent,
    SearchPlanStrategyGroup,
)
from backend.app.services.project_knowledge_service import (
    ProjectKnowledgeConflictError,
    bulk_update_project_candidate_decisions,
    create_project_corpus_from_included_candidates,
    ensure_project_knowledge_initialized,
    get_cnipa_query_pack,
    knowledge_overview,
    mark_stale_if_project_changed,
    regenerate_project_knowledge,
    run_agent_search_plan,
    run_patent_search_plan,
    update_project_candidate_decision,
)
from backend.app.services.project_service import build_project_record
from backend.app.storage import SQLiteStore
import backend.app.services.project_knowledge_service as project_knowledge_service


def _mark_candidates_as_real_sources(store: SQLiteStore, candidates: list[PriorArtCandidate]) -> None:
    for candidate in candidates:
        store.upsert_prior_art_candidate(candidate.model_copy(update={"source": "google_patents"}))


def _project() -> ProjectRecord:
    return build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        )
    )


def _static_provider() -> StaticPatentSearchProvider:
    return StaticPatentSearchProvider(
        source_id="google_patents",
        hits=[
            PatentSearchHit(
                id="hit-1",
                source="google_patents",
                query="城市体检 智能体",
                title="城市体检智能体调度方法",
                publication_number="CN112233445A",
                url="https://patents.google.com/patent/CN112233445A",
                applicant="示例申请人甲",
                publication_date="2024-01-01",
                abstract="公开了一种城市体检调度方法。",
            ),
            PatentSearchHit(
                id="hit-2",
                source="google_patents",
                query="任务编排 证据链",
                title="基于证据链的任务编排复核方法",
                publication_number="CN223344556A",
                url="https://patents.google.com/patent/CN223344556A",
                applicant="示例申请人乙",
                publication_date="2023-05-20",
                abstract="公开了一种基于证据链的任务编排复核方法。",
            ),
        ],
    )


def _semantic_scholar_provider() -> StaticPatentSearchProvider:
    return StaticPatentSearchProvider(
        source_id="semantic_scholar",
        hits=[
            PatentSearchHit(
                id="paper-1",
                source="semantic_scholar",
                query="城市体检 智能体",
                title="面向城市体检的智能体任务编排研究",
                publication_number="SS-2024-001",
                url="https://example.com/semantic-scholar/paper-1",
                applicant="示例作者",
                publication_date="2024-01-01",
                abstract="这是一篇论文而不是专利。",
            ),
        ],
    )


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


def test_knowledge_overview_includes_evidence_source_statuses(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    store.create_project(project)

    overview = knowledge_overview(store, project.id, source_statuses=[])

    assert overview.source_statuses == []


def test_project_knowledge_cnipa_query_pack_uses_latest_plan(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])

    pack = get_cnipa_query_pack(store, project.id)

    assert pack.project_id == project.id
    assert pack.plan_id == overview.latest_plan.id
    assert pack.source_id == "cnipa_official_export"
    assert pack.strategies
    assert pack.strategies[0].queries


def test_import_cnipa_official_export_adds_real_candidates_and_ledger(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    export_path = tmp_path / "cnipa.csv"
    export_path.write_text(
        "公开公告号,专利名称,摘要\n"
        "CN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
        encoding="utf-8",
    )

    imported = import_cnipa_official_export(
        store,
        project.id,
        overview.latest_plan.id,
        export_path,
        source_file_name="cnipa-original.csv",
    )

    assert imported.state.status == "candidates_pending"
    assert imported.state.candidate_count == 1
    assert imported.state.quality_flags == ["candidates_need_confirmation"]
    assert imported.candidates[0].source == "cnipa_official_export"
    assert imported.candidates[0].metadata["evidence_origin"] == "official_export"
    ledgers = store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id)
    assert len(ledgers) == 1
    assert ledgers[0].source_id == "cnipa_official_export"
    assert ledgers[0].source_file_name == "cnipa-original.csv"
    assert ledgers[0].parsed_count == 1
    assert ledgers[0].retained_candidate_ids == [imported.candidates[0].id]


def test_import_cnipa_official_export_records_zip_attachment_names_in_ledger(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    csv_path = tmp_path / "inner.csv"
    csv_path.write_text(
        "申请号,题名,摘要\nCN202410000001,城市体检证据链方法,公开了一种证据链复核方法。\n",
        encoding="utf-8",
    )
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 scanned placeholder")
    export_path = tmp_path / "cnipa-export.zip"
    with ZipFile(export_path, "w") as archive:
        archive.write(csv_path, "metadata/inner.csv")
        archive.write(pdf_path, "docs/scan.pdf")

    import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path, source_file_name="cnipa-export.zip")

    ledgers = store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id)

    assert ledgers[0].source_file_name == "cnipa-export.zip"
    assert ledgers[0].attachments == ["scan.pdf"]


def test_import_cnipa_official_export_keeps_distinct_application_number_only_candidates(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    export_path = tmp_path / "cnipa-app-only.csv"
    export_path.write_text(
        "申请号,专利名称,摘要\n"
        "CN202410000001,城市体检任务编排方法,公开了一种任务编排方法。\n"
        "CN202410000002,城市体检证据链复核方法,公开了一种证据链复核方法。\n",
        encoding="utf-8",
    )

    imported = import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path)

    assert imported.state.candidate_count == 2
    assert len(imported.candidates) == 2
    assert {candidate.application_number for candidate in imported.candidates} == {
        "CN202410000001",
        "CN202410000002",
    }
    assert len({candidate.id for candidate in imported.candidates}) == 2


def test_import_cnipa_official_export_reimport_ledger_retains_refreshed_candidates(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    export_path = tmp_path / "cnipa.csv"
    export_path.write_text(
        "公开公告号,专利名称,摘要\n"
        "CN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
        encoding="utf-8",
    )

    first_import = import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path)
    second_import = import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path)
    ledgers = store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id)

    assert len(first_import.candidates) == 1
    assert len(second_import.candidates) == 1
    assert len(ledgers) == 2
    assert ledgers[0].id != ledgers[1].id
    assert ledgers[0].retained_candidate_ids == [second_import.candidates[0].id]
    assert second_import.candidates[0].metadata["import_ledger_id"] == ledgers[0].id


def test_live_search_rerun_preserves_imported_cnipa_candidates_for_same_plan(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    export_path = tmp_path / "cnipa.csv"
    export_path.write_text(
        "公开公告号,专利名称,摘要\n"
        "CN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
        encoding="utf-8",
    )

    imported = import_cnipa_official_export(store, project.id, plan_id, export_path)
    rerun = run_agent_search_plan(store, project.id, plan_id, providers=[_static_provider()])
    candidates = store.list_prior_art_candidates(project.id, plan_id)

    assert any(candidate.id == imported.candidates[0].id for candidate in rerun.candidates)
    assert {candidate.source for candidate in candidates} >= {"cnipa_official_export", "google_patents"}
    assert imported.candidates[0].id in {candidate.id for candidate in candidates}
    assert rerun.state.candidate_count == len(candidates)


def test_run_plan_creates_real_candidates_and_state(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(
        ProjectCreate(
            name="一种城市体检智能体任务编排方法",
            draft_text="通过多智能体拆解城市体检任务，并通过证据链复核生成可信报告。",
        )
    )
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])

    assert after_run.state.status == "candidates_pending"
    assert len(after_run.candidates) >= 2
    assert all(candidate.source == "google_patents" for candidate in after_run.candidates)


def test_project_search_uses_real_provider_candidates(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None
    provider = StaticPatentSearchProvider(
        source_id="google_patents",
        hits=[
            PatentSearchHit(
                id="hit-1",
                source="google_patents",
                query="城市体检 智能体",
                title="城市体检智能体调度方法",
                publication_number="CN112233445A",
                url="https://patents.google.com/patent/CN112233445A",
                abstract="公开了一种城市体检调度方法。",
            )
        ],
    )

    result = run_agent_search_plan(store, project.id, plan.id, providers=[provider])

    assert result.state.status == "candidates_pending"
    assert result.candidates[0].source == "google_patents"
    assert result.candidates[0].publication_number == "CN112233445A"
    assert all(candidate.source != "fake" for candidate in result.candidates)


def test_project_search_all_providers_empty_fails_without_fake_candidates(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None
    provider = StaticPatentSearchProvider(source_id="google_patents", hits=[], warnings=["no hits"])

    result = run_agent_search_plan(store, project.id, plan.id, providers=[provider])

    assert result.state.status == "failed"
    assert result.state.candidate_count == 0
    assert "no_hits" in result.state.quality_flags
    assert result.candidates == []


def test_run_agent_search_plan_marks_commercial_sources_not_configured_without_no_hits(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    intent = SearchIntent(
        id="intent-commercial-1",
        project_id=project.id,
        source_project_hash="hash-commercial-1",
        technical_object="城市体检智能体",
        technical_problem="任务编排缺少可信复核",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排"],
        jurisdictions=["CN"],
        date_range="2016-2026",
        created_by="agent",
    )
    plan = AgentSearchPlan(
        id="plan-commercial-1",
        project_id=project.id,
        intent_id=intent.id,
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="commercial-patent",
                label="商业专利",
                purpose="仅验证商业专利源配置引导。",
                queries=["城市体检 智能体 任务编排"],
                sources=["patsnap_api"],
            ),
            SearchPlanStrategyGroup(
                id="commercial-literature",
                label="商业文献",
                purpose="仅验证非专利商业源配置引导。",
                queries=["城市体检 智能体 任务编排"],
                sources=["wanfang_api"],
            ),
        ],
        target_sources=["patsnap_api", "wanfang_api"],
        target_result_count=20,
        filters={"jurisdictions": ["CN"], "date_range": "2016-2026"},
    )
    store.create_search_intent(intent)
    store.create_agent_search_plan(plan)
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="search_plan_pending",
            active_intent_id=intent.id,
            active_plan_id=plan.id,
        )
    )

    result = run_agent_search_plan(store, project.id, plan.id, data_dir=tmp_path)

    assert result.state.status == "search_plan_pending"
    assert "source_not_configured" in result.state.quality_flags
    assert "no_hits" not in result.state.quality_flags
    assert result.state.candidate_count == 0
    stored_plan = store.get_agent_search_plan(project.id, plan.id)
    assert stored_plan is not None
    assert stored_plan.status == "completed"
    ledger = store.get_latest_project_search_ledger(project.id, plan.id)
    assert ledger is not None
    assert {attempt.provider for attempt in ledger.attempts} == {"patsnap_api", "wanfang_api"}
    assert all(attempt.status == "skipped" for attempt in ledger.attempts)


def test_run_agent_search_plan_marks_configured_commercial_skeletons_as_not_implemented(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    update_evidence_source_config(
        tmp_path,
        "patsnap_api",
        EvidenceSourceConfigPatch(api_key="ps-test-secret-1234", enabled=True),
    )
    update_evidence_source_config(
        tmp_path,
        "wanfang_api",
        EvidenceSourceConfigPatch(api_key="wf-test-secret-5678", enabled=True),
    )
    intent = SearchIntent(
        id="intent-commercial-2",
        project_id=project.id,
        source_project_hash="hash-commercial-2",
        technical_object="城市体检智能体",
        technical_problem="任务编排缺少可信复核",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排"],
        jurisdictions=["CN"],
        date_range="2016-2026",
        created_by="agent",
    )
    plan = AgentSearchPlan(
        id="plan-commercial-2",
        project_id=project.id,
        intent_id=intent.id,
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="commercial-patent",
                label="商业专利",
                purpose="仅验证商业专利源骨架提示。",
                queries=["城市体检 智能体 任务编排"],
                sources=["patsnap_api"],
            ),
            SearchPlanStrategyGroup(
                id="commercial-literature",
                label="商业文献",
                purpose="仅验证非专利商业源骨架提示。",
                queries=["城市体检 智能体 任务编排"],
                sources=["wanfang_api"],
            ),
        ],
        target_sources=["patsnap_api", "wanfang_api"],
        target_result_count=20,
        filters={"jurisdictions": ["CN"], "date_range": "2016-2026"},
    )
    store.create_search_intent(intent)
    store.create_agent_search_plan(plan)
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="search_plan_pending",
            active_intent_id=intent.id,
            active_plan_id=plan.id,
        )
    )

    result = run_agent_search_plan(store, project.id, plan.id, data_dir=tmp_path)

    assert result.state.status == "search_plan_pending"
    assert result.state.quality_flags == ["source_configured_not_implemented"]
    assert "no_hits" not in result.state.quality_flags
    assert result.state.candidate_count == 0
    stored_plan = store.get_agent_search_plan(project.id, plan.id)
    assert stored_plan is not None
    assert stored_plan.status == "completed"
    assert "patsnap_api_live_search_not_implemented" in stored_plan.warnings
    assert "wanfang_api_live_search_not_implemented" in stored_plan.warnings
    ledger = store.get_latest_project_search_ledger(project.id, plan.id)
    assert ledger is not None
    assert any(attempt.provider == "wanfang_api" and attempt.status == "partial" for attempt in ledger.attempts)
    assert any(attempt.provider == "patsnap_api" and attempt.status == "partial" for attempt in ledger.attempts)


def test_run_agent_search_plan_keeps_missing_commercial_setup_guidance_when_public_fallbacks_have_no_hits(
    tmp_path,
    monkeypatch,
):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    monkeypatch.setattr(
        project_knowledge_service,
        "default_project_patent_providers",
        lambda data_dir=None: [
            PatSnapPatentProvider(
                {source.source_id: source for source in project_knowledge_service.evidence_source_views(tmp_path)}[
                    "patsnap_api"
                ]
            ),
            StaticPatentSearchProvider(source_id="wipo_patentscope", hits=[]),
        ],
    )

    result = run_agent_search_plan(store, project.id, plan.id, data_dir=tmp_path)

    assert result.state.status == "search_plan_pending"
    assert "source_not_configured" in result.state.quality_flags
    assert "no_hits" in result.state.quality_flags
    assert result.state.candidate_count == 0
    ledger = store.get_latest_project_search_ledger(project.id, plan.id)
    assert ledger is not None
    assert any(attempt.provider == "patsnap_api" and attempt.status == "skipped" for attempt in ledger.attempts)
    assert any(attempt.provider == "wipo_patentscope" and attempt.status == "partial" for attempt in ledger.attempts)
    assert any(attempt.provider == "wanfang_api" and attempt.status == "skipped" for attempt in ledger.attempts)


def test_run_agent_search_plan_keeps_configured_commercial_skeleton_guidance_when_public_fallbacks_have_no_hits(
    tmp_path,
    monkeypatch,
):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    update_evidence_source_config(
        tmp_path,
        "patsnap_api",
        EvidenceSourceConfigPatch(api_key="ps-test-secret-1234", enabled=True),
    )
    update_evidence_source_config(
        tmp_path,
        "wanfang_api",
        EvidenceSourceConfigPatch(api_key="wf-test-secret-5678", enabled=True),
    )
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    monkeypatch.setattr(
        project_knowledge_service,
        "default_project_patent_providers",
        lambda data_dir=None: [
            PatSnapPatentProvider(
                {source.source_id: source for source in project_knowledge_service.evidence_source_views(tmp_path)}[
                    "patsnap_api"
                ]
            ),
            StaticPatentSearchProvider(source_id="wipo_patentscope", hits=[]),
        ],
    )

    result = run_agent_search_plan(store, project.id, plan.id, data_dir=tmp_path)

    assert result.state.status == "search_plan_pending"
    assert "source_configured_not_implemented" in result.state.quality_flags
    assert "no_hits" in result.state.quality_flags
    assert result.state.candidate_count == 0
    ledger = store.get_latest_project_search_ledger(project.id, plan.id)
    assert ledger is not None
    assert any(attempt.provider == "patsnap_api" and attempt.status == "partial" for attempt in ledger.attempts)
    assert any(attempt.provider == "wanfang_api" and attempt.status == "partial" for attempt in ledger.attempts)
    assert any(attempt.provider == "wipo_patentscope" and attempt.status == "partial" for attempt in ledger.attempts)


def test_wipo_patentscope_candidates_can_build_ready_project_corpus(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None
    provider = StaticPatentSearchProvider(
        source_id="wipo_patentscope",
        hits=[
            PatentSearchHit(
                id="wipo-hit-1",
                source="wipo_patentscope",
                query="urban health assessment agent task orchestration",
                title="Trusted multi-agent task orchestration system",
                publication_number="WO2026112646",
                url="https://patentscope.wipo.int/search/en/detail.jsf?docId=WO2026112646",
                applicant="Example Applicant",
                publication_date="2026-06-11",
                abstract="Coordinates agent tasks and verifies evidence chain consistency.",
            )
        ],
    )

    searched = run_agent_search_plan(store, project.id, plan.id, providers=[provider])
    candidate = searched.candidates[0]
    update_project_candidate_decision(store, project.id, candidate.id, "include")
    built = create_project_corpus_from_included_candidates(store, project.id, plan.id)

    assert built.state.status == "ready"
    assert built.state.document_count == 1
    assert "non_patent_source" not in built.state.quality_flags
    assert built.latest_corpus_version is not None
    assert built.latest_corpus_version.status == "ready"


def test_run_patent_search_plan_records_skipped_and_successful_default_attempts(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    provider_chain = [
        CnipaEpubPatentProvider(script_path=None),
        GooglePatentsProvider(
            http_get=lambda url, timeout: (
                '<html><body><a href="/patent/CN112233445A/en">Urban inspection agent</a></body></html>'
            )
        ),
    ]

    candidates, ledger = run_patent_search_plan(provider_chain, project.id, plan)

    assert candidates
    assert ledger.attempts
    assert any(attempt.provider == "cnipa_epub" and attempt.status == "skipped" for attempt in ledger.attempts)
    assert any(attempt.provider == "google_patents" and attempt.status == "ok" for attempt in ledger.attempts)
    assert any("CNIPA EPUB helper is not configured" in warning for warning in ledger.warnings)


def test_run_agent_search_plan_keeps_provider_warnings_for_default_chain_attempts(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    providers = [
        CnipaEpubPatentProvider(script_path=None),
        GooglePatentsProvider(
            http_get=lambda url, timeout: (
                '<html><body><a href="/patent/CN112233445A/en">Urban inspection agent</a></body></html>'
            )
        ),
    ]

    result = run_agent_search_plan(store, project.id, plan.id, providers=providers)

    assert result.state.status == "candidates_pending"
    stored_plan = store.get_agent_search_plan(project.id, plan.id)
    assert stored_plan is not None
    assert stored_plan.warnings
    assert any("CNIPA EPUB helper is not configured" in warning for warning in stored_plan.warnings)


def test_run_agent_search_plan_does_not_run_cnipa_epub_for_official_export_only_plan(tmp_path, monkeypatch):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    intent = SearchIntent(
        id="intent-1",
        project_id=project.id,
        source_project_hash="hash-1",
        technical_object="城市体检智能体",
        technical_problem="任务编排缺少可信复核",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排"],
        jurisdictions=["CN"],
        date_range="2016-2026",
        created_by="agent",
    )
    plan = AgentSearchPlan(
        id="plan-1",
        project_id=project.id,
        intent_id=intent.id,
        status="draft",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="official-export",
                label="官方导出",
                purpose="仅准备 CNIPA 官方导出查询包。",
                queries=["城市体检 智能体 任务编排"],
                sources=["cnipa_official_export"],
            )
        ],
        target_sources=["cnipa_official_export"],
        target_result_count=20,
        filters={"jurisdictions": ["CN"], "date_range": "2016-2026"},
    )
    store.create_search_intent(intent)
    store.create_agent_search_plan(plan)
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="search_plan_pending",
            active_intent_id=intent.id,
            active_plan_id=plan.id,
        )
    )

    attempted_sources: list[str] = []

    def _provider(source_id: str) -> StaticPatentSearchProvider:
        provider = StaticPatentSearchProvider(source_id=source_id, hits=[])
        original_search = provider.search

        def _tracked_search(query: str, *, filters, limit: int):
            attempted_sources.append(source_id)
            return original_search(query, filters=filters, limit=limit)

        provider.search = _tracked_search  # type: ignore[method-assign]
        return provider

    monkeypatch.setattr(
        project_knowledge_service,
        "default_project_patent_providers",
        lambda: [_provider("cnipa_epub"), _provider("wipo_patentscope")],
    )

    result = run_agent_search_plan(store, project.id, plan.id)

    assert result.state.status == "failed"
    assert attempted_sources == []


def test_run_patent_search_plan_marks_google_transport_failures(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    provider_chain = [
        GooglePatentsProvider(
            http_get=lambda url, timeout: (_ for _ in ()).throw(RuntimeError("network down"))
        )
    ]

    candidates, ledger = run_patent_search_plan(provider_chain, project.id, plan)

    assert candidates == []
    assert ledger.attempts
    assert all(attempt.status == "failed" for attempt in ledger.attempts)
    assert all("network down" in attempt.failure_reason for attempt in ledger.attempts)


def test_run_patent_search_plan_marks_cnipa_parse_failures(tmp_path):
    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    script = tmp_path / "fake_cnipa.py"
    script.write_text(
        textwrap.dedent(
            """\
            print("EPUB_HITS_JSON: [invalid]")
            """
        ),
        encoding="utf-8",
    )
    provider_chain = [CnipaEpubPatentProvider(script_path=script)]

    candidates, ledger = run_patent_search_plan(provider_chain, project.id, plan)

    assert candidates == []
    assert ledger.attempts
    assert all(attempt.status == "failed" for attempt in ledger.attempts)
    assert all("JSON parse failed" in attempt.failure_reason for attempt in ledger.attempts)


def test_run_patent_search_plan_records_timeout_attempts_without_fake_candidates(tmp_path):
    class TimeoutPatentSearchProvider:
        name = "Timeout Patent Search"
        source_id = "timeout_provider"

        def available(self) -> tuple[bool, str | None]:
            return True, None

        def search(
            self,
            query: str,
            *,
            filters: PatentSearchFilters,
            limit: int,
        ) -> tuple[list[PatentSearchHit], list[str]]:
            del query, filters, limit
            raise TimeoutError("slow provider")

    store = SQLiteStore(tmp_path / "test.sqlite")
    project = _project()
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    plan = overview.latest_plan
    assert plan is not None

    candidates, ledger = run_patent_search_plan([TimeoutPatentSearchProvider()], project.id, plan)

    assert candidates == []
    assert ledger.retained_candidate_ids == []
    assert ledger.attempts
    assert all(attempt.status == "timed_out" for attempt in ledger.attempts)
    assert all(attempt.failure_reason and "slow provider" in attempt.failure_reason for attempt in ledger.attempts)
    assert any("slow provider" in warning for warning in ledger.warnings)


def test_run_agent_search_plan_persists_latest_search_ledger(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])

    stored_plan = store.get_agent_search_plan(project.id, overview.latest_plan.id)
    assert stored_plan is not None
    ledger_id = stored_plan.metadata["latest_search_ledger_id"]
    assert after_run.latest_plan is not None
    assert after_run.latest_plan.metadata["latest_search_ledger_id"] == ledger_id

    persisted = store.get_project_search_ledger(project.id, ledger_id)
    latest = store.get_latest_project_search_ledger(project.id, overview.latest_plan.id)
    assert persisted is not None
    assert latest is not None
    assert persisted.id == ledger_id
    assert latest.id == ledger_id
    assert persisted.retained_candidate_ids == [candidate.id for candidate in after_run.candidates]


def test_run_plan_rerun_keeps_candidate_count_stable(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    first_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    second_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])

    assert len(first_run.candidates) == len(second_run.candidates)
    assert second_run.state.candidate_count == len(second_run.candidates)
    assert [candidate.id for candidate in first_run.candidates] == [candidate.id for candidate in second_run.candidates]


def test_delete_project_removes_knowledge_ledgers(tmp_path):
    from backend.app.services.project_knowledge_service import import_cnipa_official_export

    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    store.create_project(project)
    overview = regenerate_project_knowledge(store, project, [])
    run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    export_path = tmp_path / "cnipa.csv"
    export_path.write_text(
        "公开公告号,专利名称,摘要\n"
        "CN112233445A,城市体检任务编排方法,公开了一种任务编排方法。\n",
        encoding="utf-8",
    )
    import_cnipa_official_export(store, project.id, overview.latest_plan.id, export_path)

    assert store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id)
    assert store.get_latest_project_search_ledger(project.id, overview.latest_plan.id) is not None

    assert store.delete_project(project.id) is True
    assert store.list_project_knowledge_import_ledgers(project.id, overview.latest_plan.id) == []
    assert store.get_latest_project_search_ledger(project.id, overview.latest_plan.id) is None


def test_create_project_corpus_requires_explicit_include_decision(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "needs_supplemental_search"
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.document_count == 0
    assert after_build.latest_corpus_version.status == "failed"
    assert after_build.state.document_count == 0


def test_create_project_corpus_uses_explicitly_included_candidates(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    for candidate in after_run.candidates[:2]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "ready"
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.status == "ready"
    assert after_build.latest_corpus_version.document_count == 2
    assert after_build.state.document_count == 2
    assert after_build.state.quality_flags == []
    assert after_build.state.claim_coverage == 1.0
    assert after_build.state.fulltext_coverage == 1.0
    assert after_build.latest_corpus_version.quality_report is not None
    assert after_build.latest_corpus_version.quality_report.failures == []


def test_cnipa_official_export_builds_ready_corpus_with_claims_and_fulltext(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    for number in ["CN112233445A", "CN112233446A"]:
        store.upsert_prior_art_candidate(
            PriorArtCandidate(
                id=f"candidate-{number}",
                project_id=project.id,
                plan_id=plan_id,
                source="cnipa_official_export",
                title=f"城市体检方法 {number}",
                publication_number=number,
                abstract="公开了一种城市体检方法。",
                url="",
                fulltext_status="available",
                user_decision="include",
                metadata={
                    "claims": "1. 一种城市体检方法。",
                    "description": "说明书全文。",
                    "evidence_origin": "official_export",
                    "import_ledger_id": f"ledger-{number}",
                    "raw_file_hash": f"hash-{number}",
                },
            )
        )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=2,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "ready"
    assert result.state.document_count == 2
    assert result.state.claim_coverage == 1.0
    assert result.state.fulltext_coverage == 1.0
    assert result.state.quality_flags == []


def test_cnipa_candidate_missing_official_provenance_does_not_become_ready(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn-missing-provenance",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            abstract="公开了一种城市体检方法。",
            url="",
            fulltext_status="available",
            user_decision="include",
            metadata={"claims": "1. 一种城市体检方法。", "description": "说明书全文。"},
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=1,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert result.state.claim_coverage == 0.0
    assert result.state.fulltext_coverage == 0.0
    assert "cnipa_export_missing_provenance" in result.state.quality_flags
    assert result.latest_corpus_version is not None
    assert result.latest_corpus_version.quality_report is not None
    assert result.latest_corpus_version.quality_report.failures == [
        {
            "code": "cnipa_export_missing_provenance",
            "message": "CNIPA official export corpus contains records missing official-export provenance metadata.",
        }
    ]


def test_cnipa_metadata_only_corpus_needs_supplemental_search(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            url="",
            user_decision="include",
            metadata={
                "evidence_origin": "official_export",
                "import_ledger_id": "ledger-cn",
                "raw_file_hash": "hash-cn",
            },
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=1,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert "cnipa_export_metadata_only" in result.state.quality_flags
    assert "synthetic_evidence" not in result.state.quality_flags
    assert "non_patent_source" not in result.state.quality_flags
    assert result.latest_corpus_version is not None
    assert result.latest_corpus_version.quality_report is not None
    assert result.latest_corpus_version.quality_report.failures == [
        {
            "code": "cnipa_export_metadata_only",
            "message": "CNIPA official export corpus contains metadata-only records without claims or fulltext.",
        },
        {
            "code": "cnipa_export_missing_claims",
            "message": "CNIPA official export corpus is missing claims coverage for one or more included records.",
        },
    ]


def test_cnipa_claims_without_description_needs_partial_fulltext_search(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn-claims-only",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            abstract="公开了一种城市体检方法。",
            url="",
            fulltext_status="available",
            user_decision="include",
            metadata={
                "claims": "1. 一种城市体检方法。",
                "evidence_origin": "official_export",
                "import_ledger_id": "ledger-claims-only",
                "raw_file_hash": "hash-claims-only",
            },
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=1,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert result.state.claim_coverage == 1.0
    assert result.state.fulltext_coverage == 0.0
    assert "cnipa_export_partial_fulltext" in result.state.quality_flags
    assert "cnipa_export_metadata_only" not in result.state.quality_flags
    assert "cnipa_export_missing_claims" not in result.state.quality_flags


def test_cnipa_attachment_metadata_does_not_count_as_fulltext(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn-attachment-only",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            url="",
            fulltext_status="available",
            user_decision="include",
            metadata={
                "claims": "1. 一种城市体检方法。",
                "fulltext_path": "/tmp/CN112233445A.pdf",
                "fulltext_file": "CN112233445A.pdf",
                "evidence_origin": "official_export",
                "import_ledger_id": "ledger-attachment-only",
                "raw_file_hash": "hash-attachment-only",
            },
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=1,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert result.state.claim_coverage == 1.0
    assert result.state.fulltext_coverage == 0.0
    assert "cnipa_export_partial_fulltext" in result.state.quality_flags
    assert "cnipa_export_metadata_only" not in result.state.quality_flags


def test_create_project_corpus_non_patent_candidates_do_not_make_corpus_ready(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_semantic_scholar_provider()])

    assert after_run.candidates
    store.update_prior_art_candidate_decision(project.id, after_run.candidates[0].id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.status == "needs_supplemental_search"
    assert after_build.state.quality_flags == ["non_patent_only"]
    assert after_build.state.claim_coverage == 0.0
    assert after_build.state.fulltext_coverage == 0.0
    assert after_build.latest_corpus_version is not None
    assert after_build.latest_corpus_version.status == "needs_supplemental_search"
    assert after_build.latest_corpus_version.quality_report is not None
    assert after_build.latest_corpus_version.quality_report.failures == [
        {
            "code": "non_patent_source",
            "message": "Corpus includes non-patent sources: semantic_scholar",
        }
    ]


def test_non_patent_only_included_candidates_do_not_make_project_ready(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    store.create_project(project)
    state = ProjectKnowledgeState(
        project_id=project.id,
        status="candidates_pending",
        active_plan_id="plan-1",
        last_search_at="2026-07-01T00:00:00Z",
        candidate_count=1,
    )
    store.upsert_project_knowledge_state(state)
    candidate = PriorArtCandidate(
        id="wanfang-candidate-1",
        project_id=project.id,
        plan_id="plan-1",
        source="wanfang_api",
        title="城市体检智能体任务编排研究",
        url="https://apps.wanfangdata.com.cn/example",
        user_decision="include",
        evidence_kind="non_patent_literature",
        can_satisfy_patent_gate=False,
    )
    store.replace_agent_search_run(
        project_id=project.id,
        plan=store.create_agent_search_plan(
            AgentSearchPlan(
                id="plan-1",
                project_id=project.id,
                intent_id="intent-1",
                status="completed",
            )
        ),
        candidates=[candidate],
        ledger=ProjectSearchLedger(id="ledger-1", project_id=project.id, plan_id="plan-1"),
        state=state,
    )

    overview = create_project_corpus_from_included_candidates(store, project.id, "plan-1")

    assert overview.state.status == "needs_supplemental_search"
    assert overview.state.document_count == 1
    assert overview.state.patent_document_count == 0
    assert overview.state.non_patent_document_count == 1
    assert "non_patent_only" in overview.state.quality_flags


def test_create_project_corpus_preserves_non_patent_and_cnipa_quality_flags_in_mixed_corpus(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = _project()
    overview = regenerate_project_knowledge(store, project, [])
    plan_id = overview.latest_plan.id
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-cn-partial",
            project_id=project.id,
            plan_id=plan_id,
            source="cnipa_official_export",
            title="城市体检方法",
            publication_number="CN112233445A",
            abstract="公开了一种城市体检方法。",
            url="",
            user_decision="include",
            metadata={
                "claims": "1. 一种城市体检方法。",
                "evidence_origin": "official_export",
                "import_ledger_id": "ledger-mixed-partial",
                "raw_file_hash": "hash-mixed-partial",
            },
        )
    )
    store.upsert_prior_art_candidate(
        PriorArtCandidate(
            id="candidate-paper",
            project_id=project.id,
            plan_id=plan_id,
            source="semantic_scholar",
            title="面向城市体检的智能体任务编排研究",
            publication_number="SS-2024-001",
            abstract="这是一篇论文而不是专利。",
            url="https://example.com/semantic-scholar/paper-1",
            user_decision="include",
        )
    )
    store.upsert_project_knowledge_state(
        ProjectKnowledgeState(
            project_id=project.id,
            status="candidates_pending",
            active_plan_id=plan_id,
            last_search_at="2026-07-01T00:00:00+00:00",
            candidate_count=2,
        )
    )

    result = create_project_corpus_from_included_candidates(store, project.id, plan_id)

    assert result.state.status == "needs_supplemental_search"
    assert result.state.claim_coverage == 0.5
    assert result.state.fulltext_coverage == 0.0
    assert result.state.quality_flags == ["non_patent_source", "cnipa_export_partial_fulltext"]
    assert result.latest_corpus_version is not None
    assert result.latest_corpus_version.quality_report is not None
    assert result.latest_corpus_version.quality_report.failures == [
        {
            "code": "non_patent_source",
            "message": "Corpus includes non-patent sources: semantic_scholar",
        },
        {
            "code": "cnipa_export_partial_fulltext",
            "message": "CNIPA official export corpus is missing fulltext coverage for one or more included records.",
        },
    ]


def test_patent_candidate_sets_patent_gate_fields(tmp_path):
    project = _project()
    hit = PatentSearchHit(
        id="hit-1",
        source="patsnap_api",
        query="城市体检 智能体",
        title="城市体检智能体调度方法",
        publication_number="CN112233445A",
        url="https://example.com/patent/CN112233445A",
    )

    candidate = patent_hit_to_candidate(hit, project_id=project.id, plan_id="plan-1", strategy_group_id="broad")

    assert candidate.evidence_kind == "patent"
    assert candidate.can_satisfy_patent_gate is True


def test_create_project_corpus_rejects_build_before_search(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)

    with pytest.raises(ProjectKnowledgeConflictError, match="Run candidate search"):
        create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    after = knowledge_overview(store, project.id)
    assert after.state.status == "search_plan_pending"
    assert after.state.active_corpus_version_id == ""
    assert after.latest_corpus_version is None


def test_create_project_corpus_preserves_active_intent_and_last_search_metadata(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    store.update_prior_art_candidate_decision(project.id, after_run.candidates[0].id, "include")

    before_build = knowledge_overview(store, project.id)
    assert before_build.state.active_intent_id == overview.latest_intent.id
    assert before_build.state.active_plan_id == overview.latest_plan.id
    assert before_build.state.last_search_at

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)

    assert after_build.state.active_intent_id == before_build.state.active_intent_id
    assert after_build.state.active_plan_id == before_build.state.active_plan_id
    assert after_build.state.last_search_at == before_build.state.last_search_at
    assert after_build.state.last_indexed_at
    assert after_build.state.active_corpus_version_id == after_build.latest_corpus_version.id


def test_candidate_decision_change_invalidates_active_ready_corpus_state(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    _mark_candidates_as_real_sources(store, after_run.candidates[:2])
    for candidate in after_run.candidates[:2]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)
    assert after_build.state.status == "ready"
    assert after_build.state.active_corpus_version_id
    assert after_build.latest_corpus_version is not None

    before_state = after_build.state
    changed = update_project_candidate_decision(store, project.id, after_run.candidates[0].id, "exclude")
    after = knowledge_overview(store, project.id)

    assert changed.user_decision == "exclude"
    assert after.state.status == "candidates_pending"
    assert after.state.active_corpus_version_id == ""
    assert after.state.last_indexed_at == ""
    assert after.state.document_count == 0
    assert after.state.claim_coverage == 0.0
    assert after.state.fulltext_coverage == 0.0
    assert after.state.quality_flags == ["candidates_need_confirmation"]
    assert after.state.active_intent_id == before_state.active_intent_id
    assert after.state.active_plan_id == before_state.active_plan_id
    assert after.state.last_search_at == before_state.last_search_at
    assert after.state.candidate_count == before_state.candidate_count
    assert after.latest_corpus_version is None


def test_bulk_candidate_decision_change_invalidates_active_corpus_once(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    overview = ensure_project_knowledge_initialized(store, project)
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
    _mark_candidates_as_real_sources(store, after_run.candidates[:2])
    for candidate in after_run.candidates[:2]:
        store.update_prior_art_candidate_decision(project.id, candidate.id, "include")

    after_build = create_project_corpus_from_included_candidates(store, project.id, overview.latest_plan.id)
    built_version_id = after_build.latest_corpus_version.id
    before_state = after_build.state

    updated = bulk_update_project_candidate_decisions(
        store,
        project.id,
        [candidate.id for candidate in after_run.candidates[:2]],
        "exclude",
    )
    after = knowledge_overview(store, project.id)

    assert {candidate.user_decision for candidate in updated} == {"exclude"}
    assert after.state.status == "candidates_pending"
    assert after.state.active_corpus_version_id == ""
    assert after.latest_corpus_version is None
    assert after.state.active_plan_id == before_state.active_plan_id
    assert after.state.active_intent_id == before_state.active_intent_id
    assert after.state.last_search_at == before_state.last_search_at
    assert after.state.candidate_count == before_state.candidate_count
    assert store.get_latest_project_corpus_version(project.id).id == built_version_id


def test_candidate_decisions_reject_superseded_or_stale_candidates_without_partial_mutation(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    initial = ensure_project_knowledge_initialized(store, project)
    original_plan_id = initial.latest_plan.id
    original_run = run_agent_search_plan(store, project.id, original_plan_id, providers=[_static_provider()])
    original_candidate_ids = [candidate.id for candidate in original_run.candidates[:2]]

    regenerated = regenerate_project_knowledge(store, project, [])
    replacement_plan_id = regenerated.latest_plan.id
    run_agent_search_plan(store, project.id, replacement_plan_id, providers=[_static_provider()])
    replacement_candidates = store.list_prior_art_candidates(project.id, replacement_plan_id)
    active_candidate_id = replacement_candidates[0].id

    with pytest.raises(ProjectKnowledgeConflictError, match="active search plan"):
        update_project_candidate_decision(store, project.id, original_candidate_ids[0], "include")
    assert store.list_prior_art_candidates(project.id, original_plan_id)[0].user_decision == "pending"

    with pytest.raises(ProjectKnowledgeConflictError, match="active search plan"):
        bulk_update_project_candidate_decisions(
            store,
            project.id,
            [active_candidate_id, original_candidate_ids[0]],
            "include",
        )
    refreshed_active_candidates = {candidate.id: candidate for candidate in store.list_prior_art_candidates(project.id, replacement_plan_id)}
    assert refreshed_active_candidates[active_candidate_id].user_decision == "pending"

    mutated_project = project.model_copy(update={"draft_text": "改为桥梁裂缝检测和声学视觉复检。"})
    mark_stale_if_project_changed(store, mutated_project, [])

    with pytest.raises(ProjectKnowledgeConflictError, match="stale"):
        update_project_candidate_decision(store, project.id, active_candidate_id, "include")
    assert store.list_prior_art_candidates(project.id, replacement_plan_id)[0].user_decision == "pending"


def test_superseded_plan_cannot_run_or_build_and_does_not_reactivate(tmp_path):
    store = SQLiteStore(tmp_path / "knowledge.sqlite3")
    project = build_project_record(ProjectCreate(name="城市体检智能体", draft_text="任务编排和证据链复核。"))
    store.create_project(project)
    initial = ensure_project_knowledge_initialized(store, project)
    original_plan_id = initial.latest_plan.id

    run_agent_search_plan(store, project.id, original_plan_id, providers=[_static_provider()])
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

    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
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
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
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
    after_run = run_agent_search_plan(store, project.id, overview.latest_plan.id, providers=[_static_provider()])
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
