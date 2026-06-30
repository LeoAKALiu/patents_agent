# Agent Runtime Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GrantAtlas-owned agent runtime interface so future Codex, Hermes, OMP, LangGraph, and CLI agents can be adapted without rewriting patent workflow code.

**Architecture:** Add a deep `backend/app/agents` module with typed task/workflow requests, a CLI adapter that preserves current provider behavior, a provider capability registry, and a code-defined deliberation workflow behind the runtime interface. Keep existing FastAPI response models, SQLite run tables, run directories, strict deliberation gates, and frontend contracts unchanged.

**Tech Stack:** Python 3.11+, dataclasses, typing `Protocol`, FastAPI app state, existing Pydantic schemas, pytest, existing `json-repair`, optional lazy LangGraph import with no required dependency in this increment.

## Global Constraints

- Repository identity at planning time: branch `codex/grantatlas-readme-branding`, short SHA `0982004c`, worktree `/Users/leo/Projects/patents_agent`.
- Dirty status at planning time: untracked `.gstack/`, `.reasonix/`, `.worktrees/`, and `output/`; do not stage or modify those directories.
- Do not rewrite the whole backend around LangGraph.
- Do not migrate React, Tauri, storage, export, patent parsing, or patent domain models.
- Do not replace existing Pydantic schemas for deliberation, draft packages, reviews, or runtime failures in the first increment.
- Do not require user-editable workflow configuration in the first increment.
- Workflows are code-defined Python for this increment.
- LangGraph must be optional; `pyproject.toml` must not gain a required `langgraph` dependency in this plan.
- Existing strict generation gate stays unchanged: draft generation still requires a strict completed deliberation with required providers, completed openings, completed pair comparisons, and chair synthesis.
- Existing `/api/projects/{project_id}/deliberations` API shape stays unchanged.
- Existing `/api/agents/doctor` response shape stays unchanged.
- Adapters normalize runtime-specific failures into GrantAtlas failure reasons and repair suggestions.

---

## File Structure

- Create `backend/app/agents/__init__.py`: public package marker and exports for runtime interfaces.
- Create `backend/app/agents/models.py`: dataclasses for agent task/workflow requests, results, artifacts, and runtime failures.
- Create `backend/app/agents/runtime.py`: `AgentRuntime` and `WorkflowRuntime` protocols.
- Create `backend/app/agents/registry.py`: provider roles, capabilities, strict provider constants, and selection helpers.
- Create `backend/app/agents/adapters/__init__.py`: adapter package marker.
- Create `backend/app/agents/adapters/fake.py`: fake runtime for unit and API tests.
- Create `backend/app/agents/adapters/cli.py`: current CLI provider behavior moved behind the runtime interface.
- Create `backend/app/agents/adapters/legacy.py`: bridge for existing test doubles and any old object that only exposes `run_json_task`.
- Create `backend/app/agents/adapters/langgraph.py`: optional lazy LangGraph workflow adapter shell with a deterministic unavailable failure when `langgraph` is absent.
- Create `backend/app/workflows/__init__.py`: workflow package marker.
- Create `backend/app/workflows/deliberation.py`: code-defined deliberation workflow using `AgentRuntime.run_task`.
- Modify `backend/app/deliberation/providers.py`: compatibility shim that re-exports the CLI adapter under existing names.
- Modify `backend/app/deliberation/orchestrator.py`: compatibility wrapper around `DeliberationWorkflow`.
- Modify `backend/app/main.py`: use registry helpers, support optional `agent_runtime`, and pass it to deliberation execution.
- Test `tests/test_agent_runtime.py`: runtime model and fake runtime contract tests.
- Test `tests/test_agent_runtime_cli.py`: CLI adapter and compatibility shim tests.
- Test `tests/test_agent_registry.py`: provider capability and role selection tests.
- Test `tests/test_deliberation_workflow.py`: direct workflow tests.
- Modify `tests/test_deliberation_api.py`: add one API test for `agent_runtime` injection.
- Test `tests/test_agent_langgraph_adapter.py`: no-network optional LangGraph adapter test.

---

### Task 1: Runtime Models and Fake Runtime

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/models.py`
- Create: `backend/app/agents/runtime.py`
- Create: `backend/app/agents/adapters/__init__.py`
- Create: `backend/app/agents/adapters/fake.py`
- Test: `tests/test_agent_runtime.py`

**Interfaces:**
- Produces: `AgentTaskRequest`, `AgentTaskResult`, `WorkflowRunRequest`, `WorkflowRunResult`, `AgentArtifact`, `AgentRuntimeFailure`, `AgentRuntime`, `WorkflowRuntime`, `FakeAgentRuntime`.
- Later tasks rely on `AgentRuntime.run_task(request: AgentTaskRequest) -> AgentTaskResult` and `AgentRuntimeFailure.reason`.

- [ ] **Step 1: Write the failing runtime contract tests**

Add `tests/test_agent_runtime.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify the runtime package is missing**

