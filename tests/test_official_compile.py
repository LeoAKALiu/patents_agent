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
    _assert_cd_present(report_response)


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
    _assert_cd_absent(response)


def test_official_export_requires_recompile_when_draft_changes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.get(f"/api/projects/{project_id}/official-export.md")

    assert response.status_code == 409
    assert "Official draft compile is required for the current draft" in response.json()["detail"]
    _assert_cd_absent(response)


def test_locked_official_gate_refuses_formal_but_keeps_legacy_internal(tmp_path):
    # PR-2: while the formal export gate is locked (no compile, no review),
    # the official endpoints must refuse (409) and only the legacy /export.*
    # internal-working-draft endpoints may serve (200). This proves a locked
    # gate cannot hand out a formal draft via the legacy path — the legacy
    # export is the internal working draft, never the 正式提交稿.
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    # Gate is locked: no official compile run, no post-draft review yet.
    for ext in ("docx", "md"):
        official = client.get(f"/api/projects/{project_id}/official-export.{ext}")
        assert official.status_code == 409, ext
        assert "Official draft compile is required for the current draft" in official.json()["detail"]

    # Legacy internal-working-draft endpoints remain available (the internal path).
    legacy_md = client.get(f"/api/projects/{project_id}/export.md")
    assert legacy_md.status_code == 200
    assert "权利要求书" in legacy_md.text

    legacy_docx = client.get(f"/api/projects/{project_id}/export.docx")
    assert legacy_docx.status_code == 200
    assert legacy_docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


# ---------------------------------------------------------------------------
# Official export readiness metadata (PR-16A)
#
# The export gate can lock for several distinct reasons. API consumers must be
# able to tell *why* formal export is locked (and what to do next) without
# triggering the 409. These tests cover the readiness endpoint and the
# /official-compile-runs list ``export_readiness`` summary across every gate
# path, plus the machine-readable reason tag carried in the 409 detail.
# ---------------------------------------------------------------------------


