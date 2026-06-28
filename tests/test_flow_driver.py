from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from flow_driver import FlowDriver


def test_flow_driver_observes_export_gate_and_hash_invalidation(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    initial = driver.state()
    assert initial.step_status[5] == "completed"
    assert initial.export_allowed is False
    assert initial.gates["official_compile"] == "missing"

    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    ready = driver.state()
    assert ready.export_allowed is True
    assert ready.gates["official_compile"] == "current"
    assert ready.gates["post_draft_review"] == "current"

    driver.edit_source_draft("本发明涉及数据处理技术领域。修改后的实施例改变源稿哈希。")

    stale = driver.state()
    assert stale.export_allowed is False
    assert stale.gates["official_compile"] == "stale"
    assert stale.gates["post_draft_review"] == "stale"
    assert stale.hashes["current_source_draft_hash"] != ready.hashes["current_source_draft_hash"]
    assert driver.export_official()["blocked"] is True
    assert driver.export_internal()["ok"] is True


def test_flow_driver_export_gate_blocks_until_compile_and_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project("空项目", "一种尚未生成初稿的方法。", patent_type="invention")

    no_draft = driver.export_official()
    assert no_draft["blocked"] is True
    assert "Generate a draft" in no_draft["detail"]

    driver = _driver_with_working_draft(client)
    no_compile = driver.export_official()
    assert no_compile["blocked"] is True
    assert "Official draft compile is required" in no_compile["detail"]

    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    no_review = driver.export_official()
    assert no_review["blocked"] is True
    assert "Post-draft multi-agent review is required" in no_review["detail"]

    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True
    driver.run_quality()
    assert driver.export_official()["ok"] is True


def test_flow_driver_cannot_skip_required_steps_matrix(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = FlowDriver(client)
    project = driver.create_project("跳步矩阵", "一种尚未生成初稿的方法。", patent_type="invention")

    no_draft_readiness = driver.raw_get(f"/api/projects/{project['id']}/export-readiness")
    assert no_draft_readiness["next_action"] == "generate_draft"
    assert no_draft_readiness["draft_required"] is True
    for endpoint in ("filing-readiness", "completion-runs", "official-compile-runs", "post-draft-reviews"):
        status_code, detail = _post_status(client, project["id"], endpoint)
        assert status_code == 409
        assert "Generate a draft" in detail
    generate_without_deliberation = client.post(f"/api/projects/{project['id']}/generate", json={})
    assert generate_without_deliberation.status_code == 409
    assert "Multi-agent deliberation is required" in generate_without_deliberation.json()["detail"]

    driver = _driver_with_working_draft(client)

    missing_quality = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_quality["next_action"] == "run_quality_checks"
    assert missing_quality["quality_required"] is True
    assert missing_quality["missing_quality_checks"] == ["filing_readiness", "draft_completion"]
    review_without_compile = driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_without_compile.status_code == 409
    assert "Official draft compile is required" in review_without_compile.json()["detail"]

    driver.run_quality()
    missing_compile = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_compile["next_action"] == "run_official_compile"
    assert missing_compile["official_compile_required"] is True

    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    missing_review = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_review["next_action"] == "run_post_draft_review"
    assert missing_review["post_draft_review_required"] is True
    assert "Post-draft multi-agent review is required" in driver.export_official()["detail"]

    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True
    ready = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert ready["next_action"] == "export_ready"
    assert ready["export_allowed"] is True
    assert driver.export_official()["ok"] is True


def test_flow_driver_export_gate_requires_current_quality_checks(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_quality = driver.export_official()
    assert blocked_without_quality["blocked"] is True
    assert "Quality checks are required" in blocked_without_quality["detail"]
    missing_quality_state = driver.state()
    assert missing_quality_state.export_allowed is False
    assert missing_quality_state.gates["quality"] == "missing"

    driver.run_quality()

    ready = driver.state()
    assert ready.gates["quality"] == "current"
    assert ready.export_allowed is True
    assert driver.export_official()["ok"] is True


def test_flow_driver_export_gate_requires_complete_quality_bundle(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness")
    assert filing.status_code == 200
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets")
    assert worksheet.status_code == 200
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_completion = driver.export_official()
    assert blocked_without_completion["blocked"] is True
    assert "draft_completion" in blocked_without_completion["detail"]
    readiness_without_completion = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness_without_completion["missing_quality_checks"] == ["draft_completion"]

    driver = _driver_with_working_draft(client)
    completion = client.post(f"/api/projects/{driver.project_id}/completion-runs")
    assert completion.status_code == 200
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_filing = driver.export_official()
    assert blocked_without_filing["blocked"] is True
    assert "filing_readiness" in blocked_without_filing["detail"]
    readiness_without_filing = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness_without_filing["missing_quality_checks"] == ["filing_readiness"]


def test_flow_driver_later_blocking_review_invalidates_prior_pass(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    driver.compile_official()
    passed_review = driver.run_post_draft_review()
    assert passed_review["export_allowed"] is True
    assert driver.export_official()["ok"] is True

    client.app.state.llm = _review_llm(export_allowed=False)
    blocking_review = driver.run_post_draft_review()

    assert blocking_review["export_allowed"] is False
    blocked_export = driver.export_official()
    assert blocked_export["blocked"] is True
    assert "Post-draft multi-agent review is required" in blocked_export["detail"]


def test_flow_driver_generates_utility_model_draft_and_reports_readiness(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_drafting_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project(
        "可调安装支架",
        "专利类型：实用新型。一种可调安装支架，包括底座、支撑臂和限位件。",
        patent_type="utility_model",
    )

    requirement = driver.formula_requirement()
    assert requirement["required"] is False

    package = driver.generate_draft()
    assert "可调安装支架" in package["title"]
    assert driver.project()["package"]["title"] == package["title"]

    readiness = driver.export_readiness()
    assert readiness["export_allowed"] is False
    assert "official_compile" in readiness or "official_compile_required" in readiness


def test_flow_driver_runs_formula_for_formula_required_invention(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_drafting_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project(
        "置信度输入处理",
        "一种根据输入特征置信度和阈值生成处理结果的方法。",
        patent_type="invention",
    )
    driver.intake_external_draft(
        """
发明名称
一种置信度输入处理方法
摘要
本发明公开一种根据置信度阈值生成处理结果的方法。
权利要求书
1. 一种置信度输入处理方法，其特征在于，包括接收输入数据、计算输入特征置信度，并根据阈值输出处理结果。
说明书
本发明涉及数据处理技术领域。系统计算输入特征置信度，并根据阈值生成处理结果。
附图说明
图1为置信度输入处理方法流程图。
""".strip(),
        filename="formula-draft.txt",
    )

    requirement = driver.formula_requirement()
    assert requirement["required"] is True

    formula = driver.run_formula()
    assert formula["status"] == "completed"
    assert formula["package"]["formula_blocks"]


def _driver_with_working_draft(client: TestClient) -> FlowDriver:
    driver = FlowDriver(client)
    driver.create_project(
        "输入数据处理",
        "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        patent_type="invention",
    )
    driver.intake_external_draft(
        """
发明名称
一种输入数据处理方法
摘要
本发明公开一种输入数据处理方法。
权利要求书
1. 一种输入数据处理方法，其特征在于，包括接收输入数据并输出处理结果。
说明书
本发明涉及数据处理技术领域。在一个实施例中，系统接收输入数据并输出处理结果。
附图说明
图1为输入数据处理方法流程图。
""".strip(),
        filename="draft.txt",
    )
    return driver


def _post_status(client: TestClient, project_id: str, endpoint: str) -> tuple[int, str]:
    response = client.post(f"/api/projects/{project_id}/{endpoint}", json={})
    detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else ""
    return response.status_code, str(detail)


def _review_llm(*, export_allowed: bool = True) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["说明书存在未解决的正式稿阻断问题。"]
    chair_status = "passed" if export_allowed else "blocked"
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": _role_response("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_response("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_response("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": json.dumps(
                {
                    "status": chair_status,
                    "export_allowed": export_allowed,
                    "blocking_issues": blocking_issues,
                    "contamination_hits": [],
                    "claim_1_rewrite": "",
                    "system_claim_rewrite": "",
                    "abstract_rewrite": "",
                    "description_rewrite_tasks": [],
                    "official_safe_patches": [],
                    "attorney_memo": [],
                    "next_actions": [],
                },
                ensure_ascii=False,
            ),
        }
    )


def _drafting_llm() -> FakeLLMClient:
    responses = {
        "core_formula": json.dumps(
            {
                "summary": "以输入处理置信度描述处理触发关系。",
                "formula_blocks": [
                    {
                        "id": "F01",
                        "name": "输入处理置信度",
                        "latex": "S=aX+bY",
                        "purpose": "描述输入特征和上下文特征对处理结果的贡献。",
                        "claim_hook": "根据置信度输出处理结果。",
                    }
                ],
                "variable_definitions": [
                    {"symbol": "X", "meaning": "输入特征", "unit": ""},
                    {"symbol": "Y", "meaning": "上下文特征", "unit": ""},
                ],
                "derivation_notes": ["公式用于限定处理触发关系。"],
                "claim_hooks": ["将置信度写入从属权利要求。"],
                "description_insert": "本实施例根据F01计算输入处理置信度。",
                "latex_markdown": "# 核心公式\n\nF01: $S=aX+bY$。",
                "generation_logs": ["journey test formula package"],
            },
            ensure_ascii=False,
        ),
        "claims": (
            "1. 一种可调安装支架，其特征在于，包括底座、支撑臂和限位件，"
            "所述支撑臂与所述底座转动连接，所述限位件用于锁定调节角度。\n"
            "2. 根据权利要求1所述的安装支架，其特征在于，所述支撑臂设有角度刻度。"
        ),
        "description": (
            "技术领域\n本实用新型涉及安装支架技术领域。\n"
            "背景技术\n现有支架角度调整不便。\n"
            "实用新型内容\n本实用新型通过底座、支撑臂和限位件实现稳定调节。\n"
            "附图说明\n图1为安装支架结构示意图。\n"
            "具体实施方式\n底座固定在安装面，支撑臂相对底座转动，限位件锁定角度。"
        ),
        "abstract": "本实用新型公开一种可调安装支架，能够实现安装角度调节和锁定。",
        "drawings": "图1为安装支架结构示意图。",
        "diagram": "flowchart TD\nA[底座] --> B[支撑臂]\nB --> C[限位件]",
        "image_prompt": "黑白专利线稿，展示底座、支撑臂和限位件。",
        "review": json.dumps(
            [
                {
                    "category": "支持性",
                    "severity": "low",
                    "message": "权利要求与说明书一致。",
                    "suggestion": "提交前补充附图标号。",
                    "evidence": "权利要求1",
                }
            ],
            ensure_ascii=False,
        ),
        "post_draft_claims_reviewer": _role_response("claims_reviewer", "passed", []),
        "post_draft_spec_cleaner": _role_response("spec_cleaner", "passed", []),
        "post_draft_technical_hardness": _role_response("technical_hardness", "passed", []),
        "post_draft_chair_synthesis": json.dumps(
            {
                "status": "passed",
                "export_allowed": True,
                "blocking_issues": [],
                "contamination_hits": [],
                "claim_1_rewrite": "",
                "system_claim_rewrite": "",
                "abstract_rewrite": "",
                "description_rewrite_tasks": [],
                "official_safe_patches": [],
                "attorney_memo": [],
                "next_actions": [],
            },
            ensure_ascii=False,
        ),
    }
    return FakeLLMClient(responses)


def _role_response(role: str, status: str, blocking_issues: list[str]) -> str:
    return json.dumps(
        {
            "role": role,
            "status": status,
            "blocking_issues": blocking_issues,
            "contamination_hits": [],
            "rewrite_suggestions": [],
            "official_safe_patches": [],
            "attorney_memo": [],
        },
        ensure_ascii=False,
    )