Run:

```bash
python3 -m pytest tests/test_agent_runtime.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.agents'`.

- [ ] **Step 3: Add runtime models and protocols**

Create `backend/app/agents/models.py`:

```python
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
```

Create `backend/app/agents/runtime.py`:

```python
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
```

Create `backend/app/agents/adapters/fake.py`:

```python
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
```

Create `backend/app/agents/__init__.py`:

```python
"""Agent runtime interfaces and adapters for GrantAtlas workflows."""
```

Create `backend/app/agents/adapters/__init__.py`:

```python
"""Concrete adapters for GrantAtlas agent runtimes."""
```

- [ ] **Step 4: Run runtime tests to verify they pass**

Run:

```bash
python3 -m pytest tests/test_agent_runtime.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit runtime models**

Run:

```bash
git add backend/app/agents tests/test_agent_runtime.py
git commit -m "feat: add agent runtime interface"
```

Expected: commit succeeds and stages only the new runtime files and tests.

---

### Task 2: CLI Adapter and Provider Compatibility Shim

**Files:**
- Create: `backend/app/agents/adapters/cli.py`
- Modify: `backend/app/deliberation/providers.py`
- Test: `tests/test_agent_runtime_cli.py`
- Existing Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: `AgentTaskRequest`, `AgentTaskResult`, `AgentRuntimeFailure`.
- Produces: `CliAgentAdapter.run_task(request)`, `CliAgentAdapter.run_json_task(...)`, `build_provider_command(...)`, `_extract_json_payload(...)`, `repair_suggestion_for_failure(...)`.
- Compatibility: `backend.app.deliberation.providers.AgentProviderRunner` remains importable and callable with `run_json_task`.

- [ ] **Step 1: Write failing CLI adapter tests**

Create `tests/test_agent_runtime_cli.py`:

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.app.agents.adapters.cli import CliAgentAdapter, build_provider_command
from backend.app.agents.models import AgentRuntimeFailure, AgentTaskRequest
from backend.app.deliberation.providers import AgentProviderRunner, ProviderFailure


def _request(tmp_path: Path, *, provider_id: str = "gemini", label: str = "opening gemini") -> AgentTaskRequest:
    return AgentTaskRequest(
        provider_id=provider_id,
        role="deliberation",
        prompt="return json",
        workdir=tmp_path,
        label=label,
        trace=True,
        timeout_ms=1000,
    )


def test_cli_adapter_retries_invalid_json_and_writes_trace(tmp_path: Path) -> None:
    attempts = 0

    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return 0, "not json", ""
        return 0, '{"ok": true}', ""

    adapter = CliAgentAdapter(spawn_func=fake_spawn)

    result = asyncio.run(adapter.run_task(_request(tmp_path)))

    assert attempts == 2
    assert result.payload == {"ok": True}
    trace_files = sorted((tmp_path / "trace").glob("*.json"))
    assert len(trace_files) == 2
    trace_payload = json.loads(trace_files[-1].read_text(encoding="utf-8"))
    assert trace_payload["stdout"] == '{"ok": true}'


def test_cli_adapter_raises_runtime_failure_for_empty_output(tmp_path: Path) -> None:
    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        return 0, "", ""

    adapter = CliAgentAdapter(spawn_func=fake_spawn)

    with pytest.raises(AgentRuntimeFailure) as exc:
        asyncio.run(adapter.run_task(_request(tmp_path, provider_id="claude", label="opening claude")))

    assert exc.value.reason == "empty_output"
    assert exc.value.provider_id == "claude"


def test_deliberation_provider_runner_remains_compatible(tmp_path: Path) -> None:
    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        return 0, '{"ok": true}', ""

    runner = AgentProviderRunner(spawn_func=fake_spawn)

    result = asyncio.run(
        runner.run_json_task(
            provider_id="gemini",
            prompt="return json",
            workdir=tmp_path,
            label="opening gemini",
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert result.payload == {"ok": True}
    assert ProviderFailure is AgentRuntimeFailure


def test_optional_cli_commands_still_pass_prompt_non_interactively(tmp_path: Path) -> None:
    kimi_command, kimi_args = build_provider_command("kimicode", tmp_path, 1)
    mimo_command, mimo_args = build_provider_command("mimo", tmp_path, 1)

    assert kimi_command == "kimicode"
    assert kimi_args == ["-p", "{prompt}", "--output-format", "text"]
    assert mimo_command == "mimo"
    assert mimo_args == ["run", "--format", "default", "{prompt}"]
```

- [ ] **Step 2: Run tests to verify the CLI adapter module is missing**

Run:

```bash
python3 -m pytest tests/test_agent_runtime_cli.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.agents.adapters.cli'`.

- [ ] **Step 3: Move CLI behavior behind `CliAgentAdapter`**

Create `backend/app/agents/adapters/cli.py` by moving the implementation from `backend/app/deliberation/providers.py` and adapting the runner class to accept `AgentTaskRequest`:

```python
from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from backend.app.agents.models import AgentRuntimeFailure, AgentTaskRequest, AgentTaskResult
from backend.app.deliberation.cli_paths import agent_subprocess_env, resolve_agent_command
from backend.app.schemas import DeliberationLogEntry

DEFAULT_TASK_TIMEOUT_MS = 180_000
PROMPT_ARG = "{prompt}"
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

SpawnFunc = Callable[[str, list[str], Path, str, int], Awaitable[tuple[int, str, str]]]
LogCallback = Callable[[DeliberationLogEntry], None]


class CliAgentAdapter:
    def __init__(self, spawn_func: SpawnFunc | None = None) -> None:
        self.spawn_func = spawn_func or _spawn_process

    async def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        workdir = request.workdir.resolve()
        last_failure: AgentRuntimeFailure | None = None
        for attempt in range(1, request.attempt_limit + 1):
            command, args = build_provider_command(request.provider_id, workdir, attempt)
            started_at = time.perf_counter()
            _emit_log(
                request.log_callback,
                level="info",
                provider_id=request.provider_id,
                label=request.label,
                attempt=attempt,
                message="attempt started",
                detail=f"{command} {' '.join(args[:4])}".strip(),
            )
            try:
                try:
                    exit_code, stdout, stderr = await self.spawn_func(
                        command,
                        args,
                        workdir,
                        request.prompt,
                        request.timeout_ms,
                    )
                except OSError as exc:
                    raise AgentRuntimeFailure(
                        "provider_missing",
                        f"{request.label} could not start {command}: {exc}",
                        provider_id=request.provider_id,
                        stderr=str(exc),
                    ) from exc
                if exit_code != 0:
                    raise AgentRuntimeFailure(
                        "process_error",
                        f"{request.label} failed with exit code {exit_code}",
                        provider_id=request.provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                if not stdout.strip():
                    raise AgentRuntimeFailure(
                        "empty_output",
                        f"{request.label} completed without output",
                        provider_id=request.provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                payload = _extract_json_payload(stdout)
                _emit_log(
                    request.log_callback,
                    level="info",
                    provider_id=request.provider_id,
                    label=request.label,
                    attempt=attempt,
                    message="attempt completed",
                    detail=_trim(stdout or stderr),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if request.trace:
                    _write_trace(workdir, request.provider_id, request.label, attempt, request.prompt, stdout, stderr, "ok")
                return AgentTaskResult(
                    provider_id=request.provider_id,
                    payload=payload,
                    stdout=stdout,
                    stderr=stderr,
                    attempts=attempt,
                )
            except AgentRuntimeFailure as exc:
                if not exc.provider_id:
                    exc.provider_id = request.provider_id
                last_failure = exc
                _emit_log(
                    request.log_callback,
                    level="error",
                    provider_id=request.provider_id,
                    label=request.label,
                    attempt=attempt,
                    message="attempt failed",
                    detail=_failure_detail(exc),
                    repair_suggestion=repair_suggestion_for_failure(exc.reason, request.provider_id),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if request.trace:
                    _write_trace(
                        workdir,
                        request.provider_id,
                        request.label,
                        attempt,
                        request.prompt,
                        exc.stdout,
                        exc.stderr,
                        exc.reason,
                    )
                if attempt == request.attempt_limit:
                    raise exc
        raise last_failure or AgentRuntimeFailure("unknown", f"{request.label} failed", provider_id=request.provider_id)

    async def run_json_task(
        self,
        *,
        provider_id: str,
        prompt: str,
        workdir: Path,
        label: str,
        trace: bool,
        task_timeout_ms: int = DEFAULT_TASK_TIMEOUT_MS,
        log_callback: LogCallback | None = None,
    ) -> AgentTaskResult:
        return await self.run_task(
            AgentTaskRequest(
                provider_id=provider_id,
                role="deliberation",
                prompt=prompt,
                workdir=workdir,
                label=label,
                trace=trace,
                timeout_ms=task_timeout_ms,
                log_callback=log_callback,
            )
        )


def build_provider_command(provider_id: str, workdir: Path, attempt: int) -> tuple[str, list[str]]:
    if provider_id == "codex":
        last_message_path = workdir / f".codex-last-{attempt}.txt"
        return (
            "codex",
            [
                "e",
                "--skip-git-repo-check",
                "-C",
                str(workdir),
                "--json",
                "--output-last-message",
                str(last_message_path),
                "-",
            ],
        )
    if provider_id == "claude":
        return (
            "claude",
            ["-p", "--no-chrome", "--disable-slash-commands", "--tools", "", "--output-format", "text", "-"],
        )
    if provider_id == "deepseek":
        return ("reasonix", ["run", "--model", "deepseek-pro"])
    if provider_id == "gemini":
        return ("gemini", ["--prompt", "", "--approval-mode", "plan", "--output-format", "text"])
    if provider_id == "kimicode":
        return ("kimicode", ["-p", PROMPT_ARG, "--output-format", "text"])
    if provider_id == "mimo":
        return ("mimo", ["run", "--format", "default", PROMPT_ARG])
    return (provider_id, [])
```

