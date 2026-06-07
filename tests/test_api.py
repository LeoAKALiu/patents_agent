from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
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
                summary="测试会审策略",
                claim_strategy=["方法独权"],
                description_strategy=["补充实施例"],
                risk_controls=["避免功能性概括"],
                agent_consensus="测试会审通过。",
            ),
            events=["test deliberation completed"],
        )
    )
