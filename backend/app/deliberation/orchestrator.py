from __future__ import annotations

import asyncio
from typing import Any

from backend.app.agents.adapters.cli import CliAgentAdapter
from backend.app.agents.adapters.legacy import LegacyProviderRunnerAdapter
from backend.app.agents.runtime import AgentRuntime
from backend.app.workflows.deliberation import (
    DeliberationWorkflow,
    _coordinator_provider,
    _fallback_strategy,
    _run_mode,
)


class DeliberationOrchestrator:
    def __init__(self, provider_runner: Any | None = None, agent_runtime: AgentRuntime | None = None) -> None:
        if agent_runtime is not None:
            self.agent_runtime = agent_runtime
        elif provider_runner is not None and hasattr(provider_runner, "run_task"):
            self.agent_runtime = provider_runner
        elif provider_runner is not None:
            self.agent_runtime = LegacyProviderRunnerAdapter(provider_runner)
        else:
            self.agent_runtime = CliAgentAdapter()
        self.provider_runner = provider_runner or self.agent_runtime

    async def run(self, **kwargs: Any):
        return await DeliberationWorkflow(agent_runtime=self.agent_runtime).run(**kwargs)


def run_deliberation_sync(*args: Any, **kwargs: Any):
    provider_runner = kwargs.pop("provider_runner", None)
    agent_runtime = kwargs.pop("agent_runtime", None)
    remaining_args = list(args)
    if remaining_args and provider_runner is None:
        provider_runner = remaining_args.pop(0)
    if remaining_args:
        raise TypeError("run_deliberation_sync accepts at most one positional argument: provider_runner")
    orchestrator = DeliberationOrchestrator(provider_runner=provider_runner, agent_runtime=agent_runtime)
    return asyncio.run(orchestrator.run(**kwargs))
