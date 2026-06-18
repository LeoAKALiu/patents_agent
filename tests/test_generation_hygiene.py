
# ── PR-10: generation + hygiene integration ───────────────────────────────────


def test_generation_endpoint_applies_hygiene_before_save(tmp_path):
    """PR-10: the generate endpoint cleans pollution before persisting the package."""
    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.llm import FakeLLMClient

    # LLM that returns polluted output for all stages
    llm = FakeLLMClient(
        {
            "claims": (
                "好的，下面撰写权利要求书。\n"
                "1. 一种无人机任务调整方法，其特征在于，包括步骤A。\n"
                "support_gap: 需要补充步骤B的实验数据。\n"
                "image_prompt: 黑白线稿展示无人机流程。"
            ),
            "description": (
                "## 说明书\n"
                "本发明涉及无人机技术领域。\n"
                "根据会审策略补充的实施例。\n"
                "```mermaid\nflowchart TD\nA-->B\n```"
            ),
            "abstract": "本发明公开了一种无人机任务调整方法。",
            "drawings": "图1为方法流程图。",
            "diagram": "flowchart TD\nA-->B",
            "image_prompt": "黑白线稿展示无人机。",
        }
    )

    client = TestClient(
        create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False)
    )

    # Set up a utility-model project (bypasses deliberation requirement)
    project_id = client.post(
        "/api/projects",
        json={
            "name": "无人机任务调整测试",
            "draft_text": "一种无人机任务调整方法。",
            "patent_type": "utility_model",
        },
    ).json()["id"]

    # Generate
    gen_resp = client.post(f"/api/projects/{project_id}/generate", json={})
    assert gen_resp.status_code == 200, gen_resp.text

    # Fetch the saved package
    project = client.app.state.store.get_project(project_id)
    assert project.package is not None
    pkg = project.package

    # Patent-body fields must be clean
    assert "好的" not in pkg.claims
    assert "support_gap" not in pkg.claims.lower()
    assert "image_prompt" not in pkg.claims.lower()
    assert "##" not in pkg.description
    assert "会审策略" not in pkg.description
    assert "flowchart" not in pkg.description.lower()

    # Core patent text should be preserved
    assert "步骤A" in pkg.claims
    assert "无人机技术领域" in pkg.description

    # Hygiene log should be recorded
    assert any("hygiene: cleaned" in log for log in pkg.generation_logs)


def test_generation_preserves_clean_package_through_api(tmp_path):
    """A clean LLM output should survive the hygiene pass unchanged."""
    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.llm import FakeLLMClient

    llm = FakeLLMClient(
        {
            "claims": "1. 一种方法，包括步骤A。",
            "description": "技术领域\n本发明涉及AI领域。\n发明内容\n本发明提供了一种方法。",
            "abstract": "本发明公开了一种方法。",
            "drawings": "图1为方法流程图。",
            "diagram": "flowchart TD\nA-->B",
            "image_prompt": "黑白线稿。",
        }
    )

    client = TestClient(
        create_app(data_dir=tmp_path, llm_client=llm, load_env_file=False)
    )

    project_id = client.post(
        "/api/projects",
        json={
            "name": "清洁输出测试",
            "draft_text": "一种方法。",
            "patent_type": "utility_model",
        },
    ).json()["id"]

    gen_resp = client.post(f"/api/projects/{project_id}/generate", json={})
    assert gen_resp.status_code == 200

    project = client.app.state.store.get_project(project_id)
    pkg = project.package

    assert "步骤A" in pkg.claims
    assert "AI领域" in pkg.description
    assert any("hygiene: cleaned 0" in log for log in pkg.generation_logs)