def test_readiness_reports_draft_required_when_project_has_no_package(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = client.post(
        "/api/projects",
        json={"name": "无草稿项目", "draft_text": "一种城市体检指标驱动无人机采集方法。"},
    ).json()["id"]

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "draft_required"
    assert readiness["required_actions"] == ["generate_draft"]
    assert readiness["official_compile"]["state"] == "missing"
    assert readiness["post_draft_review"]["state"] == "missing"
    assert readiness["export_formats"] == []


def test_readiness_requires_official_compile_before_review_or_export(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "official_compile_required"
    assert readiness["required_actions"] == ["run_official_compile"]
    assert readiness["official_compile"]["state"] == "missing"
    assert readiness["post_draft_review"]["state"] == "missing"
    assert "[reason=official_compile_required]" in readiness["detail"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "[reason=official_compile_required]" in export_response.json()["detail"]


def test_readiness_locks_on_post_draft_review_required_after_clean_compile(tmp_path):
    """The core PR-16 regression: a clean official compile must NOT look
    export-ready. After compile (blocked_items=none) but before review, the
    readiness view must say formal export is locked because post-draft review
    is required — not silently appear ready."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))

    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    assert compile_response.status_code == 200
    compile_run = compile_response.json()
    assert compile_run["status"] == "completed"
    assert compile_run["blocked_items"] == []

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "post_draft_review_required"
    assert readiness["required_actions"] == ["run_post_draft_review"]
    assert readiness["official_compile"]["state"] == "present"
    assert readiness["official_compile"]["run_id"] == compile_run["id"]
    assert readiness["post_draft_review"]["state"] == "missing"
    assert readiness["export_formats"] == []
    assert "[reason=post_draft_review_required]" in readiness["detail"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "[reason=post_draft_review_required]" in export_response.json()["detail"]


def test_readiness_is_ready_and_export_succeeds_after_passing_review(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is True

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is True
    assert readiness["reason"] == "ready"
    assert readiness["required_actions"] == []
    assert readiness["detail"] == ""
    assert readiness["export_formats"] == ["docx", "md"]
    assert readiness["official_compile"]["state"] == "present"
    assert readiness["post_draft_review"]["state"] == "present"
    assert readiness["post_draft_review"]["export_allowed"] is True
    assert readiness["post_draft_review"]["run_id"] == review["id"]

    md_export = client.get(f"/api/projects/{project_id}/official-export.md")
    assert md_export.status_code == 200
    assert "权利要求书" in md_export.text
    docx_export = client.get(f"/api/projects/{project_id}/official-export.docx")
    assert docx_export.status_code == 200


def test_readiness_locks_on_post_draft_review_blocked(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()
    assert review["export_allowed"] is False

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "post_draft_review_blocked"
    assert readiness["required_actions"] == ["rerun_post_draft_review"]
    assert readiness["official_compile"]["state"] == "present"
    assert readiness["post_draft_review"]["state"] == "present"
    assert readiness["post_draft_review"]["export_allowed"] is False
    assert readiness["post_draft_review"]["run_id"] == review["id"]
    assert "[reason=post_draft_review_blocked]" in readiness["detail"]

    export_response = client.get(f"/api/projects/{project_id}/official-export.md")
    assert export_response.status_code == 409
    assert "[reason=post_draft_review_blocked]" in export_response.json()["detail"]


def test_readiness_409_details_distinguish_review_required_from_blocked(tmp_path):
    """Both locked review paths keep the legacy 'Post-draft multi-agent review
    is required' sentence (back-compat), but the [reason=...] tag must differ so
    a machine consumer can tell 'run review' from 'review blocked'."""
    required_client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    required_project = _create_project_with_package(required_client, _draft_package(claims="1. 一种方法。"))
    required_client.post(f"/api/projects/{required_project}/official-compile-runs", json={})
    required_export = required_client.get(f"/api/projects/{required_project}/official-export.md")
    assert required_export.status_code == 409
    required_detail = required_export.json()["detail"]
    assert "Post-draft multi-agent review is required" in required_detail
    assert "[reason=post_draft_review_required]" in required_detail
    assert "blocked" not in required_detail

    blocked_client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    blocked_project = _create_project_with_package(blocked_client, _draft_package(claims="1. 一种方法。"))
    blocked_client.post(f"/api/projects/{blocked_project}/official-compile-runs", json={})
    blocked_client.post(f"/api/projects/{blocked_project}/post-draft-reviews", json={})
    blocked_export = blocked_client.get(f"/api/projects/{blocked_project}/official-export.md")
    assert blocked_export.status_code == 409
    blocked_detail = blocked_export.json()["detail"]
    assert "Post-draft multi-agent review is required" in blocked_detail
    assert "[reason=post_draft_review_blocked]" in blocked_detail


def test_readiness_marks_official_compile_stale_after_draft_changes(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    client.app.state.store.update_project_package(project_id, _draft_package(abstract="修改后的摘要。"))

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "official_compile_required"
    assert readiness["official_compile"]["state"] == "stale"
    assert readiness["official_compile"]["run_id"] == compile_run["id"]
    assert readiness["post_draft_review"]["state"] == "missing"


def test_readiness_is_locked_again_after_a_second_compile_invalidates_prior_review(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=True), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package())
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})  # second compile

    response = client.get(f"/api/projects/{project_id}/official-export/readiness")

    readiness = response.json()
    assert readiness["ready"] is False
    assert readiness["reason"] == "post_draft_review_required"
    assert readiness["official_compile"]["state"] == "present"
    assert readiness["post_draft_review"]["state"] == "missing"


def test_official_compile_runs_list_exposes_export_readiness(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(export_allowed=False), load_env_file=False))
    project_id = _create_project_with_package(client, _draft_package(claims="1. 一种方法。"))

    before_compile = client.get(f"/api/projects/{project_id}/official-compile-runs").json()
    assert before_compile["export_readiness"]["reason"] == "official_compile_required"
    assert before_compile["export_readiness"]["official_compile"]["state"] == "missing"

    client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    after_compile = client.get(f"/api/projects/{project_id}/official-compile-runs").json()
    assert after_compile["export_readiness"]["reason"] == "post_draft_review_required"
    assert after_compile["export_readiness"]["official_compile"]["state"] == "present"

    client.post(f"/api/projects/{project_id}/post-draft-reviews", json={})
    after_review = client.get(f"/api/projects/{project_id}/official-compile-runs").json()
    assert after_review["export_readiness"]["reason"] == "post_draft_review_blocked"
    assert after_review["export_readiness"]["post_draft_review"]["state"] == "present"
    assert after_review["export_readiness"]["post_draft_review"]["export_allowed"] is False


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

def _assert_cd_present(response):
    """Verify the response carries a Content-Disposition: attachment header."""
    cd = response.headers.get("content-disposition", "")
    assert "attachment" in cd, f"Expected attachment Content-Disposition, got: {cd!r}"
    assert "filename=" in cd, f"Expected filename= in Content-Disposition, got: {cd!r}"


def _assert_cd_absent(response):
    """Verify the response does NOT carry a Content-Disposition header."""
    cd = response.headers.get("content-disposition", "")
    assert cd == "", f"Expected no Content-Disposition, got: {cd!r}"
