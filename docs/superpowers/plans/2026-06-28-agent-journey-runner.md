# Agent Journey Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 1 of the approved agent automation testing architecture: an API-mode journey runner that executes the three primary PatentAgent user journeys with fake LLM, temporary data, source identity, hash/export gate assertions, and JSON reports.

**Architecture:** Keep Phase 1 in the pytest/API layer so it is deterministic and fast. Reuse the existing untracked `tests/flow_driver.py` helper as the API driver, add a small `tests/agent_journey_runner.py` orchestration module for report schemas and journey execution, and cover the runner with focused pytest tests before adding it to broad smoke guidance.

**Tech Stack:** Python 3, pytest, FastAPI `TestClient`, `backend.app.main.create_app`, `backend.app.llm.FakeLLMClient`, JSON report files under `output/agent-journeys/`.

## Global Constraints

- Current repository: `/Users/leo/Projects/patents_agent`.
- Current branch observed while writing this plan: `codex/automation-test-plan`.
- Current HEAD observed while writing this plan: `7bc7a450`.
- Current worktree is dirty with existing automation-test-plan files; implementation commits must stage only files touched by each task.
- Follow `AGENTS.md`: record `pwd`, `git status --short --branch`, `git rev-parse --show-toplevel`, `git branch --show-current`, and `git rev-parse --short HEAD` before implementation work.
- Implement only approved spec Phase 1: `agent-journey-runner`.
- Do not implement Phase 2 `golden-patent-quality-suite`, Phase 3 `failure-injection-matrix`, or Phase 4 `agent-repair-protocol` in this plan.
- Release-blocking journey mode for this phase is `api`: FastAPI `TestClient`, fake LLM, and temporary data directory.
- Do not call live LLM providers, read `.env`, use default `data/`, inspect installed apps, package DMGs, or introduce browser/Tauri automation in this phase.
- A passing journey report must include source identity, execution metadata, ordered steps, gate state, hashes, artifacts, and failures.
- Official export must remain blocked unless quality checks, official compile, post-draft review, and current hash gates are satisfied.
- Implementation must use TDD: write each focused failing test first, watch it fail, implement the minimal code, then run the focused test again.

---

## File Structure

- Modify `tests/flow_driver.py`: extend the existing API driver with draft generation, formula, export-readiness, source package editing, and JSON-safe gate helpers needed by all journeys.
- Modify `tests/test_flow_driver.py`: add focused driver regressions for utility-model generation and export-readiness snapshots.
- Create `tests/agent_journey_runner.py`: define report dataclasses, source identity collection, deterministic journey LLM responses, three journey functions, report writer, and a small CLI entrypoint.
- Create `tests/test_agent_journey_runner.py`: verify source identity/report writing and the three API journeys using temporary data directories.
- Modify `docs/qa/ai-scenario-testing-pipeline.md`: add the API journey runner as the Phase 1 deterministic user-journey gate without replacing existing broader QA guidance.

---

### Task 1: Extend FlowDriver With Runner Primitives

**Files:**
- Modify: `tests/flow_driver.py`
- Modify: `tests/test_flow_driver.py`

**Interfaces:**
- Consumes: existing `FlowDriver(client: TestClient, project_id: str | None = None)`
- Produces:
  - `FlowDriver.formula_requirement() -> dict[str, Any]`
  - `FlowDriver.run_formula() -> dict[str, Any]`
  - `FlowDriver.generate_draft(payload: dict[str, Any] | None = None) -> dict[str, Any]`
  - `FlowDriver.export_readiness() -> dict[str, Any]`
  - `FlowDriver.project() -> dict[str, Any]`

- [ ] **Step 1: Add the failing FlowDriver generation/readiness tests**

Append these tests to `tests/test_flow_driver.py`:

```python
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
```

Add this helper near `_review_llm` in the same test file:

```python
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
```

- [ ] **Step 2: Run the focused tests and verify the new tests fail**

Run:

```bash
python3 -m pytest tests/test_flow_driver.py -q
```

Expected: FAIL because `FlowDriver` does not yet define `formula_requirement`, `run_formula`, `generate_draft`, `project`, or `export_readiness`.

