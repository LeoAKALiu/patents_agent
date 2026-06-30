import time

from fastapi.testclient import TestClient

from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.official_compile import source_draft_hash
from backend.app.schemas import (
    AgentDoctorReport,
    AgentProviderStatus,
    DeliberationRun,
    DraftPackage,
    FormulaNeedAssessment,
    FormulaRun,
    PostDraftReviewRun,
)


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
    phases = [stage["phase"] for stage in run["stage_results"]]
    assert phases[:2] == ["deep_research_material_intake", "project_scan"]

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


def test_disclosure_cancel_request_wins_provider_exception_race(tmp_path):
    llm = _CancelThenFailDisclosureLLM(_disclosure_responses())
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=llm,
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    project_id = _create_project(client)
    llm.store = client.app.state.store
    llm.project_id = project_id

    run = client.post(f"/api/projects/{project_id}/disclosures", json={}).json()

    assert run["status"] == "interrupted"
    assert run["cancel_requested"] is True
    assert run["failure_details"][0]["reason"] == "cancelled"
    assert "run cancelled" in run["events"]
    assert not any("Connection error" in event for event in run["events"])


def test_deliberation_cancel_marks_queued_run_and_retry_links_previous(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.main.inspect_agent_environment", _retry_ready_doctor)
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({}),
            provider_runner=_FastDeliberationProviderRunner(),
            load_env_file=False,
        )
    )
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
    assert retry["providers"] == ["codex", "deepseek", "kimicode"]
    assert retry["participant_providers"] == []
    assert retry["status"] == "completed"


def test_deliberation_cancel_marks_running_run_interrupted(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({}),
            provider_runner=_FastDeliberationProviderRunner(),
            load_env_file=False,
        )
    )
    project_id = _create_project(client)
    run = DeliberationRun(
        id="running-delib",
        project_id=project_id,
        status="running",
        providers=["codex"],
        run_mode="minimal",
        events=["run started"],
    )
    client.app.state.store.create_deliberation_run(run)

    cancelled = client.post(f"/api/projects/{project_id}/deliberations/{run.id}/cancel").json()

    assert cancelled["status"] == "interrupted"
    assert cancelled["cancel_requested"] is True
    assert cancelled["events"][-1] == "run cancelled"
    assert cancelled["failure_details"][0]["reason"] == "cancelled"


def test_deliberation_list_reconciles_cancelled_active_run(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({}),
            provider_runner=_FastDeliberationProviderRunner(),
            load_env_file=False,
        )
    )
    project_id = _create_project(client)
    run = DeliberationRun(
        id="stale-cancelled-delib",
        project_id=project_id,
        status="running",
        providers=["codex"],
        run_mode="minimal",
        events=["run started", "cancel requested"],
        cancel_requested=True,
    )
    client.app.state.store.create_deliberation_run(run)

    listed = client.get(f"/api/projects/{project_id}/deliberations").json()["runs"][0]
    stored = client.app.state.store.get_deliberation_run(project_id, run.id)

    assert listed["status"] == "interrupted"
    assert listed["failure_details"][0]["reason"] == "cancelled"
    assert stored is not None
    assert stored.status == "interrupted"


def test_deliberation_cancel_request_wins_provider_exception_race(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.main.inspect_agent_environment", _retry_ready_doctor)
    runner = _CancelThenFailDeliberationProviderRunner()
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({}),
            provider_runner=runner,
            load_env_file=False,
        )
    )
    project_id = _create_project(client)
    runner.store = client.app.state.store
    runner.project_id = project_id

    run = client.post(f"/api/projects/{project_id}/deliberations", json={}).json()

    assert run["status"] == "interrupted"
    assert run["cancel_requested"] is True
    assert run["failure_details"][0]["reason"] == "cancelled"
    assert "run cancelled" in run["events"]
    assert not any("Connection error" in event for event in run["events"])
    assert not any("object has no attribute" in event for event in run["events"])
    assert not any("Connection error" in failure["message"] for failure in run["failure_details"])
    assert not any("object has no attribute" in failure["message"] for failure in run["failure_details"])


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


