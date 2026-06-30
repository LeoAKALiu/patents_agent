from __future__ import annotations

from typing import Any

from backend.app.agents.models import AgentRuntimeFailure, AgentTaskRequest, AgentTaskResult


class LegacyProviderRunnerAdapter:
    def __init__(self, provider_runner: Any) -> None:
        self.provider_runner = provider_runner

    async def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        try:
            result = await self.provider_runner.run_json_task(
                provider_id=request.provider_id,
                prompt=request.prompt,
                workdir=request.workdir,
                label=request.label,
                trace=request.trace,
                task_timeout_ms=request.timeout_ms,
                log_callback=request.log_callback,
            )
        except AgentRuntimeFailure:
            raise
        return AgentTaskResult(
            provider_id=getattr(result, "provider_id", request.provider_id),
            payload=result.payload,
            stdout=getattr(result, "stdout", ""),
            stderr=getattr(result, "stderr", ""),
            attempts=getattr(result, "attempts", 1),
        )
