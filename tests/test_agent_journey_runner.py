from __future__ import annotations

import json
from pathlib import Path

import pytest

import agent_journey_runner
from agent_journey_runner import (
    JourneyReport,
    JourneyStepResult,
    SourceIdentity,
    collect_source_identity,
    run_journey,
    run_journeys,
    write_report,
)


def test_write_report_persists_source_identity_steps_and_failures(tmp_path: Path) -> None:
    report = JourneyReport(
        source_identity=SourceIdentity(
            worktree_path="/repo",
            git_top_level="/repo",
            branch="codex/automation-test-plan",
            short_sha="7bc7a450",
            dirty_status="dirty",
            dirty_files_summary=["tests/flow_driver.py"],
        ),
        journey_id="invention_from_idea",
        mode="api",
        test_target="api_testclient",
        llm_mode="fake",
        data_dir=str(tmp_path / "data"),
        status="failed",
        steps=[
            JourneyStepResult(
                id="official_export_gate",
                status="failed",
                input_summary="export before review",
                expected="blocked",
                actual="HTTP 200",
                evidence=["api-payloads/export-readiness.json"],
            )
        ],
        gates={"official_compile": "missing"},
        hashes={"current_source_draft_hash": "abc"},
        failures=[
            {
                "classification": "export_gate",
                "severity": "P1",
                "user_visible_message": "正式导出被错误放行。",
                "suggested_fix": "require post-draft review before official export",
            }
        ],
        artifacts={"api_payloads": ["api-payloads/export-readiness.json"], "logs": [], "screenshots": []},
    )

    path = write_report(report, tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["source_identity"]["branch"] == "codex/automation-test-plan"
    assert payload["execution"]["journey_id"] == "invention_from_idea"
    assert payload["steps"][0]["id"] == "official_export_gate"
    assert payload["failures"][0]["classification"] == "export_gate"


def test_collect_source_identity_reports_current_repo() -> None:
    identity = collect_source_identity()

    assert identity.worktree_path
    assert identity.git_top_level == identity.worktree_path
    assert identity.branch
    assert len(identity.short_sha) >= 7
    assert identity.dirty_status in {"clean", "dirty"}
    assert isinstance(identity.dirty_files_summary, list)


def test_collect_source_identity_falls_back_to_head_for_detached_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_git(root: Path, *args: str) -> str:
        if args == ("status", "--short", "--branch"):
            return "## HEAD (no branch)"
        if args == ("rev-parse", "--show-toplevel"):
            return "/repo"
        if args == ("branch", "--show-current"):
            return ""
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "HEAD"
        if args == ("rev-parse", "--short", "HEAD"):
            return "abc1234"
        raise AssertionError(f"unexpected git command: {args}")

    monkeypatch.setattr(agent_journey_runner, "_git", fake_git)
    monkeypatch.setattr(agent_journey_runner, "_run", lambda root, *args: "/repo")

    identity = collect_source_identity(Path("/repo"))

    assert identity.branch == "HEAD"
    assert identity.dirty_status == "clean"


@pytest.mark.parametrize(
    "journey_id",
    ["invention_from_idea", "utility_model_from_structure", "polish_existing_draft"],
)
def test_run_journey_writes_passing_api_report(tmp_path: Path, journey_id: str) -> None:
    path = run_journey(
        journey_id,
        tmp_path,
        source_identity=SourceIdentity(
            worktree_path="/repo",
            git_top_level="/repo",
            branch="test-branch",
            short_sha="abc1234",
            dirty_status="dirty",
            dirty_files_summary=["tests/agent_journey_runner.py"],
        ),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["execution"]["journey_id"] == journey_id
    assert payload["execution"]["mode"] == "api"
    assert payload["execution"]["llm_mode"] == "fake"
    assert payload["execution"]["data_dir"].startswith("ephemeral:")
    assert payload["execution"]["status"] == "passed"
    assert payload["source_identity"]["short_sha"] == "abc1234"
    assert payload["gates"]["quality"] == "current"
    assert payload["gates"]["official_compile"] == "current"
    assert payload["gates"]["post_draft_review"] == "current"
    assert payload["hashes"]["current_source_draft_hash"]
    assert payload["hashes"]["latest_official_package_hash"]
    assert payload["hashes"]["latest_review_draft_hash"]
    assert payload["hashes"]["latest_review_official_package_hash"]
    assert payload["steps"]
    assert payload["failures"] == []
    if journey_id == "utility_model_from_structure":
        step_ids = [step["id"] for step in payload["steps"]]
        assert "formula_requirement" in step_ids
        draft_step = next(step for step in payload["steps"] if step["id"] == "lightweight_draft")
        assert "可调安装支架" in draft_step["actual"]
        assert "底座" in draft_step["actual"]


def test_run_journey_records_hash_drift_export_block_evidence(tmp_path: Path) -> None:
    path = run_journey(
        "utility_model_from_structure",
        tmp_path,
        source_identity=SourceIdentity(
            worktree_path="/repo",
            git_top_level="/repo",
            branch="test-branch",
            short_sha="abc1234",
            dirty_status="clean",
            dirty_files_summary=[],
        ),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    drift_step = next(step for step in payload["steps"] if step["id"] == "hash_drift_export_gate")

    assert drift_step["status"] == "passed"
    assert "export_blocked=True" in drift_step["actual"]
    assert "quality=stale" in drift_step["actual"]
    assert any(evidence.startswith("api:GET /api/projects/") for evidence in drift_step["evidence"])
    assert any(evidence.startswith("current_source_draft_hash:") for evidence in drift_step["evidence"])
    assert payload["artifacts"]["api_payloads"]


def test_run_journeys_rejects_unknown_journey_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown journey_id"):
        run_journeys(["unknown"], tmp_path)


def test_run_journeys_prevalidates_all_ids_before_writing_reports(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown journey_id: unknown"):
        run_journeys(["invention_from_idea", "unknown"], tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_run_journey_writes_failed_report_before_reraising(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_journey(driver, steps):
        steps.append(
            JourneyStepResult(
                id="forced_break",
                status="failed",
                input_summary="forced test break",
                expected="journey continues",
                actual="forced gate failure",
            )
        )
        raise AssertionError("forced gate failure")

    monkeypatch.setattr(agent_journey_runner, "_run_utility_model_from_structure", fail_journey)

    with pytest.raises(AssertionError, match="forced gate failure"):
        run_journey(
            "utility_model_from_structure",
            tmp_path,
            source_identity=SourceIdentity(
                worktree_path="/repo",
                git_top_level="/repo",
                branch="test-branch",
                short_sha="abc1234",
                dirty_status="clean",
                dirty_files_summary=[],
            ),
        )

    reports = list(tmp_path.glob("*-utility_model_from_structure.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["execution"]["status"] == "failed"
    assert payload["steps"][-1]["status"] == "failed"
    assert payload["failures"][0]["classification"] == "journey_assertion"
    assert "forced gate failure" in payload["failures"][0]["user_visible_message"]


def test_main_runs_selected_journey_and_returns_zero(tmp_path: Path) -> None:
    from agent_journey_runner import main

    exit_code = main(["--journey", "utility_model_from_structure", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    reports = list(tmp_path.glob("*-utility_model_from_structure.json"))
    assert len(reports) == 1


def test_main_returns_one_when_journey_fails_and_keeps_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_journey(driver, steps):
        raise AssertionError("forced main failure")

    monkeypatch.setattr(agent_journey_runner, "_run_utility_model_from_structure", fail_journey)

    exit_code = agent_journey_runner.main(
        ["--journey", "utility_model_from_structure", "--output-dir", str(tmp_path)]
    )

    assert exit_code == 1
    reports = list(tmp_path.glob("*-utility_model_from_structure.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["execution"]["status"] == "failed"
