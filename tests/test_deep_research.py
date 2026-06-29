"""Tests for the free patent deep research mode.

Boundaries verified here:

* Standard disclosures keep their existing pipeline byte-for-byte.
* ``free_deep_research`` mode adds deep research stages but never unlocks
  the official-export gate (compile + post-draft review remain required).
* The deep-research loop survives empty prior-art results and emits
  warnings explaining the degraded state.
* ``DeepResearchPacket`` round-trips through Pydantic without loss.

The integration tests inject an offline search provider so they never touch the
network — production builds a live multi-provider chain, but tests stay
deterministic.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.research.deep_researcher import (
    FakeDeepResearchProvider,
    PatentDeepResearcher,
)
from backend.app.schemas import (
    DeepResearchEvidenceRef,
    DeepResearchFinding,
    DeepResearchPacket,
    PatentPointCandidate,
    PriorArtHit,
    ProjectRecord,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _prior_art_hit() -> PriorArtHit:
    return PriorArtHit(
        id="h1",
        source="Google Patents",
        query="图像 缺陷",
        title="一种图像缺陷检测方法",
        publication_number="CN123456789A",
        url="https://patents.google.com/patent/CN123456789A",
        abstract="公开了一种图像缺陷检测方法。",
    )


def _user_candidate(candidate_id: str = "p1", selected: bool = True) -> PatentPointCandidate:
    return PatentPointCandidate(
        id=candidate_id,
        title="实时图像缺陷识别",
        technical_problem="缺陷检测效率低",
        innovation="神经网络实时反馈",
        technical_solution="采集图像并实时输出缺陷位置。",
        protection_focus=["方法", "系统"],
        selected=selected,
    )


def _deep_research_llm_responses() -> dict[str, str]:
    return {
        "deep_research_plan": (
            '{"research_questions":["新颖性"],"technical_field":"图像处理",'
            '"claim_elements":["实时反馈","缺陷定位"],'
            '"search_themes":[{"theme":"缺陷检测","keywords":["缺陷","检测","神经网络"],'
            '"rationale":"核心"}],"max_cycles":1,"stop_conditions":["覆盖核心特征"]}'
        ),
        "deep_research_queries_c1": '["缺陷 检测 神经网络"]',
        "deep_research_synthesis_c1": (
            '{"findings":[{"id":"f1","category":"differentiator","title":"实时反馈差异",'
            '"summary":"现有技术未实现实时反馈。","severity":"medium",'
            '"suggested_action":"在权利要求中强调实时反馈。",'
            '"evidence":[{"source":"Google Patents","query":"缺陷 检测","title":"一种图像缺陷检测方法",'
            '"publication_number":"CN123456789A","url":"https://patents.google.com/patent/CN123456789A",'
            '"relevance":"涉及图像缺陷检测"}]}],'
            '"novelty_opportunities":["实时反馈方向"],'
            '"differentiators":["闭环反馈步骤"],'
            '"claim_drafting_constraints":["避免纯功能性概括"],'
            '"warnings":[],"suggested_completion_tasks":["补充实验数据"],'
            '"should_continue":false,"next_queries":[]}'
        ),
        "deep_research_obviousness_c1": (
            '{"obviousness_risks":["审查员可能组合 CN123456789A 与通用神经网络教科书攻击创造性"],'
            '"claim_drafting_constraints":["强调实时闭环的结构耦合，避免被拆解组合"]}'
        ),
    }


def _standard_disclosure_responses() -> dict[str, str]:
    return {
        "disclosure_scan": '{"summary":"图像缺陷识别","materials_summary":"材料覆盖","technical_keywords":["图像"],"implementation_gaps":[]}',
        "patent_points": '{"candidates":[{"id":"p1","title":"图像缺陷识别方法","technical_problem":"效率低","innovation":"神经网络检测","technical_solution":"采集并检测","beneficial_effects":["提高效率"],"protection_focus":["方法","系统"],"grantability_score":0.8,"rationale":"完整"}],"selected_candidate_id":"p1"}',
        "prior_art_terms": '["图像 缺陷 神经网络"]',
        "prior_art_relevance": '{"prior_art_differences":"区别在实时反馈。","hits":[{"id":"h1","relevance_summary":"涉及缺陷检测。","differentiators":["缺少实时反馈"]}]}',
        "disclosure_body": "# 交底书正文",
        "disclosure_mermaid": "flowchart TD\nA[采集] --> B[输出]",
        "disclosure_image_prompt": "黑白线稿。",
        "disclosure_self_check": '[{"category":"术语","severity":"low","message":"术语一致。","suggestion":"无。"}]',
    }


def _disclosure_llm(include_deep_research: bool) -> FakeLLMClient:
    responses = _standard_disclosure_responses()
    if include_deep_research:
        responses.update(_deep_research_llm_responses())
    return FakeLLMClient(responses)


# ---------------------------------------------------------------------------
# Unit tests for the deep researcher
# ---------------------------------------------------------------------------


def test_patent_deep_researcher_produces_packet_with_findings() -> None:
    llm = FakeLLMClient(_deep_research_llm_responses())
    provider = FakeDeepResearchProvider(hits=[_prior_art_hit()])
    researcher = PatentDeepResearcher(llm=llm, search_provider=provider, max_cycles=2)
    project = ProjectRecord(
        id="proj-1",
        name="图像缺陷识别",
        draft_text="一种基于神经网络的图像缺陷识别方法。",
    )

    packet, stages = researcher.research(
        project=project,
        candidates=[_user_candidate("p1")],
        selected_candidate_id="p1",
    )

    assert packet.status == "completed"
    assert packet.internal_only is True
    assert packet.findings, "expected at least one finding"
    assert packet.findings[0].category == "differentiator"
    assert "闭环反馈" in packet.differentiators[0]
    assert "补充实验数据" in packet.suggested_completion_tasks
    phase_names = {stage["phase"] for stage in stages}
    assert "deep_research_plan" in phase_names
    assert "deep_research_queries_c1" in phase_names
    assert "deep_research_search_c1" in phase_names
    assert "deep_research_synthesis_c1" in phase_names
    assert "deep_research_evidence" in phase_names
    assert "deep_research_final" in phase_names
    # Search provider must have actually been called by the loop.
    assert provider.calls, "expected the search provider to have been invoked"
    # Evidence ledger should record the retrieved hit.
    assert packet.evidence_ledger, "expected evidence ledger entries"
    assert packet.evidence_ledger[0]["publication_number"] == "CN123456789A"


def test_deep_research_plan_prompt_includes_project_metadata() -> None:
    llm = FakeLLMClient(_deep_research_llm_responses())
    provider = FakeDeepResearchProvider(hits=[])
    researcher = PatentDeepResearcher(llm=llm, search_provider=provider, max_cycles=1)
    project = ProjectRecord(
        id="proj-meta",
        name="道路病害检测",
        draft_text="一种道路病害检测方法。",
        technical_field="计算机视觉、市政工程检测",
        background="人工巡检效率低。",
        pain_point="夜间检测误检率高。",
        technical_solution="可见光、红外和激光雷达多模态融合。",
        innovation="跨模态特征对齐。",
        embodiments="车载多传感器巡检。",
        beneficial_effects="夜间检测准确率提升。",
    )

    researcher.research(project=project, candidates=[_user_candidate("p1")])

    plan_call = next(call for call in llm.calls if call.stage == "deep_research_plan")
    assert "计算机视觉、市政工程检测" in plan_call.user_prompt
    assert "跨模态特征对齐" in plan_call.user_prompt
    assert "夜间检测准确率提升" in plan_call.user_prompt


def test_deep_research_broadens_queries_after_empty_cycle() -> None:
    class EmptyThenHitProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], int]] = []

        def search(self, terms: list[str], limit: int) -> tuple[list[PriorArtHit], list[str]]:
            self.calls.append((list(terms), limit))
            if len(self.calls) == 1:
                return [], []
            return [_prior_art_hit()], []

    llm = FakeLLMClient(_deep_research_llm_responses())
    provider = EmptyThenHitProvider()
    researcher = PatentDeepResearcher(llm=llm, search_provider=provider, max_cycles=1)
    project = ProjectRecord(
        id="proj-retry",
        name="图像缺陷识别",
        draft_text="一种基于神经网络的图像缺陷识别方法。",
    )

    packet, _stages = researcher.research(
        project=project,
        candidates=[_user_candidate("p1")],
        selected_candidate_id="p1",
    )

    assert len(provider.calls) == 2
    assert any("图像缺陷识别" in term for term in provider.calls[1][0])
    assert packet.status == "completed"
    assert packet.evidence_ledger, "expected evidence ledger entries"
    assert packet.evidence_ledger[0]["publication_number"] == "CN123456789A"


def test_patent_deep_researcher_handles_empty_prior_art() -> None:
    llm = FakeLLMClient(_deep_research_llm_responses())
    provider = FakeDeepResearchProvider(hits=[], warnings=["live search returned no hits"])
    researcher = PatentDeepResearcher(llm=llm, search_provider=provider, max_cycles=1)
    project = ProjectRecord(
        id="proj-empty", name="空命中", draft_text="一种少见技术领域的方法。"
    )

    packet, _ = researcher.research(project=project, candidates=[_user_candidate("p1")])

    assert packet.status in {"completed", "partial"}
    # When the LLM still emits structured findings we end up "completed"; when
    # the loop has no findings we end up "partial" with explicit warnings.
    assert packet.warnings, "expected warnings to surface degraded state"


def test_deep_researcher_downgrades_ungrounded_assertion() -> None:
    """A synthesis finding that asserts prior art it never retrieved must be
    downgraded rather than presented as evidence-backed."""

    responses = _deep_research_llm_responses()
    responses["deep_research_synthesis_c1"] = (
        '{"findings":[{"id":"f1","category":"differentiator","title":"凭空捏造",'
        '"summary":"某专利公开了相同方案。","severity":"high",'
        '"evidence":[{"source":"x","title":"不存在","publication_number":"CN999X","url":""}]}],'
        '"novelty_opportunities":[],"differentiators":[],"claim_drafting_constraints":[],'
        '"warnings":[],"suggested_completion_tasks":[],"should_continue":false,"next_queries":[]}'
    )
    llm = FakeLLMClient(responses)
    provider = FakeDeepResearchProvider(hits=[_prior_art_hit()])  # ledger has CN123456789A only
    researcher = PatentDeepResearcher(llm=llm, search_provider=provider, max_cycles=1)
    project = ProjectRecord(id="p", name="x", draft_text="y")

    packet, _ = researcher.research(project=project, candidates=[_user_candidate("p1")])
    categories = {finding.category for finding in packet.findings}
    assert "differentiator" not in categories  # downgraded
    assert "evidence_gap" in categories
    assert any("未取证假设" in finding.summary for finding in packet.findings)


def test_deep_research_packet_round_trips_through_pydantic() -> None:
    packet = DeepResearchPacket(
        status="completed",
        cycles=2,
        project_id="proj-x",
        query_plan=["图像 缺陷"],
        queries_run=["图像 缺陷", "缺陷 检测 神经网络"],
        prior_art_clusters=[{"图像缺陷检测": ["CN123456789A"]}],
        novelty_opportunities=["实时反馈方向"],
        differentiators=["闭环反馈"],
        claim_drafting_constraints=["避免纯功能性概括"],
        obviousness_risks=["组合攻击风险"],
        evidence_map={"实时反馈差异": ["CN123456789A"]},
        evidence_ledger=[{"evidence_id": "E001", "publication_number": "CN123456789A"}],
        provider_chain=["patent", "arxiv"],
        suggested_completion_tasks=["补充实验数据"],
        warnings=["部分文献无法获取全文"],
        findings=[
            DeepResearchFinding(
                id="f1",
                category="differentiator",
                title="实时反馈差异",
                summary="现有技术未实现实时反馈。",
                severity="medium",
                suggested_action="强调反馈步骤。",
                evidence=[
                    DeepResearchEvidenceRef(
                        source="Google Patents",
                        query="缺陷 检测",
                        title="一种图像缺陷检测方法",
                        publication_number="CN123456789A",
                        url="https://patents.google.com/patent/CN123456789A",
                        relevance="涉及图像缺陷检测",
                    )
                ],
            )
        ],
        generation_logs=["cycle 1: 1 hits"],
    )

    dumped = packet.model_dump(mode="json")
    assert dumped["status"] == "completed"
    assert dumped["internal_only"] is True
    reloaded = DeepResearchPacket.model_validate(dumped)
    assert reloaded.findings[0].evidence[0].publication_number == "CN123456789A"
    assert reloaded.differentiators == ["闭环反馈"]
    assert reloaded.obviousness_risks == ["组合攻击风险"]
    assert reloaded.provider_chain == ["patent", "arxiv"]


def test_fake_deep_research_provider_records_calls() -> None:
    hit = _prior_art_hit()
    provider = FakeDeepResearchProvider(hits=[hit])
    results, warnings = provider.search(["图像 缺陷"], 3)
    assert [h.id for h in results] == ["h1"]
    assert warnings == []
    assert provider.calls == [(["图像 缺陷"], 3)]


# ---------------------------------------------------------------------------
# Integration: API endpoint with research_mode (offline injected provider)
# ---------------------------------------------------------------------------


def _make_client(tmp_path: Path, include_deep_research: bool, hits: list[PriorArtHit]) -> TestClient:
    # Inject an offline search provider so the deep researcher never hits the
    # network during tests. StaticPriorArtProvider satisfies the
    # search(terms, limit) -> (hits, warnings) contract.
    return TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_disclosure_llm(include_deep_research=include_deep_research),
            prior_art_provider=StaticPriorArtProvider(hits=hits),
            research_search_provider=StaticPriorArtProvider(hits=hits),
        )
    )


def _create_project(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/projects",
        json={"name": name, "draft_text": "一种基于神经网络的图像缺陷识别方法。"},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_standard_mode_keeps_existing_disclosure_behaviour(tmp_path: Path) -> None:
    client = _make_client(tmp_path, include_deep_research=False, hits=[_prior_art_hit()])
    project_id = _create_project(client, "标准模式")
    response = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 8, "research_mode": "standard"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["research_mode"] == "standard"
    phases = [stage.get("phase") for stage in run["stage_results"] if isinstance(stage, dict)]
    assert "project_scan" in phases
    assert "prior_art_search" in phases
    assert "deep_research_material_intake" in phases
    assert not any(
        p and p.startswith("deep_research_") and p != "deep_research_material_intake"
        for p in phases
    )
    assert run["package"] is not None
    assert not any(
        "free_deep_research" in log or "deep_research:" in log
        for log in run["package"]["generation_logs"]
    )


def test_free_deep_research_mode_appends_deep_research_stages(tmp_path: Path) -> None:
    client = _make_client(tmp_path, include_deep_research=True, hits=[_prior_art_hit()])
    project_id = _create_project(client, "Deep Research 模式")
    response = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 8, "research_mode": "free_deep_research"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["research_mode"] == "free_deep_research"

    phases = [stage.get("phase") for stage in run["stage_results"] if isinstance(stage, dict)]
    assert "deep_research_plan" in phases
    assert any(p and p.startswith("deep_research_synthesis_") for p in phases)
    assert "deep_research_evidence" in phases
    assert "deep_research_final" in phases

    package = run["package"]
    assert package is not None
    # Internal-only notice must appear in generation_logs.
    assert any(
        "free_deep_research: internal supporting research packet" in log
        for log in package["generation_logs"]
    )
    # prior_art_differences may be augmented with neutral technical analysis,
    # but internal process labels must not enter draft-generation context.
    assert "补充现有技术差异分析" in package["prior_art_differences"]
    assert "Free Deep Research" not in package["prior_art_differences"]
    assert "free_deep_research" not in package["prior_art_differences"]
    assert "Free Deep Research" not in package["body_markdown"]
    assert "free_deep_research" not in package["body_markdown"]


def test_free_deep_research_does_not_unlock_official_export(tmp_path: Path) -> None:
    client = _make_client(tmp_path, include_deep_research=True, hits=[_prior_art_hit()])
    project_id = _create_project(client, "Deep Research 不解锁导出")
    disclosure_response = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 8, "research_mode": "free_deep_research"},
    )
    assert disclosure_response.status_code == 200

    # Official compile must still be gated — there is no draft yet.
    compile_response = client.post(
        f"/api/projects/{project_id}/official-compile-runs",
        json={},
    )
    assert compile_response.status_code == 409, compile_response.text

    # And official export must not be readable.
    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code in {404, 409}


def test_free_deep_research_with_no_prior_art_still_completes(tmp_path: Path) -> None:
    client = _make_client(tmp_path, include_deep_research=True, hits=[])
    project_id = _create_project(client, "无现有技术")
    response = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 8, "research_mode": "free_deep_research"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    # Should surface at least one explanatory warning event.
    warning_events = [event for event in run["events"] if event.startswith("warning:")]
    assert warning_events, "expected explanatory warnings when provider returned no hits"
