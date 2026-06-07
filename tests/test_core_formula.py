from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief


def test_formula_requirement_detects_hcu_confidence_terms(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "根据每类指标的证据缺失度、置信区间、传感器贡献矩阵和置信度增益生成无人机任务包。",
        },
    ).json()["id"]

    response = client.get(f"/api/projects/{project_id}/formula-requirement")

    assert response.status_code == 200
    payload = response.json()
    assert payload["required"] is True
    assert {"置信区间", "贡献矩阵", "增益"}.issubset(set(payload["signals"]))
    assert payload["reasons"]


def test_formula_requirement_uses_selected_route_before_backup_routes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "路线选择项目",
            "draft_text": "一种基于图像采集和人工复核的缺陷识别方法。",
        },
    ).json()["id"]
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "main-route",
            "title": "非公式主路线",
            "technical_problem": "人工巡检效率低",
            "innovation": "组织采集和复核流程",
            "technical_solution": "采集图像并由人工复核输出结果。",
            "beneficial_effects": ["提升流程完整性"],
            "protection_focus": ["采集", "复核"],
            "selected": True,
        },
    )
    client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "backup-route",
            "title": "公式后备路线",
            "technical_problem": "指标置信度不足",
            "innovation": "基于贡献矩阵和置信度增益补采",
            "technical_solution": "根据贡献矩阵、置信区间和置信度增益生成任务。",
            "beneficial_effects": ["提升置信度"],
            "protection_focus": ["贡献矩阵", "置信度增益"],
            "selected": False,
        },
    )

    response = client.get(f"/api/projects/{project_id}/formula-requirement")

    assert response.status_code == 200
    assert response.json()["required"] is False


def test_non_formula_project_does_not_require_formula_package_before_generation(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别",
            "draft_text": "一种基于图像采集和人工复核的缺陷识别方法，解决人工巡检效率低的问题。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)

    requirement = client.get(f"/api/projects/{project_id}/formula-requirement").json()
    generate_response = client.post(f"/api/projects/{project_id}/generate", json={})

    assert requirement["required"] is False
    assert generate_response.status_code == 200
    assert generate_response.json()["formula_run_id"] is None


def test_project_delete_removes_formula_runs(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "根据指标置信度增益和贡献矩阵生成任务包。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)
    formula_run = client.post(f"/api/projects/{project_id}/formula-runs", json={}).json()

    delete_response = client.delete(f"/api/projects/{project_id}")

    assert delete_response.status_code == 200
    assert client.app.state.store.get_formula_run(project_id, formula_run["id"]) is None


def test_required_formula_blocks_generation_until_formula_package_completed(tmp_path):
    llm = _fake_llm()
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机主动采集",
            "draft_text": "以指标置信度增益为任务优化目标，结合贡献矩阵、后验置信度和置信区间生成补采任务。",
        },
    ).json()["id"]
    _create_strict_completed_deliberation(client, project_id)

    blocked = client.post(f"/api/projects/{project_id}/generate", json={})
    assert blocked.status_code == 409
    assert "Core formula package" in blocked.json()["detail"]

    formula_response = client.post(f"/api/projects/{project_id}/formula-runs", json={})
    assert formula_response.status_code == 200
    formula_run = formula_response.json()
    assert formula_run["status"] == "completed"
    assert formula_run["package"]["formula_blocks"][0]["id"] == "F01"

    latex_response = client.get(f"/api/projects/{project_id}/formula-runs/{formula_run['id']}/latex.md")
    assert latex_response.status_code == 200
    assert "F01" in latex_response.text
    assert "\\Delta C_i" in latex_response.text
    assert "权利要求落点" in latex_response.text

    generate_response = client.post(
        f"/api/projects/{project_id}/generate",
        json={"formula_run_id": formula_run["id"]},
    )
    assert generate_response.status_code == 200
    package = generate_response.json()
    assert package["formula_run_id"] == formula_run["id"]
    assert any("formula" in log for log in package["generation_logs"])
    claim_call = next(call for call in llm.calls if call.stage == "claims")
    assert "\\Delta C_i" in claim_call.user_prompt
    assert "指标置信度增益" in claim_call.user_prompt


def _fake_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "core_formula": """
{
  "summary": "以指标置信度增益作为无人机主动采集任务的优化核心。",
  "formula_blocks": [
    {
      "id": "F01",
      "name": "指标置信度增益",
      "latex": "\\\\Delta C_i = C_i^{post} - C_i^{prior}",
      "purpose": "衡量一次任务对城市体检指标置信度的提升。",
      "claim_hook": "根据指标置信度增益生成无人机任务包"
    }
  ],
  "variable_definitions": [
    {"symbol": "C_i^{post}", "meaning": "采集后第i类指标的后验置信度", "unit": ""},
    {"symbol": "C_i^{prior}", "meaning": "采集前第i类指标的先验置信度", "unit": ""}
  ],
  "derivation_notes": ["由证据缺失度和传感器贡献矩阵更新后验置信度。"],
  "claim_hooks": ["独立权利要求中写入以指标置信度增益作为任务优化目标。"],
  "description_insert": "本实施例以公式F01计算每类城市体检指标的置信度增益。",
  "latex_markdown": ""
}
""",
            "claims": "1. 一种城市体检指标驱动的无人机主动采集方法，其特征在于，根据指标置信度增益生成任务包。",
            "description": "技术领域\n本发明涉及无人机主动采集。\n具体实施方式\n本实施例包括公式F01。",
            "abstract": "本发明公开一种无人机主动采集方法。",
            "drawings": "图1为方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[指标] --> B[任务包]",
            "image_prompt": "黑白线稿。",
        }
    )


def _create_strict_completed_deliberation(client: TestClient, project_id: str) -> None:
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "ok"},
                status="completed",
            )
            for provider in ["codex", "gemini", "claude"]
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=label,
                payload={"resolved_recommendation": "ok"},
                status="completed",
            )
            for label in ["pair codex-vs-gemini", "pair codex-vs-claude", "pair gemini-vs-claude"]
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "ok"},
            status="completed",
        ),
    ]
    client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=f"delib-{project_id}",
            project_id=project_id,
            status="completed",
            providers=["codex", "gemini", "claude"],
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="三方会审通过。",
                claim_strategy=["方法独权"],
                description_strategy=["补充公式实施例"],
                risk_controls=["避免功能性概括"],
                agent_consensus="三方一致。",
            ),
            events=["test deliberation completed"],
        )
    )
