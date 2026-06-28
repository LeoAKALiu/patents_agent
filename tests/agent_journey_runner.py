from __future__ import annotations

import argparse
import sys
import json
import subprocess
import tempfile
from itertools import combinations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.llm import FakeLLMClient
from backend.app.main import STRICT_DELIBERATION_PROVIDERS, create_app
from backend.app.schemas import DeliberationRun, DeliberationStageResult, PatentStrategyBrief
from flow_driver import FlowDriver

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


def run_journeys(journey_ids: list[str], output_dir: Path) -> list[Path]:
    _validate_journey_ids(journey_ids)
    return [run_journey(journey_id, output_dir) for journey_id in journey_ids]


def run_journey(
    journey_id: str,
    output_dir: Path,
    source_identity: SourceIdentity | None = None,
) -> Path:
    _validate_journey_ids([journey_id])
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
            data_dir=f"ephemeral:{data_dir}",
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


def _validate_journey_ids(journey_ids: list[str]) -> None:
    unknown_ids = [journey_id for journey_id in journey_ids if journey_id not in JOURNEY_IDS]
    if unknown_ids:
        quoted = ", ".join(unknown_ids)
        raise ValueError(f"unknown journey_id: {quoted}")


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
