import json
import sqlite3

from backend.app.schemas import (
    DeliberationRun,
    DeliberationStageResult,
    DisclosurePackage,
    DisclosureRun,
    MoatScores,
    PatentPointCandidate,
    PatentPointCreate,
    PatentStrategyBrief,
    PriorArtHit,
    ProjectRecord,
)
from fastapi.testclient import TestClient

from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.storage import SQLiteStore


def test_patent_point_defaults_support_unverified_user_schemes():
    payload = PatentPointCreate(
        title="遮挡构件语义补全方法",
        technical_problem="遮挡导致门窗洞口漏识别",
        innovation="用多视角互证补全遮挡洞口",
        technical_solution="获取多视角图像和点云，反投二维语义并补全洞口边界。",
        evidence_status="feasible_unverified",
        source_type="user",
        feasibility_basis="已有多视角图像和点云输入，算法路径可实现。",
    )

    candidate = payload.to_candidate("p-user-1")

    assert candidate.id == "p-user-1"
    assert candidate.evidence_status == "feasible_unverified"
    assert candidate.source_type == "user"
    assert candidate.moat_scores.support_strength == 0.2
    assert candidate.support_gaps == ["提交前需补充实验或工程样例。"]


def test_existing_candidate_payloads_remain_backward_compatible():
    candidate = PatentPointCandidate(
        id="p1",
        title="图像缺陷识别方法及系统",
        technical_problem="人工检测效率低",
        innovation="基于神经网络输出缺陷位置",
        technical_solution="采集图像、训练模型并输出缺陷位置",
    )

    assert candidate.evidence_status == "model_generated"
    assert isinstance(candidate.moat_scores, MoatScores)


def test_patent_point_create_passes_claim_chart_to_candidate():
    payload = PatentPointCreate(
        title="遮挡构件语义补全方法",
        technical_problem="遮挡导致门窗洞口漏识别",
        innovation="用多视角互证补全遮挡洞口",
        technical_solution="获取多视角图像和点云，反投二维语义并补全洞口边界。",
        claim_chart=[
            {
                "prior_art_id": "cn-1",
                "prior_art_title": "既有洞口识别方法",
                "overlapping_features": ["识别门窗洞口"],
                "differentiating_features": ["多视角互证补全遮挡边界"],
                "claim_drafting_advice": "突出遮挡场景下的边界补全步骤。",
            }
        ],
    )

    candidate = payload.to_candidate("p-user-2")

    assert len(candidate.claim_chart) == 1
    assert candidate.claim_chart[0].prior_art_id == "cn-1"
    assert candidate.claim_chart[0].differentiating_features == ["多视角互证补全遮挡边界"]