- [ ] **Step 3: Add the minimal FlowDriver methods**

Insert these methods inside `class FlowDriver` in `tests/flow_driver.py`, after `run_post_draft_review`:

```python
    def formula_requirement(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}/formula-requirement"))

    def run_formula(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.post(f"/api/projects/{self.project_id}/formula-runs", json={}))

    def generate_draft(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.post(f"/api/projects/{self.project_id}/generate", json=payload or {}))

    def export_readiness(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}/export-readiness"))

    def project(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}"))
```

- [ ] **Step 4: Run the focused FlowDriver tests**

Run:

```bash
python3 -m pytest tests/test_flow_driver.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add tests/flow_driver.py tests/test_flow_driver.py
git commit -m "test: extend API flow driver for agent journeys"
```

---

### Task 2: Add Journey Report Schema And Source Identity Collection

**Files:**
- Create: `tests/agent_journey_runner.py`
- Create: `tests/test_agent_journey_runner.py`

**Interfaces:**
- Produces:
  - `SourceIdentity`
  - `JourneyStepResult`
  - `JourneyReport`
  - `collect_source_identity(root: Path = ROOT) -> SourceIdentity`
  - `write_report(report: JourneyReport, output_dir: Path) -> Path`

- [ ] **Step 1: Write failing report/schema tests**

Create `tests/test_agent_journey_runner.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

from agent_journey_runner import (
    JourneyReport,
    JourneyStepResult,
    SourceIdentity,
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
```

- [ ] **Step 2: Run the focused report/schema test and verify it fails**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_write_report_persists_source_identity_steps_and_failures -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent_journey_runner'`.

- [ ] **Step 3: Implement report dataclasses and report writer**

Create `tests/agent_journey_runner.py` with:

```python
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
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
    path.write_text(json.dumps(report.to_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def _git(root: Path, *args: str) -> str:
    return _run(root, "git", *args)
```

- [ ] **Step 4: Run the focused report/schema test**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_write_report_persists_source_identity_steps_and_failures -q
```

Expected: PASS.

- [ ] **Step 5: Add and run source identity collection test**

Append this test to `tests/test_agent_journey_runner.py`:

```python
def test_collect_source_identity_reports_current_repo() -> None:
    from agent_journey_runner import collect_source_identity

    identity = collect_source_identity()

    assert identity.worktree_path.endswith("patents_agent")
    assert identity.git_top_level.endswith("patents_agent")
    assert identity.branch
    assert len(identity.short_sha) >= 7
    assert identity.dirty_status in {"clean", "dirty"}
    assert isinstance(identity.dirty_files_summary, list)
```

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_collect_source_identity_reports_current_repo -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add tests/agent_journey_runner.py tests/test_agent_journey_runner.py
git commit -m "test: add agent journey report schema"
```

---

### Task 3: Implement Three API Journeys With JSON Reports

**Files:**
- Modify: `tests/agent_journey_runner.py`
- Modify: `tests/test_agent_journey_runner.py`

**Interfaces:**
- Produces:
  - `run_journey(journey_id: str, output_dir: Path, source_identity: SourceIdentity | None = None) -> Path`
  - `run_journeys(journey_ids: list[str], output_dir: Path) -> list[Path]`
  - Journey IDs: `invention_from_idea`, `utility_model_from_structure`, `polish_existing_draft`

- [ ] **Step 1: Add failing journey tests**

Append these tests to `tests/test_agent_journey_runner.py`:

```python
import pytest

from agent_journey_runner import run_journey, run_journeys


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
    assert payload["execution"]["status"] == "passed"
    assert payload["source_identity"]["short_sha"] == "abc1234"
    assert payload["gates"]["official_compile"] == "current"
    assert payload["gates"]["post_draft_review"] == "current"
    assert payload["hashes"]["current_source_draft_hash"]
    assert payload["steps"]
    assert payload["failures"] == []


def test_run_journeys_rejects_unknown_journey_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown journey_id"):
        run_journeys(["unknown"], tmp_path)
```

