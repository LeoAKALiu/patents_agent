from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import _repair_patch_store, create_app
from backend.app.official_compile import source_draft_hash
from backend.app.schemas import (
    CompletionIssue,
    CompletionScoreCard,
    CompletionTask,
    DraftCompletionRun,
    DraftPackage,
    DraftRepairPatch,
    PostDraftReviewRun,
    ProposedPatch,
)
from tests.test_post_draft_review import _safe_patch_review_llm


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


def _completion_run(project_id: str, draft_package_hash: str) -> DraftCompletionRun:
    return DraftCompletionRun(
        id="completion-1",
        project_id=project_id,
        snapshot_hash="snapshot-1",
        draft_package_hash=draft_package_hash,
        status="completed",
        issues=[
            CompletionIssue(
                id="issue-1",
                category="claim_support_gap",
                severity="high",
                target="claim",
                source_refs=["claim:1"],
                message="Claim 1 lacks support.",
                why_it_matters="Unsupported features weaken the filing package.",
                suggested_action="补充权利要求的支撑内容。",
                blocks_submission=True,
            ),
            CompletionIssue(
                id="issue-2",
                category="claim_support_gap",
                severity="medium",
                target="description",
                source_refs=["description:1"],
                message="Description needs a concrete embodiment.",
                why_it_matters="Embodiment support is too thin.",
                suggested_action="补充说明书实施方式。",
                blocks_submission=True,
            ),
        ],
        tasks=[
            CompletionTask(
                id="task-1",
                issue_id="issue-1",
                task_type="revise_claim_support",
                priority=100,
                expected_output="Strengthen claim support.",
                draft_section_target="claims",
            ),
            CompletionTask(
                id="task-2",
                issue_id="issue-2",
                task_type="revise_description_support",
                priority=90,
                expected_output="Add embodiment support.",
                draft_section_target="description",
            ),
        ],
        patches=[
            ProposedPatch(
                id="patch-claim",
                task_id="task-1",
                target_section="claim",
                patch_kind="insert",
                before_text="1. 一种方法，其特征在于，包括旧特征。",
                after_text="其中，所述旧特征进一步包括置信度驱动的任务调度步骤。",
                rationale="补强权利要求1的支撑与保护点。",
                risk_delta="lower",
                evidence_refs=["evidence:E1"],
                can_enter_official_draft=True,
            ),
            ProposedPatch(
                id="patch-description",
                task_id="task-2",
                target_section="description",
                patch_kind="insert",
                before_text="说明书包含旧特征。",
                after_text="在一个实施例中，系统根据置信度结果生成对应的采集任务并写入追溯记录。",
                rationale="补充说明书实施方式。",
                risk_delta="lower",
                evidence_refs=["evidence:E2"],
                can_enter_official_draft=True,
            ),
        ],
        scorecard=CompletionScoreCard(
            authorization_stability=70,
            protection_scope=68,
            support_strength=66,
            prior_art_distinction=65,
            filing_maturity=64,
            official_hygiene=88,
            overall=70,
        ),
    )


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
    assert records[0]["protection_scope_changed"] is False


def test_revision_ledger_records_single_issue_claims_repair_as_scope_change(tmp_path) -> None:
    _repair_patch_store().clear()
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
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
        blocking_issues=["权利要求表述需修正"],
        contamination_hits=[],
        logs=[],
    )
    app.state.store.create_post_draft_review_run(run)
    patch = DraftRepairPatch(
        id="patch-claims",
        issue_id="issue-1",
        project_id=project_id,
        review_run_id=run.id,
        status="proposed",
        target_section="claims",
        original="旧特征",
        patched="新特征",
        diff_summary="修正权利要求保护特征",
        risk_notes=[],
        draft_package_hash=draft_hash,
    )
    _repair_patch_store()[patch.id] = patch

    apply_response = client.post(
        f"/api/projects/{project_id}/post-draft-reviews/{run.id}/repair-patches/{patch.id}/apply"
    )
    assert apply_response.status_code == 200

    records = client.get(f"/api/projects/{project_id}/revision-ledger").json()
    assert len(records) == 1
    assert records[0]["affected_sections"] == ["claims"]
    assert records[0]["protection_scope_changed"] is True


