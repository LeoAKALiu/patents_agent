from __future__ import annotations

import importlib.util

from backend.app.agents.models import AgentRuntimeFailure, WorkflowRunRequest, WorkflowRunResult


class LangGraphWorkflowAdapter:
    async def run_workflow(self, request: WorkflowRunRequest) -> WorkflowRunResult:
        if importlib.util.find_spec("langgraph") is None:
            raise AgentRuntimeFailure(
                "runtime_unavailable",
                "LangGraph is not installed; install the optional workflow runtime before enabling this adapter.",
                provider_id="langgraph-local",
            )
        raise AgentRuntimeFailure(
            "runtime_unavailable",
            "LangGraph adapter is available for dependency probing but is not wired to a GrantAtlas workflow in this increment.",
            provider_id="langgraph-local",
        )