Also move the existing helper functions from `backend/app/deliberation/providers.py` into this file without behavioral changes:

- `_spawn_process`
- `_read_codex_last_message`
- `_extract_json_payload`
- `_json_payload_candidates`
- `_strip_ansi`
- `_loads_json_object`
- `repair_suggestion_for_failure`
- `_emit_log`
- `_phase_from_label`
- `_elapsed_ms`
- `_failure_detail`
- `_trim`
- `_write_trace`

In `_spawn_process`, replace `_PROMPT_ARG` with `PROMPT_ARG`.

- [ ] **Step 4: Replace old provider module with a compatibility shim**

Replace `backend/app/deliberation/providers.py` with:

```python
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
```

- [ ] **Step 5: Run CLI and legacy provider tests**

Run:

```bash
python3 -m pytest tests/test_agent_runtime_cli.py tests/test_agents.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit CLI adapter migration**

Run:

```bash
git add backend/app/agents/adapters/cli.py backend/app/deliberation/providers.py tests/test_agent_runtime_cli.py tests/test_agents.py
git commit -m "feat: move cli providers behind agent adapter"
```

Expected: commit succeeds.

---

### Task 3: Provider Capability Registry

**Files:**
- Create: `backend/app/agents/registry.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_agent_registry.py`
- Existing Test: `tests/test_deliberation_api.py`

**Interfaces:**
- Consumes: `AgentDoctorReport` and `AgentProviderStatus`.
- Produces: `STRICT_DELIBERATION_PROVIDERS`, `AgentCapability`, `selectable_agent_provider_ids(doctor)`, `agent_provider_ids_for_role(doctor, requested, role)`.
- Compatibility: `backend.app.main._selectable_agent_provider_ids` and `backend.app.main._agent_provider_ids_for_role` remain as wrappers for existing tests and call sites.

- [ ] **Step 1: Write failing registry tests**

Create `tests/test_agent_registry.py`:

```python
from __future__ import annotations

from backend.app.agents.registry import (
    STRICT_DELIBERATION_PROVIDERS,
    agent_provider_ids_for_role,
    selectable_agent_provider_ids,
)
from backend.app.schemas import AgentDoctorReport, AgentProviderStatus


def _status(
    provider_id: str,
    *,
    available: bool,
    selectable: bool,
    roles: list[str],
    required: bool = False,
) -> AgentProviderStatus:
    return AgentProviderStatus(
        id=provider_id,
        label=provider_id,
        command=provider_id,
        available=available,
        required=required,
        roles=roles,
        installed=True,
        auth_status="ready" if available else "unknown",
        selectable=selectable,
    )


def test_registry_preserves_strict_deliberation_provider_order() -> None:
    assert STRICT_DELIBERATION_PROVIDERS == ("codex", "deepseek", "claude")


def test_provider_ids_for_role_prepends_strict_providers_and_filters_by_role() -> None:
    doctor = AgentDoctorReport(
        status="ready",
        run_mode="full",
        commands={
            "codex": _status("codex", available=True, selectable=True, roles=["deliberation"], required=True),
            "deepseek": _status("deepseek", available=True, selectable=True, roles=["deliberation"], required=True),
            "claude": _status("claude", available=True, selectable=True, roles=["deliberation"], required=True),
            "kimicode": _status("kimicode", available=False, selectable=True, roles=["deliberation", "formula"]),
            "gemini": _status("gemini", available=False, selectable=True, roles=["deprecated"]),
        },
        active_provider_ids=["codex", "deepseek", "claude"],
        missing_required=[],
        missing_optional=[],
        unknown_required=[],
    )

    selected = agent_provider_ids_for_role(doctor, ["gemini", "kimicode", "codex"], "deliberation")

    assert selected == ["codex", "deepseek", "claude", "kimicode"]


def test_selectable_provider_ids_include_unknown_required_and_selectable_optional() -> None:
    doctor = AgentDoctorReport(
        status="degraded",
        run_mode="partial",
        commands={
            "codex": _status("codex", available=True, selectable=True, roles=["deliberation"], required=True),
            "deepseek": _status("deepseek", available=False, selectable=False, roles=["deliberation"], required=True),
            "claude": _status("claude", available=True, selectable=True, roles=["deliberation"], required=True),
            "mimo": _status("mimo", available=False, selectable=True, roles=["deliberation"]),
        },
        active_provider_ids=["codex", "claude"],
        missing_required=[],
        missing_optional=[],
        unknown_required=["deepseek"],
    )

    assert selectable_agent_provider_ids(doctor) == {"codex", "deepseek", "claude", "mimo"}
```

- [ ] **Step 2: Run tests to verify registry is missing**

Run:

```bash
python3 -m pytest tests/test_agent_registry.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.agents.registry'`.

