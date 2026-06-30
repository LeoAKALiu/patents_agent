from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.app.agents.adapters.fake import FakeAgentRuntime
from backend.app.agents.models import (
    AgentRuntimeFailure,
    AgentTaskRequest,
    AgentTaskResult,
    WorkflowRunRequest,
)


def _request(tmp_path: Path, label: str = "opening codex") -> AgentTaskRequest:
    return AgentTaskRequest(
        provider_id="codex",
        role="deliberation",
        prompt="return json",
        workdir=tmp_path,
        label=label,
        trace=False,
        timeout_ms=1000,
    )


def test_fake_runtime_returns_configured_task_payload(tmp_path: Path) -> None:
    runtime = FakeAgentRuntime(
        task_payloads={
            "opening codex": {
                "stance": "codex stance",
                "claim_scope": ["method"],
                "risks": [],
                "recommendations": ["narrow claim 1"],
            }
        }
    )

    result = asyncio.run(runtime.run_task(_request(tmp_path)))

    assert isinstance(result, AgentTaskResult)
    assert result.provider_id == "codex"
    assert result.payload["stance"] == "codex stance"
    assert result.attempts == 1
    assert result.status == "completed"
    assert runtime.requests[0].label == "opening codex"


def test_fake_runtime_raises_configured_failure(tmp_path: Path) -> None:
    runtime = FakeAgentRuntime(
        task_failures={
            "opening codex": AgentRuntimeFailure(
                reason="process_error",
                message="opening codex failed with exit code 1",
                provider_id="codex",
                stderr="readonly database",
            )
        }
    )

    with pytest.raises(AgentRuntimeFailure) as exc:
        asyncio.run(runtime.run_task(_request(tmp_path)))

    assert exc.value.reason == "process_error"
    assert exc.value.provider_id == "codex"
    assert "readonly database" in exc.value.stderr


def test_fake_runtime_records_workflow_requests(tmp_path: Path) -> None:
    runtime = FakeAgentRuntime(workflow_payloads={"deliberation": {"ok": True}})

    result = asyncio.run(
        runtime.run_workflow(
            WorkflowRunRequest(
                run_id="run-1",
                workflow_name="deliberation",
                initial_state={"project_id": "project-1"},
                workdir=tmp_path,
                trace=False,
                timeout_ms=1000,
            )
        )
    )

    assert result.run_id == "run-1"
    assert result.workflow_name == "deliberation"
    assert result.status == "completed"
    assert result.payload == {"ok": True}
    assert runtime.workflow_requests[0].initial_state == {"project_id": "project-1"}
