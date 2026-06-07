from backend.app.schemas import CompletionScoreCard, CompletionTask, DraftCompletionRun, ProposedPatch
from backend.app.storage import SQLiteStore
from fastapi.testclient import TestClient

from backend.app.main import create_app


def _stored_completion_run(project_id: str = "project-1") -> DraftCompletionRun:
    return DraftCompletionRun(
        id="run-1",
        project_id=project_id,
        snapshot_hash="hash-1",
        status="completed",
        tasks=[
            CompletionTask(
                id="task-1",
                issue_id="issue-1",
                task_type="revise_draft_support",
                priority=100,
                expected_output="Strengthen claim support.",
                draft_section_target="claims",
            )
        ],
        patches=[
            ProposedPatch(
                id="patch-1",
                task_id="task-1",
                target_section="claims",
                patch_kind="rewrite",
                before_text="old claim text",
                after_text="new claim text",
                rationale="Strengthen claim support.",
                risk_delta="lower",
                evidence_refs=["matrix:claim-1"],
            )
        ],
        scorecard=CompletionScoreCard(
            authorization_stability=80,
            protection_scope=75,
            support_strength=70,
            prior_art_distinction=65,
            filing_maturity=72,
            official_hygiene=90,
            overall=75,
        ),
    )


def test_store_persists_and_updates_completion_runs(tmp_path):
    db_path = tmp_path / "patents_agent.sqlite3"
    store = SQLiteStore(db_path)
    run = store.create_draft_completion_run(_stored_completion_run())

    assert store.get_draft_completion_run("project-1", run.id) is not None
    assert store.list_draft_completion_runs("project-1")[0].id == "run-1"

    updated = store.update_completion_patch_status("project-1", "run-1", "patch-1", "accepted")
    assert updated is not None
    assert updated.patches[0].status == "accepted"
    assert updated.tasks[0].status == "accepted"

    reloaded = store.get_draft_completion_run("project-1", "run-1")
    assert reloaded is not None
    assert reloaded.patches[0].status == "accepted"
    assert reloaded.tasks[0].status == "accepted"

    reopened = SQLiteStore(db_path)
    persisted = reopened.get_draft_completion_run("project-1", "run-1")
    assert persisted is not None
    assert persisted.patches[0].status == "accepted"
    assert persisted.tasks[0].status == "accepted"

    updated = store.update_completion_patch_status("project-1", "run-1", "missing", "accepted")
    assert updated is None


def _client(tmp_path):
    return TestClient(create_app(data_dir=tmp_path, load_env_file=False))


def test_completion_api_runs_lists_exports_and_updates_patch_status(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "name": "外立面逆建模",
            "draft_text": "一种生成IfcRelVoidsElement并建立工程量清单回链的方法。",
        },
    ).json()
    package_response = client.post(f"/api/projects/{project['id']}/generate")
    assert package_response.status_code == 503

    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种既有建筑外立面逆建模方法",
            abstract="本发明公开一种外立面逆建模方法。",
            claims="1. 一种方法，其特征在于生成IfcRelVoidsElement并建立工程量清单回链。",
            description="本实施例生成IFC模型。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="prompt",
            review_findings=[],
            citations=[],
            generation_logs=["deliberation: no completed multi-agent deliberation injected"],
        ),
    )

    run_response = client.post(f"/api/projects/{project['id']}/completion-runs")
    assert run_response.status_code == 200
    run = run_response.json()
    assert run["scorecard"]["overall"] <= 100
    assert run["issues"]

    list_response = client.get(f"/api/projects/{project['id']}/completion-runs")
    assert list_response.status_code == 200
    assert list_response.json()["runs"][0]["id"] == run["id"]

    report_response = client.get(f"/api/projects/{project['id']}/completion-runs/{run['id']}/report.md")
    assert report_response.status_code == 200
    assert "DRAFT_COMPLETION_REPORT" in report_response.text

    patch_id = run["patches"][0]["id"]
    accept_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/accept")
    assert accept_response.status_code == 200
    accepted_run = accept_response.json()
    accepted_patch = next(patch for patch in accepted_run["patches"] if patch["id"] == patch_id)
    assert accepted_patch["status"] == "accepted"
    assert any(
        task["id"] == accepted_patch["task_id"] and task["status"] == "accepted"
        for task in accepted_run["tasks"]
    )

    reject_response = client.post(f"/api/projects/{project['id']}/completion-runs/{run['id']}/patches/{patch_id}/reject")
    assert reject_response.status_code == 200
    rejected_run = reject_response.json()
    rejected_patch = next(patch for patch in rejected_run["patches"] if patch["id"] == patch_id)
    assert rejected_patch["status"] == "rejected"
    assert any(
        task["id"] == rejected_patch["task_id"] and task["status"] == "rejected"
        for task in rejected_run["tasks"]
    )


def test_score_improvement_applies_safe_patches_and_re_scores_project(tmp_path):
    client = _client(tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "name": "通用处理流程",
            "draft_text": "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        },
    ).json()
    app = client.app
    store = app.state.store
    from backend.app.schemas import DraftPackage

    store.update_project_package(
        project["id"],
        DraftPackage(
            title="一种输入数据处理方法",
            abstract="本发明公开一种输入数据处理方法。",
            claims="1. 一种输入数据处理方法，其特征在于，包括接收输入数据、生成处理结果并输出控制指令。",
            description="本实施例接收输入数据。",
            drawing_description="图1为流程图。",
            mermaid="flowchart TD\nA-->B",
            image_prompt="prompt",
            review_findings=[],
            citations=[],
            generation_logs=[],
        ),
    )

    response = client.post(f"/api/projects/{project['id']}/score-improvement", json={"max_rounds": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["before_score"] < payload["after_score"]
    assert payload["accepted_patch_ids"]
    assert any("重新评分" in line for line in payload["logs"])

    updated_project = client.get(f"/api/projects/{project['id']}").json()
    assert "生成处理结果" in updated_project["package"]["description"]
    assert "伪代码" in updated_project["package"]["description"]
