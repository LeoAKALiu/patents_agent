from __future__ import annotations

from backend.app.agents.models import (
    AgentRuntimeFailure,
    AgentTaskRequest,
    AgentTaskResult,
    WorkflowRunRequest,
    WorkflowRunResult,
)


class FakeAgentRuntime:
    def __init__(
        self,
        *,
        task_payloads: dict[str, dict] | None = None,
        task_failures: dict[str, AgentRuntimeFailure] | None = None,
        workflow_payloads: dict[str, dict] | None = None,
    ) -> None:
        self.task_payloads = task_payloads or {}
        self.task_failures = task_failures or {}
        self.workflow_payloads = workflow_payloads or {}
        self.requests: list[AgentTaskRequest] = []
        self.workflow_requests: list[WorkflowRunRequest] = []

    async def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        self.requests.append(request)
        failure = self.task_failures.get(request.label)
        if failure is not None:
            raise failure
        payload = self.task_payloads.get(request.label, {})
        return AgentTaskResult(
            provider_id=request.provider_id,
            payload=payload,
            stdout="",
            stderr="",
            attempts=1,
        )

    async def run_workflow(self, request: WorkflowRunRequest) -> WorkflowRunResult:
        self.workflow_requests.append(request)
        payload = self.workflow_payloads.get(request.workflow_name, {})
        return WorkflowRunResult(
            run_id=request.run_id,
            workflow_name=request.workflow_name,
            status="completed",
            payload=payload,
        )
