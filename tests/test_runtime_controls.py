import time

from fastapi.testclient import TestClient

from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DeliberationRun, FormulaNeedAssessment, FormulaRun


def test_disclosure_run_records_runtime_state_and_retry_link(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_disclosure_llm(),
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = _create_project(client)

    run = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"stage_timeout_ms": 5_000, "run_timeout_ms": 30_000},
    ).json()

    assert run["status"] == "completed"
    assert run["runtime_state"]["current_stage"] == "disclosure_package"
    assert run["runtime_state"]["partial_artifact_count"] >= 8
    assert run["stage_results"][0]["phase"] == "project_scan"

    retry = client.post(f"/api/projects/{project_id}/disclosures/{run['id']}/retry").json()
    assert retry["status"] == "completed"
    assert retry["retry_of"] == run["id"]


def test_disclosure_timeout_preserves_partial_stage_results(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_SlowDisclosureLLM(_disclosure_responses()),
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = _create_project(client)

    run = client.post(
        f"/api/projects/{project_id}/disclosures",
        json={"stage_timeout_ms": 1, "run_timeout_ms": 1},
    ).json()

    assert run["status"] == "failed"
    assert run["failure_details"][0]["reason"] == "timeout"
    assert run["stage_results"]
    assert run["failure_details"][0]["partial_artifact_count"] >= 1


def test_deliberation_cancel_marks_queued_run_and_retry_links_previous(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = _create_project(client)
    run = DeliberationRun(
        id="queued-delib",
        project_id=project_id,
        status="queued",
        providers=["codex"],
        run_mode="minimal",
    )
    client.app.state.store.create_deliberation_run(run)

    cancelled = client.post(f"/api/projects/{project_id}/deliberations/{run.id}/cancel").json()
    assert cancelled["status"] == "interrupted"
    assert cancelled["cancel_requested"] is True
    assert cancelled["failure_details"][0]["reason"] == "cancelled"

    retry = client.post(f"/api/projects/{project_id}/deliberations/{run.id}/retry").json()
    assert retry["retry_of"] == run.id


def test_formula_run_records_runtime_state_and_retry_link(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_formula_llm(), load_env_file=False))
    project_id = _create_project(
        client,
        draft_text="根据置信度增益、贡献矩阵和后验概率生成补采任务包。",
    )

    run = client.post(f"/api/projects/{project_id}/formula-runs", json={"run_timeout_ms": 30_000}).json()
    assert run["status"] == "completed"
    assert run["runtime_state"]["current_stage"] == "formula_generation"

    retry = client.post(f"/api/projects/{project_id}/formula-runs/{run['id']}/retry").json()
    assert retry["status"] == "completed"
    assert retry["retry_of"] == run["id"]


def test_formula_cancel_marks_queued_run(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False))
    project_id = _create_project(client)
    run = client.app.state.store.create_formula_run(
        FormulaRun(
            id="queued-formula",
            project_id=project_id,
            status="queued",
            requirement=FormulaNeedAssessment(required=False),
        )
    )

    cancelled = client.post(f"/api/projects/{project_id}/formula-runs/{run.id}/cancel").json()

    assert cancelled["status"] == "interrupted"
    assert cancelled["cancel_requested"] is True
    assert cancelled["failure_details"][0]["flow"] == "formula"


class _SlowDisclosureLLM(FakeLLMClient):
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        time.sleep(0.005)
        return super().complete_stage(stage, system_prompt, user_prompt)


def _create_project(client: TestClient, draft_text: str | None = None) -> str:
    response = client.post(
        "/api/projects",
        json={
            "name": "运行态测试项目",
            "draft_text": draft_text or "一种基于神经网络的图像缺陷识别方法。",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _disclosure_llm() -> FakeLLMClient:
    return FakeLLMClient(_disclosure_responses())


def _disclosure_responses() -> dict[str, str]:
    return {
        "disclosure_scan": '{"summary":"图像缺陷识别项目","materials_summary":"无补充材料","technical_keywords":["图像"],"implementation_gaps":[]}',
        "patent_points": '{"candidates":[{"id":"p1","title":"图像缺陷识别方法","technical_problem":"人工检测效率低","innovation":"输出缺陷位置","technical_solution":"采集图像并输出缺陷位置","beneficial_effects":["提高效率"],"protection_focus":["方法"],"grantability_score":0.8,"rationale":"链条完整"}],"selected_candidate_id":"p1"}',
        "prior_art_terms": '["图像 缺陷"]',
        "prior_art_relevance": '{"prior_art_differences":"未获得公开文献。","hits":[]}',
        "disclosure_body": "技术方案正文",
        "disclosure_mermaid": "flowchart TD\nA-->B",
        "disclosure_image_prompt": "黑白线稿。",
        "disclosure_self_check": "[]",
    }


def _formula_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "core_formula": """
{
  "summary": "以置信度增益为目标生成任务包。",
  "formula_blocks": [{"id": "F1", "name": "增益", "latex": "G=w^Tx", "purpose": "选择补采任务", "claim_hook": "任务包生成"}],
  "variable_definitions": [{"symbol": "G", "meaning": "置信度增益", "unit": ""}],
  "derivation_notes": ["基于贡献矩阵加权。"],
  "claim_hooks": ["根据G选择任务"],
  "description_insert": "计算置信度增益。",
  "latex_markdown": "# 核心公式\\n"
}
"""
        }
    )