- [ ] **Step 2: Run the journey tests and verify they fail**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py -q
```

Expected: FAIL because `run_journey` and `run_journeys` are not implemented.

- [ ] **Step 3: Add deterministic journey LLM and helper functions**

Append this code to `tests/agent_journey_runner.py`:

```python
def journey_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "core_formula": json.dumps(
                {
                    "summary": "以处理置信度限定输入数据处理关系。",
                    "formula_blocks": [
                        {
                            "id": "F01",
                            "name": "处理置信度",
                            "latex": "S=aX+bY",
                            "purpose": "描述输入特征和上下文特征对处理结果的贡献。",
                            "claim_hook": "根据处理置信度输出结果。",
                        }
                    ],
                    "variable_definitions": [
                        {"symbol": "X", "meaning": "输入特征", "unit": ""},
                        {"symbol": "Y", "meaning": "上下文特征", "unit": ""},
                    ],
                    "derivation_notes": ["公式用于支撑处理触发关系。"],
                    "claim_hooks": ["将处理置信度写入从属权利要求。"],
                    "description_insert": "本实施例根据F01计算处理置信度。",
                    "latex_markdown": "# 核心公式\n\nF01: $S=aX+bY$。",
                    "generation_logs": ["agent journey formula package"],
                },
                ensure_ascii=False,
            ),
            "claims": (
                "1. 一种输入数据处理方法，其特征在于，包括接收输入数据、提取输入特征、"
                "根据处理置信度生成处理结果，并将处理结果与证据记录关联存储。\n"
                "2. 根据权利要求1所述的方法，其特征在于，所述处理置信度根据输入特征和上下文特征确定。"
            ),
            "description": (
                "技术领域\n本发明涉及数据处理技术领域。\n"
                "背景技术\n现有输入数据处理方法难以追溯处理依据。\n"
                "发明内容\n本发明通过输入特征、处理置信度和证据记录形成可追溯处理闭环。\n"
                "附图说明\n图1为输入数据处理方法流程图。\n"
                "具体实施方式\n系统接收输入数据，提取输入特征，计算处理置信度，生成处理结果并绑定证据记录。"
            ),
            "abstract": "本发明公开一种输入数据处理方法，能够生成可追溯的处理结果。",
            "drawings": "图1为输入数据处理方法流程图。",
            "diagram": "flowchart TD\nA[接收输入] --> B[提取特征]\nB --> C[输出结果]",
            "image_prompt": "黑白专利线稿，展示输入数据处理流程。",
            "review": json.dumps(
                [
                    {
                        "category": "支持性",
                        "severity": "low",
                        "message": "权利要求与说明书主要技术特征一致。",
                        "suggestion": "提交前补充实施例参数。",
                        "evidence": "权利要求1",
                    }
                ],
                ensure_ascii=False,
            ),
            "post_draft_claims_reviewer": _post_review_role("claims_reviewer"),
            "post_draft_spec_cleaner": _post_review_role("spec_cleaner"),
            "post_draft_technical_hardness": _post_review_role("technical_hardness"),
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
    )


def _post_review_role(role: str) -> str:
    return json.dumps(
        {
            "role": role,
            "status": "passed",
            "blocking_issues": [],
            "contamination_hits": [],
            "rewrite_suggestions": [],
            "official_safe_patches": [],
            "attorney_memo": [],
        },
        ensure_ascii=False,
    )
```

- [ ] **Step 4: Add journey execution functions**

Append this code to `tests/agent_journey_runner.py`:

```python
def run_journeys(journey_ids: list[str], output_dir: Path) -> list[Path]:
    return [run_journey(journey_id, output_dir) for journey_id in journey_ids]


