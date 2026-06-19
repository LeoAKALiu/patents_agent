from fastapi.testclient import TestClient
from docx import Document

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import DraftPackage


def test_post_draft_review_pass_unlocks_official_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(drawing_description="图1为系统流程图。", image_prompt="黑白线稿。"),
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


def test_official_export_blocks_case_insensitive_internal_labels_before_review(tmp_path):
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
    assert compile_response.json()["status"] == "blocked"

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert export_response.status_code == 409
    assert "Official draft compile is required" in export_response.json()["detail"]

    docx_response = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_response.status_code == 409
    assert "Official draft compile is required" in docx_response.json()["detail"]


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


def test_apply_post_draft_safe_patches_updates_draft_and_invalidates_old_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_safe_patch_review_llm(), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="一种城市体检指标驱动无人机主动采集方法方法",
            claims="好的，根据交底书撰写权利要求。\n1. 一种旧方法。",
            description=(
                "本发明涉及无人机任务规划技术领域，说明书包括贡献矩阵和后验更新流程。\n\n"
                "补充实施方式：\n"
                "在一个实施例中，针对权利要求特征“主席修订权利要求1”，系统接收 input_data 并形成中间状态记录。\n\n"
                "具体实施方式中，系统根据指标置信度生成采集任务。"
            ),
            drawing_description="好的，根据您提供的材料，图1为系统流程图。",
        ),
    )
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compile_run["status"] == "completed"
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is False

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/apply-safe-patches")

    assert response.status_code == 200
    result = response.json()
    assert result["applied_count"] == 4
    assert result["previous_draft_hash"] == review["draft_package_hash"]
    assert result["current_draft_hash"] != review["draft_package_hash"]
    package = result["package"]
    assert package["title"] == "一种城市体检指标驱动无人机主动采集方法"
    assert package["claims"].startswith("1. 一种城市体检指标驱动无人机主动采集方法")
    assert package["drawing_description"] == "图1为系统流程图。"
    assert "补充实施方式" not in package["description"]
    assert "主席修订" not in package["description"]
    assert "input_data" not in package["description"]

    project = client.get(f"/api/projects/{project_id}").json()
    assert project["package"]["title"] == package["title"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "current draft" in export_response.json()["detail"]


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


def test_manual_draft_package_update_preserves_metadata_and_changes_hash(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _package(
            title="旧标题",
            claims="1. 旧权利要求。",
            generation_logs=["manual editor regression guard"],
            image_prompt="保留的内部绘图提示",
        ),
    )
    before = client.get(f"/api/projects/{project_id}/post-draft-reviews").json()["current_draft_hash"]

    response = client.put(
        f"/api/projects/{project_id}/draft-package",
        json={
            "title": "一种基于城市体检指标置信度的无人机主动采集方法",
            "abstract": "本发明公开一种按置信度主动采集的方法。",
            "claims": "1. 一种方法，包括基于置信度热力图生成采集任务。",
            "description": "本发明涉及无人机主动采集技术领域。",
            "drawing_description": "图1为方法流程图。",
        },
    )

    assert response.status_code == 200
    package = response.json()
    assert package["title"] == "一种基于城市体检指标置信度的无人机主动采集方法"
    assert package["claims"].startswith("1. 一种方法")
    assert package["generation_logs"] == ["manual editor regression guard"]
    assert package["image_prompt"] == "保留的内部绘图提示"
    after = client.get(f"/api/projects/{project_id}/post-draft-reviews").json()["current_draft_hash"]
    assert after != before


def test_invalid_json_post_draft_review_downgrades_role_and_completes(tmp_path):
    """One reviewer returning non-JSON is downgraded to blocked (not a whole-run
    crash); the review completes fail-closed. Other reviewers run normally."""
    base = _review_llm(export_allowed=False)
    # Override technical_hardness to return non-JSON (the production failure).
    base.responses["post_draft_technical_hardness"] = "this is plain text, not json"
    client = TestClient(create_app(data_dir=tmp_path, llm_client=base, load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; logs={run.get('logs')}"
    assert run["export_allowed"] is False
    technical = next(r for r in run["role_results"] if r["role"] == "technical_hardness")
    assert technical["status"] == "blocked"
    assert any(
        log["level"] == "error" and "downgraded to blocked" in log["message"] and log["provider_id"] == "technical_hardness"
        for log in run["logs"]
    )


def test_post_draft_review_repairs_common_schema_drift_and_stays_fail_closed(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_schema_drift_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["export_allowed"] is False
    assert run["role_results"][0]["status"] == "passed"
    assert run["role_results"][1]["status"] == "blocked"
    assert run["role_results"][1]["official_safe_patches"]
    assert run["chair_result"]["status"] == "blocked"
    assert any(log["level"] == "warn" and "schema repair" in log["message"] for log in run["logs"])

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409


def test_post_draft_review_schema_failure_downgrades_role_and_completes(tmp_path):
    """A reviewer returning an invalid schema (missing required enum) is
    downgraded to blocked; the review completes fail-closed. Other reviewers
    run normally."""
    base = _review_llm(export_allowed=False)
    # claims_reviewer missing the required `status` field -> repair fills it in
    # as needs_revision; the review completes without triggering the downgrade
    # path (no "downgraded" error log).
    base.responses["post_draft_claims_reviewer"] = """
{
  "role": "claims_reviewer",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
"""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=base, load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; logs={run.get('logs')}"
    assert run["export_allowed"] is False
    claims = next(r for r in run["role_results"] if r["role"] == "claims_reviewer")
    assert claims["status"] == "needs_revision"
    # Repair must be logged, but no catastrophic downgrade should occur.
    repair_logs = [log for log in run["logs"] if log["level"] == "warn" and "schema repair" in log["message"]]
    assert repair_logs
    assert not any(log["level"] == "error" and "downgraded" in log["message"] for log in run["logs"])


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


def _safe_patch_review_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
  "status": "blocked",
  "blocking_issues": ["权利要求含内部引导语。"],
  "contamination_hits": ["好的，根据"],
  "rewrite_suggestions": ["替换为干净权利要求。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec_cleaner",
  "status": "blocked",
  "blocking_issues": ["说明书含补充实施方式和内部标记。"],
  "contamination_hits": ["补充实施方式", "主席修订"],
  "rewrite_suggestions": ["删除内部污染段落。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "blocked",
  "blocking_issues": ["需重新会审技术硬度。"],
  "contamination_hits": [],
  "rewrite_suggestions": ["补充量化实施例。"],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "blocked",
  "export_allowed": false,
  "blocking_issues": ["需要先应用安全补丁并重新会审。"],
  "contamination_hits": ["内部引导语", "补充实施方式"],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": ["重新运行正式稿编译。"],
  "official_safe_patches": [
    "{\\"action\\": \\"replace\\", \\"target\\": \\"title\\", \\"content\\": \\"一种城市体检指标驱动无人机主动采集方法\\"}",
    "{\\"action\\": \\"replace_with\\", \\"target\\": \\"claims\\", \\"content\\": \\"1. 一种城市体检指标驱动无人机主动采集方法，其特征在于，包括：根据城市体检指标置信度生成无人机采集任务。\\"}",
    "{\\"action\\": \\"remove_all_instances_of\\", \\"target\\": \\"description\\", \\"content\\": [\\"补充实施方式：\\", \\"主席修订\\", \\"待验证\\"]}",
    "{\\"action\\": \\"replace\\", \\"target\\": \\"drawing_description\\", \\"content\\": \\"图1为系统流程图。\\"}"
  ],
  "attorney_memo": ["安全补丁只写回工作稿，不允许直接导出。"],
  "next_actions": ["重新编译正式稿", "重新成稿会审"]
}
""",
        }
    )



def test_post_draft_review_chair_invalid_json_downgrades_and_completes(tmp_path):
    """Chair synthesis returning non-JSON is downgraded to a blocked chair; the
    review completes fail-closed. Reviewer findings are still surfaced."""
    base = _review_llm(export_allowed=False)
    base.responses["post_draft_chair_synthesis"] = "chair returned plain text"
    client = TestClient(create_app(data_dir=tmp_path, llm_client=base, load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; logs={run.get('logs')}"
    assert run["export_allowed"] is False
    assert run["chair_result"]["status"] == "blocked"
    assert any(
        log["level"] == "error" and log["provider_id"] == "chair" and "downgraded" in log["message"]
        for log in run["logs"]
    )


def _schema_drift_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": """
{
  "role": "claims",
  "status": "PASSED",
  "blocking_issues": "",
  "contamination_hits": "[]",
  "rewrite_suggestions": "权利要求1保留闭环。",
  "official_safe_patches": {"target": "claims", "patch": "不应直接入稿"},
  "attorney_memo": "权利要求需代理人复核。"
}
""",
            "post_draft_spec_cleaner": """
{
  "role": "spec",
  "status": "BLOCKING",
  "blocking_issues": "说明书仍需复核支撑。",
  "contamination_hits": {"field": "description", "text": "support_gap"},
  "rewrite_suggestions": ["删除内部提示词。"],
  "official_safe_patches": [{"target": "description", "text": "support_gap"}],
  "attorney_memo": "清污后再提交。"
}
""",
            "post_draft_technical_hardness": """
{
  "role": "technical_hardness",
  "status": "PASSED",
  "blocking_issues": [],
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": []
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "PASSED",
  "export_allowed": "true",
  "blocking_issues": "",
  "contamination_hits": "",
  "claim_1_rewrite": null,
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": "补充实施例。",
  "official_safe_patches": {"target": "description", "text": "object patch"},
  "attorney_memo": "主席综合意见。",
  "next_actions": "修复后重新会审。"
}
""",
        }
    )


def _unknown_status_llm() -> FakeLLMClient:
    """LLM whose technical_hardness role returns a status outside the known
    alias table (the failure mode observed in production run e9b7484d)."""
    return FakeLLMClient(
        {
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
  "status": "revision_needed",
  "blocking_issues": ["技术贡献矩阵缺失量化指标。"],
  "contamination_hits": [],
  "rewrite_suggestions": ["补充增益计算的实施细节。"],
  "official_safe_patches": [],
  "attorney_memo": ["硬度需代理人复核。"]
}
""",
            "post_draft_chair_synthesis": """
{
  "status": "needs_revision",
  "export_allowed": false,
  "blocking_issues": ["技术贡献矩阵缺失。"],
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": ["补充实施例。"],
  "official_safe_patches": [],
  "attorney_memo": ["主席综合意见。"],
  "next_actions": ["修复后重新会审。"]
}
""",
        }
    )


def test_post_draft_review_unknown_status_falls_back_to_needs_revision(tmp_path):
    """An unmapped role status must fall back to needs_revision instead of
    failing the whole review with schema_validation."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_unknown_status_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; got {run.get('status')}"
    technical = next(r for r in run["role_results"] if r["role"] == "technical_hardness")
    assert technical["status"] == "needs_revision"
    assert technical["blocking_issues"] == ["技术贡献矩阵缺失量化指标。"]
    assert run["chair_result"]["status"] == "needs_revision"
    assert run["export_allowed"] is False


def _missing_status_llm() -> FakeLLMClient:
    """LLM whose claims_reviewer output omits the status key entirely."""
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": """
{
  "role": "claims_reviewer",
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
    )


def test_post_draft_review_missing_status_defaults_to_needs_revision(tmp_path):
    """A role result that omits status entirely must not crash the review."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_missing_status_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; got {run.get('status')}"
    claims = next(r for r in run["role_results"] if r["role"] == "claims_reviewer")
    assert claims["status"] == "needs_revision"


def _null_status_llm() -> FakeLLMClient:
    """LLM whose chair synthesis returns status: null."""
    return FakeLLMClient(
        {
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
  "status": null,
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
    )


def test_post_draft_review_null_status_defaults_to_needs_revision(tmp_path):
    """A chair synthesis with status: null must fall back instead of rejecting None as str."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_null_status_llm(), load_env_file=False))
    project_id = _create_project_with_package(client, _package())
    assert client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()["status"] == "completed"

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed", f"review should complete, not crash; got {run.get('status')}"
    assert run["chair_result"]["status"] == "needs_revision"