- [ ] **Step 3: Add registry implementation**

Create `backend/app/agents/registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from backend.app.schemas import AgentDoctorReport

STRICT_DELIBERATION_PROVIDERS = ("codex", "deepseek", "claude")


@dataclass(frozen=True, slots=True)
class AgentCapability:
    provider_id: str
    role: str
    output_modes: frozenset[str]
    supports_streaming: bool = False
    supports_resume: bool = False
    supports_cancel: bool = False
    supports_artifacts: bool = False
    max_context_tokens: int | None = None


DEFAULT_AGENT_CAPABILITIES: tuple[AgentCapability, ...] = (
    AgentCapability("codex", "deliberation", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("codex", "formula", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("codex", "chair", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("deepseek", "deliberation", frozenset({"json"})),
    AgentCapability("deepseek", "formula", frozenset({"json"})),
    AgentCapability("deepseek", "critic", frozenset({"json"})),
    AgentCapability("claude", "deliberation", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("claude", "formula", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("claude", "critic", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("kimicode", "deliberation", frozenset({"json"})),
    AgentCapability("kimicode", "formula", frozenset({"json"})),
    AgentCapability("kimicode", "critic", frozenset({"json"})),
    AgentCapability("mimo", "deliberation", frozenset({"json"})),
    AgentCapability("mimo", "formula", frozenset({"json"})),
    AgentCapability("mimo", "critic", frozenset({"json"})),
    AgentCapability("langgraph-local", "workflow", frozenset({"json"}), supports_streaming=True, supports_resume=True, supports_cancel=True, supports_artifacts=True),
)


def selectable_agent_provider_ids(doctor: AgentDoctorReport) -> set[str]:
    return (
        set(doctor.active_provider_ids)
        | set(doctor.unknown_required)
        | {provider_id for provider_id, status in doctor.commands.items() if status.selectable}
    )


def agent_provider_ids_for_role(doctor: AgentDoctorReport, requested: list[str], role: str) -> list[str]:
    provider_role = "deliberation" if role == "post_review" else role
    normalized: list[str] = []
    for provider_id in STRICT_DELIBERATION_PROVIDERS:
        if provider_id not in normalized:
            normalized.append(provider_id)
    for provider_id in requested:
        if provider_id in normalized:
            continue
        status = doctor.commands.get(provider_id)
        if not status or not status.selectable:
            continue
        if provider_role not in status.roles:
            continue
        normalized.append(provider_id)
    return normalized
```

- [ ] **Step 4: Wire registry wrappers in `main.py`**

Modify imports in `backend/app/main.py`:

```python
from backend.app.agents.registry import (
    STRICT_DELIBERATION_PROVIDERS,
    agent_provider_ids_for_role,
    selectable_agent_provider_ids,
)
```

Remove the existing local `STRICT_DELIBERATION_PROVIDERS = ("codex", "deepseek", "claude")` assignment.

Replace the helper bodies at the bottom of `backend/app/main.py` with compatibility wrappers:

```python
def _selectable_agent_provider_ids(doctor: AgentDoctorReport) -> set[str]:
    return selectable_agent_provider_ids(doctor)


def _agent_provider_ids_for_role(doctor: AgentDoctorReport, requested: list[str], role: str) -> list[str]:
    return agent_provider_ids_for_role(doctor, requested, role)
```

- [ ] **Step 5: Run registry and deliberation API tests**

Run:

```bash
python3 -m pytest tests/test_agent_registry.py tests/test_deliberation_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit registry extraction**

Run:

```bash
git add backend/app/agents/registry.py backend/app/main.py tests/test_agent_registry.py
git commit -m "feat: add agent capability registry"
```

Expected: commit succeeds.

---

### Task 4: Code-Defined Deliberation Workflow

**Files:**
- Create: `backend/app/agents/adapters/legacy.py`
- Create: `backend/app/workflows/__init__.py`
- Create: `backend/app/workflows/deliberation.py`
- Modify: `backend/app/deliberation/orchestrator.py`
- Test: `tests/test_deliberation_workflow.py`
- Existing Test: `tests/test_deliberation_concurrency.py`
- Existing Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: `AgentRuntime.run_task(request)`, `AgentTaskRequest`, `AgentRuntimeFailure`.
- Produces: `DeliberationWorkflow.run(...) -> DeliberationRun`.
- Compatibility: `DeliberationOrchestrator(provider_runner=old_fake).run(...)` remains valid by wrapping old fakes in `LegacyProviderRunnerAdapter`.

- [ ] **Step 1: Write failing direct workflow tests**

Create `tests/test_deliberation_workflow.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify workflow module is missing**

Run:

```bash
python3 -m pytest tests/test_deliberation_workflow.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.workflows'`.

- [ ] **Step 3: Add legacy runner adapter**

Create `backend/app/agents/adapters/legacy.py`:

