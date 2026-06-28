from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import _repair_patch_store, create_app
from backend.app.official_compile import source_draft_hash
from backend.app.schemas import DraftPackage, DraftRepairPatch, PostDraftReviewRun


def _package(**overrides) -> DraftPackage:
    payload = {
        "title": "一种方法",
        "abstract": "摘要",
        "claims": "1. 一种方法，其特征在于，包括旧特征。",
        "description": "说明书包含旧特征。",
        "drawing_description": "图1。",
        "mermaid": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿",
    }
    payload.update(overrides)
    return DraftPackage(**payload)


def test_revision_ledger_api_lists_records_after_safe_patch(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)

    run = PostDraftReviewRun(
        id="review-1",
        project_id=project_id,
        status="completed",
        providers=["fake"],
        prompt_pack_version="test",
        draft_package_hash=source_draft_hash(package),
        export_allowed=False,
        blocking_issues=[],
        contamination_hits=[],
        logs=[],
    )
    app.state.store.create_post_draft_review_run(run)

    response = client.get(f"/api/projects/{project_id}/revision-ledger")

    assert response.status_code == 200
    assert response.json() == []


def test_revision_ledger_records_single_issue_repair_patch(tmp_path) -> None:
    _repair_patch_store().clear()
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package(title="一种重复重复方法")
    app.state.store.update_project_package(project_id, package)
    draft_hash = source_draft_hash(package)
    run = PostDraftReviewRun(
        id="review-1",
        project_id=project_id,
        status="completed",
        providers=["fake"],
        prompt_pack_version="test",
        draft_package_hash=draft_hash,
        export_allowed=False,
        blocking_issues=["标题存在重复词汇"],
        contamination_hits=[],
        logs=[],
    )
    app.state.store.create_post_draft_review_run(run)
    patch = DraftRepairPatch(
        id="patch-1",
        issue_id="issue-1",
        project_id=project_id,
        review_run_id=run.id,
        status="proposed",
        target_section="title",
        original="重复重复",
        patched="重复",
        diff_summary="删除重复词",
        risk_notes=[],
        draft_package_hash=draft_hash,
    )
    _repair_patch_store()[patch.id] = patch

    apply_response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{run.id}/repair-patches/{patch.id}/apply"
    )
    assert apply_response.status_code == 200

    response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["revision_kind"] == "post_draft_repair"
    assert records[0]["baseline_artifact_hash"] == draft_hash
    assert records[0]["new_artifact_hash"] == apply_response.json()["current_draft_hash"]
    assert records[0]["affected_sections"] == ["title"]
