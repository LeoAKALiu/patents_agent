from __future__ import annotations

from backend.app.agents.adapters.cli import (
    DEFAULT_TASK_TIMEOUT_MS,
    PROMPT_ARG as _PROMPT_ARG,
    CliAgentAdapter,
    LogCallback,
    SpawnFunc,
    _extract_json_payload,
    build_provider_command,
    repair_suggestion_for_failure,
)
from backend.app.agents.models import AgentRuntimeFailure, AgentTaskResult

ProviderFailure = AgentRuntimeFailure
ProviderTaskResult = AgentTaskResult
AgentProviderRunner = CliAgentAdapter

__all__ = [
    "DEFAULT_TASK_TIMEOUT_MS",
    "_PROMPT_ARG",
    "AgentProviderRunner",
    "LogCallback",
    "ProviderFailure",
    "ProviderTaskResult",
    "SpawnFunc",
    "_extract_json_payload",
    "build_provider_command",
    "repair_suggestion_for_failure",
]