def run_journey(
    journey_id: str,
    output_dir: Path,
    source_identity: SourceIdentity | None = None,
) -> Path:
    if journey_id not in JOURNEY_IDS:
        raise ValueError(f"unknown journey_id: {journey_id}")
    identity = source_identity or collect_source_identity()
    started_at = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix=f"patentagent-{journey_id}-") as data_dir:
        client = TestClient(create_app(data_dir=Path(data_dir), llm_client=journey_llm(), load_env_file=False))
        driver = FlowDriver(client)
        steps: list[JourneyStepResult] = []
        if journey_id == "invention_from_idea":
            _run_invention_from_idea(driver, steps)
        elif journey_id == "utility_model_from_structure":
            _run_utility_model_from_structure(driver, steps)
        else:
            _run_polish_existing_draft(driver, steps)
        state = driver.state()
        _assert_ready_for_official_export(driver, steps)
        finished_at = datetime.now(timezone.utc).isoformat()
        report = JourneyReport(
            source_identity=identity,
            journey_id=journey_id,
            mode="api",
            test_target="api_testclient",
            llm_mode="fake",
            data_dir=data_dir,
            started_at=started_at,
            finished_at=finished_at,
            status="passed",
            steps=steps,
            gates=state.gates,
            hashes=state.hashes,
            failures=[],
            artifacts={"api_payloads": [], "logs": [], "screenshots": []},
        )
        return write_report(report, output_dir)


def _run_invention_from_idea(driver: FlowDriver, steps: list[JourneyStepResult]) -> None:
    driver.create_project(
        "置信度输入处理",
        "一种根据输入特征置信度和阈值生成处理结果的方法，解决处理结果不可追溯的问题。",
        patent_type="invention",
    )
    steps.append(_step("create_project", "passed", "idea project", "project id assigned", driver.project()["id"]))
    deliberation_id = _seed_completed_deliberation(driver)
    steps.append(_step("deliberation", "passed", "strict deterministic deliberation", "run id assigned", deliberation_id))
    requirement = driver.formula_requirement()
    if requirement["required"] is not True:
        raise AssertionError(f"invention journey should require formula: {requirement}")
    formula = driver.run_formula()
    if formula["status"] != "completed" or not formula["package"]["formula_blocks"]:
        raise AssertionError(f"invention formula run incomplete: {formula}")
    steps.append(_step("formula", "passed", "run core formula", "completed formula package", formula["id"]))
    package = driver.generate_draft({"deliberation_run_id": deliberation_id, "formula_run_id": formula["id"]})
    steps.append(_step("draft", "passed", "generate invention draft", "package title", package["title"]))
    driver.run_quality()
    driver.compile_official()
    review = driver.run_post_draft_review()
    steps.append(_step("post_draft_review", "passed", "review official package", "export_allowed true", str(review["export_allowed"])))


def _seed_completed_deliberation(driver: FlowDriver) -> str:
    providers = list(STRICT_DELIBERATION_PROVIDERS)
    project_id = driver.project_id
    stages = [
        *[
            DeliberationStageResult(
                phase="opening",
                provider_id=provider,
                label=f"opening {provider}",
                payload={"stance": "agent journey ready"},
                status="completed",
            )
            for provider in providers
        ],
        *[
            DeliberationStageResult(
                phase="pair",
                provider_id="codex",
                label=f"pair {provider_a}-vs-{provider_b}",
                payload={"resolved_recommendation": "deterministic journey path accepted"},
                status="completed",
            )
            for provider_a, provider_b in combinations(providers, 2)
        ],
        DeliberationStageResult(
            phase="chair",
            provider_id="codex",
            label="chair synthesis",
            payload={"summary": "agent journey strict deliberation completed"},
            status="completed",
        ),
    ]
    run_id = f"agent-journey-delib-{project_id}"
    driver.client.app.state.store.create_deliberation_run(
        DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=providers,
            run_mode="full",
            stage_results=stages,
            strategy_brief=PatentStrategyBrief(
                summary="agent journey 会审策略：以置信度、阈值和证据记录支撑权利要求。",
                claim_strategy=["独立权利要求覆盖输入、置信度、阈值和证据记录闭环。"],
                description_strategy=["说明书补充置信度计算和证据记录的数据结构。"],
                risk_controls=["未验证效果不得写成已验证事实。"],
                agent_consensus=f"{'、'.join(providers)} 会审同意进入确定性 journey 生成路径。",
            ),
            events=["agent journey deliberation seeded without live providers"],
        )
    )
    return run_id


