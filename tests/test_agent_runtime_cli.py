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


def test_cli_adapter_normalizes_timeout_provider_id_for_aliases(tmp_path: Path) -> None:
    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        raise AgentRuntimeFailure("timeout", "reasonix timed out", provider_id="reasonix")

    adapter = CliAgentAdapter(spawn_func=fake_spawn)

    with pytest.raises(AgentRuntimeFailure) as exc:
        asyncio.run(adapter.run_task(_request(tmp_path, provider_id="deepseek", label="opening deepseek")))

    assert exc.value.reason == "timeout"
    assert exc.value.provider_id == "deepseek"


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
