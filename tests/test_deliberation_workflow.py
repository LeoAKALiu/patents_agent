from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.app.agents.adapters.fake import FakeAgentRuntime
from backend.app.agents.models import AgentRuntimeFailure
from backend.app.schemas import InventionBrief
from backend.app.workflows.deliberation import DeliberationWorkflow


def _brief() -> InventionBrief:
    return InventionBrief(
        title="Image defect detection",
        technical_field="AI inspection",
        technical_problem="Manual inspection is slow",
        technical_solution="Capture images and infer defect locations",
        beneficial_effects=["Higher throughput"],
        key_steps=["capture", "infer", "output"],
    )


def _runtime() -> FakeAgentRuntime:
    return FakeAgentRuntime(
        task_payloads={
            "opening codex": {
                "stance": "codex stance",
                "claim_scope": ["method"],
                "risks": [],
                "recommendations": ["add examples"],
            },
            "opening deepseek": {
                "stance": "deepseek stance",
                "claim_scope": ["system"],
                "risks": [],
                "recommendations": ["narrow novelty"],
            },
            "opening claude": {
                "stance": "claude stance",
                "claim_scope": ["medium"],
                "risks": [],
                "recommendations": ["align terms"],
            },
            "pair codex-vs-deepseek": {
                "conflict_level": 0.2,
                "agreements": ["method claim"],
                "disagreements": [],
                "resolved_recommendation": "keep method claim",
            },
            "pair codex-vs-claude": {
                "conflict_level": 0.3,
                "agreements": ["support examples"],
                "disagreements": [],
                "resolved_recommendation": "add embodiments",
            },
            "pair deepseek-vs-claude": {
                "conflict_level": 0.1,
                "agreements": ["avoid pure function claim"],
                "disagreements": [],
                "resolved_recommendation": "add concrete input and output",
            },
            "chair synthesis": {
                "summary": "Three agents agree.",
                "claim_strategy": ["method claim"],
                "description_strategy": ["add embodiments"],
                "risk_controls": ["avoid functional overbreadth"],
                "agent_consensus": "Three agents agree.",
            },
        }
    )


def test_deliberation_workflow_uses_agent_runtime_and_writes_artifacts(tmp_path: Path) -> None:
    runtime = _runtime()
    workflow = DeliberationWorkflow(agent_runtime=runtime)

    run = asyncio.run(
        workflow.run(
            run_id="run-1",
            project_id="project-1",
            brief=_brief(),
            context_chunks=[],
            providers=["codex", "deepseek", "claude"],
            run_dir=tmp_path,
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert run.status == "completed"
    assert run.strategy_brief is not None
    assert run.strategy_brief.claim_strategy == ["method claim"]
    assert [request.label for request in runtime.requests[:3]] == [
        "opening codex",
        "opening deepseek",
        "opening claude",
    ]
    assert (tmp_path / "openings.json").exists()
    assert (tmp_path / "pair_results.json").exists()
    assert (tmp_path / "strategy_brief.json").exists()


def test_deliberation_workflow_records_opening_failure_without_pair_phase(tmp_path: Path) -> None:
    runtime = _runtime()
    runtime.task_failures["opening deepseek"] = AgentRuntimeFailure(
        reason="process_error",
        message="opening deepseek failed",
        provider_id="deepseek",
        stderr="process exited 1",
    )
    workflow = DeliberationWorkflow(agent_runtime=runtime)

    run = asyncio.run(
        workflow.run(
            run_id="run-2",
            project_id="project-1",
            brief=_brief(),
            context_chunks=[],
            providers=["codex", "deepseek", "claude"],
            run_dir=tmp_path,
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert run.status == "failed"
    assert run.strategy_brief is None
    assert any(stage.phase == "opening" and stage.status == "failed" for stage in run.stage_results)
    assert not any(request.label.startswith("pair") for request in runtime.requests)