def _run_utility_model_from_structure(driver: FlowDriver, steps: list[JourneyStepResult]) -> None:
    driver.create_project(
        "可调安装支架",
        "专利类型：实用新型。一种可调安装支架，包括底座、支撑臂和限位件。",
        patent_type="utility_model",
    )
    steps.append(_step("create_project", "passed", "utility model structure", "project id assigned", driver.project()["id"]))
    package = driver.generate_draft()
    steps.append(_step("lightweight_draft", "passed", "generate utility model draft", "package title", package["title"]))
    driver.run_quality()
    driver.compile_official()
    review = driver.run_post_draft_review()
    steps.append(_step("post_draft_review", "passed", "review utility model package", "export_allowed true", str(review["export_allowed"])))


def _run_polish_existing_draft(driver: FlowDriver, steps: list[JourneyStepResult]) -> None:
    driver.create_project(
        "已有稿件润色",
        "导入已有稿件进行质量检查和正式稿清理。",
        patent_type="invention",
    )
    driver.intake_external_draft(_external_draft_text(), filename="existing-draft.txt")
    steps.append(_step("external_draft_intake", "passed", "pasted existing draft", "package present", driver.project()["package"]["title"]))
    driver.run_quality()
    driver.compile_official()
    review = driver.run_post_draft_review()
    steps.append(_step("post_draft_review", "passed", "review polished draft", "export_allowed true", str(review["export_allowed"])))


def _assert_ready_for_official_export(driver: FlowDriver, steps: list[JourneyStepResult]) -> None:
    state = driver.state()
    if state.gates["quality"] != "current":
        raise AssertionError(f"quality gate is not current: {state.gates}")
    if state.gates["official_compile"] != "current":
        raise AssertionError(f"official compile gate is not current: {state.gates}")
    if state.gates["post_draft_review"] != "current":
        raise AssertionError(f"post-draft review gate is not current: {state.gates}")
    export = driver.export_official()
    if not export["ok"]:
        raise AssertionError(f"official export is blocked: {export}")
    steps.append(_step("official_export", "passed", "export official markdown", "ok true", str(export["ok"])))


def _step(step_id: str, status: str, input_summary: str, expected: str, actual: str) -> JourneyStepResult:
    return JourneyStepResult(
        id=step_id,
        status=status,
        input_summary=input_summary,
        expected=expected,
        actual=actual,
        evidence=[],
    )


def _external_draft_text() -> str:
    return """
发明名称
一种输入数据处理方法
摘要
本发明公开一种输入数据处理方法。
权利要求书
1. 一种输入数据处理方法，其特征在于，包括接收输入数据、提取输入特征并输出处理结果。
说明书
本发明涉及数据处理技术领域。在一个实施例中，系统接收输入数据，提取输入特征，计算处理置信度并输出处理结果。
附图说明
图1为输入数据处理方法流程图。
""".strip()
```

- [ ] **Step 5: Run the focused journey tests**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py -q
```

Expected: PASS.

- [ ] **Step 6: Run FlowDriver and journey tests together**

Run:

