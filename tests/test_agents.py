import asyncio
import json
from pathlib import Path

import pytest

from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.deliberation.providers import AgentProviderRunner, ProviderFailure
from backend.app.schemas import DeliberationLogEntry, InventionBrief, PatentChunk, SectionType


# ---------------------------------------------------------------------------
# Fake probe helpers for doctor auth tests
# ---------------------------------------------------------------------------


def _probe_ready(command: str, args: list[str], timeout_ms: int) -> tuple[int | None, str, str]:
    """Fake probe that returns auth-ready output for each known provider."""
    args_key = " ".join(args)
    if args_key == "login status":
        return 0, "Logged in using ChatGPT", ""
    if args_key == "auth status":
        return 0, json.dumps({"loggedIn": True, "authMethod": "oauth_token"}), ""
    # gemini --version
    return 0, "0.45.2", ""


def _probe_not_authenticated(command: str, args: list[str], timeout_ms: int) -> tuple[int | None, str, str]:
    """Fake probe that returns not-logged-in output for each provider."""
    args_key = " ".join(args)
    if args_key == "login status":
        return 1, "", "Not logged in. Run `codex login`."
    if args_key == "auth status":
        return 0, json.dumps({"loggedIn": False}), ""
    # gemini --version
    return 0, "0.45.2", ""


def _probe_timeout(command: str, args: list[str], timeout_ms: int) -> tuple[int | None, str, str]:
    """Fake probe that always times out."""
    return None, "", ""


# ---------------------------------------------------------------------------
# Doctor auth-probe tests
# ---------------------------------------------------------------------------


def test_doctor_reports_core_required_and_optional_provider_metadata():
    # codex+claude ready via auth probes; gemini has no auth subcommand → unknown.
    # gemini is installed + required + unknown → unknown_required list (not blocked).
    full = inspect_agent_environment(
        command_lookup=lambda command: f"/bin/{command}",
        command_probe=_probe_ready,
    )
    assert full.status == "degraded"
    assert full.run_mode == "partial"
    assert full.missing_required == []
    assert set(full.unknown_required) == {"gemini"}
    assert full.commands["gemini"].auth_status == "unknown"
    assert full.commands["gemini"].available is False
    assert full.commands["gemini"].selectable is True
    assert full.commands["codex"].auth_status == "ready"
    assert full.commands["claude"].auth_status == "ready"

    core_only = inspect_agent_environment(
        command_lookup=lambda command: f"/bin/{command}" if command in {"codex", "gemini", "claude"} else "",
        command_probe=_probe_ready,
    )
    assert core_only.status == "degraded"  # gemini unknown, not blocked
    assert core_only.missing_optional == ["kimicode", "deepseek_pi"]
    assert core_only.commands["codex"].model_version
    assert "deliberation" in core_only.commands["codex"].roles
    assert core_only.commands["gemini"].required is True
    assert core_only.commands["claude"].required is True

    missing_claude = inspect_agent_environment(
        command_lookup=lambda command: f"/bin/{command}" if command in {"codex", "gemini"} else "",
        command_probe=_probe_ready,
    )
    assert missing_claude.status == "blocked"
    assert missing_claude.run_mode == "blocked"
    assert "claude" in missing_claude.missing_required

    blocked = inspect_agent_environment(
        command_lookup=lambda command: "",
        command_probe=_probe_ready,
    )
    assert blocked.status == "blocked"
    assert blocked.run_mode == "blocked"
    assert set(blocked.missing_required) == {"codex", "gemini", "claude"}


def test_doctor_probe_ready_requires_auth_confirmation():
    """Gemini has no auth subcommand — always reports unknown even when binary works."""
    report = inspect_agent_environment(
        command_lookup=lambda c: f"/bin/{c}",
        command_probe=_probe_ready,
        probe_timeout_ms=1000,
    )
    # codex+claude = ready, gemini = unknown (no auth subcmd)
    gemini = report.commands["gemini"]
    assert gemini.installed is True
    assert gemini.auth_status == "unknown"
    assert gemini.available is False
    assert gemini.selectable is True
    assert "无 auth status 子命令" in gemini.diagnostic