def test_formula_cancel_request_wins_provider_exception_race(tmp_path):
    llm = _CancelThenFailFormulaLLM(_formula_llm().responses)
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    project_id = _create_project(
        client,
        draft_text="根据置信度增益、贡献矩阵和后验概率生成补采任务包。",
    )
    llm.store = client.app.state.store
    llm.project_id = project_id

    run = client.post(f"/api/projects/{project_id}/formula-runs", json={"run_timeout_ms": 30_000}).json()

    assert run["status"] == "interrupted"
    assert run["cancel_requested"] is True
    assert run["failure_details"][0]["reason"] == "cancelled"
    assert "run cancelled" in run["events"]
    assert not any("Connection error" in event for event in run["events"])
    assert not any("Connection error" in failure["message"] for failure in run["failure_details"])


def test_post_draft_review_cancel_is_idempotent_and_retry_links_previous(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_post_draft_review_llm(), load_env_file=False))
    project_id = _create_project(client)
    package = _draft_package()
    client.app.state.store.update_project_package(project_id, package)
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compile_run["status"] == "completed"
    queued = PostDraftReviewRun(
        id="queued-post-review",
        project_id=project_id,
        status="queued",
        providers=["codex", "deepseek", "claude"],
        draft_package_hash=source_draft_hash(package),
        official_compile_run_id=compile_run["id"],
        official_package_hash=compile_run["official_package_hash"],
    )
    client.app.state.store.create_post_draft_review_run(queued)

    cancelled = client.post(f"/api/projects/{project_id}/post-draft-reviews/{queued.id}/cancel").json()
    assert cancelled["status"] == "interrupted"
    assert cancelled["cancel_requested"] is True
    assert cancelled["failure_details"][0]["flow"] == "post_draft_review"
    assert cancelled["failure_details"][0]["reason"] == "cancelled"

    cancelled_again = client.post(f"/api/projects/{project_id}/post-draft-reviews/{queued.id}/cancel").json()
    assert cancelled_again["status"] == "interrupted"
    assert cancelled_again["cancel_requested"] is True
    assert cancelled_again["failure_details"] == cancelled["failure_details"]

    retry = client.post(f"/api/projects/{project_id}/post-draft-reviews/{queued.id}/retry").json()
    assert retry["status"] == "completed"
    assert retry["retry_of"] == queued.id
    assert retry["official_compile_run_id"] == compile_run["id"]
    assert retry["export_allowed"] is True


def test_post_draft_review_cancel_preserves_partial_role_result_and_wins_provider_exception(tmp_path):
    llm = _CancelThenFailPostDraftReviewLLM(_post_draft_review_responses())
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False))
    project_id = _create_project(client)
    package = _draft_package()
    client.app.state.store.update_project_package(project_id, package)
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compile_run["status"] == "completed"
    llm.store = client.app.state.store
    llm.project_id = project_id

    run = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()

    assert run["status"] == "interrupted"
    assert run["cancel_requested"] is True
    assert run["failure_details"][0]["reason"] == "cancelled"
    assert len(run["role_results"]) == 1
    assert run["role_results"][0]["role"] == "claims_reviewer"
    assert run["role_results"][0]["status"] == "passed"
    assert not any("Connection error" in failure["message"] for failure in run["failure_details"])


class _SlowDisclosureLLM(FakeLLMClient):
    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        time.sleep(0.005)
        return super().complete_stage(stage, system_prompt, user_prompt)


class _CancelThenFailDisclosureLLM(FakeLLMClient):
    store = None
    project_id = None

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        if stage == "disclosure_scan" and self.store is not None and self.project_id is not None:
            run = self.store.list_disclosure_runs(self.project_id)[0]
            self.store.update_disclosure_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                        "events": [*run.events, "cancel requested"],
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return super().complete_stage(stage, system_prompt, user_prompt)


