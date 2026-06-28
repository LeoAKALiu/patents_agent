from __future__ import annotations

import json
from pathlib import Path

import pytest

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

    assert identity.worktree_path.endswith("patents_agent")
    assert identity.git_top_level.endswith("patents_agent")
    assert identity.branch
    assert len(identity.short_sha) >= 7
    assert identity.dirty_status in {"clean", "dirty"}
    assert isinstance(identity.dirty_files_summary, list)


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


def test_run_journeys_rejects_unknown_journey_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown journey_id"):
        run_journeys(["unknown"], tmp_path)


def test_run_journeys_prevalidates_all_ids_before_writing_reports(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown journey_id: unknown"):
        run_journeys(["invention_from_idea", "unknown"], tmp_path)

    assert list(tmp_path.iterdir()) == []