def test_project_patent_point_crud_and_selection(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_response = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    )
    project_id = project_response.json()["id"]

    create_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "树木和防盗网遮挡导致洞口漏识别",
            "innovation": "多视角语义互证并补全洞口边界",
            "technical_solution": "融合点云、图像和楼层规律生成洞口边界。",
            "beneficial_effects": ["降低洞口漏检率"],
            "protection_focus": ["方法", "系统", "介质"],
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "feasibility_basis": "已有多视角图像、点云和人工复核记录。",
            "selected": True,
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["source_type"] == "user"
    assert created["selected"] is True

    list_response = client.get(f"/api/projects/{project_id}/patent-points")
    assert list_response.status_code == 200
    assert list_response.json()["points"][0]["title"] == "遮挡洞口语义补全"

    patch_response = client.patch(
        f"/api/projects/{project_id}/patent-points/{created['id']}",
        json={"evidence_status": "needs_experiment", "experiment_needed": ["用10栋楼样例统计洞口召回率"]},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["evidence_status"] == "needs_experiment"

    delete_response = client.delete(f"/api/projects/{project_id}/patent-points/{created['id']}")
    assert delete_response.status_code == 200
    assert client.get(f"/api/projects/{project_id}/patent-points").json()["points"] == []


def test_project_patent_point_patch_rejects_null_without_corruption(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = _create_project(client)
    point = _create_patent_point(client, project_id, title="原始创新点")

    patch_response = client.patch(
        f"/api/projects/{project_id}/patent-points/{point['id']}",
        json={"title": None},
    )

    assert patch_response.status_code == 422
    points = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    assert points[0]["title"] == "原始创新点"


def test_project_patent_point_patch_merges_partial_moat_scores(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = _create_project(client)
    point = _create_patent_point(client, project_id)

    patch_response = client.patch(
        f"/api/projects/{project_id}/patent-points/{point['id']}",
        json={"moat_scores": {"scope_width": 0.5}},
    )

    assert patch_response.status_code == 200
    moat_scores = patch_response.json()["moat_scores"]
    assert moat_scores["scope_width"] == 0.5
    assert moat_scores["feasibility"] == 0.5
    assert moat_scores["support_strength"] == 0.2
    assert moat_scores["strategic_value"] == 0.6


def test_evaluate_moat_persists_llm_scores_and_rationale(tmp_path):
    llm = FakeLLMClient(
        {
            "moat_scoring": json.dumps(
                {
                    "scope_width": 0.82,
                    "designaround_difficulty": 0.7,
                    "feasibility": 0.6,
                    "support_strength": 0.45,
                    "prior_art_distance": 0.78,
                    "strategic_value": 0.88,
                    "rationale": "权利要求覆盖多视角互证，绕开需复刻整套流程；说明书提供了点云与图像证据。",
                },
                ensure_ascii=False,
            )
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    project_id = _create_project(client)
    point = _create_patent_point(client, project_id)

    evaluate_response = client.post(
        f"/api/projects/{project_id}/patent-points/{point['id']}/evaluate-moat"
    )

    assert evaluate_response.status_code == 200
    updated = evaluate_response.json()
    assert updated["moat_scores"]["scope_width"] == 0.82
    assert updated["moat_scores"]["strategic_value"] == 0.88
    assert "多视角互证" in updated["moat_rationale"]

    listed = client.get(f"/api/projects/{project_id}/patent-points").json()["points"][0]
    assert listed["moat_scores"]["prior_art_distance"] == 0.78
    assert listed["moat_rationale"] == updated["moat_rationale"]

    moat_call = next(call for call in llm.calls if call.stage == "moat_scoring")
    assert point["title"] in moat_call.user_prompt


def test_evaluate_moat_clamps_out_of_range_and_falls_back_on_garbage(tmp_path):
    llm = FakeLLMClient(
        {
            "moat_scoring": "这不是合法 JSON，模型偶尔会这样返回。"
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    project_id = _create_project(client)
    point = _create_patent_point(client, project_id)

    evaluate_response = client.post(
        f"/api/projects/{project_id}/patent-points/{point['id']}/evaluate-moat"
    )

    assert evaluate_response.status_code == 200
    fallback = evaluate_response.json()
    assert fallback["moat_scores"]["feasibility"] == 0.5
    assert fallback["moat_scores"]["strategic_value"] == 0.5
    assert "占位分" in fallback["moat_rationale"]


def test_evaluate_moat_returns_404_for_unknown_point(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/patent-points/does-not-exist/evaluate-moat")

    assert response.status_code == 404


def test_project_patent_point_cross_project_patch_returns_404(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_a = _create_project(client, name="项目A")
    project_b = _create_project(client, name="项目B")
    point = _create_patent_point(client, project_a, title="项目A创新点")

    patch_response = client.patch(
        f"/api/projects/{project_b}/patent-points/{point['id']}",
        json={"title": "错误更新"},
    )

    assert patch_response.status_code == 404
    points_a = client.get(f"/api/projects/{project_a}/patent-points").json()["points"]
    points_b = client.get(f"/api/projects/{project_b}/patent-points").json()["points"]
    assert points_a[0]["title"] == "项目A创新点"
    assert points_b == []


def test_project_patent_point_selection_is_project_scoped(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_a = _create_project(client, name="项目A")
    project_b = _create_project(client, name="项目B")
    first_a = _create_patent_point(client, project_a, title="项目A第一点", selected=True)
    point_b = _create_patent_point(client, project_b, title="项目B第一点", selected=True)
    second_a = _create_patent_point(client, project_a, title="项目A第二点", selected=True)

    points_a = client.get(f"/api/projects/{project_a}/patent-points").json()["points"]
    points_b = client.get(f"/api/projects/{project_b}/patent-points").json()["points"]

    selected_a = {point["id"]: point["selected"] for point in points_a}
    assert selected_a[first_a["id"]] is False
    assert selected_a[second_a["id"]] is True
    assert points_b == [point_b]


def test_project_patent_point_storage_allows_same_point_id_per_project(tmp_path):
    store = SQLiteStore(tmp_path / "patents_agent.sqlite3")
    store.create_project(ProjectRecord(id="project-a", name="项目A", draft_text="草稿A"))
    store.create_project(ProjectRecord(id="project-b", name="项目B", draft_text="草稿B"))
    point_a = PatentPointCandidate(
        id="shared-point",
        title="项目A创新点",
        technical_problem="问题A",
        innovation="创新A",
        technical_solution="方案A",
        selected=True,
    )
    point_b = point_a.model_copy(update={"title": "项目B创新点", "selected": True})

    store.add_project_patent_point("project-a", point_a)
    store.add_project_patent_point("project-b", point_b)

    assert store.get_project_patent_point("project-a", "shared-point").title == "项目A创新点"
    assert store.get_project_patent_point("project-b", "shared-point").title == "项目B创新点"


def test_project_patent_point_migrates_legacy_global_primary_key(tmp_path):
    db_path = tmp_path / "patents_agent.sqlite3"
    legacy_point = PatentPointCandidate(
        id="shared-point",
        title="项目A旧创新点",
        technical_problem="问题A",
        innovation="创新A",
        technical_solution="方案A",
        selected=True,
    )
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            create table project_patent_points (
                id text primary key,
                project_id text not null,
                candidate_json text not null,
                selected integer not null default 0,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );
            """
        )
        connection.execute(
            """
            insert into project_patent_points(id, project_id, candidate_json, selected)
            values (?, ?, ?, ?)
            """,
            (
                legacy_point.id,
                "project-a",
                json.dumps(legacy_point.model_dump(mode="json"), ensure_ascii=False),
                1,
            ),
        )

    store = SQLiteStore(db_path)
    store.create_project(ProjectRecord(id="project-a", name="项目A", draft_text="草稿A"))
    store.create_project(ProjectRecord(id="project-b", name="项目B", draft_text="草稿B"))
    point_b = legacy_point.model_copy(update={"title": "项目B创新点", "selected": True})

    points_a = store.list_project_patent_points("project-a")
    store.add_project_patent_point("project-b", point_b)
    points_b = store.list_project_patent_points("project-b")

    assert [point.title for point in points_a] == ["项目A旧创新点"]
    assert [point.title for point in store.list_project_patent_points("project-a")] == ["项目A旧创新点"]
    assert [point.title for point in points_b] == ["项目B创新点"]


def test_user_patent_point_is_preserved_in_disclosure_generation(tmp_path):
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"外立面逆建模项目","materials_summary":"材料覆盖点云和图像","technical_keywords":["点云","图像"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":[{"id":"p-model","title":"模型生成点","technical_problem":"人工建模效率低","innovation":"自动生成构件","technical_solution":"采集点云并生成构件","beneficial_effects":["提高效率"],"protection_focus":["方法"],"grantability_score":0.7,"rationale":"结构完整"}],"selected_candidate_id":"p-model"}',
            "prior_art_terms": '["外立面 逆建模 遮挡"]',
            "prior_art_relevance": '{"prior_art_differences":"用户点区别在遮挡洞口补全。","hits":[]}',
            "disclosure_body": "# 技术交底书\n包含遮挡洞口语义补全作为可选实施例。",
            "disclosure_mermaid": "flowchart TD\nA[图像] --> B[补全]",
            "disclosure_image_prompt": "黑白线稿，展示遮挡洞口补全。",
            "disclosure_self_check": "[]",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "遮挡导致洞口漏识别",
            "innovation": "多视角互证补全洞口",
            "technical_solution": "融合点云和图像补全洞口边界。",
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "selected": True,
        },
    )

    run = client.post(f"/api/projects/{project_id}/disclosures", json={"trace": False, "max_prior_art_results": 0}).json()

    titles = [item["title"] for item in run["package"]["candidates"]]
    assert titles[0] == "遮挡洞口语义补全"
    assert run["package"]["selected_candidate_id"].startswith("user-")
    assert run["package"]["candidates"][0]["support_gaps"] == ["提交前需补充实验或工程样例。"]


def test_disclosure_adds_claim_chart_to_user_candidate(tmp_path):
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"外立面逆建模项目","materials_summary":"材料覆盖点云","technical_keywords":["点云"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":[],"selected_candidate_id":""}',
            "prior_art_terms": '["外立面 逆建模"]',
            "prior_art_relevance": '{"prior_art_differences":"区别在遮挡洞口补全。","hits":[{"id":"h1","relevance_summary":"公开点云建模。","differentiators":["未公开遮挡洞口补全"]}],"claim_charts":[{"candidate_id":"user-fixed","prior_art_id":"h1","prior_art_title":"LLM编造的错误标题","overlapping_features":["点云建模"],"differentiating_features":["遮挡洞口补全"],"claim_drafting_advice":"将多视角互证补全写入从属权利要求。"}]}',
            "disclosure_body": "# 技术交底书\n遮挡洞口补全。",
            "disclosure_mermaid": "flowchart TD\nA[点云] --> B[补全]",
            "disclosure_image_prompt": "黑白线稿。",
            "disclosure_self_check": "[]",
        }
    )
    provider = StaticPriorArtProvider(
        hits=[
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query="外立面 逆建模",
                title="一种点云建模方法",
                publication_number="CN000000001A",
                url="https://patents.google.com/patent/CN000000001A",
            )
        ]
    )
    generator = DisclosureGenerator(llm, provider)
    user_candidate = PatentPointCreate(
        title="遮挡洞口语义补全",
        technical_problem="遮挡导致洞口漏识别",
        innovation="多视角互证补全洞口",
        technical_solution="融合点云和图像补全洞口边界。",
        evidence_status="feasible_unverified",
        source_type="user",
        selected=True,
    ).to_candidate("user-fixed")

    package, stage_results, _ = generator.generate(
        project=ProjectRecord(id="p1", name="外立面逆建模", draft_text="一种既有建筑外立面逆建模方法。"),
        materials=[],
        context_chunks=[],
        max_prior_art_results=8,
        user_candidates=[user_candidate],
    )

    assert package.candidates[0].claim_chart[0].differentiating_features == ["遮挡洞口补全"]
    assert package.candidates[0].claim_chart[0].claim_drafting_advice == "将多视角互证补全写入从属权利要求。"
    assert package.candidates[0].claim_chart[0].prior_art_title == "一种点云建模方法"
    relevance_payload = next(item["payload"] for item in stage_results if item["phase"] == "prior_art_relevance")
    assert relevance_payload["claim_charts"][0]["candidate_id"] == "user-fixed"
    assert relevance_payload["claim_charts"][0]["prior_art_id"] == "h1"
    assert relevance_payload["claim_charts"][0]["prior_art_title"] == "一种点云建模方法"


def test_disclosure_ignores_claim_chart_for_unknown_prior_art_hit(tmp_path):
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"外立面逆建模项目","materials_summary":"材料覆盖点云","technical_keywords":["点云"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":[],"selected_candidate_id":""}',
            "prior_art_terms": '["外立面 逆建模"]',
            "prior_art_relevance": '{"prior_art_differences":"区别在遮挡洞口补全。","hits":[{"id":"h1","relevance_summary":"公开点云建模。","differentiators":["未公开遮挡洞口补全"]}],"claim_charts":[{"candidate_id":"user-fixed","prior_art_id":"h1","prior_art_title":"一种点云建模方法","overlapping_features":["点云建模"],"differentiating_features":["遮挡洞口补全"],"claim_drafting_advice":"保留有效证据。"},{"candidate_id":"user-fixed","prior_art_id":"hallucinated-hit","prior_art_title":"不存在的现有技术","overlapping_features":["不存在"],"differentiating_features":["不得采纳"],"claim_drafting_advice":"不得进入权利要求图表。"},{"candidate_id":"unknown-candidate","prior_art_id":"h1","prior_art_title":"一种点云建模方法","overlapping_features":["点云建模"],"differentiating_features":["不得采纳"],"claim_drafting_advice":"候选不存在。"}]}',
            "disclosure_body": "# 技术交底书\n遮挡洞口补全。",
            "disclosure_mermaid": "flowchart TD\nA[点云] --> B[补全]",
            "disclosure_image_prompt": "黑白线稿。",
            "disclosure_self_check": "[]",
        }
    )
    provider = StaticPriorArtProvider(
        hits=[
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query="外立面 逆建模",
                title="一种点云建模方法",
                publication_number="CN000000001A",
                url="https://patents.google.com/patent/CN000000001A",
            )
        ]
    )
    generator = DisclosureGenerator(llm, provider)
    user_candidate = PatentPointCreate(
        title="遮挡洞口语义补全",
        technical_problem="遮挡导致洞口漏识别",
        innovation="多视角互证补全洞口",
        technical_solution="融合点云和图像补全洞口边界。",
        evidence_status="feasible_unverified",
        source_type="user",
        selected=True,
    ).to_candidate("user-fixed")

    package, stage_results, _ = generator.generate(
        project=ProjectRecord(id="p1", name="外立面逆建模", draft_text="一种既有建筑外立面逆建模方法。"),
        materials=[],
        context_chunks=[],
        max_prior_art_results=8,
        user_candidates=[user_candidate],
    )

    assert [chart.prior_art_id for chart in package.candidates[0].claim_chart] == ["h1"]
    relevance_payload = next(item["payload"] for item in stage_results if item["phase"] == "prior_art_relevance")
    assert [chart["prior_art_id"] for chart in relevance_payload["claim_charts"]] == ["h1"]


def test_draft_generation_prompt_marks_unverified_schemes_as_optional(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种外立面逆建模方法。\n2. 根据权利要求1所述的方法，其中可选地进行遮挡洞口语义补全。",
            "description": "具体实施方式\n在可选实施例中，执行遮挡洞口语义补全。",
            "abstract": "本发明公开了一种外立面逆建模方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[点云] --> B[模型]",
            "image_prompt": "黑白线稿。",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "外立面逆建模", "draft_text": "一种既有建筑外立面逆建模方法。"},
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "遮挡洞口语义补全",
            "technical_problem": "遮挡导致洞口漏识别",
            "innovation": "多视角互证补全洞口",
            "technical_solution": "融合点云和图像补全洞口边界。",
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "selected": True,
        },
    )
    _create_completed_deliberation(client, project_id)

    client.post(f"/api/projects/{project_id}/generate", json={})

    claims_prompt = next(call.user_prompt for call in llm.calls if call.stage == "claims")
    description_prompt = next(call.user_prompt for call in llm.calls if call.stage == "description")
    assert "feasible_unverified" in claims_prompt
    assert "不得写成已经完成验证的实施事实" in claims_prompt
    assert "feasible_unverified" in description_prompt
    assert "不得写成已经完成验证的实施事实" in description_prompt
    assert "1. 对 evidence_status" in description_prompt


def test_generate_prefers_completed_disclosure_over_selected_user_synthesis(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种外立面逆建模方法。",
            "description": "具体实施方式\n基于已完成交底书撰写。",
            "abstract": "本发明公开了一种外立面逆建模方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[点云] --> B[模型]",
            "image_prompt": "黑白线稿。",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, prior_art_provider=StaticPriorArtProvider(), load_env_file=False))
    project_id = _create_project(client)
    _create_patent_point(client, project_id, title="未验证用户点", selected=True)
    completed_candidate = PatentPointCandidate(
        id="completed-point",
        title="已完成交底书专利点",
        technical_problem="已完成交底书中的技术问题",
        innovation="已完成交底书中的创新",
        technical_solution="已完成交底书中的方案",
        selected=True,
    )
    completed_package = DisclosurePackage(
        title="已完成交底书",
        summary="已完成公开差异分析的交底书摘要",
        materials_summary="已完成交底书材料摘要",
        candidates=[completed_candidate],
        selected_candidate_id="completed-point",
        prior_art_hits=[],
        prior_art_differences="已完成公开现有技术差异分析。",
        body_markdown="已完成交底书正文。",
        mermaid="flowchart TD\nA[交底书] --> B[初稿]",
        image_prompt="黑白线稿。",
        self_check_findings=[],
    )
    client.app.state.store.create_disclosure_run(
        DisclosureRun(
            id="completed-run",
            project_id=project_id,
            status="completed",
            package=completed_package,
        )
    )
    _create_completed_deliberation(client, project_id)

    package = client.post(f"/api/projects/{project_id}/generate", json={}).json()

    claims_prompt = next(call.user_prompt for call in llm.calls if call.stage == "claims")
    assert "已完成交底书专利点" in claims_prompt
    assert "未验证用户点" not in claims_prompt
    assert package["disclosure_run_id"] == "completed-run"
    assert package["patent_point_summary"] == "已完成交底书专利点"


def test_generate_synthesizes_disclosure_from_selected_user_points_only(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种外立面逆建模方法。",
            "description": "具体实施方式\n基于选中用户点撰写。",
            "abstract": "本发明公开了一种外立面逆建模方法。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA[点云] --> B[模型]",
            "image_prompt": "黑白线稿。",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, prior_art_provider=StaticPriorArtProvider(), load_env_file=False))
    project_id = _create_project(client)
    _create_patent_point(client, project_id, title="未选中用户点", selected=False)
    selected = _create_patent_point(client, project_id, title="选中用户点", selected=True)
    _create_completed_deliberation(client, project_id)

    package = client.post(f"/api/projects/{project_id}/generate", json={}).json()

    claims_prompt = next(call.user_prompt for call in llm.calls if call.stage == "claims")
    assert selected["id"] in claims_prompt
    assert "选中用户点" in claims_prompt
    assert "未选中用户点" not in claims_prompt
    assert package["disclosure_run_id"] is None
    assert package["patent_point_summary"] == "选中用户点"


def _create_project(client: TestClient, name: str = "外立面逆建模") -> str:
    response = client.post(
        "/api/projects",
        json={"name": name, "draft_text": "一种既有建筑外立面逆建模方法。"},
    )
    return response.json()["id"]


def _create_patent_point(
    client: TestClient,
    project_id: str,
    title: str = "遮挡洞口语义补全",
    selected: bool = False,
) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": title,
            "technical_problem": "树木和防盗网遮挡导致洞口漏识别",
            "innovation": "多视角语义互证并补全洞口边界",
            "technical_solution": "融合点云、图像和楼层规律生成洞口边界。",
            "evidence_status": "feasible_unverified",
            "source_type": "user",
            "selected": selected,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_disclosure_persists_candidates_as_editable_patent_points(tmp_path):
    """Disclosure-generated candidate patent points should appear in GET /patent-points."""
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"多模态检索项目","materials_summary":"无材料","technical_keywords":["多模态","检索"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":['
            '{"id":"p1","title":"多模态检索方法","technical_problem":"单模态检索精度不足","innovation":"融合文本和图像特征","technical_solution":"构建跨模态编码器","beneficial_effects":["提高检索精度"],"protection_focus":["方法"],"grantability_score":0.8,"rationale":"结构完整"},'
            '{"id":"p2","title":"跨模态编码器系统","technical_problem":"现有编码器无法跨模态对齐","innovation":"联合训练文本和图像编码器","technical_solution":"共享嵌入空间训练","beneficial_effects":["统一表示"],"protection_focus":["系统"],"grantability_score":0.7,"rationale":"结构完整"}'
            '],"selected_candidate_id":"p1"}',
            "prior_art_terms": '["多模态 检索 跨模态"]',
            "prior_art_relevance": '{"prior_art_differences":"现有技术未公开跨模态编码器。","hits":[]}',
            "disclosure_body": "# 技术交底书\n多模态检索方法及系统。",
            "disclosure_mermaid": "flowchart TD\nA[文本] --> C[编码器]\nB[图像] --> C",
            "disclosure_image_prompt": "黑白线稿，展示多模态编码器。",
            "disclosure_self_check": "[]",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    # Create a project
    project_resp = client.post(
        "/api/projects",
        json={"name": "多模态检索", "draft_text": "一种多模态检索方法，融合文本和图像特征。"},
    )
    assert project_resp.status_code == 200
    project_id = project_resp.json()["id"]

    # Before disclosure, patent points should be empty
    points_before = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    assert points_before == []

    # Run disclosure
    run = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 0},
    )
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert len(run.json()["package"]["candidates"]) == 2

    # After disclosure, patent points should contain the generated candidates
    points_after = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    assert len(points_after) == 2
    titles = [p["title"] for p in points_after]
    assert "多模态检索方法" in titles
    assert "跨模态编码器系统" in titles
    selected = [p for p in points_after if p["selected"]]
    assert len(selected) == 1
    assert selected[0]["title"] == "多模态检索方法"


def test_disclosure_preserves_user_edited_point_when_id_collides(tmp_path):
    """A point the user has in the store must never be overwritten when
    disclosure completion persists candidates.

    Simulates the long-running disclosure scenario: a user-created point
    with id ``p1`` exists in the store with custom title and rationale.
    Disclosure completes and emits a candidate also id'd ``p1`` (because
    the LLM was prompted with strategic context containing ``p1``). The
    user's title and rationale must be preserved exactly — only NEW ids
    are inserted.
    """
    store = SQLiteStore(tmp_path / "store.sqlite")
    # Seed the store with a project + a user-created point.
    project = ProjectRecord(
        id="proj-1",
        name="多模态检索",
        draft_text="一种多模态检索方法。",
        patent_type=PatentType.INVENTION,
    )
    store.create_project(project)
    user_point = PatentPointCandidate(
        id="p1",
        title="用户手工编辑：跨模态编码器方法",
        technical_problem="用户补写的技术问题",
        innovation="用户补写的创新点",
        technical_solution="用户补写的技术方案",
        rationale="用户在长跑过程中编辑的说明",
        evidence_status="feasible_unverified",
        source_type="user",
    )
    store.add_project_patent_point("proj-1", user_point)

    # Disclosure completion tries to persist p1 (LLM-generated) and p2.
    incoming = [
        PatentPointCandidate(
            id="p1",
            title="模型生成 p1 标题（应当被忽略）",
            technical_problem="LLM 问题（应当被忽略）",
            innovation="LLM 创新（应当被忽略）",
            technical_solution="LLM 方案（应当被忽略）",
            rationale="LLM 说明（应当被忽略）",
        ),
        PatentPointCandidate(
            id="p2",
            title="模型生成 p2 标题",
            technical_problem="LLM 问题 p2",
            innovation="LLM 创新 p2",
            technical_solution="LLM 方案 p2",
            rationale="LLM 说明 p2",
        ),
    ]
    inserted = _persist_disclosure_candidates(
        store=store,
        project_id="proj-1",
        package_candidates=incoming,
        package_selected_id="p1",
    )

    assert inserted == 1
    points = store.list_project_patent_points("proj-1")
    by_id = {point.id: point for point in points}
    assert set(by_id) == {"p1", "p2"}
    # Existing user record preserved exactly.
    assert by_id["p1"].title == "用户手工编辑：跨模态编码器方法"
    assert by_id["p1"].rationale == "用户在长跑过程中编辑的说明"
    assert by_id["p1"].source_type == "user"
    assert by_id["p1"].technical_problem == "用户补写的技术问题"
    assert by_id["p1"].selected is False
    # New row inserted as-is (no selection was inherited because the existing
    # user row was not selected and the package's selected id collides with
    # the user row — so selection is NOT applied to a NEW row).
    assert by_id["p2"].title == "模型生成 p2 标题"
    assert by_id["p2"].selected is False


def test_disclosure_does_not_clobber_user_selection_on_existing_point(tmp_path):
    """The user's pre-existing selection must not be moved onto a different
    candidate by the disclosure completion write."""
    store = SQLiteStore(tmp_path / "store.sqlite")
    store.create_project(
        ProjectRecord(
            id="proj-2",
            name="选点冲突测试",
            draft_text="一种测试方法。",
            patent_type=PatentType.INVENTION,
        )
    )
    store.add_project_patent_point(
        "proj-2",
        PatentPointCandidate(
            id="user-existing",
            title="用户原有点",
            technical_problem="用户原有",
            innovation="用户原有",
            technical_solution="用户原有",
            selected=True,
        ),
    )
    # Disclosure emits a fresh candidate and selects it.
    incoming = [
        PatentPointCandidate(
            id="new-1",
            title="新生成的候选点",
            technical_problem="新生成",
            innovation="新生成",
            technical_solution="新生成",
        )
    ]
    _persist_disclosure_candidates(
        store=store,
        project_id="proj-2",
        package_candidates=incoming,
        package_selected_id="new-1",
    )
    points = store.list_project_patent_points("proj-2")
    by_id = {p.id: p for p in points}
    # New candidate inserted but its `selected` flag must stay False because
    # the user already had a selection.
    assert by_id["new-1"].selected is False
    # User's selection preserved.
    assert by_id["user-existing"].selected is True


def test_disclosure_rerun_preserves_previous_generated_p1_p2(tmp_path):
    """A second disclosure run must not overwrite p1/p2 from the first run;
    any additional generated candidates (e.g. p3, p4) should be appended as
    new rows."""
    store = SQLiteStore(tmp_path / "store.sqlite")
    store.create_project(
        ProjectRecord(
            id="proj-3",
            name="重跑测试",
            draft_text="一种重跑方法。",
            patent_type=PatentType.INVENTION,
        )
    )
    # Simulate state from a previous run: p1/p2 already stored as
    # model-generated, with the user having edited p1's title.
    store.add_project_patent_point(
        "proj-3",
        PatentPointCandidate(
            id="p1",
            title="用户编辑过的 p1",
            technical_problem="用户编辑",
            innovation="用户编辑",
            technical_solution="用户编辑",
            evidence_status="model_generated",
            source_type="model",
        ),
    )
    store.add_project_patent_point(
        "proj-3",
        PatentPointCandidate(
            id="p2",
            title="原始 p2",
            technical_problem="原始 p2",
            innovation="原始 p2",
            technical_solution="原始 p2",
            evidence_status="model_generated",
            source_type="model",
            selected=True,
        ),
    )

    # Second run: LLM again emits p1 and p2 (this would have happened with
    # the old code and overwritten user edits). Plus two new ones: p3, p4.
    incoming = [
        PatentPointCandidate(
            id="p1",
            title="重跑生成的 p1（应被忽略）",
            technical_problem="重跑 p1",
            innovation="重跑 p1",
            technical_solution="重跑 p1",
        ),
        PatentPointCandidate(
            id="p2",
            title="重跑生成的 p2（应被忽略）",
            technical_problem="重跑 p2",
            innovation="重跑 p2",
            technical_solution="重跑 p2",
        ),
        PatentPointCandidate(
            id="p3",
            title="重跑新生成的 p3",
            technical_problem="重跑 p3",
            innovation="重跑 p3",
            technical_solution="重跑 p3",
        ),
        PatentPointCandidate(
            id="p4",
            title="重跑新生成的 p4",
            technical_problem="重跑 p4",
            innovation="重跑 p4",
            technical_solution="重跑 p4",
        ),
    ]
    inserted = _persist_disclosure_candidates(
        store=store,
        project_id="proj-3",
        package_candidates=incoming,
        package_selected_id="p1",
    )
    assert inserted == 2  # only p3 and p4 are new

    points = store.list_project_patent_points("proj-3")
    by_id = {p.id: p for p in points}
    assert set(by_id) == {"p1", "p2", "p3", "p4"}
    # p1 (user-edited) preserved; selection is NOT moved here because the
    # user's existing p2 selection stands.
    assert by_id["p1"].title == "用户编辑过的 p1"
    assert by_id["p1"].selected is False
    assert by_id["p2"].title == "原始 p2"
    assert by_id["p2"].selected is True
    # New rows are appended without selection (user already had p2 selected).
    assert by_id["p3"].title == "重跑新生成的 p3"
    assert by_id["p3"].selected is False
    assert by_id["p4"].title == "重跑新生成的 p4"
    assert by_id["p4"].selected is False


def test_disclosure_rerun_api_preserves_user_edited_generated_point(tmp_path):
    """End-to-end: run disclosure (creates p1/p2), user edits p1's title,
    then run disclosure again. The user's edit on p1 must survive."""
    llm = FakeLLMClient(
        {
            "disclosure_scan": '{"summary":"重跑项目","materials_summary":"无材料","technical_keywords":["重跑"],"implementation_gaps":[]}',
            "patent_points": '{"candidates":['
            '{"id":"p1","title":"重跑生成 p1 标题","technical_problem":"重跑 p1","innovation":"重跑 p1","technical_solution":"重跑 p1","grantability_score":0.5,"rationale":"重跑 p1"},'
            '{"id":"p2","title":"重跑生成 p2 标题","technical_problem":"重跑 p2","innovation":"重跑 p2","technical_solution":"重跑 p2","grantability_score":0.5,"rationale":"重跑 p2"}'
            '],"selected_candidate_id":"p1"}',
            "prior_art_terms": '["重跑"]',
            "prior_art_relevance": '{"prior_art_differences":"无显著差异。","hits":[]}',
            "disclosure_body": "# 重跑项目交底书",
            "disclosure_mermaid": "flowchart TD\nA-->B",
            "disclosure_image_prompt": "黑白线稿。",
            "disclosure_self_check": "[]",
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_resp = client.post(
        "/api/projects",
        json={"name": "重跑项目", "draft_text": "一种重跑方法。"},
    )
    assert project_resp.status_code == 200
    project_id = project_resp.json()["id"]

    # First run: persists p1/p2.
    first = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 0},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    # User edits p1's title via PATCH.
    patched = client.patch(
        f"/api/projects/{project_id}/patent-points/p1",
        json={"title": "用户手工编辑的 p1 标题"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "用户手工编辑的 p1 标题"

    # Second run: same LLM outputs p1/p2 again. With the bug, this would
    # overwrite the user's edit. With the fix, p1 stays edited and p2 is
    # untouched (the LLM's p1/p2 collide with existing ids).
    second = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"trace": False, "max_prior_art_results": 0},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "completed"

    points = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    by_id = {p["id"]: p for p in points}
    assert set(by_id) == {"p1", "p2"}
    assert by_id["p1"]["title"] == "用户手工编辑的 p1 标题"
    assert by_id["p2"]["title"] == "重跑生成 p2 标题"


def test_disclosure_first_run_marks_selected_when_store_was_empty(tmp_path):
    """Sanity: on a fresh project, the LLM's selected candidate IS marked
    selected (this preserves the original PR-9 contract)."""
    store = SQLiteStore(tmp_path / "store.sqlite")
    store.create_project(
        ProjectRecord(
            id="proj-4",
            name="首次运行测试",
            draft_text="一种首次运行方法。",
            patent_type=PatentType.INVENTION,
        )
    )
    incoming = [
        PatentPointCandidate(
            id="p1",
            title="首点",
            technical_problem="首点问题",
            innovation="首点创新",
            technical_solution="首点方案",
        ),
        PatentPointCandidate(
            id="p2",
            title="次点",
            technical_problem="次点问题",
            innovation="次点创新",
            technical_solution="次点方案",
        ),
    ]
    inserted = _persist_disclosure_candidates(
        store=store,
        project_id="proj-4",
        package_candidates=incoming,
        package_selected_id="p1",
    )
    assert inserted == 2
    points = store.list_project_patent_points("proj-4")
    by_id = {p.id: p for p in points}
    assert by_id["p1"].selected is True
    assert by_id["p2"].selected is False


def test_disclosure_does_not_revive_user_deleted_run_start_candidate(tmp_path):
    """If a user deletes a run-start candidate during a disclosure run, the
    persistence helper must NOT re-insert that stale candidate when the
    disclosure completes.

    Scenario:
    1. At run-start, the project has a user candidate "user-existing".
    2. During the disclosure, the user deletes "user-existing".
    3. At completion, package.candidates still contains "user-existing"
       (merged at run start) plus a new generated candidate "gen-new".
    4. _persist_disclosure_candidates takes a fresh store snapshot — only
       the generated IDs that were truly new (not present at run start)
       should be inserted. "user-existing" must not reappear.
    """
    store = SQLiteStore(tmp_path / "store.sqlite")
    store.create_project(
        ProjectRecord(
            id="proj-5",
            name="用户删除测试",
            draft_text="一种用户删除运行起点的方法。",
            patent_type=PatentType.INVENTION,
        )
    )
    # Seed a run-start user candidate.
    store.add_project_patent_point(
        "proj-5",
        PatentPointCandidate(
            id="user-existing",
            title="用户原有候选点",
            technical_problem="用户原有",
            innovation="用户原有",
            technical_solution="用户原有",
            source_type="user",
        ),
    )

    # Simulate user deletion during the disclosure run: remove the
    # run-start candidate from the store.
    store.delete_project_patent_point("proj-5", "user-existing")

    # The package contains the run-start candidate (merged at run start)
    # plus a new generated candidate.
    incoming = [
        PatentPointCandidate(
            id="user-existing",
            title="用户原有候选点（应被忽略）",
            technical_problem="用户原有",
            innovation="用户原有",
            technical_solution="用户原有",
        ),
        PatentPointCandidate(
            id="gen-new",
            title="新生成的候选点",
            technical_problem="新生成",
            innovation="新生成",
            technical_solution="新生成",
        ),
    ]
    inserted = _persist_disclosure_candidates(
        store=store,
        project_id="proj-5",
        package_candidates=incoming,
        package_selected_id=None,
        run_start_candidate_ids={"user-existing"},
    )
    # Only the genuinely new generated candidate should be inserted.
    assert inserted == 1

    points = store.list_project_patent_points("proj-5")
    by_id = {p.id: p for p in points}
    # "user-existing" must NOT be resurrected.
    assert "user-existing" not in by_id
    # "gen-new" must be present.
    assert "gen-new" in by_id
    assert by_id["gen-new"].title == "新生成的候选点"


def _create_completed_deliberation(client: TestClient, project_id: str) -> None:
    client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=f"delib-{project_id}",
            project_id=project_id,
            status="completed",
            providers=["codex", "deepseek", "claude"],
            run_mode="full",
            stage_results=_strict_deliberation_stages(),
            strategy_brief=PatentStrategyBrief(
                summary="测试会审策略",
                claim_strategy=["方法独权"],
                description_strategy=["补充实施例"],
                risk_controls=["避免功能性概括"],
                agent_consensus="测试会审通过。",
            ),
            events=["test deliberation completed"],
        )
    )


def _strict_deliberation_stages() -> list[DeliberationStageResult]:
    return [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "ok"},
                status="completed",
            )
            for provider in ["codex", "deepseek", "claude"]
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "ok"},
                status="completed",
            )
            for label in ["pair codex-vs-deepseek", "pair codex-vs-claude", "pair deepseek-vs-claude"]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "ok"},
            status="completed",
        ),
    ]