class _CancelThenFailPostDraftReviewLLM(FakeLLMClient):
    store = None
    project_id = None

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        if stage == "post_draft_spec_cleaner" and self.store is not None and self.project_id is not None:
            run = self.store.list_post_draft_review_runs(self.project_id)[0]
            self.store.update_post_draft_review_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return super().complete_stage(stage, system_prompt, user_prompt)


class _CancelThenFailFormulaLLM(FakeLLMClient):
    store = None
    project_id = None

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        if stage == "core_formula" and self.store is not None and self.project_id is not None:
            run = self.store.list_formula_runs(self.project_id)[0]
            self.store.update_formula_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                        "events": [*run.events, "cancel requested"],
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return super().complete_stage(stage, system_prompt, user_prompt)


class _CancelThenFailDeliberationProviderRunner:
    store = None
    project_id = None
    cancelled_once = False

    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if (
            label.startswith("opening codex")
            and not self.cancelled_once
            and self.store is not None
            and self.project_id is not None
        ):
            self.cancelled_once = True
            run = self.store.list_deliberation_runs(self.project_id)[0]
            self.store.update_deliberation_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                        "events": [*run.events, "cancel requested"],
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return await _FastDeliberationProviderRunner().run_json_task(
            provider_id,
            prompt,
            workdir,
            label,
            trace,
            task_timeout_ms,
            log_callback,
        )


class _FastDeliberationProviderRunner:
    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if label.startswith("opening"):
            return _Result(
                {
                    "stance": f"{provider_id} ready",
                    "claim_scope": ["方法"],
                    "risks": [],
                    "recommendations": ["补充实施例"],
                }
            )
        if label.startswith("pair"):
            return _Result(
                {
                    "conflict_level": 0.1,
                    "agreements": ["范围一致"],
                    "disagreements": [],
                    "resolved_recommendation": "继续生成",
                }
            )
        return _Result(
            {
                "summary": "会审通过。",
                "claim_strategy": ["方法独权"],
                "description_strategy": ["补充实施例"],
                "risk_controls": ["人工复核"],
                "agent_consensus": "一致通过。",
            }
        )


class _Result:
    def __init__(self, payload):
        self.payload = payload


def _retry_ready_doctor() -> AgentDoctorReport:
    return AgentDoctorReport(
        status="degraded",
        run_mode="partial",
        commands={
            "codex": AgentProviderStatus(id="codex", label="Codex", command="codex", available=True, path="/bin/codex", required=True, roles=["deliberation", "chair"], installed=True, auth_status="ready", selectable=True),
            "deepseek": AgentProviderStatus(id="deepseek", label="DeepSeek", command="reasonix", available=True, path="/bin/reasonix", required=False, roles=["deliberation"], installed=True, auth_status="ready", selectable=True),
            "claude": AgentProviderStatus(id="claude", label="Claude", command="claude", available=False, path="/bin/claude", required=False, roles=["deliberation"], installed=True, auth_status="not_authenticated", selectable=False),
            "kimicode": AgentProviderStatus(id="kimicode", label="KimiCode", command="kimicode", available=True, path="/bin/kimicode", required=False, roles=["deliberation"], installed=True, auth_status="ready", selectable=True),
        },
        active_provider_ids=["codex", "deepseek", "kimicode"],
        missing_required=[],
        missing_optional=["claude"],
        unknown_required=[],
    )


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


def _draft_package() -> DraftPackage:
    return DraftPackage(
        title="一种运行态控制方法",
        abstract="本发明公开一种运行态控制方法。",
        claims="1. 一种运行态控制方法，其特征在于，包括记录运行状态并在中断后重试。",
        description="本发明涉及任务运行态控制技术领域。系统记录运行状态并支持重试。",
        drawing_description="图1为运行态控制流程图。",
        mermaid="",
        image_prompt="",
        review_findings=[],
        citations=[],
        generation_logs=[],
    )


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


def _post_draft_review_llm() -> FakeLLMClient:
    return FakeLLMClient(_post_draft_review_responses())


def _post_draft_review_responses() -> dict[str, str]:
    return {
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "passed",
  "export_allowed": true,
  "blocking_issues": [],
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": [],
  "next_actions": []
}
""",
    }
