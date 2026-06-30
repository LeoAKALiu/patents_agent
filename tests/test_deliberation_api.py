from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import _selectable_agent_provider_ids, create_app
from backend.app.schemas import AgentDoctorReport, AgentProviderStatus, DeliberationRun


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

    generate_without_deliberation = client.post(f"/api/projects/{project_id}/generate", json={})
    assert generate_without_deliberation.status_code == 409
    assert "Multi-agent deliberation" in generate_without_deliberation.json()["detail"]

    run_response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "deepseek", "claude"], "trace": False},
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

    run_response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "deepseek", "claude"], "trace": False},
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


def test_deliberation_create_replaces_deprecated_gemini_request(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_minimal_llm(), provider_runner=_FakeProviderRunner()))
    project_id = client.post(
        "/api/projects",
        json={"name": "旧会审 provider 项目", "draft_text": "一种城市体检指标驱动采集方法。"},
    ).json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "gemini", "claude"], "trace": False},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["providers"] == ["codex", "deepseek", "claude"]
    assert "gemini" not in {stage["provider_id"] for stage in run["stage_results"]}
    assert not any("gemini" in event for event in run["events"])


def test_deliberation_api_accepts_agent_runtime_adapter(tmp_path):
    from backend.app.agents.adapters.fake import FakeAgentRuntime

    runtime = FakeAgentRuntime(
        task_payloads={
            "opening codex": {
                "stance": "codex stance",
                "claim_scope": ["method"],
                "risks": [],
                "recommendations": ["add embodiments"],
            },
            "opening deepseek": {
                "stance": "deepseek stance",
                "claim_scope": ["system"],
                "risks": [],
                "recommendations": ["narrow novelty"],
            },
            "opening claude": {
                "stance": "claude stance",
                "claim_scope": ["medium"],
                "risks": [],
                "recommendations": ["align terms"],
            },
            "pair codex-vs-deepseek": {
                "conflict_level": 0.2,
                "agreements": ["method claim"],
                "disagreements": [],
                "resolved_recommendation": "keep method claim",
            },
            "pair codex-vs-claude": {
                "conflict_level": 0.1,
                "agreements": ["embodiments"],
                "disagreements": [],
                "resolved_recommendation": "add examples",
            },
            "pair deepseek-vs-claude": {
                "conflict_level": 0.3,
                "agreements": ["term alignment"],
                "disagreements": [],
                "resolved_recommendation": "align terms",
            },
            "chair synthesis": {
                "summary": "Runtime adapter synthesis.",
                "claim_strategy": ["method claim"],
                "description_strategy": ["add embodiments"],
                "risk_controls": ["avoid functional overbreadth"],
                "agent_consensus": "Runtime adapter consensus.",
            },
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_minimal_llm(),
            agent_runtime=runtime,
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "runtime adapter project", "draft_text": "A defect detection method."},
    ).json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "deepseek", "claude"], "trace": False},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["strategy_brief"]["summary"] == "Runtime adapter synthesis."
    assert [request.label for request in runtime.requests[:3]] == [
        "opening codex",
        "opening deepseek",
        "opening claude",
    ]


