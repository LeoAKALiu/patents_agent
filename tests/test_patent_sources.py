from backend.app.knowledge.patent_sources import (
    CNIPA_AUTHORIZED_API_SOURCE,
    CNIPA_OFFICIAL_EXPORT_SOURCE,
    build_cnipa_query_pack,
    list_patent_source_capabilities,
)
from backend.app.schemas import AgentSearchPlan, SearchIntent, SearchPlanStrategyGroup


def test_patent_source_capabilities_include_manual_cnipa_export():
    capabilities = {source.source_id: source for source in list_patent_source_capabilities()}

    assert CNIPA_OFFICIAL_EXPORT_SOURCE in capabilities
    cnipa = capabilities[CNIPA_OFFICIAL_EXPORT_SOURCE]
    assert cnipa.display_name == "CNIPA 官方导出"
    assert cnipa.jurisdictions == ["CN"]
    assert cnipa.modes == ["official_export"]
    assert cnipa.availability == "manual_import"
    assert cnipa.trusted_patent_source is True
    assert cnipa.evidence_origin == "official_export"
    assert "CNIPA" in cnipa.setup_hint

    assert CNIPA_AUTHORIZED_API_SOURCE in capabilities
    assert capabilities[CNIPA_AUTHORIZED_API_SOURCE].availability == "unavailable"


def test_build_cnipa_query_pack_uses_plan_queries_and_filters():
    intent = SearchIntent(
        id="intent-1",
        project_id="p-1",
        source_project_hash="hash",
        technical_object="城市体检智能体",
        technical_problem="任务编排缺少可信复核",
        technical_means="多智能体任务编排和证据链复核",
        technical_effect="提高报告可信度",
        keywords_zh=["城市体检", "智能体", "任务编排", "证据链"],
        negative_keywords=["医疗体检"],
        ipc_candidates=["G06Q"],
        cpc_candidates=["G06Q10/063"],
        jurisdictions=["CN", "WO"],
        date_range="2016-2026",
    )
    plan = AgentSearchPlan(
        id="plan-1",
        project_id="p-1",
        intent_id="intent-1",
        strategy_groups=[
            SearchPlanStrategyGroup(
                id="broad-recall",
                label="宽召回检索",
                purpose="尽量找全公开和授权专利。",
                queries=["城市体检 智能体 任务编排 证据链"],
                sources=["cnipa_official_export"],
            )
        ],
        target_sources=["cnipa_official_export"],
        filters={"jurisdictions": ["CN"], "date_range": "2016-2026"},
    )

    pack = build_cnipa_query_pack(intent, plan)

    assert pack.project_id == "p-1"
    assert pack.plan_id == "plan-1"
    assert pack.source_id == "cnipa_official_export"
    assert pack.keywords_zh == ["城市体检", "智能体", "任务编排", "证据链"]
    assert pack.negative_keywords == ["医疗体检"]
    assert pack.ipc_candidates == ["G06Q"]
    assert pack.cpc_candidates == ["G06Q10/063"]
    assert pack.date_range == "2016-2026"
    assert pack.strategies[0].strategy_group_id == "broad-recall"
    assert pack.strategies[0].queries == ["城市体检 智能体 任务编排 证据链"]
