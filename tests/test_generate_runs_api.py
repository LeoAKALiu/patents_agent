"""Backend lifecycle tests for the /api/projects/{project_id}/generate-runs endpoints.

Covers: create, list, get, cancel, retry, active duplicate 409,
delete-project cascade, retry_of linkage, and legacy /generate compatibility.
"""

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import GenerateRun


def _create_project(client: TestClient, name: str = "test-generate-runs") -> str:
    return client.post(
        "/api/projects",
        json={"name": name, "draft_text": "一种基于神经网络的图像缺陷识别方法，解决人工检测效率低的问题。"},
    ).json()["id"]


def _create_completed_deliberation(client: TestClient, project_id: str) -> None:
    """Create a completed deliberation run so the generate gate passes."""
    from test_deliberation_api import _FakeProviderRunner

    original = getattr(client.app.state, "provider_runner", None)
    client.app.state.provider_runner = _FakeProviderRunner()
    try:
        response = client.post(
            f"/api/projects/{project_id}/deliberations",
            json={"providers": ["codex", "deepseek", "claude"], "trace": False},
        )
        assert response.status_code == 200, f"deliberation setup failed: {response.json()}"
    finally:
        client.app.state.provider_runner = original


def _generate_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": "1. 一种图像缺陷识别方法，其特征在于，包括采集图像、训练模型并输出缺陷位置。",
            "description": "技术领域\n本发明涉及AI检测技术领域。\n发明内容\n本发明通过模型训练实现缺陷识别。",
            "abstract": "本发明公开了一种图像缺陷识别方法，能够提高检测效率。",
            "drawings": "图1为方法流程图。\n图2为系统结构图。",
            "diagram": "flowchart TD\nA[采集图像] --> B[训练模型] --> C[输出缺陷位置]",
            "image_prompt": "黑白线稿，展示图像采集、模型训练、缺陷输出流程。",
        }
    )


# ── lifecycle ──────────────────────────────────────────────────────────


def test_generate_run_create_list_get(tmp_path):
    """POST /generate-runs creates a run; GET lists it; GET by id returns it."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    # --- create ---
    create_response = client.post(f"/api/projects/{project_id}/generate-runs", json={})
    assert create_response.status_code == 200
    run = create_response.json()
    assert run["status"] == "completed"
    assert run["project_id"] == project_id
    assert run["retry_of"] is None
    assert run["cancel_requested"] is False
    assert run["package"] is not None
    assert run["package"]["claims"] != ""

    # --- list ---
    list_response = client.get(f"/api/projects/{project_id}/generate-runs")
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == run["id"]

    # --- get by id ---
    get_response = client.get(f"/api/projects/{project_id}/generate-runs/{run['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == run["id"]


def test_generate_run_active_duplicate_409(tmp_path):
    """Creating a second generate run while one is active returns 409."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    # Create first run (synchronous, so it completes immediately)
    client.post(f"/api/projects/{project_id}/generate-runs", json={})

    # Manually insert a queued run to simulate an active run
    store = client.app.state.store
    active = GenerateRun(
        id="queued-gen",
        project_id=project_id,
        status="queued",
        providers=["llm"],
        events=["queued for test"],
    )
    store.create_generate_run(active)

    # Try to create another — should get 409
    dup_response = client.post(f"/api/projects/{project_id}/generate-runs", json={})
    assert dup_response.status_code == 409
    assert "already" in dup_response.json()["detail"]


def test_generate_run_get_not_found_404(tmp_path):
    """GET with a nonexistent run id returns 404."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    response = client.get(f"/api/projects/{project_id}/generate-runs/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ── cancel ─────────────────────────────────────────────────────────────


def test_cancel_queued_generate_run(tmp_path):
    """Cancelling a queued generate run marks it interrupted."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    store = client.app.state.store
    queued = GenerateRun(
        id="queued-gen-cancel",
        project_id=project_id,
        status="queued",
        providers=["llm"],
        events=["queued for cancel test"],
    )
    store.create_generate_run(queued)

    cancel_response = client.post(f"/api/projects/{project_id}/generate-runs/{queued.id}/cancel")
    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == "interrupted"
    assert cancelled["cancel_requested"] is True
    assert any("cancel request" in event.lower() for event in cancelled["events"])
    assert len(cancelled["failure_details"]) >= 1
    assert cancelled["failure_details"][0]["reason"] == "cancelled"