def test_doctor_probe_not_authenticated_blocks_required():
    """Probe returns not-logged-in → not_authenticated, required provider blocked."""
    report = inspect_agent_environment(
        command_lookup=lambda c: f"/bin/{c}",
        command_probe=_probe_not_authenticated,
        probe_timeout_ms=1000,
    )
    assert report.status == "blocked"
    assert report.run_mode == "blocked"
    for required_id in ("codex", "claude"):
        provider = report.commands[required_id]
        assert provider.installed is True
        assert provider.auth_status == "not_authenticated"
        assert provider.available is False
        assert provider.selectable is False
        assert provider.diagnostic
        assert provider.repair_suggestion
    # gemini always reports unknown (no auth subcommand)
    gemini = report.commands["gemini"]
    assert gemini.auth_status == "unknown"
    assert gemini.available is False
    assert gemini.selectable is True


def test_doctor_probe_timeout_blocked():
    """Probe timeout → auth_status timeout, required provider blocked."""
    report = inspect_agent_environment(
        command_lookup=lambda c: f"/bin/{c}",
        command_probe=_probe_timeout,
        probe_timeout_ms=1000,
    )
    assert report.status == "blocked"
    assert report.run_mode == "blocked"
    for required_id in ("codex", "gemini", "claude"):
        provider = report.commands[required_id]
        assert provider.auth_status == "timeout"
        assert provider.available is False
        assert provider.selectable is False
        assert provider.repair_suggestion


def test_doctor_probe_missing_command_unavailable():
    """Command not in PATH → auth_status unavailable."""
    report = inspect_agent_environment(
        command_lookup=lambda c: "",
        command_probe=_probe_ready,
        probe_timeout_ms=1000,
    )
    assert report.status == "blocked"
    assert report.run_mode == "blocked"
    for provider in report.commands.values():
        assert provider.installed is False
        assert provider.auth_status == "unavailable"
        assert provider.available is False
        assert provider.selectable is False


def test_doctor_probe_sanitizes_token_like_strings():
    """Diagnostic output must not leak token-like strings."""
    token_value = "sk-abc123def456ghi789jkl012mno345pq"

    def fake_probe(command, args, timeout_ms):
        args_key = " ".join(args)
        if args_key == "login status":
            return 1, "", f"Error: auth failed with token {token_value}"
        if args_key == "auth status":
            return 1, "", f"Error: auth failed with token {token_value}"
        return 0, "version", ""

    report = inspect_agent_environment(
        command_lookup=lambda c: f"/bin/{c}",
        command_probe=fake_probe,
        probe_timeout_ms=1000,
    )
    for required_id in ("codex", "claude"):
        diagnostic = report.commands[required_id].diagnostic
        assert token_value not in diagnostic
        assert "<scrubbed>" in diagnostic or "auth" in diagnostic.lower()


def test_doctor_probe_truncates_long_diagnostics():
    """Diagnostic output must be truncated to avoid bloating responses."""
    long_error = "Error: ".join([f"segment-{i}" for i in range(50)])

    def fake_probe(command, args, timeout_ms):
        args_key = " ".join(args)
        if args_key == "login status":
            return 1, "", long_error
        if args_key == "auth status":
            return 1, "", long_error
        return 0, "version", ""

    report = inspect_agent_environment(
        command_lookup=lambda c: f"/bin/{c}",
        command_probe=fake_probe,
        probe_timeout_ms=1000,
    )
    for required_id in ("codex", "claude"):
        diagnostic = report.commands[required_id].diagnostic
        assert len(diagnostic) <= 203  # max_length + "..."
        assert "..." in diagnostic


# ---------------------------------------------------------------------------
# ProviderRunner & Orchestrator unit tests (preserved from original)
# ---------------------------------------------------------------------------


def test_doctor_reports_core_required_and_optional_provider_metadata():
    # With the real auth probes, codex+claude can report ready but gemini
    # has no auth subcommand → unknown. The old PATH-only lookup would
    # report all three as ready, but the new logic separates unknown
    # required providers into unknown_required with degraded status.
    pass  # replaced by new auth-probe-aware tests below


