from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app


def test_knowledge_readiness_requires_deep_research_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_knowledge_llm(90), load_env_file=False))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/knowledge-readiness", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["score"] == 90
    assert run["proceed_allowed"] is False
    assert "DeepResearch" in run["blocking_issues"][0]


def test_knowledge_readiness_allows_progress_above_threshold_with_deep_research(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_knowledge_llm(82), load_env_file=False))
    project_id = _create_project(client)
    _upload_material(
        client,
        project_id,
        "deepresearch-report.md",
        "DeepResearch 报告：覆盖现有技术、关键论文和专利差异。",
    )
    _upload_material(client, project_id, "prior-art-patent.md", "CN 专利对比文件，包含区别特征。")

    response = client.post(
        f"/api/projects/{project_id}/knowledge-readiness",
        json={"providers": ["codex", "claude"]},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["score"] > 80
    assert run["score_before_bonus"] == 82
    assert run["related_reference_count"] == 1
    assert run["deep_research_report_uploaded"] is True
    assert run["proceed_allowed"] is True
    assert run["providers"] == ["codex", "claude"]


def test_generate_blocks_without_completed_knowledge_readiness(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_knowledge_llm(90), load_env_file=False))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/generate", json={})

    assert response.status_code == 409
    assert "Knowledge readiness" in response.json()["detail"]


def _create_project(client: TestClient) -> str:
    return client.post(
        "/api/projects",
        json={
            "name": "城市体检指标置信度采集",
            "draft_text": "一种基于城市体检指标置信度的无人机主动采集方法。",
        },
    ).json()["id"]


def _upload_material(client: TestClient, project_id: str, file_name: str, text: str) -> None:
    response = client.post(
        f"/api/projects/{project_id}/materials",
        files={"file": (file_name, text.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


def _knowledge_llm(score: int) -> FakeLLMClient:
    def payload(role: str) -> str:
        return f"""
{{
  "role": "{role}",
  "score": {score},
  "strengths": ["已覆盖核心现有技术"],
  "issues": [],
  "recommendations": ["继续补充从属权利要求支撑材料"]
}}
"""

    return FakeLLMClient(
        {
            "knowledge_deep_research_auditor": payload("deep_research_auditor"),
            "knowledge_prior_art_auditor": payload("prior_art_auditor"),
            "knowledge_drafting_support_auditor": payload("drafting_support_auditor"),
        }
    )
