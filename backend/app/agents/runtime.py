from __future__ import annotations

from typing import Protocol

from backend.app.agents.models import (
    AgentTaskRequest,
    AgentTaskResult,
    WorkflowRunRequest,
    WorkflowRunResult,
)


class AgentRuntime(Protocol):
    async def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        raise NotImplementedError


class WorkflowRuntime(Protocol):
    async def run_workflow(self, request: WorkflowRunRequest) -> WorkflowRunResult:
        raise NotImplementedError
