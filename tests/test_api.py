from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.patent_mode import UTILITY_MODEL_MODE_PREFIX
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief


def _test_app_without_env(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_api_corpus_project_generation_review_and_export(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种图像缺陷识别方法，其特征在于，包括采集图像并训练模型。\n2. 根据权利要求1所述的方法，其特征在于，输出缺陷位置。",
            "description": "技术领域\n本发明涉及AI检测技术领域。\n发明内容\n本发明通过模型训练实现缺陷识别。",
            "abstract": "本发明公开了一种图像缺陷识别方法，能够提高检测准确性。",
            "drawings": "图1为图像缺陷识别方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[采集图像] --> B[训练模型] --> C[输出结果]",
            "image_prompt": "黑白线稿，展示图像采集、模型训练和结果输出流程。",
            "review": '[{"category":"支持性","severity":"medium","message":"从属权利要求支撑略少。","suggestion":"在具体实施方式中补充缺陷位置输出细节。","evidence":"权利要求2"}]',
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    sample = """摘要
本发明公开了一种图像缺陷识别方法。
权利要求书
1. 一种图像缺陷识别方法，其特征在于，包括训练神经网络模型并输出检测结果。
说明书
技术领域
本发明涉及人工智能检测技术领域。
具体实施方式
系统采集图像、训练模型并输出结果。
"""

    import_response = client.post(
        "/api/corpus/import",
        files={"file": ("sample.txt", sample.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["chunks_count"] >= 3

    search_response = client.get("/api/corpus/search", params={"q": "图像 神经网络 缺陷", "section_type": "claims"})
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["chunk"]["section_type"] == "claims"

    project_response = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别",
            "draft_text": "一种基于神经网络的图像缺陷识别方法，解决人工检测效率低的问题。",
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    _create_completed_deliberation(client, project_id)

    generate_response = client.post(f"/api/projects/{project_id}/generate")
    assert generate_response.status_code == 200
    assert "权利要求1" in generate_response.json()["claims"]

    review_response = client.post(f"/api/projects/{project_id}/review")
    assert review_response.status_code == 200
    assert review_response.json()["review_findings"][0]["category"] == "支持性"

    export_response = client.get(f"/api/projects/{project_id}/export.docx")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_generate_fails_closed_without_llm_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = _test_app_without_env(tmp_path)
    project_response = client.post(
        "/api/projects",
        json={"name": "未配置模型", "draft_text": "一种AI方法，用于生成专利文本。"},
    )
    project_id = project_response.json()["id"]

    generate_response = client.post(f"/api/projects/{project_id}/generate")

    assert generate_response.status_code == 503
    assert "DEEPSEEK_API_KEY" in generate_response.json()["detail"]


def test_utility_model_lite_skips_deliberation_and_formula_gate(tmp_path):
    llm = FakeLLMClient(
        {
            "claims": "1. 一种可调安装支架，其特征在于，包括底座、支撑臂和限位件。",
            "description": "技术领域\n本实用新型涉及安装支架结构。\n具体实施方式\n底座与支撑臂转动连接，限位件限制支撑臂角度。",
            "abstract": "本实用新型公开了一种可调安装支架。",
            "drawings": "图1为整体结构示意图。\n图2为限位件局部放大图。",
            "diagram": "flowchart TD\nA[底座] --> B[支撑臂]\nB --> C[限位件]",
            "image_prompt": "黑白线稿，展示底座、支撑臂和限位件连接关系。",
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": ["权利要求1保持结构闭环。"],
  "official_safe_patches": [],
  "attorney_memo": ["代理人复核结构限定。"]
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": ["说明书保持附图标号一致。"],
  "official_safe_patches": [],
  "attorney_memo": ["确认无内部提示词。"]
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "passed",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": ["补充限位件替代结构。"],
  "official_safe_patches": [],
  "attorney_memo": ["结构效果可继续增强。"]
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "passed",
  "export_allowed": true,
  "blocking_issues": [],
  "contamination_hits": [],
  "claim_1_rewrite": "1. 一种可调安装支架，包括底座、支撑臂和限位件。",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": ["保持结构连接关系清楚。"],
  "official_safe_patches": [],
  "attorney_memo": ["主席综合意见：可进入正式导出。"],
  "next_actions": ["提交前代理人复核。"]
}
""",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "可调安装支架",
            "draft_text": (
                f"{UTILITY_MODEL_MODE_PREFIX}专利类型：实用新型。\n"
                "一种可调安装支架，包括底座、支撑臂和限位件，可根据角度矩阵调节安装位置。"
            ),
        },
    ).json()["id"]

    requirement = client.get(f"/api/projects/{project_id}/formula-requirement").json()
    generate_response = client.post(f"/api/projects/{project_id}/generate", json={})

    assert requirement["required"] is False
    assert "结构、部件和连接关系" in requirement["reasons"][0]
    assert generate_response.status_code == 200
    package = generate_response.json()
    assert package["deliberation_run_id"] is None
    assert "deliberation: no completed multi-agent deliberation injected" in package["generation_logs"]
    claims_call = next(call for call in llm.calls if call.stage == "claims")
    assert "中国实用新型专利权利要求书" in claims_call.user_prompt
    assert "不得写成方法步骤" in claims_call.user_prompt
    assert "中国实用新型专利撰写助手" in claims_call.system_prompt

    blocked_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert blocked_export.status_code == 409
    assert "Official draft compile is required" in blocked_export.json()["detail"]

    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    compile_run = compile_response.json()
    assert compile_run["status"] == "completed"

    blocked_after_compile = client.get(f"/api/projects/{project_id}/official-export.md")
    assert blocked_after_compile.status_code == 409
    assert "Post-draft multi-agent review is required" in blocked_after_compile.json()["detail"]

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["status"] == "completed"
    assert review["export_allowed"] is True
    assert review["official_compile_run_id"] == compile_run["id"]

    official_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert official_export.status_code == 200
    assert "权利要求书" in official_export.text


def test_invention_patent_type_requires_deliberation(tmp_path):
    """Explicit patent_type='invention' must not skip the deliberation gate."""
    llm = FakeLLMClient({})
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "图像缺陷识别方法",
            "draft_text": "一种基于神经网络的图像缺陷识别方法。",
            "patent_type": "invention",
        },
    ).json()["id"]

    response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert response.status_code == 409
    assert "deliberation" in response.json()["detail"].lower()


def test_utility_model_explicit_patent_type_skips_gates(tmp_path):
    """Explicit patent_type='utility_model' (no text markers in draft_text)
    must skip the deliberation/formula gates."""
    llm = FakeLLMClient(
        {
            "claims": "1. 一种可调安装支架，其特征在于，包括底座、支撑臂和限位件。",
            "description": "技术领域\n本实用新型涉及安装支架结构。",
            "abstract": "本实用新型公开了一种可调安装支架。",
            "drawings": "图1为整体结构示意图。",
            "diagram": "flowchart TD\nA[底座] --> B[支撑臂]",
            "image_prompt": "黑白线稿，展示底座、支撑臂和限位件连接关系。",
        }
    )
    client = TestClient(create_app(data_dir=tmp_path, llm_client=llm))
    project_id = client.post(
        "/api/projects",
        json={
            "name": "可调安装支架",
            "draft_text": "一种可调安装支架，包括底座、支撑臂和限位件。",
            "patent_type": "utility_model",
        },
    ).json()["id"]

    # Formula requirement must be false for utility model.
    requirement = client.get(f"/api/projects/{project_id}/formula-requirement").json()
    assert requirement["required"] is False
    assert any(
        "结构" in reason or "部件" in reason or "连接" in reason
        for reason in requirement["reasons"]
    )

    # Generation must succeed without a deliberation run.
    response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert response.status_code == 200
    package = response.json()
    assert package["deliberation_run_id"] is None
    claims_call = next(call for call in llm.calls if call.stage == "claims")
    assert "中国实用新型专利权利要求书" in claims_call.user_prompt
    assert "不得写成方法步骤" in claims_call.user_prompt


def test_project_records_include_timestamps_and_can_be_deleted(tmp_path):
    client = _test_app_without_env(tmp_path)
    create_response = client.post(
        "/api/projects",
        json={"name": "时间字段项目", "draft_text": "一种城市体检指标驱动的采集方法。"},
    )
    assert create_response.status_code == 200
    project = create_response.json()
    assert project["created_at"]
    assert project["updated_at"]

    project_id = project["id"]
    point_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "title": "指标置信度增益主路线",
            "technical_problem": "传统无人机采集不按城市体检指标缺口调度。",
            "innovation": "以指标置信度增益驱动采集任务。",
            "technical_solution": "计算指标证据缺失度并生成任务包。",
            "selected": True,
        },
    )
    assert point_response.status_code == 200

    delete_response = client.delete(f"/api/projects/{project_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    assert client.get(f"/api/projects/{project_id}").status_code == 404
    assert project_id not in {item["id"] for item in client.get("/api/projects").json()["projects"]}
    assert client.get(f"/api/projects/{project_id}/patent-points").status_code == 404


def test_project_patent_points_preserve_generated_candidate_ids_for_backup_routes(tmp_path):
    client = _test_app_without_env(tmp_path)
    project_id = client.post(
        "/api/projects",
        json={"name": "路线保留项目", "draft_text": "一种指标置信度驱动无人机采集方法。"},
    ).json()["id"]

    main_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "route-main",
            "title": "指标置信度增益主路线",
            "technical_problem": "指标置信度不足时缺少主动采集闭环。",
            "innovation": "以指标后验置信度增益作为任务优化目标。",
            "technical_solution": "按指标-证据项-传感器贡献矩阵生成任务包。",
            "source_type": "model",
            "selected": True,
        },
    )
    backup_response = client.post(
        f"/api/projects/{project_id}/patent-points",
        json={
            "source_candidate_id": "route-backup",
            "title": "热红外采集窗口后备路线",
            "technical_problem": "热红外采集窗口受天气和时段限制。",
            "innovation": "按窗口收益和约束生成后备补采任务。",
            "technical_solution": "结合天气、遮挡和热红外窗口调整任务包。",
            "source_type": "model",
            "selected": False,
        },
    )

    assert main_response.status_code == 200
    assert backup_response.status_code == 200
    points = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    assert [point["id"] for point in points] == ["route-main", "route-backup"]
    assert points[0]["selected"] is True
    assert points[1]["selected"] is False

    promote_response = client.patch(
        f"/api/projects/{project_id}/patent-points/route-backup",
        json={"selected": True},
    )
    assert promote_response.status_code == 200
    promoted = client.get(f"/api/projects/{project_id}/patent-points").json()["points"]
    assert promoted[0]["id"] == "route-backup"
    assert promoted[0]["selected"] is True
    assert next(point for point in promoted if point["id"] == "route-main")["selected"] is False


def _create_completed_deliberation(client: TestClient, project_id: str) -> None:
    stages = [
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
    client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=f"delib-{project_id}",
            project_id=project_id,
            status="completed",
            providers=["codex", "deepseek", "claude"],
            run_mode="full",
            stage_results=stages,
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