```bash
python3 -m pytest tests/test_flow_driver.py tests/test_agent_journey_runner.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

Run:

```bash
git add tests/agent_journey_runner.py tests/test_agent_journey_runner.py
git commit -m "test: add API agent journey runner"
```

---

### Task 4: Add CLI Entrypoint And QA Documentation Hook

**Files:**
- Modify: `tests/agent_journey_runner.py`
- Modify: `tests/test_agent_journey_runner.py`
- Modify: `docs/qa/ai-scenario-testing-pipeline.md`

**Interfaces:**
- Produces CLI:
  - `python3 tests/agent_journey_runner.py --journey all --output-dir output/agent-journeys`
  - `python3 tests/agent_journey_runner.py --journey invention_from_idea --output-dir /tmp/agent-journeys`

- [ ] **Step 1: Add failing CLI test**

Append this test to `tests/test_agent_journey_runner.py`:

```python
def test_main_runs_selected_journey_and_returns_zero(tmp_path: Path) -> None:
    from agent_journey_runner import main

    exit_code = main(["--journey", "utility_model_from_structure", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    reports = list(tmp_path.glob("*-utility_model_from_structure.json"))
    assert len(reports) == 1
```

- [ ] **Step 2: Run the CLI test and verify it fails**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_main_runs_selected_journey_and_returns_zero -q
```

Expected: FAIL because `main` is not implemented.

- [ ] **Step 3: Add `main` to the runner module**

Append this code to `tests/agent_journey_runner.py`:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PatentAgent API journeys.")
    parser.add_argument(
        "--journey",
        choices=[*JOURNEY_IDS, "all"],
        default="all",
        help="Journey to run. Use all to run every Phase 1 journey.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON journey reports.",
    )
    args = parser.parse_args(argv)
    selected = list(JOURNEY_IDS) if args.journey == "all" else [args.journey]
    paths = run_journeys(selected, args.output_dir)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the CLI test**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_main_runs_selected_journey_and_returns_zero -q
```

Expected: PASS.

- [ ] **Step 5: Add QA docs hook**

In `docs/qa/ai-scenario-testing-pipeline.md`, under `## 6. 推荐自动化层`, add this paragraph after the regular development verification commands:

Add exactly this Markdown text:

    Phase 1 agent journey runner:

    ```bash
    python3 tests/agent_journey_runner.py --journey all --output-dir output/agent-journeys
    ```

    This runner uses FastAPI `TestClient`, fake LLM, temporary data directories, and JSON reports. It proves the three primary API journeys reach a current quality gate, current official compile, current post-draft review, and allowed official export before any broader browser or Tauri smoke is treated as user-facing evidence.

- [ ] **Step 6: Run focused docs/CLI tests**

Run:

```bash
python3 -m pytest tests/test_agent_journey_runner.py tests/test_qa_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Run the CLI once and inspect generated reports**

Run:

```bash
python3 tests/agent_journey_runner.py --journey all --output-dir /tmp/patentagent-agent-journeys
```

Expected: command prints three JSON report paths, one for each journey ID. Each JSON file has `execution.status` equal to `passed`, `execution.llm_mode` equal to `fake`, and non-empty `hashes.current_source_draft_hash`.

- [ ] **Step 8: Commit Task 4**

Run:

```bash
git add tests/agent_journey_runner.py tests/test_agent_journey_runner.py docs/qa/ai-scenario-testing-pipeline.md
git commit -m "docs: document API agent journey runner"
```

---

### Task 5: Broad Verification And Handoff Evidence

**Files:**
- No new source files expected.
- Verification covers files modified in Tasks 1-4.

**Interfaces:**
- Consumes: `tests/agent_journey_runner.py`, `tests/flow_driver.py`, existing deterministic gates.
- Produces: final verification output and a concise handoff summary.

- [ ] **Step 1: Run narrow Phase 1 verification**

Run:

```bash
python3 -m pytest tests/test_flow_driver.py tests/test_agent_journey_runner.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend suite**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS. If unrelated failures appear, record the failing test names and classify them before patching.

- [ ] **Step 3: Run deterministic v1 API smoke**

Run:

```bash
python3 scripts/v1_api_smoke.py --repeat-count 2
```

Expected: PASS with `v1.1 deterministic quality gate passed`.

- [ ] **Step 4: Run the agent journeys after broad verification**

Run:

```bash
python3 tests/agent_journey_runner.py --journey all --output-dir /tmp/patentagent-agent-journeys
```

Expected: three report paths printed; each report is `passed`.

- [ ] **Step 5: Check final working tree**

Run:

```bash
git status --short --branch
```

Expected: branch remains `codex/automation-test-plan`. Dirty files are either intentional task changes already committed or pre-existing unrelated dirty files noted in the final handoff.

- [ ] **Step 6: Final handoff**

Report:

```text
Source identity:
- Worktree:
- Branch:
- Short SHA:
- Dirty state:

Implemented:
- FlowDriver runner primitives
- API journey report schema
- Three API journeys
- CLI and QA docs hook

Verification:
- python3 -m pytest tests/test_flow_driver.py tests/test_agent_journey_runner.py -q
- python3 -m pytest -q
- python3 scripts/v1_api_smoke.py --repeat-count 2
- python3 tests/agent_journey_runner.py --journey all --output-dir /tmp/patentagent-agent-journeys

Remaining risks:
- Browser/Tauri DOM journey inspection is Phase 2+ planning, not part of this Phase 1 API runner.
- Patent quality oracle golden cases are a separate Phase 2 milestone.
```
