import asyncio
import json
from pathlib import Path

import pytest

from backend.app.deliberation.doctor import inspect_agent_environment
from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.deliberation.providers import AgentProviderRunner, ProviderFailure
from backend.app.schemas import InventionBrief, PatentChunk, SectionType


def test_doctor_reports_full_partial_minimal_and_blocked_modes():
    full = inspect_agent_environment(lambda command: f"/bin/{command}")
    assert full.status == "ready"
    assert full.run_mode == "full"
    assert full.missing_required == []

    partial = inspect_agent_environment(lambda command: f"/bin/{command}" if command in {"codex", "gemini"} else "")
    assert partial.status == "degraded"
    assert partial.run_mode == "partial"
    assert partial.missing_optional == ["claude"]

    minimal = inspect_agent_environment(lambda command: "/bin/codex" if command == "codex" else "")
    assert minimal.status == "degraded"
    assert minimal.run_mode == "minimal"
    assert minimal.active_provider_ids == ["codex"]

    blocked = inspect_agent_environment(lambda command: "")
    assert blocked.status == "blocked"
    assert blocked.run_mode == "blocked"
    assert blocked.missing_required == ["codex"]


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


def test_orchestrator_runs_openings_pairs_and_chair_summary(tmp_path: Path):
    calls: list[tuple[str, str]] = []

    class FakeRunner:
        async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms):
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