```python
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
            provider_id=result.provider_id,
            payload=result.payload,
            stdout=getattr(result, "stdout", ""),
            stderr=getattr(result, "stderr", ""),
            attempts=getattr(result, "attempts", 1),
        )
```

- [ ] **Step 4: Add deliberation workflow**

Create `backend/app/workflows/__init__.py`:

```python
"""Code-defined GrantAtlas workflows."""
```

Create `backend/app/workflows/deliberation.py` by moving the current orchestration behavior from `backend/app/deliberation/orchestrator.py` and replacing each provider call with `AgentTaskRequest`.

Use these imports:

```python
from __future__ import annotations

import asyncio
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

from backend.app.agents.adapters.cli import CliAgentAdapter, repair_suggestion_for_failure
from backend.app.agents.models import AgentRuntimeFailure, AgentTaskRequest
from backend.app.agents.runtime import AgentRuntime
from backend.app.deliberation.prompts import build_dossier, chair_prompt, opening_prompt, pair_prompt
from backend.app.schemas import (
    AgentFailure,
    DeliberationLogEntry,
    DeliberationRun,
    DeliberationStageResult,
    InventionBrief,
    PatentChunk,
    PatentStrategyBrief,
)
```

Add the workflow class and task helper:

```python
class DeliberationWorkflow:
    def __init__(self, agent_runtime: AgentRuntime | None = None) -> None:
        self.agent_runtime = agent_runtime or CliAgentAdapter()

    async def _run_agent_task(
        self,
        *,
        provider_id: str,
        prompt: str,
        workdir: Path,
        label: str,
        trace: bool,
        task_timeout_ms: int,
        log_callback: Callable[[DeliberationLogEntry], None] | None,
    ):
        return await self.agent_runtime.run_task(
            AgentTaskRequest(
                provider_id=provider_id,
                role="deliberation",
                prompt=prompt,
                workdir=workdir,
                label=label,
                trace=trace,
                timeout_ms=task_timeout_ms,
                log_callback=log_callback,
            )
        )
```

In `DeliberationWorkflow.run`, preserve the current `DeliberationOrchestrator.run` body with these replacements:

```python
opening_outcomes = await asyncio.gather(
    *(
        self._run_agent_task(
            provider_id=provider_id,
            prompt=opening_prompt(provider_id, dossier),
            workdir=run_dir,
            label=f"opening {provider_id}",
            trace=trace,
            task_timeout_ms=task_timeout_ms,
            log_callback=append_log,
        )
        for provider_id in providers
    ),
    return_exceptions=True,
)
```

```python
pair_outcomes = await asyncio.gather(
    *(
        self._run_agent_task(
            provider_id=coordinator_provider,
            prompt=pair_prompt(
                provider_a,
                provider_b,
                dossier,
                {provider_a: openings[provider_a], provider_b: openings[provider_b]},
            ),
            workdir=run_dir,
            label=f"pair {provider_a}-vs-{provider_b}",
            trace=trace,
            task_timeout_ms=task_timeout_ms,
            log_callback=append_log,
        )
        for provider_a, provider_b in pair_pairs
    ),
    return_exceptions=True,
)
```

```python
chair = await self._run_agent_task(
    provider_id=coordinator_provider,
    prompt=chair_prompt(dossier, openings, pair_results),
    workdir=run_dir,
    label="chair synthesis",
    trace=trace,
    task_timeout_ms=task_timeout_ms,
    log_callback=append_log,
)
```

Replace all `isinstance(outcome, ProviderFailure)` checks with:

```python
isinstance(outcome, AgentRuntimeFailure)
```

Replace all `except ProviderFailure as exc:` blocks with:

```python
except AgentRuntimeFailure as exc:
```

Move these helpers from the old orchestrator into `backend/app/workflows/deliberation.py` unchanged except for the failure type:

- `run_deliberation_sync`
- `_failure`
- `_failure_log`
- `_payload_summary`
- `_build_run`
- `_emit_update`
- `_run_mode`
- `_coordinator_provider`
- `_fallback_strategy`
- `_write_json`
- `_write_events`

- [ ] **Step 5: Replace orchestrator with compatibility wrapper**

Replace `backend/app/deliberation/orchestrator.py` with:

```python
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

    async def run(self, **kwargs: Any):
        return await DeliberationWorkflow(agent_runtime=self.agent_runtime).run(**kwargs)


def run_deliberation_sync(*args: Any, **kwargs: Any):
    provider_runner = kwargs.pop("provider_runner", None)
    agent_runtime = kwargs.pop("agent_runtime", None)
    orchestrator = DeliberationOrchestrator(provider_runner=provider_runner, agent_runtime=agent_runtime)
    return asyncio.run(orchestrator.run(**kwargs))
```

- [ ] **Step 6: Run workflow and existing deliberation tests**

Run:

```bash
python3 -m pytest tests/test_deliberation_workflow.py tests/test_deliberation_concurrency.py tests/test_agents.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit deliberation workflow migration**

Run:

```bash
git add backend/app/agents/adapters/legacy.py backend/app/workflows backend/app/deliberation/orchestrator.py tests/test_deliberation_workflow.py tests/test_deliberation_concurrency.py tests/test_agents.py
git commit -m "feat: run deliberation through agent runtime"
```

Expected: commit succeeds.

---

### Task 5: FastAPI Runtime Injection

**Files:**
- Modify: `backend/app/main.py`
- Modify: `tests/test_deliberation_api.py`
- Existing Test: `tests/test_runtime_controls.py`

**Interfaces:**
- Consumes: `agent_runtime` object with `run_task`.
- Produces: `create_app(..., agent_runtime: object | None = None)` and `_execute_deliberation(..., agent_runtime: object | None = None)`.
- Compatibility: existing `provider_runner` parameter remains valid for all current tests and the Kimi language polish endpoint.

- [ ] **Step 1: Add failing API test for runtime injection**

Append this test to `tests/test_deliberation_api.py`:

```python
def test_deliberation_api_accepts_agent_runtime_adapter(tmp_path):
    from backend.app.agents.adapters.fake import FakeAgentRuntime

    runtime = FakeAgentRuntime(
        task_payloads={
            "opening codex": {
                "stance": "codex stance",
                "claim_scope": ["method"],
                "risks": [],
                "recommendations": ["add embodiments"],
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
                "conflict_level": 0.1,
                "agreements": ["embodiments"],
                "disagreements": [],
                "resolved_recommendation": "add examples",
            },
            "pair deepseek-vs-claude": {
                "conflict_level": 0.3,
                "agreements": ["term alignment"],
                "disagreements": [],
                "resolved_recommendation": "align terms",
            },
            "chair synthesis": {
                "summary": "Runtime adapter synthesis.",
                "claim_strategy": ["method claim"],
                "description_strategy": ["add embodiments"],
                "risk_controls": ["avoid functional overbreadth"],
                "agent_consensus": "Runtime adapter consensus.",
            },
        }
    )
    client = TestClient(
        create_app(
            data_dir=tmp_path,
            llm_client=_minimal_llm(),
            agent_runtime=runtime,
            load_env_file=False,
        )
    )
    project_id = client.post(
        "/api/projects",
        json={"name": "runtime adapter project", "draft_text": "A defect detection method."},
    ).json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/deliberations",
        json={"providers": ["codex", "deepseek", "claude"], "trace": False},
    )

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["strategy_brief"]["summary"] == "Runtime adapter synthesis."
    assert [request.label for request in runtime.requests[:3]] == [
        "opening codex",
        "opening deepseek",
        "opening claude",
    ]
```

- [ ] **Step 2: Run test to verify `create_app` rejects `agent_runtime`**

Run:

```bash
python3 -m pytest tests/test_deliberation_api.py::test_deliberation_api_accepts_agent_runtime_adapter -q
```

Expected: FAIL with `TypeError: create_app() got an unexpected keyword argument 'agent_runtime'`.

- [ ] **Step 3: Add app state and execution wiring**

Modify `create_app` signature in `backend/app/main.py`:

```python
def create_app(
    data_dir: Path | None = None,
    llm_client: LLMClient | None = None,
    provider_runner: object | None = None,
    agent_runtime: object | None = None,
    prior_art_provider: object | None = None,
    research_search_provider: DeepResearchSearchProvider | None = None,
    load_env_file: bool = True,
) -> FastAPI:
```

Set app state after `app.state.provider_runner = provider_runner`:

```python
    app.state.agent_runtime = agent_runtime
```

In `create_deliberation`, add a local flag after `requested` is computed:

```python
        runtime_injected = app.state.provider_runner is not None or app.state.agent_runtime is not None
```

Replace `active_requested_count` with:

```python
        active_requested_count = (
            len(requested)
            if runtime_injected
            else len([provider for provider in requested if provider in available])
        )
```

Replace the missing-provider guard:

```python
        if app.state.provider_runner is None:
```

with:

```python
        if not runtime_injected:
```

Modify both `_execute_deliberation` calls inside `create_deliberation`:

```python
completed = _execute_deliberation(
    store=store,
    index=index,
    provider_runner=app.state.provider_runner,
    agent_runtime=app.state.agent_runtime,
    project=project,
    run=run,
    trace=payload.trace,
    task_timeout_ms=payload.task_timeout_ms or 180_000,
    run_timeout_ms=payload.run_timeout_ms,
)
```

```python
background_tasks.add_task(
    _execute_deliberation,
    store,
    index,
    app.state.provider_runner,
    app.state.agent_runtime,
    project,
    run,
    payload.trace,
    payload.task_timeout_ms or 180_000,
    payload.run_timeout_ms,
)
```

Modify both retry call paths the same way.

Modify `_execute_deliberation` signature:

```python
def _execute_deliberation(
    store: SQLiteStore,
    index: LocalVectorIndex,
    provider_runner: object | None,
    agent_runtime: object | None,
    project: ProjectRecord,
    run: DeliberationRun,
    trace: bool,
    task_timeout_ms: int,
    run_timeout_ms: int | None = None,
) -> DeliberationRun:
```

Modify orchestrator creation:

```python
        orchestrator = DeliberationOrchestrator(
            provider_runner=provider_runner,
            agent_runtime=agent_runtime,
        )
