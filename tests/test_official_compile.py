from fastapi.testclient import TestClient

from backend.app.official_compile import (
    OfficialDraftCompiler,
)
from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.storage import SQLiteStore
from backend.app.schemas import DraftPackage


def test_compiler_blocks_internal_pollution_in_official_fields():
    package = _draft_package(
        claims="好的，下面撰写权利要求书。\n1. 一种方法。\n\n撰写说明与支撑不足提示 support_gap: 需要补矩阵。",
        description=(
            "## 说明书\n"
            "本发明涉及无人机采集。\n"
            "```mermaid\nflowchart TD\nA-->B\n```\n"
            "generation_logs: claims generated\n"
            "根据会审策略补充。"
        ),
        drawing_description="图1为方法流程图。\nimage_prompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "support_gap" for item in run.contamination_removed)
    assert any(item["pattern"] == "image_prompt" for item in run.contamination_removed)
    assert any(item["category"] == "official_hygiene_contamination" for item in run.blocked_items)


def test_compiler_moves_trailing_support_gap_appendix_to_sidecar_without_blocking():
    appendix = """
---
**提交前需补强的实验或工程材料 (support_gaps)**

为满足充分公开要求并增强权利要求稳定性，建议在提交前补充：
1. 置信度计算模型的具体化。
2. 航线规划算法的仿真验证。
"""
    package = _draft_package(
        claims="1. 一种基于置信度的无人机主动采集方法。\n2. 根据权利要求1所述的方法。" + appendix,
        description="本发明涉及无人机主动采集技术。实施例公开完整闭环流程。" + appendix,
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "completed"
    assert run.official_package is not None
    assert run.blocked_items == []
    assert any(item["category"] == "support_gap_appendix" and item["section"] == "claims" for item in run.sidecar_notes)
    assert any(item["category"] == "support_gap_appendix" and item["section"] == "description" for item in run.sidecar_notes)
    assert "support_gaps" not in run.official_package.claims
    assert "提交前需补强" not in run.official_package.claims
    assert "航线规划算法的仿真验证" not in run.official_package.description


def test_compiler_blocks_cross_project_title_contamination():
    package = _draft_package(
        description="本说明书还包括：基于边缘端动态推理的无人机飞行中任务调整方法。"
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "cross_project_contamination" for item in run.blocked_items)


def test_compiler_blocks_when_cleaning_empties_required_section():
    package = _draft_package(description="support_gap: 说明书待补充。")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["category"] == "empty_required_section" for item in run.blocked_items)


def test_compiler_blocks_json_style_prompt_internal_field():
    package = _draft_package(
        drawing_description='图1为方法流程图。\n"prompt": "黑白线稿"',
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(item["pattern"] == "prompt" for item in run.contamination_removed)


def test_compiler_blocks_case_insensitive_internal_labels_and_memos():
    package = _draft_package(
        description=(
            "本发明涉及无人机任务规划技术领域。\n"
            "attorney_memo: 代理人复核从属权利要求。\n"
            "System_Trace: deliberation payload\n"
            "official_safe_patches: patch-1"
        ),
        drawing_description="图1为方法流程图。\nPrompt: 黑白线稿。",
    )

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert {item["pattern"] for item in run.contamination_removed} >= {
        "prompt",
        "attorney_memo",
        "system_trace",
        "official_safe_patches",
    }


def test_compiler_blocks_ai_preface_title_contamination():
    package = _draft_package(title="好的，下面撰写一种方法")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] in {"residual_internal_text", "empty_required_section"}
        and item["section"] == "title"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_drawing_description():
    package = _draft_package(drawing_description="图1为方法流程图。prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "drawing_description"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_inline_prompt_contamination_in_title():
    package = _draft_package(title="一种方法 prompt: 黑白线稿")

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "residual_internal_text"
        and item["section"] == "title"
        and item["pattern"] == "prompt"
        for item in run.blocked_items
    )


def test_compiler_blocks_json_wrapper_only_required_section():
    package = _draft_package(drawing_description='{\n  "prompt": "黑白线稿"\n}')

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] == "empty_required_section"
        and item["section"] == "drawing_description"
        for item in run.blocked_items
    )


def test_compiler_blocks_empty_official_section_json_wrapper():
    package = _draft_package(drawing_description='{\n  "drawing_description": ""\n}')

    run = OfficialDraftCompiler().compile(project_id="p1", package=package)

    assert run.status == "blocked"
    assert run.official_package is None
    assert any(
        item["category"] in {"empty_required_section", "json_wrapper"}
        and item["section"] == "drawing_description"
        for item in run.blocked_items
    )