def test_cancel_completed_generate_run_is_idempotent(tmp_path):
    """Cancelling an already-completed run returns it unchanged."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    store = client.app.state.store
    completed = GenerateRun(
        id="completed-gen",
        project_id=project_id,
        status="completed",
        providers=["llm"],
        events=["completed"],
    )
    store.create_generate_run(completed)

    cancel_response = client.post(f"/api/projects/{project_id}/generate-runs/{completed.id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "completed"


def test_cancel_nonexistent_generate_run_404(tmp_path):
    """Cancelling a nonexistent run returns 404."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/generate-runs/nonexistent/cancel")
    assert response.status_code == 404


# ── retry ──────────────────────────────────────────────────────────────


def test_retry_generate_run_links_previous(tmp_path):
    """Retrying a completed run creates a new run with retry_of set."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    # Create first run
    first = client.post(f"/api/projects/{project_id}/generate-runs", json={}).json()
    assert first["status"] == "completed"

    # Retry it
    retry_response = client.post(f"/api/projects/{project_id}/generate-runs/{first['id']}/retry")
    assert retry_response.status_code == 200
    retry = retry_response.json()
    assert retry["status"] == "completed"
    assert retry["retry_of"] == first["id"]
    assert retry["id"] != first["id"]


def test_retry_when_active_run_exists_409(tmp_path):
    """Retry returns 409 when another run is already active."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    first = client.post(f"/api/projects/{project_id}/generate-runs", json={}).json()
    assert first["status"] == "completed"

    # Manually insert a queued run to block retry
    store = client.app.state.store
    active = GenerateRun(
        id="blocking-queued",
        project_id=project_id,
        status="queued",
        providers=["llm"],
    )
    store.create_generate_run(active)

    retry_response = client.post(f"/api/projects/{project_id}/generate-runs/{first['id']}/retry")
    assert retry_response.status_code == 409
    assert "already" in retry_response.json()["detail"]


def test_retry_nonexistent_run_404(tmp_path):
    """Retrying a nonexistent run returns 404."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/generate-runs/nonexistent/retry")
    assert response.status_code == 404


# ── delete-project cascade ─────────────────────────────────────────────


def test_delete_project_cascades_to_generate_runs(tmp_path):
    """Deleting a project removes all associated generate runs."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    # Create two generate runs
    client.post(f"/api/projects/{project_id}/generate-runs", json={})
    client.post(f"/api/projects/{project_id}/generate-runs/{client.get(f'/api/projects/{project_id}/generate-runs').json()['runs'][0]['id']}/retry")

    # Verify they exist
    list_before = client.get(f"/api/projects/{project_id}/generate-runs")
    assert list_before.status_code == 200
    assert len(list_before.json()["runs"]) == 2

    # Delete the project
    delete_response = client.delete(f"/api/projects/{project_id}")
    assert delete_response.status_code == 200

    # Verify runs are gone (project not found → 404)
    list_after = client.get(f"/api/projects/{project_id}/generate-runs")
    assert list_after.status_code == 404


# ── legacy /generate compatibility ─────────────────────────────────────


def test_legacy_generate_endpoint_still_works(tmp_path):
    """Legacy POST /generate returns a DraftPackage and updates project."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    generate_response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert generate_response.status_code == 200
    package = generate_response.json()
    assert package["title"] != ""
    assert "权利要求" in package["claims"] or "1." in package["claims"]
    assert package["deliberation_run_id"] is not None
    assert any("deliberation" in log for log in package["generation_logs"])

    # Verify project was updated with the package
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["package"] is not None
    assert project["package"]["claims"] == package["claims"]


def test_legacy_generate_without_deliberation_409(tmp_path):
    """Legacy /generate without deliberation returns 409."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert response.status_code == 409
    assert "Multi-agent deliberation" in response.json()["detail"]


def test_legacy_generate_without_llm_503(tmp_path, monkeypatch):
    """Legacy /generate without LLM config returns 503."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_response = client.post(
        "/api/projects",
        json={"name": "test", "draft_text": "test"},
    )
    project_id = project_response.json()["id"]

    response = client.post(f"/api/projects/{project_id}/generate", json={})
    assert response.status_code == 503
    assert "LLM" in response.json()["detail"] or "not configured" in response.json()["detail"]


def test_generate_runs_without_llm_503(tmp_path, monkeypatch):
    """POST /generate-runs without LLM config returns 503."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(create_app(data_dir=tmp_path, load_env_file=False))
    project_id = _create_project(client)

    response = client.post(f"/api/projects/{project_id}/generate-runs", json={})
    assert response.status_code == 503
    assert "LLM" in response.json()["detail"] or "not configured" in response.json()["detail"]


