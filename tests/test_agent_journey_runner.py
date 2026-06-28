from __future__ import annotations

import json
from pathlib import Path

from agent_journey_runner import (
    JourneyReport,
    JourneyStepResult,
    SourceIdentity,
    collect_source_identity,
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
