from fastapi.testclient import TestClient
from docx import Document

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DraftPackage
from tests.helpers import seed_knowledge_ready


def test_post_draft_review_pass_unlocks_official_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(drawing_description="图1为系统流程图。\nimage_prompt: 黑白线稿。"),
    )

    blocked = client.get(f"/api/projects/{project_id}/official-export.md")
    assert blocked.status_code == 409
    assert "Official draft compile is required" in blocked.json()["detail"]

    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    compile_run = compile_response.json()
    assert compile_run["status"] == "completed"

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    run = review_response.json()
    assert run["status"] == "completed"
    assert run["prompt_pack_version"] == "post-draft-review-v1"
    assert run["export_allowed"] is True
    assert run["official_compile_run_id"] == compile_run["id"]
    assert run["official_package_hash"] == compile_run["official_package_hash"]
    assert {result["role"] for result in run["role_results"]} == {
        "claims_reviewer",
        "spec_cleaner",
        "technical_hardness",
    }

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 200
    assert "权利要求书" in export_response.text
    assert "附图计划" in export_response.text
    assert "image_prompt" not in export_response.text
    assert "黑白线稿" not in export_response.text

    docx_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_response.status_code == 200
    docx_path = tmp_path / "official.docx"
    docx_path.write_bytes(docx_response.content)
    docx_text = "\n".join(paragraph.text for paragraph in Document(docx_path).paragraphs)
    assert "附图计划" in docx_text
    assert "image_prompt" not in docx_text
    assert "黑白线稿" not in docx_text


def test_official_export_blocks_inline_prompt_after_passing_review(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(drawing_description="图1为方法流程图。prompt: 黑白线稿"),
    )
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.json()["status"] == "blocked"

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "Official draft compile is required" in review_response.json()["detail"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert export_response.status_code == 409
    assert "Official draft compile is required" in export_response.json()["detail"]

    docx_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_response.status_code == 409
    assert "Official draft compile is required" in docx_response.json()["detail"]


def test_official_export_blocks_empty_json_wrapper_after_passing_review(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(drawing_description='{\n  "drawing_description": ""\n}'),
    )
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.json()["status"] == "blocked"

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "Official draft compile is required" in review_response.json()["detail"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert export_response.status_code == 409
    assert "Official draft compile is required" in export_response.json()["detail"]

    docx_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_response.status_code == 409
    assert "Official draft compile is required" in docx_response.json()["detail"]


def test_official_export_removes_case_insensitive_internal_labels_after_passing_review(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            description=(
                "本发明涉及无人机任务规划技术领域。\n"
                "attorney_memo: 代理人复核从属权利要求。\n"
                "official_safe_patches: patch-1"
            ),
            drawing_description="图1为系统流程图。\nPrompt: 黑白线稿。",
        ),
    )
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is True

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert export_response.status_code == 200
    assert "本发明涉及无人机任务规划技术领域。" in export_response.text
    assert "图1为系统流程图。" in export_response.text
    assert "attorney_memo" not in export_response.text
    assert "代理人复核" not in export_response.text
    assert "official_safe_patches" not in export_response.text
    assert "Prompt" not in export_response.text
    assert "黑白线稿" not in export_response.text

    docx_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_response.status_code == 200
    docx_path = tmp_path / "clean-official.docx"
    docx_path.write_bytes(docx_response.content)
    docx_text = "\n".join(paragraph.text for paragraph in Document(docx_path).paragraphs)
    assert "本发明涉及无人机任务规划技术领域。" in docx_text
    assert "图1为系统流程图。" in docx_text
    assert "attorney_memo" not in docx_text
    assert "代理人复核" not in docx_text
    assert "official_safe_patches" not in docx_text
    assert "Prompt" not in docx_text
    assert "黑白线稿" not in docx_text


def test_blocking_post_draft_review_prevents_official_export_and_reports(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    run = review_response.json()
    assert run["status"] == "completed"
    assert run["export_allowed"] is False
    assert run["blocking_issues"]
    assert run["contamination_hits"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert export_response.status_code == 409
    assert "Post-draft multi-agent review is required" in export_response.json()["detail"]

    report_response = client.get(f"/api/projects/{project_id}/post-draft-reviews/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "POST_DRAFT_REVIEW_REPORT" in report_response.text
    assert "support_gap" in report_response.text
    assert "attorney_memo" in report_response.text


def test_apply_chair_revision_updates_draft_and_recompiles_official_package(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["export_allowed"] is False

    apply_response = client.post(f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/apply-revisions")

    assert apply_response.status_code == 200
    result = apply_response.json()
    assert result["applied_revision_count"] == 1
    assert result["description_rewrite_tasks"] == ["补充贡献矩阵示例。"]
    assert result["package"]["claims"].startswith("1. 一种方法，包括根据置信度增益生成任务包。")
    assert "applied chair revisions" in "\n".join(result["package"]["generation_logs"])
    assert result["official_compile_run"]["status"] == "completed"
    assert result["official_compile_run"]["source_draft_hash"] == result["current_source_draft_hash"]

    project = client.app.state.store.get_project(project_id)
    assert project.package
    assert project.package.claims.startswith("1. 一种方法，包括根据置信度增益生成任务包。")

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "Post-draft multi-agent review is required" in export_response.json()["detail"]


def test_apply_chair_revision_does_not_update_package_when_compile_raises(tmp_path, monkeypatch):
    client = TestClient(
        create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False),
        raise_server_exceptions=False,
    )
    project_id = _create_project_with_package(client, _package())
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    original_claims = client.app.state.store.get_project(project_id).package.claims

    def fail_compile(self, project_id, package):
        raise RuntimeError("compile exploded")

    monkeypatch.setattr("backend.app.main.OfficialDraftCompiler.compile", fail_compile)

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/apply-revisions")

    assert response.status_code == 500
    assert client.app.state.store.get_project(project_id).package.claims == original_claims


def test_later_blocking_post_draft_review_invalidates_prior_pass_for_same_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200

    passed_review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert passed_review["export_allowed"] is True

    client.app.state.llm = _review_llm(export_allowed=False)
    blocking_review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert blocking_review["status"] == "completed"
    assert blocking_review["export_allowed"] is False
    assert blocking_review["official_compile_run_id"] == passed_review["official_compile_run_id"]
    assert blocking_review["official_package_hash"] == passed_review["official_package_hash"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert export_response.status_code == 409
    assert "Post-draft multi-agent review is required" in export_response.json()["detail"]


def test_post_draft_review_hash_mismatch_invalidates_export_gate(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
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
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200

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
    seed_knowledge_ready(client, project_id)
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