def test_revision_ledger_records_accept_all_completion_patches_sequentially(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "补强测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)
    run = app.state.store.create_draft_completion_run(_completion_run(project_id, source_draft_hash(package)))

    response = client.post(f"/api/projects/{project_id}/completion-runs/{run.id}/patches/accept-all")

    assert response.status_code == 200
    updated_project = client.get(f"/api/projects/{project_id}").json()
    assert "置信度驱动的任务调度步骤" in updated_project["package"]["claims"]
    assert "写入追溯记录" in updated_project["package"]["description"]

    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert ledger_response.status_code == 200
    records = ledger_response.json()
    assert len(records) == 2
    by_section = {tuple(record["affected_sections"]): record for record in records}

    claim_record = by_section[("claims",)]
    assert claim_record["revision_kind"] == "completion_patch"
    assert claim_record["protection_scope_changed"] is True
    assert claim_record["artifact_refs"] == [f"completion-run:{run.id}", "completion-patch:patch-claim"]

    description_record = by_section[("description",)]
    assert description_record["revision_kind"] == "completion_patch"
    assert description_record["protection_scope_changed"] is False
    assert description_record["artifact_refs"] == [f"completion-run:{run.id}", "completion-patch:patch-description"]


def test_revision_ledger_records_manual_draft_package_update(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "手工修改", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)

    response = client.put(
        f"/api/projects/{project_id}/draft-package",
        json={
            "title": package.title,
            "abstract": "更新后的摘要",
            "claims": "1. 一种方法，其特征在于，包括新特征。",
            "description": package.description,
            "drawing_description": package.drawing_description,
        },
    )

    assert response.status_code == 200
    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert ledger_response.status_code == 200
    records = ledger_response.json()
    assert len(records) == 1
    assert records[0]["revision_kind"] == "correction"
    assert records[0]["affected_sections"] == ["abstract", "claims"]
    assert records[0]["protection_scope_changed"] is True
    assert records[0]["artifact_refs"] == ["manual-draft-package"]


def test_revision_ledger_accept_all_completion_patches_rejects_stale_run(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "补强测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)
    run = app.state.store.create_draft_completion_run(_completion_run(project_id, source_draft_hash(package)))
    stale_package = package.model_copy(update={"abstract": "这是变更后的摘要。"})
    app.state.store.update_project_package(project_id, stale_package)

    response = client.post(f"/api/projects/{project_id}/completion-runs/{run.id}/patches/accept-all")

    assert response.status_code == 409
    assert "stale" in response.json()["detail"].lower()
    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert ledger_response.status_code == 200
    assert ledger_response.json() == []


def test_revision_ledger_single_completion_patch_accept_rejects_stale_run(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "单补丁测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package()
    app.state.store.update_project_package(project_id, package)
    run = app.state.store.create_draft_completion_run(_completion_run(project_id, source_draft_hash(package)))
    patch_id = "patch-claim"
    stale_package = package.model_copy(update={"abstract": "这是变更后的摘要。"})
    app.state.store.update_project_package(project_id, stale_package)

    response = client.post(f"/api/projects/{project_id}/completion-runs/{run.id}/patches/{patch_id}/accept")

    assert response.status_code == 409
    assert "stale" in response.json()["detail"].lower()
    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    assert ledger_response.status_code == 200
    assert ledger_response.json() == []
    stored_run = client.app.state.store.get_draft_completion_run(project_id, run.id)
    assert stored_run is not None
    patch = next(candidate for candidate in stored_run.patches if candidate.id == patch_id)
    assert patch.status == "proposed"


def test_revision_ledger_records_post_draft_safe_patch_apply(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_safe_patch_review_llm(), load_env_file=False))
    project = client.post("/api/projects", json={"name": "安全补丁", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package(
        title="一种城市体检指标驱动无人机主动采集方法方法",
        claims="好的，根据交底书撰写权利要求。\n1. 一种旧方法。",
        description=(
            "本发明涉及无人机任务规划技术领域，说明书包括贡献矩阵和后验更新流程。\n\n"
            "补充实施方式：\n"
            "在一个实施例中，针对权利要求特征“主席修订权利要求1”，系统接收 input_data 并形成中间状态记录。\n\n"
            "具体实施方式中，系统根据指标置信度生成采集任务。"
        ),
        drawing_description="好的，根据您提供的材料，图1为系统流程图。",
    )
    client.app.state.store.update_project_package(project_id, package)
    compile_run = client.post(f"/api/projects/{project_id}/official-compile-runs", json={}).json()
    assert compile_run["status"] == "completed"
    review = client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}).json()

    apply_response = client.post(f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/apply-safe-patches")

    assert apply_response.status_code == 200
    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    records = ledger_response.json()
    assert len(records) == 1
    assert records[0]["revision_kind"] == "post_draft_repair"
    assert records[0]["baseline_artifact_hash"] == review["draft_package_hash"]
    assert records[0]["new_artifact_hash"] == apply_response.json()["current_draft_hash"]
    assert set(records[0]["affected_sections"]) == {"title", "claims", "description", "drawing_description"}
    assert records[0]["protection_scope_changed"] is True


def test_revision_ledger_records_official_cleanup_apply(tmp_path) -> None:
    app = create_app(data_dir=tmp_path, llm_client=FakeLLMClient({}), load_env_file=False)
    client = TestClient(app)
    project = client.post("/api/projects", json={"name": "清污测试", "draft_text": "一种方法。"}).json()
    project_id = project["id"]
    package = _package(
        claims="### 权利要求书\n1. 一种城市体检指标驱动的无人机主动采集方法，包括生成任务有向无环图。",
        description=(
            "### 说明书\n"
            "本发明涉及城市体检智能体任务编排技术领域。\n"
            "### support_gaps（提交前需补强的实验或工程材料）\n"
            "#### 具体实施方式\n"
            "系统依据任务有向无环图调度采集、复核和交付物生成。"
        ),
    )
    client.app.state.store.update_project_package(project_id, package)

    compile_response = client.post(f"/api/projects/{project_id}/official-compile-runs", json={})
    blocked = compile_response.json()
    assert compile_response.status_code == 200
    assert blocked["status"] == "blocked"

    cleanup_response = client.post(f"/api/projects/{project_id}/official-compile-runs/{blocked['id']}/apply-cleanup")

    assert cleanup_response.status_code == 200
    ledger_response = client.get(f"/api/projects/{project_id}/revision-ledger")
    records = ledger_response.json()
    assert len(records) == 1
    assert records[0]["revision_kind"] == "official_cleanup"
    assert records[0]["baseline_artifact_hash"] == blocked["source_draft_hash"]
    assert records[0]["new_artifact_hash"] == cleanup_response.json()["current_draft_hash"]
    assert set(records[0]["affected_sections"]) == {"claims", "description"}
    assert records[0]["protection_scope_changed"] is True
