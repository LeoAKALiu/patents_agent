from __future__ import annotations

import asyncio
import importlib.util

import pytest

from backend.app.agents.adapters.langgraph import LangGraphWorkflowAdapter
from backend.app.agents.models import AgentRuntimeFailure, WorkflowRunRequest


def test_langgraph_adapter_imports_without_langgraph_dependency(monkeypatch, tmp_path) -> None:
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "langgraph" else original_find_spec(name))
    adapter = LangGraphWorkflowAdapter()

    with pytest.raises(AgentRuntimeFailure) as exc:
        asyncio.run(
            adapter.run_workflow(
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

    assert exc.value.reason == "runtime_unavailable"
    assert "LangGraph is not installed" in str(exc.value)