```

- [ ] **Step 4: Preserve provider-runner synchronous test behavior**

In `create_deliberation`, keep this branch condition unchanged:

```python
if app.state.provider_runner is not None:
```

Then extend it to also run synchronously when an injected runtime is supplied:

```python
if app.state.provider_runner is not None or app.state.agent_runtime is not None:
```

Apply the same condition to `retry_deliberation`.

- [ ] **Step 5: Run API and runtime-control tests**

Run:

```bash
python3 -m pytest tests/test_deliberation_api.py tests/test_runtime_controls.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit app runtime injection**

Run:

```bash
git add backend/app/main.py tests/test_deliberation_api.py
git commit -m "feat: inject agent runtime into deliberation api"
```

Expected: commit succeeds.

---

### Task 6: Optional LangGraph Workflow Adapter Shell

**Files:**
- Create: `backend/app/agents/adapters/langgraph.py`
- Test: `tests/test_agent_langgraph_adapter.py`

**Interfaces:**
- Consumes: `WorkflowRunRequest`, `WorkflowRunResult`, `AgentRuntimeFailure`.
- Produces: `LangGraphWorkflowAdapter.run_workflow(request)`.
- Constraint: importing the adapter must not require `langgraph` to be installed.

- [ ] **Step 1: Write failing no-network LangGraph adapter test**

Create `tests/test_agent_langgraph_adapter.py`:

```python
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
```

- [ ] **Step 2: Run test to verify adapter is missing**

Run:

```bash
python3 -m pytest tests/test_agent_langgraph_adapter.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.agents.adapters.langgraph'`.

- [ ] **Step 3: Add lazy LangGraph adapter shell**

Create `backend/app/agents/adapters/langgraph.py`:

```python
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
```

- [ ] **Step 4: Run LangGraph adapter test**

Run:

```bash
python3 -m pytest tests/test_agent_langgraph_adapter.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit LangGraph adapter shell**

Run:

```bash
git add backend/app/agents/adapters/langgraph.py tests/test_agent_langgraph_adapter.py
git commit -m "feat: add optional langgraph workflow adapter"
```

Expected: commit succeeds.

---

### Task 7: Final Parity Verification

**Files:**
- Modify only files from Tasks 1-6 if verification exposes a regression.

**Interfaces:**
- Consumes: all runtime, registry, adapter, workflow, and API changes.
- Produces: passing targeted regression suite and a final implementation commit only if fixes are needed.

- [ ] **Step 1: Run focused backend regression suite**

Run:

```bash
python3 -m pytest \
  tests/test_agent_runtime.py \
  tests/test_agent_runtime_cli.py \
  tests/test_agent_registry.py \
  tests/test_agent_langgraph_adapter.py \
  tests/test_agents.py \
  tests/test_deliberation_workflow.py \
  tests/test_deliberation_concurrency.py \
  tests/test_deliberation_api.py \
  tests/test_runtime_controls.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run full backend tests if the focused suite passes**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS. If failures appear outside agent runtime behavior, inspect whether they are caused by changed imports, app state, or provider selection before editing.

- [ ] **Step 3: Inspect git diff for accidental surface changes**

Run:

```bash
git diff --stat
git diff -- backend/app/main.py backend/app/deliberation backend/app/agents backend/app/workflows tests
```

Expected:

- No frontend, Tauri, export, storage migration, or packaging files changed.
- `backend/app/deliberation/providers.py` is a compatibility shim.
- `backend/app/deliberation/orchestrator.py` delegates to `backend/app/workflows/deliberation.py`.
- `backend/app/main.py` keeps old `provider_runner` behavior and adds `agent_runtime`.

- [ ] **Step 4: Commit verification fixes if any tracked files changed**

If Step 2 or Step 3 required fixes, run:

```bash
git add backend/app tests
git commit -m "fix: preserve agent runtime migration parity"
```

Expected: commit succeeds only when there are verification fixes to commit. If there are no fixes, do not create an empty commit.

## Self-Review Notes

- Spec coverage: runtime interface, CLI adapter, provider capabilities, code-defined deliberation workflow, unchanged API models, unchanged strict gates, optional LangGraph behavior, and fake adapter testing are covered.
- Out of scope for this implementation: Hermes and OMP concrete adapters, shared `agent_runs` storage migration, frontend changes, Tauri packaging, and user-editable workflow specs.
- Type consistency: runtime methods are async; legacy `run_json_task` remains async; `AgentRuntimeFailure` is the compatibility alias for old `ProviderFailure`; `AgentTaskResult` is the compatibility alias for old `ProviderTaskResult`.