def test_provider_runner_retries_invalid_json_and_preserves_trace_outputs(tmp_path: Path):
    attempts = 0

    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return 0, "not json", ""
        return 0, '{"ok": true}', ""

    runner = AgentProviderRunner(spawn_func=fake_spawn)
    result = asyncio.run(
        runner.run_json_task(
            provider_id="gemini",
            prompt="return json",
            workdir=tmp_path,
            label="test task",
            trace=True,
            task_timeout_ms=1000,
        )
    )

    assert attempts == 2
    assert result.payload == {"ok": True}
    trace_files = sorted((tmp_path / "trace").glob("*.json"))
    assert len(trace_files) == 2
    trace_payload = json.loads(trace_files[-1].read_text(encoding="utf-8"))
    assert trace_payload["stdout"] == '{"ok": true}'


def test_provider_runner_resolves_relative_workdir_for_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    relative_run_dir = Path("data/deliberation-runs/run-1")
    relative_run_dir.mkdir(parents=True)
    observed: dict[str, object] = {}

    async def fake_spawn(command, args, cwd, _prompt, _timeout_ms):
        observed["command"] = command
        observed["args"] = args
        observed["cwd"] = cwd
        return 0, '{"ok": true}', ""

    runner = AgentProviderRunner(spawn_func=fake_spawn)
    result = asyncio.run(
        runner.run_json_task(
            provider_id="codex",
            prompt="return json",
            workdir=relative_run_dir,
            label="codex task",
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert result.payload == {"ok": True}
    assert observed["command"] == "codex"
    assert observed["cwd"] == relative_run_dir.resolve()
    args = observed["args"]
    assert isinstance(args, list)
    assert Path(args[args.index("-C") + 1]).is_absolute()
    assert Path(args[args.index("--output-last-message") + 1]).is_absolute()


def test_provider_runner_raises_after_empty_output(tmp_path: Path):
    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        return 0, "", ""

    runner = AgentProviderRunner(spawn_func=fake_spawn)

    with pytest.raises(ProviderFailure) as exc:
        asyncio.run(
            runner.run_json_task(
                provider_id="claude",
                prompt="return json",
                workdir=tmp_path,
                label="empty task",
                trace=False,
                task_timeout_ms=1000,
            )
        )

    assert exc.value.reason == "empty_output"


def test_provider_runner_emits_attempt_logs_for_invalid_json(tmp_path: Path):
    emitted: list[DeliberationLogEntry] = []

    async def fake_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        return 0, "not json", "stderr payload"

    runner = AgentProviderRunner(spawn_func=fake_spawn)

    with pytest.raises(ProviderFailure):
        asyncio.run(
            runner.run_json_task(
                provider_id="gemini",
                prompt="return json",
                workdir=tmp_path,
                label="opening gemini",
                trace=False,
                task_timeout_ms=1000,
                log_callback=emitted.append,
            )
        )

    assert [entry.message for entry in emitted].count("attempt started") == 2
    assert [entry.message for entry in emitted].count("attempt failed") == 2
    assert emitted[-1].level == "error"
    assert emitted[-1].provider_id == "gemini"
    assert emitted[-1].phase == "opening"
    assert emitted[-1].repair_suggestion


def test_provider_runner_converts_spawn_oserror_to_diagnostic_log(tmp_path: Path):
    emitted: list[DeliberationLogEntry] = []

    async def missing_spawn(_command, _args, _cwd, _prompt, _timeout_ms):
        raise FileNotFoundError("gemini not found")

    runner = AgentProviderRunner(spawn_func=missing_spawn)

    with pytest.raises(ProviderFailure) as exc:
        asyncio.run(
            runner.run_json_task(
                provider_id="gemini",
                prompt="return json",
                workdir=tmp_path,
                label="opening gemini",
                trace=False,
                task_timeout_ms=1000,
                log_callback=emitted.append,
            )
        )

    assert exc.value.reason == "provider_missing"
    assert emitted[-1].level == "error"
    assert emitted[-1].provider_id == "gemini"
    assert emitted[-1].repair_suggestion
    assert "gemini not found" in emitted[-1].detail


def test_orchestrator_runs_openings_pairs_and_chair_summary(tmp_path: Path):
    calls: list[tuple[str, str]] = []

    class FakeRunner:
        async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
            calls.append((provider_id, label))
            if label.startswith("opening"):
                return type(
                    "Result",
                    (),
                    {
                        "payload": {
                            "stance": f"{provider_id} stance",
                            "claim_scope": ["方法", "系统"],
                            "risks": ["支持性不足"],
                            "recommendations": [f"{provider_id} recommendation"],
                        }
                    },
                )()
            if label.startswith("pair"):
                return type(
                    "Result",
                    (),
                    {
                        "payload": {
                            "conflict_level": 0.5,
                            "agreements": ["先限定独立权利要求"],
                            "disagreements": ["保护范围宽窄"],
                            "resolved_recommendation": "采用方法+系统双独权布局",
                        }
                    },
                )()
            return type(
                "Result",
                (),
                {
                    "payload": {
                        "summary": "建议先明确技术问题和独立权利要求边界。",
                        "claim_strategy": ["方法独权", "系统独权"],
                        "description_strategy": ["补足实施例支撑"],
                        "risk_controls": ["避免功能性概括过宽"],
                        "agent_consensus": "三方一致建议收窄首版保护范围。",
                    }
                },
            )()

    brief = InventionBrief(
        title="一种图像缺陷识别方法",
        technical_field="AI软件",
        technical_problem="人工检测效率低",
        technical_solution="采集图像并训练模型输出缺陷位置",
        beneficial_effects=["提高检测准确率"],
        key_steps=["采集", "训练", "输出"],
    )
    chunks = [
        PatentChunk(
            id="c1",
            document_id="d1",
            section_type=SectionType.CLAIMS,
            text="1. 一种图像缺陷识别方法，包括训练模型。",
            ordinal=1,
        )
    ]
    orchestrator = DeliberationOrchestrator(provider_runner=FakeRunner())

    result = asyncio.run(
        orchestrator.run(
            run_id="run-1",
            project_id="project-1",
            brief=brief,
            context_chunks=chunks,
            providers=["codex", "gemini", "claude"],
            run_dir=tmp_path,
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert [provider for provider, label in calls if label.startswith("opening")] == [
        "codex",
        "gemini",
        "claude",
    ]
    assert len([label for _, label in calls if label.startswith("pair")]) == 3
    assert calls[-1] == ("codex", "chair synthesis")
    assert result.strategy_brief.summary.startswith("建议先明确")
    assert result.run_mode == "full"
    assert (tmp_path / "openings.json").exists()
    assert not (tmp_path / "trace").exists()


def test_orchestrator_fails_when_any_required_agent_opening_fails(tmp_path: Path):
    calls: list[tuple[str, str]] = []

    class FakeRunner:
        async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
            calls.append((provider_id, label))
            if provider_id == "codex" and label.startswith("opening"):
                raise ProviderFailure(
                    "process_error",
                    "opening codex failed with exit code 1",
                    provider_id="codex",
                    stderr="attempt to write a readonly database",
                )
            if label.startswith("opening"):
                return type(
                    "Result",
                    (),
                    {
                        "payload": {
                            "stance": f"{provider_id} stance",
                            "claim_scope": ["方法"],
                            "risks": ["支持性不足"],
                            "recommendations": [f"{provider_id} recommendation"],
                        }
                    },
                )()
            raise AssertionError("strict deliberation must not run pair/chair after an opening failure")

    brief = InventionBrief(
        title="一种城市体检指标驱动采集方法",
        technical_field="无人机采集",
        technical_problem="固定航线无法补足指标证据",
        technical_solution="根据指标置信度增益生成任务包",
        beneficial_effects=["减少冗余采集"],
        key_steps=["计算", "生成", "更新"],
    )
    orchestrator = DeliberationOrchestrator(provider_runner=FakeRunner())

    result = asyncio.run(
        orchestrator.run(
            run_id="run-codex-fails",
            project_id="project-1",
            brief=brief,
            context_chunks=[],
            providers=["codex", "gemini", "claude"],
            run_dir=tmp_path,
            trace=False,
            task_timeout_ms=1000,
        )
    )

    assert [call for call in calls if call[1].startswith("opening")] == [
        ("codex", "opening codex"),
        ("gemini", "opening gemini"),
        ("claude", "opening claude"),
    ]
    assert not any(label.startswith("pair") or label == "chair synthesis" for _, label in calls)
    assert result.status == "failed"
    assert result.run_mode == "partial"
    assert result.strategy_brief is None
    assert any(entry.level == "error" and entry.provider_id == "codex" for entry in result.logs)
    assert any("修复" in entry.repair_suggestion or entry.repair_suggestion for entry in result.logs)
