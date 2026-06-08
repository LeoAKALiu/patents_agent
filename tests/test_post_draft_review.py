from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DraftPackage


def test_post_draft_review_pass_unlocks_official_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _package())

    blocked = client.get(f"/api/projects/{project_id}/official-export.md")
    assert blocked.status_code == 409
    assert "Post-draft multi-agent review" in blocked.json()["detail"]

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    run = review_response.json()
    assert run["status"] == "completed"
    assert run["prompt_pack_version"] == "post-draft-review-v1"
    assert run["export_allowed"] is True
    assert {result["role"] for result in run["role_results"]} == {
        "claims_reviewer",
        "spec_cleaner",
        "technical_hardness",
    }

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 200
    assert "权利要求书" in export_response.text


def test_blocking_post_draft_review_prevents_official_export_and_reports(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    project_id = _create_project_with_package(client, _package(description="说明书包含 support_gap 和 好的，下面将继续撰写。"))

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    run = review_response.json()
    assert run["status"] == "completed"
    assert run["export_allowed"] is False
    assert run["blocking_issues"]
    assert run["contamination_hits"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert export_response.status_code == 409
    assert "Post-draft multi-agent review blocked official export" in export_response.json()["detail"]

    report_response = client.get(f"/api/projects/{project_id}/post-draft-reviews/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "POST_DRAFT_REVIEW_REPORT" in report_response.text
    assert "support_gap" in report_response.text
    assert "attorney_memo" in report_response.text


def test_post_draft_review_hash_mismatch_invalidates_export_gate(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is True

    mutated = _package(abstract="本发明公开了一种修改后的方法。")
    client.app.state.store.update_project_package(project_id, mutated)

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "current draft" in export_response.json()["detail"]


def test_invalid_json_post_draft_review_fails_with_diagnostic_log(tmp_path):
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=FakeLLMClient({"post_draft_claims_reviewer": "not-json"}),
            load_env_file=False,
        )
    )
    project_id = _create_project_with_package(client, _package())

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "failed"
    assert run["export_allowed"] is False
    assert run["logs"][0]["level"] == "error"
    assert "invalid_json" in run["logs"][0]["message"]


def _create_project_with_package(client: TestClient, package: DraftPackage) -> str:
    project_id = client.post(
        "/api/projects",
        json={"name": "成稿会审测试", "draft_text": "一种城市体检指标驱动无人机采集方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, package)
    return project_id


def _package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种多模态无人机主动采集方法。",
        "claims": "1. 一种方法，包括根据城市体检指标置信度增益生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域，说明书包括贡献矩阵和后验更新流程。",
        "drawing_description": "图1为系统流程图。",
        "mermaid": "",
        "image_prompt": "",
        "review_findings": [],
        "citations": [],
        "generation_logs": [],
    }
    data.update(overrides)
    return DraftPackage(**data)


def _review_llm(*, export_allowed: bool) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["说明书包含内部提示词 support_gap。"]
    contamination_hits = [] if export_allowed else ["support_gap"]
    chair_status = "passed" if export_allowed else "blocked"
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": f"""
{{
  "role": "claims_reviewer",
  "status": "{role_status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "rewrite_suggestions": ["权利要求1应保留置信度增益闭环。"],
  "official_safe_patches": [],
  "attorney_memo": ["权利要求1需要代理人复核。"]
}}
""".replace("'", '"'),
            "post_draft_spec_cleaner": f"""
{{
  "role": "spec_cleaner",
  "status": "{role_status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": {contamination_hits!r},
  "rewrite_suggestions": ["删除内部提示词。"],
  "official_safe_patches": [],
  "attorney_memo": ["attorney_memo: 清污后再提交。"]
}}
""".replace("'", '"'),
            "post_draft_technical_hardness": f"""
{{
  "role": "technical_hardness",
  "status": "{role_status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "rewrite_suggestions": ["补充贡献矩阵和任务包字段。"],
  "official_safe_patches": [],
  "attorney_memo": ["技术硬度可继续增强。"]
}}
""".replace("'", '"'),
            "post_draft_chair_synthesis": f"""
{{
  "status": "{chair_status}",
  "export_allowed": {str(export_allowed).lower()},
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": {contamination_hits!r},
  "claim_1_rewrite": "1. 一种方法，包括根据置信度增益生成任务包。",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": ["补充贡献矩阵示例。"],
  "official_safe_patches": [],
  "attorney_memo": ["attorney_memo: 主席综合意见。"],
  "next_actions": ["修复 blocking 后重新会审。"]
}}
""".replace("'", '"'),
        }
    )