# ── running cancel ─────────────────────────────────────────────────────


def test_cancel_running_generate_run_sets_flag(tmp_path):
    """Cancelling a running generate run sets cancel_requested but keeps running status."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    store = client.app.state.store
    running = GenerateRun(
        id="running-gen-cancel",
        project_id=project_id,
        status="running",
        providers=["llm"],
        events=["run started"],
    )
    store.create_generate_run(running)

    cancel_response = client.post(f"/api/projects/{project_id}/generate-runs/{running.id}/cancel")
    assert cancel_response.status_code == 200
    cancelled = cancel_response.json()
    assert cancelled["status"] == "running"  # stays running; background task checks flag
    assert cancelled["cancel_requested"] is True
    assert any("cancel request" in event.lower() for event in cancelled["events"])


def test_execution_detects_cancel_flag(tmp_path):
    """_execute_generate_run detects cancel_requested and marks run interrupted."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    from backend.app.main import _execute_generate_run

    store = client.app.state.store
    run_id = "exec-cancel-test"
    queued = GenerateRun(
        id=run_id,
        project_id=project_id,
        status="queued",
        providers=["llm"],
        events=["run created"],
    )
    store.create_generate_run(queued)

    # Mark as running with cancel_requested
    running = queued.model_copy(
        update={"status": "running", "cancel_requested": True, "events": [*queued.events, "run started", "cancel requested"]}
    )
    store.update_generate_run(running)

    # Execute — should detect cancel and mark interrupted
    _execute_generate_run(
        app=client.app,
        store=store,
        index=client.app.state.index,
        project=store.get_project(project_id),
        project_id=project_id,
        run_id=run_id,
        deliberation_run_id=None,
        formula_run_id=None,
        run_timeout_ms=None,
        retry_of=None,
    )

    final = store.get_generate_run(project_id, run_id)
    assert final.status == "interrupted"
    assert any(failure.reason == "cancelled" for failure in final.failure_details)


# ── timeout ─────────────────────────────────────────────────────────────


def test_generate_run_timeout_fails(tmp_path):
    """run_timeout_ms triggers a timeout failure when execution exceeds budget."""
    from unittest.mock import patch
    import time

    from backend.app.main import _execute_generate_run

    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    store = client.app.state.store
    run_id = "timeout-test"

    # Create queued run
    queued = GenerateRun(
        id=run_id,
        project_id=project_id,
        status="queued",
        providers=["llm"],
        events=["run created"],
    )
    store.create_generate_run(queued)

    # Patch _build_draft_package to sleep past the 1ms timeout, then return a valid package
    def _slow_build(*args, **kwargs):
        time.sleep(0.1)  # 100ms > 1ms timeout

    with patch("backend.app.main._build_draft_package", side_effect=_slow_build):
        _execute_generate_run(
            app=client.app,
            store=store,
            index=client.app.state.index,
            project=store.get_project(project_id),
            project_id=project_id,
            run_id=run_id,
            deliberation_run_id=None,
            formula_run_id=None,
            run_timeout_ms=1,
            retry_of=None,
        )

    final = store.get_generate_run(project_id, run_id)
    assert final.status == "failed"
    assert any(failure.reason == "timeout" for failure in final.failure_details)


def test_generate_run_create_without_deliberation_409(tmp_path):
    """Create generate-runs without deliberation returns 409 (via failed run)."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)

    create_response = client.post(f"/api/projects/{project_id}/generate-runs", json={})
    assert create_response.status_code == 200
    run = create_response.json()
    assert run["status"] == "failed"
    error_details = [failure["message"] for failure in run.get("failure_details", [])]
    assert any("deliberation" in detail.lower() for detail in error_details), f"Expected deliberation error in: {error_details}"


# ── lifecycle events ───────────────────────────────────────────────────


def test_generate_run_records_full_lifecycle_events(tmp_path):
    """Create → poll verifies queued→running→completed event sequence."""
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_generate_llm()))
    project_id = _create_project(client)
    _create_completed_deliberation(client, project_id)

    create_response = client.post(f"/api/projects/{project_id}/generate-runs", json={})
    assert create_response.status_code == 200
    run = create_response.json()
    # With FakeLLMClient + inline mode, the run completes immediately
    assert run["status"] == "completed"
    events = run["events"]
    assert "run created" in events
    assert "run started" in events
    assert "run completed" in events
    assert run["package"] is not None
    assert run["package"]["claims"] != ""

    # Verify the project package was updated
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["package"] is not None
    assert project["package"]["claims"] == run["package"]["claims"]
