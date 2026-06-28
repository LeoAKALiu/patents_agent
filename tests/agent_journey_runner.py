from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import STRICT_DELIBERATION_PROVIDERS, create_app
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief
from flow_driver import FlowDriver

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "agent-journeys"
JOURNEY_IDS = ("invention_from_idea", "utility_model_from_structure", "polish_existing_draft")


@dataclass(frozen=True)
class SourceIdentity:
    worktree_path: str
    git_top_level: str
    branch: str
    short_sha: str
    dirty_status: str
    dirty_files_summary: list[str]


@dataclass(frozen=True)
class JourneyStepResult:
    id: str
    status: str
    input_summary: str
    expected: str
    actual: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JourneyReport:
    source_identity: SourceIdentity
    journey_id: str
    mode: str
    test_target: str
    llm_mode: str
    data_dir: str
    status: str
    steps: list[JourneyStepResult]
    gates: dict[str, str]
    hashes: dict[str, str]
    failures: list[dict[str, str]]
    artifacts: dict[str, list[str]]
    started_at: str = ""
    finished_at: str = ""
    schema_version: int = 1

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_identity": asdict(self.source_identity),
            "execution": {
                "journey_id": self.journey_id,
                "mode": self.mode,
                "test_target": self.test_target,
                "llm_mode": self.llm_mode,
                "data_dir": self.data_dir,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "status": self.status,
            },
            "steps": [asdict(step) for step in self.steps],
            "gates": self.gates,
            "hashes": self.hashes,
            "failures": self.failures,
            "artifacts": self.artifacts,
        }


def collect_source_identity(root: Path = ROOT) -> SourceIdentity:
    status = _git(root, "status", "--short", "--branch")
    dirty_lines = [line for line in status.splitlines()[1:] if line.strip()]
    return SourceIdentity(
        worktree_path=_run(root, "pwd"),
        git_top_level=_git(root, "rev-parse", "--show-toplevel"),
        branch=_git(root, "branch", "--show-current"),
        short_sha=_git(root, "rev-parse", "--short", "HEAD"),
        dirty_status="dirty" if dirty_lines else "clean",
        dirty_files_summary=[line[3:] if len(line) > 3 else line for line in dirty_lines],
    )


def write_report(report: JourneyReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = output_dir / f"{timestamp}-{report.journey_id}.json"
    path.write_text(
        json.dumps(report.to_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _run(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def _git(root: Path, *args: str) -> str:
    return _run(root, "git", *args)