def test_missing_required_provider_creates_failed_diagnostic_run(tmp_path, monkeypatch):
    def fake_doctor():
        return AgentDoctorReport(
            status="degraded",
            run_mode="partial",
            commands={
                "codex": AgentProviderStatus(id="codex", label="Codex", command="codex", available=True, path="/bin/codex", required=True),
                "deepseek": AgentProviderStatus(id="deepseek", label="DeepSeek", command="reasonix", available=False, required=True),
                "claude": AgentProviderStatus(id="claude", label="Claude", command="claude", available=True, path="/bin/claude", required=True),
                "gemini": AgentProviderStatus(id="gemini", label="Gemini", command="gemini", available=False, required=False),
            },
            active_provider_ids=["codex", "claude"],
            missing_required=["deepseek"],
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
    assert any(log["provider_id"] == "deepseek" and log["repair_suggestion"] for log in run["logs"])


def test_deliberation_retry_normalizes_legacy_gemini_providers(tmp_path, monkeypatch):
    def fake_doctor():
        return AgentDoctorReport(
            status="ready",
            run_mode="full",
            commands={
                "codex": AgentProviderStatus(id="codex", label="Codex", command="codex", available=True, path="/bin/codex", required=True, roles=["deliberation"], installed=True, auth_status="ready", selectable=True),
                "deepseek": AgentProviderStatus(id="deepseek", label="DeepSeek", command="reasonix", available=True, path="/bin/reasonix", required=True, roles=["deliberation"], installed=True, auth_status="ready", selectable=True),
                "claude": AgentProviderStatus(id="claude", label="Claude", command="claude", available=True, path="/bin/claude", required=True, roles=["deliberation"], installed=True, auth_status="ready", selectable=True),
                "gemini": AgentProviderStatus(id="gemini", label="Gemini", command="gemini", available=False, required=False, roles=["deprecated"], installed=True, auth_status="unknown", selectable=True),
                "kimicode": AgentProviderStatus(id="kimicode", label="KimiCode", command="kimicode", available=False, required=False, roles=["deliberation"], installed=True, auth_status="unknown", selectable=True),
            },
            active_provider_ids=["codex", "deepseek", "claude"],
            missing_required=[],
            missing_optional=[],
            unknown_required=[],
        )

    monkeypatch.setattr("backend.app.main.inspect_agent_environment", fake_doctor)
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_minimal_llm(), provider_runner=_FakeProviderRunner(), load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "旧 run 重试项目", "draft_text": "一种城市体检指标驱动采集方法。"},
    ).json()["id"]
    previous = DeliberationRun(
        id="legacy-delib",
        project_id=project_id,
        status="failed",
        providers=["codex", "gemini", "claude", "kimicode"],
        run_mode="full",
    )
    client.app.state.store.create_deliberation_run(previous)

    retry = client.post(f"/api/projects/{project_id}/deliberations/{previous.id}/retry").json()

    assert retry["retry_of"] == previous.id
    assert retry["providers"] == ["codex", "deepseek", "claude", "kimicode"]
    assert "gemini" not in {stage["provider_id"] for stage in retry["stage_results"]}


def test_selectable_providers_include_optional_unknown_installed_agents():
    doctor = AgentDoctorReport(
        status="degraded",
        run_mode="partial",
        commands={
            "codex": AgentProviderStatus(
                id="codex",
                label="Codex",
                command="codex",
                available=True,
                path="/opt/homebrew/bin/codex",
                installed=True,
                required=True,
                auth_status="ready",
                selectable=True,
            ),
            "gemini": AgentProviderStatus(
                id="gemini",
                label="Gemini",
                command="gemini",
                available=False,
                path="/opt/homebrew/bin/gemini",
                installed=True,
                required=False,
                auth_status="unknown",
                selectable=True,
            ),
            "deepseek": AgentProviderStatus(
                id="deepseek",
                label="DeepSeek",
                command="reasonix",
                available=True,
                path="/opt/homebrew/bin/reasonix",
                installed=True,
                required=True,
                auth_status="ready",
                selectable=True,
            ),
            "claude": AgentProviderStatus(
                id="claude",
                label="Claude",
                command="claude",
                available=True,
                path="/opt/homebrew/bin/claude",
                installed=True,
                required=True,
                auth_status="ready",
                selectable=True,
            ),
            "kimicode": AgentProviderStatus(
                id="kimicode",
                label="KimiCode",
                command="kimicode",
                available=False,
                path="/Users/leo/.kimi-code/bin/kimi",
                installed=True,
                required=False,
                auth_status="unknown",
                selectable=True,
            ),
            "mimo": AgentProviderStatus(
                id="mimo",
                label="MimoCode",
                command="mimo",
                available=False,
                path="/Users/leo/.mimocode/bin/mimo",
                installed=True,
                required=False,
                auth_status="unknown",
                selectable=True,
                roles=["deliberation", "formula", "critic"],
            ),
        },
        active_provider_ids=["codex", "deepseek", "claude"],
        unknown_required=[],
        missing_required=[],
        missing_optional=[],
    )

    selectable = _selectable_agent_provider_ids(doctor)

    assert "codex" in selectable
    assert "deepseek" in selectable
    assert "claude" in selectable
    assert "gemini" in selectable
    assert "kimicode" in selectable
    assert "mimo" in selectable


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
