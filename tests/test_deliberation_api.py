from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import AgentDoctorReport, AgentProviderStatus
from tests.helpers import seed_knowledge_ready


def test_deliberation_api_lifecycle_and_generation_injection(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种图像缺陷识别方法，其特征在于，包括采集图像、训练模型并输出缺陷位置。",
            "description": "技术领域\n本发明涉及AI检测技术领域。\n发明内容\n本发明根据会审策略限定方法和系统边界。",
            "abstract": "本发明公开了一种图像缺陷识别方法，能够提高检测效率。",
            "drawings": "图1为方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[采集图像] --> B[训练模型] --> C[输出缺陷位置]",
            "image_prompt": "黑白线稿，展示图像采集、模型训练、缺陷输出流程。",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, provider_runner=_FakeProviderRunner()))

    doctor_response = client.get("/api/agents/doctor")
    assert doctor_response.status_code == 200
    assert "codex" in doctor_response.json()["commands"]

    project_response = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别",
            "draft_text": "一种基于神经网络的图像缺陷识别方法，解决人工检测效率低的问题。",
        },
    )
    project_id = project_response.json()["id"]
    seed_knowledge_ready(client, project_id)

    generate_without_deliberation = client.post(f"/api/projects/{project_id}/generate", json={})
    assert generate_without_deliberation.status_code == 409
    assert "Multi-agent deliberation" in generate_without_deliberation.json()["detail"]

    run_response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "gemini", "claude"], "trace": False},
    )
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "completed"
    assert run["strategy_brief"]["claim_strategy"] == ["方法独权", "系统独权"]

    list_response = client.get(f"/api/projects/{project_id}/deliberations")
    assert list_response.status_code == 200
    assert list_response.json()["runs"][0]["id"] == run["id"]

    generate_response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert generate_response.status_code == 200
    package = generate_response.json()
    assert package["deliberation_run_id"] == run["id"]
    assert "三方一致" in package["agent_consensus"]
    assert any("deliberation" in log for log in package["generation_logs"])


def test_failed_deliberation_has_diagnostic_logs_and_cannot_generate(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种方法。",
            "description": "说明书。",
            "abstract": "摘要。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA-->B",
            "image_prompt": "黑白线稿。",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, provider_runner=_FailingOpeningProviderRunner()))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "城市体检指标驱动无人机采集",
            "draft_text": "根据指标置信度增益生成无人机任务包。",
        },
    ).json()["id"]
    seed_knowledge_ready(client, project_id)

    run_response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "gemini", "claude"], "trace": False},
    )

    assert run_response.status_code == 200
    run = run_response.json()
    assert run["status"] == "failed"
    assert run["strategy_brief"] is None
    assert any(log["level"] == "error" and log["provider_id"] == "codex" for log in run["logs"])
    assert any(log["repair_suggestion"] for log in run["logs"])

    generate_response = client.post(f"/api/projects/{project_id}/generate", json={"deliberation_run_id": run["id"]})
    assert generate_response.status_code == 409
    assert "strict multi-agent deliberation" in generate_response.json()["detail"]


def test_missing_required_provider_creates_failed_diagnostic_run(tmp_path, monkeypatch):
    def fake_doctor():
        return AgentDoctorReport(
            status="degraded",
            run_mode="partial",
            commands={
                "codex": AgentProviderStatus(id="codex", label="Codex", command="codex", available=True, path="/bin/codex", required=True),
                "gemini": AgentProviderStatus(id="gemini", label="Gemini", command="gemini", available=False, required=False),
                "claude": AgentProviderStatus(id="claude", label="Claude", command="claude", available=True, path="/bin/claude", required=False),
            },
            active_provider_ids=["codex", "claude"],
            missing_optional=["gemini"],
        )

    monkeypatch.setattr("backend.app.main.inspect_agent_environment", fake_doctor)
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_minimal_llm()))
    project_id = client.post(
        "/api/projects",
        json={"name": "缺少 provider 项目", "draft_text": "一种城市体检指标驱动采集方法。"},
    ).json()["id"]

    response = client.post(f"/api/projects/{project_id}/deliberations", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "failed"
    assert run["strategy_brief"] is None
    assert run["failures"][0]["reason"] == "provider_missing"
    assert any(log["provider_id"] == "gemini" and log["repair_suggestion"] for log in run["logs"])


class _FakeProviderResult:
    def __init__(self, payload):
        self.payload = payload


class _FakeProviderRunner:
    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if label.startswith("opening"):
            return _FakeProviderResult(
                {
                    "stance": f"{provider_id} 建议限定AI软件方法",
                    "claim_scope": ["方法", "系统"],
                    "risks": ["支持性不足"],
                    "recommendations": ["补充实施例", "限定模型输入输出"],
                }
            )
        if label.startswith("pair"):
            return _FakeProviderResult(
                {
                    "conflict_level": 0.4,
                    "agreements": ["需要方法独权"],
                    "disagreements": ["系统独权范围"],
                    "resolved_recommendation": "保留系统独权但补充模块限定",
                }
            )
        return _FakeProviderResult(
            {
                "summary": "三方一致建议先明确技术问题、限定输入输出并补充实施例。",
                "claim_strategy": ["方法独权", "系统独权"],
                "description_strategy": ["补充训练与推理实施例"],
                "risk_controls": ["避免纯功能性概括"],
                "agent_consensus": "三方一致建议收敛保护范围。",
            }
        )


def _minimal_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": "1. 一种方法。",
            "description": "说明书。",
            "abstract": "摘要。",
            "drawings": "图1为流程图。",
            "diagram": "flowchart TD\nA-->B",
            "image_prompt": "黑白线稿。",
        }
    )


class _FailingOpeningProviderRunner:
    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if provider_id == "codex" and label.startswith("opening"):
            from backend.app.deliberation.providers import ProviderFailure

            raise ProviderFailure(
                "process_error",
                "opening codex failed with exit code 1",
                provider_id="codex",
                stderr="attempt to write a readonly database",
            )
        return await _FakeProviderRunner().run_json_task(provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback)
