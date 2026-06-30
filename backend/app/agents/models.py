from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from backend.app.schemas import DeliberationLogEntry


AgentTaskStatus = Literal["completed"]
WorkflowRunStatus = Literal["completed", "failed", "interrupted"]
OutputMode = Literal["json"]


@dataclass(slots=True)
class AgentArtifact:
    path: str
    kind: str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentTaskRequest:
    provider_id: str
    role: str
    prompt: str
    workdir: Path
    label: str
    trace: bool
    timeout_ms: int
    output_mode: OutputMode = "json"
    attempt_limit: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)
    log_callback: Callable[[DeliberationLogEntry], None] | None = None


@dataclass(slots=True)
class AgentTaskResult:
    provider_id: str
    payload: dict[str, Any]
    stdout: str = ""
    stderr: str = ""
    attempts: int = 1
    status: AgentTaskStatus = "completed"
    artifacts: list[AgentArtifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowRunRequest:
    run_id: str
    workflow_name: str
    initial_state: dict[str, Any]
    workdir: Path
    trace: bool
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowRunResult:
    run_id: str
    workflow_name: str
    status: WorkflowRunStatus
    payload: dict[str, Any] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    artifacts: list[AgentArtifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRuntimeFailure(RuntimeError):
    def __init__(
        self,
        reason: str,
        message: str,
        *,
        provider_id: str = "",
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.provider_id = provider_id
        self.stdout = stdout
        self.stderr = stderr