def test_sqlite_store_persists_official_compile_run(tmp_path):
    store = SQLiteStore(tmp_path / "store.sqlite3")
    package = _draft_package(claims="1. 一种方法。")
    run = OfficialDraftCompiler().compile(project_id="p1", package=package)
    assert run.status == "completed"
    assert run.official_package is not None
    blocked_run = OfficialDraftCompiler().compile(
        project_id="p1",
        package=_draft_package(description="support_gap: 说明书待补充。"),
    )
    assert blocked_run.status == "blocked"
    failed_run = run.model_copy(update={"id": "failed-official-compile", "status": "failed"})

    stored = store.create_official_compile_run(run)
    store.create_official_compile_run(blocked_run)
    store.create_official_compile_run(failed_run)

    assert stored.created_at
    assert stored.updated_at
    fetched = store.get_official_compile_run("p1", run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.official_package is not None
    assert fetched.official_package.title == package.title
    assert fetched.official_package_hash == run.official_package_hash
    assert fetched.contamination_removed == run.contamination_removed
    assert fetched.sidecar_notes == run.sidecar_notes
    assert fetched.logs[0].phase == "official_compile"
    listed = store.list_official_compile_runs("p1")
    assert {item.id for item in listed} == {run.id, blocked_run.id, failed_run.id}
    latest = store.get_latest_completed_official_compile_run("p1")
    assert latest is not None
    assert latest.id == run.id
    latest_for_hash = store.get_latest_completed_official_compile_run_for_hash("p1", run.source_draft_hash)
    assert latest_for_hash is not None
    assert latest_for_hash.id == run.id


def test_official_compile_api_creates_lists_gets_and_exports_report(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))

    create_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})

    assert create_response.status_code == 200
    run = create_response.json()
    assert run["status"] == "completed"
    assert run["official_package"]["title"] == "一种城市体检指标驱动无人机主动采集方法"
    assert "1. 一种方法。" in run["official_package"]["claims"]

    list_response = client.get(f"/api/projects/{project_id}/official-compile-runs")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["current_source_draft_hash"] == run["source_draft_hash"]
    assert [item["id"] for item in listed["runs"]] == [run["id"]]

    detail_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["official_package_hash"] == run["official_package_hash"]

    report_response = client.get(f"/api/projects/{project_id}/official-compile-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert report_response.headers["content-type"].startswith("text/markdown")
    assert "# OFFICIAL_COMPILE_RUN" in report_response.text
    assert run["id"] in report_response.text
    assert "## Official Package" in report_response.text


def test_post_draft_review_requires_completed_official_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 409
    assert "Official draft compile is required" in response.json()["detail"]


def test_post_draft_review_requires_completed_official_compile_for_current_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert response.status_code == 409
    assert "Official draft compile is required" in response.json()["detail"]


def test_post_draft_review_records_official_package_hash_and_unlocks_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))
    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    compile_run = compile_response.json()
    assert compile_run["status"] == "completed"

    review_response = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    assert review_response.status_code == 200
    review = review_response.json()
    assert review["status"] == "completed"
    assert review["export_allowed"] is True
    assert review["draft_package_hash"] == compile_run["source_draft_hash"]
    assert review["official_compile_run_id"] == compile_run["id"]
    assert review["official_package_hash"] == compile_run["official_package_hash"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 200
    assert "权利要求书" in export_response.text


def test_official_export_uses_compiled_package_not_raw_draft(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(
        client,
        _draft_package(
            claims="1. 一种方法，包括生成任务包。",
            image_prompt="内部绘图提示词。",
            generation_logs=["generation_logs: internal"],
        ),
    )
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 200
    assert "1. 一种方法，包括生成任务包。" in response.text
    assert "内部绘图提示词" not in response.text
    assert "generation_logs" not in response.text


def test_review_for_previous_compile_run_cannot_unlock_latest_compile(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    first_compile = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is True
    assert review["official_compile_run_id"] == first_compile["id"]

    second_compile = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert second_compile["status"] == "completed"
    assert second_compile["id"] != first_compile["id"]
    assert second_compile["source_draft_hash"] == first_compile["source_draft_hash"]
    assert second_compile["official_package_hash"] == first_compile["official_package_hash"]

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Post-draft multi-agent review is required" in response.json()["detail"]


def test_official_export_requires_recompile_when_draft_changes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Official draft compile is required for the current draft" in response.json()["detail"]


def _create_project_with_package(client: TestClient, package: DraftPackage) -> str:
    project_id = client.post(
        "/api/projects",
        json={"name": "正式稿编译测试", "draft_text": "一种城市体检指标驱动无人机采集方法。"},
    ).json()["id"]
    client.app.state.store.update_project_package(project_id, package)
    return project_id


def _draft_package(**overrides) -> DraftPackage:
    data = {
        "title": "一种城市体检指标驱动无人机主动采集方法",
        "abstract": "本发明公开了一种无人机主动采集方法。",
        "claims": "1. 一种方法，包括生成无人机任务包。",
        "description": "本发明涉及无人机任务规划技术领域。",
        "drawing_description": "图1为方法流程图。",
        "mermaid": "flowchart TD",
        "image_prompt": "黑白线稿",
        "review_findings": [],
        "citations": [],
        "generation_logs": ["claims generated"],
    }
    data.update(overrides)
    return DraftPackage(**data)


def _review_llm(*, export_allowed: bool) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    chair_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["正式稿存在阻断问题。"]
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": _role_json("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_json("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_json("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": f"""
{{
  "status": "{chair_status}",
  "export_allowed": {str(export_allowed).lower()},
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "claim_1_rewrite": "",
  "system_claim_rewrite": "",
  "abstract_rewrite": "",
  "description_rewrite_tasks": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"],
  "next_actions": []
}}
""".replace("'", '"'),
        }
    )


def _role_json(role: str, status: str, blocking_issues: list[str]) -> str:
    return f"""
{{
  "role": "{role}",
  "status": "{status}",
  "blocking_issues": {blocking_issues!r},
  "contamination_hits": [],
  "rewrite_suggestions": [],
  "official_safe_patches": [],
  "attorney_memo": ["内部备忘。"]
}}
""".replace("'", '"')
