from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import create_app
from backend.app.schemas import (
    ClaimDefenseWorksheet,
    CompletionScoreCard,
    DraftCompletionRun,
    FilingReadinessReport,
    OfficialCompileRun,
    OfficialDraftPackage,
    PostDraftReviewRun,
)
from flow_driver import FlowDriver


def test_flow_driver_observes_export_gate_and_hash_invalidation(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    initial = driver.state()
    assert initial.step_status[5] == "completed"
    assert initial.export_allowed is False
    assert initial.gates["official_compile"] == "missing"

    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    ready = driver.state()
    assert ready.export_allowed is True
    assert ready.gates["official_compile"] == "current"
    assert ready.gates["post_draft_review"] == "current"

    driver.edit_source_draft("本发明涉及数据处理技术领域。修改后的实施例改变源稿哈希。")

    stale = driver.state()
    assert stale.export_allowed is False
    assert stale.gates["official_compile"] == "stale"
    assert stale.gates["post_draft_review"] == "stale"
    assert stale.hashes["current_source_draft_hash"] != ready.hashes["current_source_draft_hash"]
    assert driver.export_official()["blocked"] is True
    assert driver.export_internal()["ok"] is True


def test_flow_driver_export_gate_blocks_until_compile_and_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project("空项目", "一种尚未生成初稿的方法。", patent_type="invention")

    no_draft = driver.export_official()
    assert no_draft["blocked"] is True
    assert "Generate a draft" in no_draft["detail"]

    driver = _driver_with_working_draft(client)
    no_quality = driver.export_official()
    assert no_quality["blocked"] is True
    assert "Quality checks are required" in no_quality["detail"]

    driver.run_quality()
    no_compile = driver.export_official()
    assert no_compile["blocked"] is True
    assert "Official draft compile is required" in no_compile["detail"]
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    no_review = driver.export_official()
    assert no_review["blocked"] is True
    assert "Post-draft multi-agent review is required" in no_review["detail"]

    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True
    assert driver.export_official()["ok"] is True


def test_flow_driver_cannot_skip_required_steps_matrix(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = FlowDriver(client)
    project = driver.create_project("跳步矩阵", "一种尚未生成初稿的方法。", patent_type="invention")

    no_draft_readiness = driver.raw_get(f"/api/projects/{project['id']}/export-readiness")
    assert no_draft_readiness["next_action"] == "generate_draft"
    assert no_draft_readiness["draft_required"] is True
    for endpoint in ("filing-readiness", "completion-runs", "official-compile-runs", "post-draft-reviews"):
        status_code, detail = _post_status(client, project["id"], endpoint)
        assert status_code == 409
        assert "Generate a draft" in detail
    generate_without_deliberation = client.post(f"/api/projects/{project['id']}/generate", json={})
    assert generate_without_deliberation.status_code == 409
    assert "Multi-agent deliberation is required" in generate_without_deliberation.json()["detail"]

    driver = _driver_with_working_draft(client)

    missing_quality = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_quality["next_action"] == "run_quality_checks"
    assert missing_quality["quality_required"] is True
    assert missing_quality["missing_quality_checks"] == [
        "filing_readiness",
        "claim_defense_worksheet",
        "draft_completion",
    ]
    review_without_compile = driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_without_compile.status_code == 409
    assert "Official draft compile is required" in review_without_compile.json()["detail"]

    driver.run_quality()
    missing_compile = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_compile["next_action"] == "run_official_compile"
    assert missing_compile["official_compile_required"] is True

    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    missing_review = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert missing_review["next_action"] == "run_post_draft_review"
    assert missing_review["post_draft_review_required"] is True
    assert "Post-draft multi-agent review is required" in driver.export_official()["detail"]

    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True
    ready = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert ready["next_action"] == "export_ready"
    assert ready["export_allowed"] is True
    assert driver.export_official()["ok"] is True


def test_flow_driver_export_gate_requires_current_quality_checks(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_quality = driver.export_official()
    assert blocked_without_quality["blocked"] is True
    assert "Quality checks are required" in blocked_without_quality["detail"]
    missing_quality_state = driver.state()
    assert missing_quality_state.export_allowed is False
    assert missing_quality_state.gates["quality"] == "missing"

    driver.run_quality()

    ready = driver.state()
    assert ready.gates["quality"] == "current"
    assert ready.export_allowed is True
    assert driver.export_official()["ok"] is True


def test_flow_driver_state_requires_claim_defense_for_current_quality_gate(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness")
    assert filing.status_code == 200
    completion = client.post(f"/api/projects/{driver.project_id}/completion-runs")
    assert completion.status_code == 200

    state = driver.state()

    assert state.gates["quality"] == "missing"
    assert state.hashes["latest_worksheet_draft_hash"] == ""


def test_official_export_reports_missing_quality_before_missing_compile_for_legacy_drafts(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    readiness = driver.export_readiness()
    blocked_export = driver.export_official()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["missing_quality_checks"] == [
        "filing_readiness",
        "claim_defense_worksheet",
        "draft_completion",
    ]
    assert blocked_export["blocked"] is True
    assert "Quality checks are required" in blocked_export["detail"]
    assert "missing quality checks: filing_readiness, claim_defense_worksheet, draft_completion" in blocked_export["detail"]


def test_export_readiness_distinguishes_stale_quality_bundle_from_missing_checks(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    driver.compile_official()
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True
    assert driver.export_official()["ok"] is True

    driver.edit_source_draft("本发明涉及数据处理技术领域。修改后质量检查应全部过期。")

    readiness = driver.export_readiness()
    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["quality_required"] is True
    assert readiness["missing_quality_checks"] == []
    assert readiness["stale_quality_checks"] == [
        "filing_readiness",
        "claim_defense_worksheet",
        "draft_completion",
    ]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "stale",
        "claim_defense_worksheet": "stale",
        "draft_completion": "stale",
    }
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "stale quality checks" in blocked["detail"]
    assert "filing_readiness" in blocked["detail"]
    assert "claim_defense_worksheet" in blocked["detail"]
    assert "draft_completion" in blocked["detail"]


def test_export_readiness_reports_mixed_stale_and_missing_quality_checks(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness").json()
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets").json()
    old_hash = filing["draft_package_hash"]
    assert worksheet["draft_package_hash"] == old_hash
    client.app.state.store.create_draft_completion_run(
        DraftCompletionRun(
            id="failed-old-completion",
            project_id=driver.project_id,
            draft_package_hash=old_hash,
            status="failed",
            scorecard=_scorecard(),
            notes=["provider failed before a usable completion report was produced"],
        )
    )

    driver.edit_source_draft("本发明涉及数据处理技术领域。修改后仅旧质量检查部分可视为过期。")

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["missing_quality_checks"] == ["draft_completion"]
    assert readiness["stale_quality_checks"] == ["filing_readiness", "claim_defense_worksheet"]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "stale",
        "claim_defense_worksheet": "stale",
        "draft_completion": "missing",
    }
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "missing quality checks: draft_completion" in blocked["detail"]
    assert "stale quality checks: filing_readiness, claim_defense_worksheet" in blocked["detail"]


def test_export_readiness_reports_failed_current_quality_checks(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness").json()
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets").json()
    current_hash = filing["draft_package_hash"]
    assert worksheet["draft_package_hash"] == current_hash
    client.app.state.store.create_draft_completion_run(
        DraftCompletionRun(
            id="failed-current-completion",
            project_id=driver.project_id,
            draft_package_hash=current_hash,
            status="failed",
            scorecard=_scorecard(),
            notes=["provider failed before a usable completion report was produced"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["quality_required"] is True
    assert readiness["missing_quality_checks"] == []
    assert readiness["stale_quality_checks"] == []
    assert readiness["failed_quality_checks"] == ["draft_completion"]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "current",
        "claim_defense_worksheet": "current",
        "draft_completion": "failed",
    }
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed quality checks: draft_completion" in blocked["detail"]


def test_export_readiness_reports_unknown_hash_legacy_quality_bundle(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    store = client.app.state.store
    store.create_filing_readiness_report(
        FilingReadinessReport(
            id="legacy-filing-without-hash",
            project_id=driver.project_id,
            draft_package_hash="",
            status="clean",
        )
    )
    store.create_claim_defense_worksheet(
        ClaimDefenseWorksheet(
            id="legacy-worksheet-without-hash",
            project_id=driver.project_id,
            draft_package_hash="",
            status="reviewed",
        )
    )
    store.create_draft_completion_run(
        DraftCompletionRun(
            id="legacy-completion-without-hash",
            project_id=driver.project_id,
            draft_package_hash="",
            status="completed",
            scorecard=_scorecard(),
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["quality_required"] is True
    assert readiness["missing_quality_checks"] == []
    assert readiness["unknown_quality_checks"] == [
        "filing_readiness",
        "claim_defense_worksheet",
        "draft_completion",
    ]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "unknown",
        "claim_defense_worksheet": "unknown",
        "draft_completion": "unknown",
    }
    state = driver.state()
    assert state.gates["quality"] == "unknown"
    assert state.step_status[6] == "locked"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "unknown-hash quality checks: filing_readiness, claim_defense_worksheet, draft_completion" in blocked["detail"]


def test_flow_driver_state_reports_failed_current_quality_gate(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness").json()
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets").json()
    current_hash = filing["draft_package_hash"]
    assert worksheet["draft_package_hash"] == current_hash
    client.app.state.store.create_draft_completion_run(
        DraftCompletionRun(
            id="failed-current-completion-for-state",
            project_id=driver.project_id,
            draft_package_hash=current_hash,
            status="failed",
            scorecard=_scorecard(),
            notes=["provider failed before a usable completion report was produced"],
        )
    )

    state = driver.state()

    assert state.gates["quality"] == "failed"
    assert state.step_status[6] == "locked"
    assert state.export_allowed is False
    assert driver.export_readiness()["failed_quality_checks"] == ["draft_completion"]


def test_export_readiness_treats_superseded_current_claim_defense_as_missing(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness").json()
    completion = client.post(f"/api/projects/{driver.project_id}/completion-runs").json()
    current_hash = filing["draft_package_hash"]
    assert completion["draft_package_hash"] == current_hash
    client.app.state.store.create_claim_defense_worksheet(
        ClaimDefenseWorksheet(
            id="superseded-current-worksheet",
            project_id=driver.project_id,
            draft_package_hash=current_hash,
            status="superseded",
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["quality_required"] is True
    assert readiness["missing_quality_checks"] == ["claim_defense_worksheet"]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "current",
        "claim_defense_worksheet": "missing",
        "draft_completion": "current",
    }
    state = driver.state()
    assert state.gates["quality"] == "missing"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "missing quality checks: claim_defense_worksheet" in blocked["detail"]


def test_export_readiness_uses_latest_current_draft_completion_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    quality = driver.run_quality()
    current_hash = quality["draft_completion"]["draft_package_hash"]
    client.app.state.store.create_draft_completion_run(
        DraftCompletionRun(
            id="failed-latest-current-completion",
            project_id=driver.project_id,
            draft_package_hash=current_hash,
            status="failed",
            scorecard=_scorecard(),
            notes=["latest completion attempt failed after an earlier completed report"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_quality_checks"
    assert readiness["quality_required"] is True
    assert readiness["failed_quality_checks"] == ["draft_completion"]
    assert readiness["quality_check_states"] == {
        "filing_readiness": "current",
        "claim_defense_worksheet": "current",
        "draft_completion": "failed",
    }
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed quality checks: draft_completion" in blocked["detail"]


def test_export_readiness_reports_failed_current_post_draft_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="failed-current-review",
            project_id=driver.project_id,
            status="failed",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
            export_allowed=False,
            blocking_issues=["claims reviewer failed before chair synthesis"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["post_draft_review_required"] is True
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "failed-current-review"
    assert readiness["review_status"] == "failed"
    assert readiness["review_export_allowed"] is False
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed post-draft review" in blocked["detail"]


def test_export_readiness_reports_interrupted_current_post_draft_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="interrupted-current-review",
            project_id=driver.project_id,
            status="interrupted",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
            export_allowed=False,
            blocking_issues=["review was cancelled before chair synthesis"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "interrupted-current-review"
    assert readiness["review_status"] == "interrupted"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "interrupted post-draft review" in blocked["detail"]


def test_export_readiness_reports_queued_current_post_draft_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="queued-current-review",
            project_id=driver.project_id,
            status="queued",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "queued-current-review"
    assert readiness["review_status"] == "queued"
    assert readiness["review_gate_status"] == "queued"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "queued post-draft review" in blocked["detail"]


def test_export_readiness_reports_running_current_post_draft_review(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="running-current-review",
            project_id=driver.project_id,
            status="running",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "running-current-review"
    assert readiness["review_status"] == "running"
    assert readiness["review_gate_status"] == "running"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "running post-draft review" in blocked["detail"]


def test_export_readiness_reports_blocked_current_official_compile_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.edit_source_draft(
        "本发明涉及数据处理技术领域。系统接收输入数据并输出处理结果。\n"
        "support_gap: 当前正式稿仍包含内部支撑缺口标记。"
    )
    driver.run_quality()
    compile_run = driver.compile_official()
    assert compile_run["status"] == "blocked"

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == compile_run["id"]
    assert readiness["compile_status"] == "blocked"
    assert readiness["compile_blocked_items"]
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "blocked official compile" in blocked["detail"]


def test_export_readiness_reports_failed_current_official_compile_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    quality = driver.run_quality()
    current_hash = quality["filing_readiness"]["draft_package_hash"]
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="failed-current-compile",
            project_id=driver.project_id,
            status="failed",
            source_draft_hash=current_hash,
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "failed-current-compile"
    assert readiness["compile_status"] == "failed"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed official compile" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "failed official compile" in review_response.json()["detail"]


def test_export_readiness_reports_in_flight_current_official_compile_attempts(tmp_path) -> None:
    for status in ("queued", "running"):
        client = TestClient(
            create_app(data_dir=tmp_path / status, llm_client=_review_llm(), load_env_file=False)
        )
        driver = _driver_with_working_draft(client)
        quality = driver.run_quality()
        current_hash = quality["filing_readiness"]["draft_package_hash"]
        client.app.state.store.create_official_compile_run(
            OfficialCompileRun(
                id=f"{status}-current-compile",
                project_id=driver.project_id,
                status=status,
                source_draft_hash=current_hash,
            )
        )

        readiness = driver.export_readiness()

        assert readiness["next_action"] == "run_official_compile"
        assert readiness["official_compile_required"] is True
        assert readiness["has_compile_run"] is True
        assert readiness["compile_run_id"] == f"{status}-current-compile"
        assert readiness["compile_status"] == status
        assert readiness["compile_artifact_state"] == status
        blocked = driver.export_official()
        assert blocked["blocked"] is True
        assert f"{status} official compile" in blocked["detail"]
        review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
        assert review_response.status_code == 409
        assert f"{status} official compile" in review_response.json()["detail"]
        state = driver.state()
        assert state.gates["official_compile"] == status
        assert state.export_allowed is False
        assert [run["id"] for run in state.active_runs] == [f"{status}-current-compile"]


def test_export_readiness_reports_completed_compile_missing_official_package(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    quality = driver.run_quality()
    current_hash = quality["filing_readiness"]["draft_package_hash"]
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="completed-compile-missing-package",
            project_id=driver.project_id,
            status="completed",
            source_draft_hash=current_hash,
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "completed-compile-missing-package"
    assert readiness["compile_status"] == "completed"
    assert readiness["compile_artifact_state"] == "missing_official_package"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "incomplete official compile" in blocked["detail"]
    assert "missing official package" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "missing official package" in review_response.json()["detail"]


def test_export_readiness_reports_completed_compile_missing_official_package_hash(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    completed_compile = driver.compile_official()
    assert completed_compile["status"] == "completed"
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="completed-compile-missing-package-hash",
            project_id=driver.project_id,
            status="completed",
            source_draft_hash=completed_compile["source_draft_hash"],
            official_package=OfficialDraftPackage.model_validate(completed_compile["official_package"]),
            official_package_hash="",
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["post_draft_review_required"] is False
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "completed-compile-missing-package-hash"
    assert readiness["compile_status"] == "completed"
    assert readiness["compile_artifact_state"] == "missing_official_package_hash"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "incomplete official compile" in blocked["detail"]
    assert "missing official package hash" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "missing official package hash" in review_response.json()["detail"]


def test_export_readiness_blocks_completed_compile_with_blocked_items(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    completed_compile = driver.compile_official()
    assert completed_compile["status"] == "completed"
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="completed-compile-with-blocked-items",
            project_id=driver.project_id,
            status="completed",
            source_draft_hash=completed_compile["source_draft_hash"],
            official_package=OfficialDraftPackage.model_validate(completed_compile["official_package"]),
            official_package_hash=completed_compile["official_package_hash"],
            blocked_items=[
                {
                    "category": "residual_internal_text",
                    "section": "claims",
                    "pattern": "support_gap",
                    "message": "legacy completed compile still records blocking contamination",
                }
            ],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["post_draft_review_required"] is False
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "completed-compile-with-blocked-items"
    assert readiness["compile_status"] == "completed"
    assert readiness["compile_artifact_state"] == "blocked"
    assert readiness["compile_blocked_items"]
    state = driver.state()
    assert state.gates["official_compile"] == "blocked"
    assert state.export_allowed is False
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "blocked official compile" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "blocked official compile" in review_response.json()["detail"]


def test_export_readiness_uses_latest_failed_official_compile_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    completed_compile = driver.compile_official()
    assert completed_compile["status"] == "completed"
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="failed-latest-current-compile",
            project_id=driver.project_id,
            status="failed",
            source_draft_hash=completed_compile["source_draft_hash"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "failed-latest-current-compile"
    assert readiness["compile_status"] == "failed"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed official compile" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "failed official compile" in review_response.json()["detail"]


def test_export_readiness_uses_latest_blocked_official_compile_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    completed_compile = driver.compile_official()
    assert completed_compile["status"] == "completed"
    client.app.state.store.create_official_compile_run(
        OfficialCompileRun(
            id="blocked-latest-current-compile",
            project_id=driver.project_id,
            status="blocked",
            source_draft_hash=completed_compile["source_draft_hash"],
            blocked_items=[
                {
                    "category": "residual_internal_text",
                    "section": "claims",
                    "pattern": "support_gap",
                    "message": "latest compile attempt blocked after an earlier completed official package",
                }
            ],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_official_compile"
    assert readiness["official_compile_required"] is True
    assert readiness["has_compile_run"] is True
    assert readiness["compile_run_id"] == "blocked-latest-current-compile"
    assert readiness["compile_status"] == "blocked"
    assert readiness["compile_blocked_items"]
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "blocked official compile" in blocked["detail"]
    review_response = client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    assert review_response.status_code == 409
    assert "blocked official compile" in review_response.json()["detail"]


def test_flow_driver_export_gate_requires_complete_quality_bundle(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)

    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness")
    assert filing.status_code == 200
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets")
    assert worksheet.status_code == 200
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_completion = driver.export_official()
    assert blocked_without_completion["blocked"] is True
    assert "draft_completion" in blocked_without_completion["detail"]
    readiness_without_completion = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness_without_completion["missing_quality_checks"] == ["draft_completion"]

    driver = _driver_with_working_draft(client)
    worksheet = client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets")
    assert worksheet.status_code == 200
    completion = client.post(f"/api/projects/{driver.project_id}/completion-runs")
    assert completion.status_code == 200
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_filing = driver.export_official()
    assert blocked_without_filing["blocked"] is True
    assert "filing_readiness" in blocked_without_filing["detail"]
    readiness_without_filing = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness_without_filing["missing_quality_checks"] == ["filing_readiness"]

    driver = _driver_with_working_draft(client)
    filing = client.post(f"/api/projects/{driver.project_id}/filing-readiness")
    assert filing.status_code == 200
    completion = client.post(f"/api/projects/{driver.project_id}/completion-runs")
    assert completion.status_code == 200
    compile_run = driver.compile_official()
    assert compile_run["status"] == "completed"
    review_run = driver.run_post_draft_review()
    assert review_run["export_allowed"] is True

    blocked_without_worksheet = driver.export_official()
    assert blocked_without_worksheet["blocked"] is True
    assert "claim_defense_worksheet" in blocked_without_worksheet["detail"]
    readiness_without_worksheet = driver.raw_get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness_without_worksheet["missing_quality_checks"] == ["claim_defense_worksheet"]


def test_flow_driver_later_blocking_review_invalidates_prior_pass(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    driver.compile_official()
    passed_review = driver.run_post_draft_review()
    assert passed_review["export_allowed"] is True
    assert driver.export_official()["ok"] is True

    client.app.state.llm = _review_llm(export_allowed=False)
    blocking_review = driver.run_post_draft_review()

    assert blocking_review["export_allowed"] is False
    readiness = driver.export_readiness()
    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == blocking_review["id"]
    assert readiness["review_status"] == "completed"
    assert readiness["review_gate_status"] == "blocked"
    assert readiness["review_blocking_issues"] == ["说明书存在未解决的正式稿阻断问题。"]
    blocked_export = driver.export_official()
    assert blocked_export["blocked"] is True
    assert "blocked post-draft review" in blocked_export["detail"]


def test_export_readiness_uses_latest_failed_post_draft_review_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    passed_review = driver.run_post_draft_review()
    assert passed_review["export_allowed"] is True
    assert driver.export_official()["ok"] is True
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="failed-latest-current-review",
            project_id=driver.project_id,
            status="failed",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
            export_allowed=False,
            blocking_issues=["latest review attempt failed after an earlier passed review"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["post_draft_review_required"] is True
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "failed-latest-current-review"
    assert readiness["review_status"] == "failed"
    assert readiness["review_export_allowed"] is False
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "failed post-draft review" in blocked["detail"]


def test_export_readiness_uses_latest_queued_post_draft_review_attempt(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    passed_review = driver.run_post_draft_review()
    assert passed_review["export_allowed"] is True
    assert driver.export_official()["ok"] is True
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="queued-latest-current-review",
            project_id=driver.project_id,
            status="queued",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
            export_allowed=False,
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["post_draft_review_required"] is True
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "queued-latest-current-review"
    assert readiness["review_status"] == "queued"
    assert readiness["review_gate_status"] == "queued"
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "queued post-draft review" in blocked["detail"]


def test_flow_driver_state_reports_latest_post_draft_review_attempt_status(tmp_path) -> None:
    scenarios = [
        ("queued", "queued"),
        ("running", "running"),
        ("failed", "failed"),
        ("interrupted", "interrupted"),
        ("completed", "blocked"),
    ]
    for status, expected_gate in scenarios:
        client = TestClient(
            create_app(data_dir=tmp_path / expected_gate, llm_client=_review_llm(), load_env_file=False)
        )
        driver = _driver_with_working_draft(client)
        driver.run_quality()
        compile_run = driver.compile_official()
        passed_review = driver.run_post_draft_review()
        assert passed_review["export_allowed"] is True
        assert driver.state().gates["post_draft_review"] == "current"
        client.app.state.store.create_post_draft_review_run(
            PostDraftReviewRun(
                id=f"{expected_gate}-latest-current-review",
                project_id=driver.project_id,
                status=status,
                draft_package_hash=compile_run["source_draft_hash"],
                official_compile_run_id=compile_run["id"],
                official_package_hash=compile_run["official_package_hash"],
                export_allowed=False,
                blocking_issues=[f"latest review attempt is {expected_gate} after an earlier passed review"],
            )
        )

        state = driver.state()

        assert state.gates["post_draft_review"] == expected_gate
        assert state.export_allowed is False
        if expected_gate in {"queued", "running"}:
            assert [run["id"] for run in state.active_runs] == [f"{expected_gate}-latest-current-review"]


def test_export_readiness_blocks_contradictory_passed_review_with_blocking_issues(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_review_llm(), load_env_file=False))
    driver = _driver_with_working_draft(client)
    driver.run_quality()
    compile_run = driver.compile_official()
    passed_review = driver.run_post_draft_review()
    assert passed_review["export_allowed"] is True
    assert driver.export_official()["ok"] is True
    client.app.state.store.create_post_draft_review_run(
        PostDraftReviewRun(
            id="contradictory-passed-review",
            project_id=driver.project_id,
            status="completed",
            draft_package_hash=compile_run["source_draft_hash"],
            official_compile_run_id=compile_run["id"],
            official_package_hash=compile_run["official_package_hash"],
            export_allowed=True,
            blocking_issues=["legacy record says export is allowed while blocking issues remain"],
        )
    )

    readiness = driver.export_readiness()

    assert readiness["next_action"] == "run_post_draft_review"
    assert readiness["post_draft_review_required"] is True
    assert readiness["has_review_run"] is True
    assert readiness["review_run_id"] == "contradictory-passed-review"
    assert readiness["review_gate_status"] == "blocked"
    assert readiness["review_export_allowed"] is False
    assert readiness["review_blocking_issues"] == ["legacy record says export is allowed while blocking issues remain"]
    state = driver.state()
    assert state.gates["post_draft_review"] == "blocked"
    assert state.export_allowed is False
    blocked = driver.export_official()
    assert blocked["blocked"] is True
    assert "blocked post-draft review" in blocked["detail"]


def test_flow_driver_generates_utility_model_draft_and_reports_readiness(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_drafting_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project(
        "可调安装支架",
        "专利类型：实用新型。一种可调安装支架，包括底座、支撑臂和限位件。",
        patent_type="utility_model",
    )

    requirement = driver.formula_requirement()
    assert requirement["required"] is False

    package = driver.generate_draft()
    assert "可调安装支架" in package["title"]
    assert driver.project()["package"]["title"] == package["title"]

    readiness = driver.export_readiness()
    assert readiness["export_allowed"] is False
    assert "official_compile_required" in readiness


def test_flow_driver_runs_formula_for_formula_required_invention(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, llm_client=_drafting_llm(), load_env_file=False))
    driver = FlowDriver(client)
    driver.create_project(
        "置信度输入处理",
        "一种根据输入特征置信度和阈值生成处理结果的方法。",
        patent_type="invention",
    )
    driver.intake_external_draft(
        """
发明名称
一种置信度输入处理方法
摘要
本发明公开一种根据置信度阈值生成处理结果的方法。
权利要求书
1. 一种置信度输入处理方法，其特征在于，包括接收输入数据、计算输入特征置信度，并根据阈值输出处理结果。
说明书
本发明涉及数据处理技术领域。系统计算输入特征置信度，并根据阈值生成处理结果。
附图说明
图1为置信度输入处理方法流程图。
""".strip(),
        filename="formula-draft.txt",
    )

    requirement = driver.formula_requirement()
    assert requirement["required"] is True

    formula = driver.run_formula()
    assert formula["status"] == "completed"
    assert formula["package"]["formula_blocks"]


def _driver_with_working_draft(client: TestClient) -> FlowDriver:
    driver = FlowDriver(client)
    driver.create_project(
        "输入数据处理",
        "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        patent_type="invention",
    )
    driver.intake_external_draft(
        """
发明名称
一种输入数据处理方法
摘要
本发明公开一种输入数据处理方法。
权利要求书
1. 一种输入数据处理方法，其特征在于，包括接收输入数据并输出处理结果。
说明书
本发明涉及数据处理技术领域。在一个实施例中，系统接收输入数据并输出处理结果。
附图说明
图1为输入数据处理方法流程图。
""".strip(),
        filename="draft.txt",
    )
    return driver


def _scorecard() -> CompletionScoreCard:
    return CompletionScoreCard(
        authorization_stability=0,
        protection_scope=0,
        support_strength=0,
        prior_art_distinction=0,
        filing_maturity=0,
        official_hygiene=0,
        overall=0,
    )


def _post_status(client: TestClient, project_id: str, endpoint: str) -> tuple[int, str]:
    response = client.post(f"/api/projects/{project_id}/{endpoint}", json={})
    detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else ""
    return response.status_code, str(detail)


def _review_llm(*, export_allowed: bool = True) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["说明书存在未解决的正式稿阻断问题。"]
    chair_status = "passed" if export_allowed else "blocked"
    return FakeLLMClient(
        {
            "post_draft_claims_reviewer": _role_response("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_response("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_response("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": json.dumps(
                {
                    "status": chair_status,
                    "export_allowed": export_allowed,
                    "blocking_issues": blocking_issues,
                    "contamination_hits": [],
                    "claim_1_rewrite": "",
                    "system_claim_rewrite": "",
                    "abstract_rewrite": "",
                    "description_rewrite_tasks": [],
                    "official_safe_patches": [],
                    "attorney_memo": [],
                    "next_actions": [],
                },
                ensure_ascii=False,
            ),
        }
    )


def _drafting_llm() -> FakeLLMClient:
    responses = {
        "core_formula": json.dumps(
            {
                "summary": "以输入处理置信度描述处理触发关系。",
                "formula_blocks": [
                    {
                        "id": "F01",
                        "name": "输入处理置信度",
                        "latex": "S=aX+bY",
                        "purpose": "描述输入特征和上下文特征对处理结果的贡献。",
                        "claim_hook": "根据置信度输出处理结果。",
                    }
                ],
                "variable_definitions": [
                    {"symbol": "X", "meaning": "输入特征", "unit": ""},
                    {"symbol": "Y", "meaning": "上下文特征", "unit": ""},
                ],
                "derivation_notes": ["公式用于限定处理触发关系。"],
                "claim_hooks": ["将置信度写入从属权利要求。"],
                "description_insert": "本实施例根据F01计算输入处理置信度。",
                "latex_markdown": "# 核心公式\n\nF01: $S=aX+bY$。",
                "generation_logs": ["journey test formula package"],
            },
            ensure_ascii=False,
        ),
        "claims": (
            "1. 一种可调安装支架，其特征在于，包括底座、支撑臂和限位件，"
            "所述支撑臂与所述底座转动连接，所述限位件用于锁定调节角度。\n"
            "2. 根据权利要求1所述的安装支架，其特征在于，所述支撑臂设有角度刻度。"
        ),
        "description": (
            "技术领域\n本实用新型涉及安装支架技术领域。\n"
            "背景技术\n现有支架角度调整不便。\n"
            "实用新型内容\n本实用新型通过底座、支撑臂和限位件实现稳定调节。\n"
            "附图说明\n图1为安装支架结构示意图。\n"
            "具体实施方式\n底座固定在安装面，支撑臂相对底座转动，限位件锁定角度。"
        ),
        "abstract": "本实用新型公开一种可调安装支架，能够实现安装角度调节和锁定。",
        "drawings": "图1为安装支架结构示意图。",
        "diagram": "flowchart TD\nA[底座] --> B[支撑臂]\nB --> C[限位件]",
        "image_prompt": "黑白专利线稿，展示底座、支撑臂和限位件。",
        "review": json.dumps(
            [
                {
                    "category": "支持性",
                    "severity": "low",
                    "message": "权利要求与说明书一致。",
                    "suggestion": "提交前补充附图标号。",
                    "evidence": "权利要求1",
                }
            ],
            ensure_ascii=False,
        ),
        "post_draft_claims_reviewer": _role_response("claims_reviewer", "passed", []),
        "post_draft_spec_cleaner": _role_response("spec_cleaner", "passed", []),
        "post_draft_technical_hardness": _role_response("technical_hardness", "passed", []),
        "post_draft_chair_synthesis": json.dumps(
            {
                "status": "passed",
                "export_allowed": True,
                "blocking_issues": [],
                "contamination_hits": [],
                "claim_1_rewrite": "",
                "system_claim_rewrite": "",
                "abstract_rewrite": "",
                "description_rewrite_tasks": [],
                "official_safe_patches": [],
                "attorney_memo": [],
                "next_actions": [],
            },
            ensure_ascii=False,
        ),
    }
    return FakeLLMClient(responses)


def _role_response(role: str, status: str, blocking_issues: list[str]) -> str:
    return json.dumps(
        {
            "role": role,
            "status": status,
            "blocking_issues": blocking_issues,
            "contamination_hits": [],
            "rewrite_suggestions": [],
            "official_safe_patches": [],
            "attorney_memo": [],
        },
        ensure_ascii=False,
    )
