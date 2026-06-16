"""Concurrency tests for the deliberation orchestrator.

The opening and pair phases dispatch independent provider calls.  These
tests assert the orchestrator runs them concurrently (via ``asyncio.gather``)
rather than sequentially, and that failures from one call do not suppress
the results of its siblings.
"""

from __future__ import annotations

import asyncio
from itertools import combinations
from pathlib import Path

import pytest

from backend.app.deliberation.orchestrator import DeliberationOrchestrator
from backend.app.deliberation.providers import ProviderFailure, ProviderTaskResult
from backend.app.schemas import InventionBrief, PatentChunk


def _brief() -> InventionBrief:
    return InventionBrief(
        title="图像缺陷识别",
        technical_field="AI检测技术领域",
        technical_problem="人工检测效率低",
        innovation="神经网络识别缺陷",
        technical_solution="采集图像并检测",
        beneficial_effects=["效率提升"],
        protection_focus=["方法"],
    )


class _ConcurrencyTrackingRunner:
    """Records the high-water mark of simultaneously in-flight tasks.

    Each ``run_json_task`` call sleeps briefly so that, when the orchestrator
    dispatches several calls concurrently, they overlap and the in-flight
    counter climbs above 1.
    """

    def __init__(self, *, opening_payload: dict | None = None, fail_providers: tuple[str, ...] = ()) -> None:
        self._opening_payload = opening_payload or {
            "stance": "限定方法",
            "claim_scope": ["方法"],
            "risks": [],
            "recommendations": ["补充实施例"],
        }
        self._fail_providers = set(fail_providers)
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = asyncio.Lock()

    async def run_json_task(self, *, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        async with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.05)
            if provider_id in self._fail_providers and label.startswith("opening"):
                raise ProviderFailure("process_error", f"{label} failed", provider_id=provider_id)
            phase_payload = self._opening_payload if label.startswith("opening") else {
                "conflict_level": 0.3,
                "agreements": ["方法独权"],
                "disagreements": [],
                "resolved_recommendation": "保留方法独权",
            }
            if label.startswith("chair"):
                phase_payload = {
                    "summary": "三方一致。",
                    "claim_strategy": ["方法独权"],
                    "description_strategy": ["补充实施例"],
                    "risk_controls": [],
                    "agent_consensus": "三方一致。",
                }
            return ProviderTaskResult(
                provider_id=provider_id,
                payload=phase_payload,
                stdout="",
                stderr="",
                attempts=1,
            )
        finally:
            async with self._lock:
                self.in_flight -= 1


def test_opening_phase_runs_providers_concurrently(tmp_path: Path) -> None:
    providers = ["codex", "deepseek", "claude"]
    runner = _ConcurrencyTrackingRunner()
    orchestrator = DeliberationOrchestrator(provider_runner=runner)

    run = asyncio.run(_run_deliberation(orchestrator, tmp_path / "r1", providers))

    assert run.status == "completed"
    # Three independent openings dispatched together must overlap.
    assert runner.max_in_flight >= 2, "opening phase did not run concurrently"


async def _run_deliberation(orchestrator, run_dir, providers):
    return await orchestrator.run(
        run_id=run_dir.name,
        project_id="p1",
        brief=_brief(),
        context_chunks=[],
        providers=providers,
        run_dir=run_dir,
        trace=False,
        task_timeout_ms=60000,
    )


def test_pair_phase_runs_pairs_concurrently(tmp_path: Path) -> None:
    providers = ["codex", "deepseek", "claude"]
    runner = _ConcurrencyTrackingRunner()
    orchestrator = DeliberationOrchestrator(provider_runner=runner)

    run = asyncio.run(_run_deliberation(orchestrator, tmp_path / "r2", providers))

    assert run.status == "completed"
    pair_count = len(list(combinations(providers, 2)))
    assert pair_count == 3
    # The three pair comparisons are independent and should overlap.
    assert runner.max_in_flight >= 2, "pair phase did not run concurrently"


def test_opening_failure_still_completes_siblings(tmp_path: Path) -> None:
    providers = ["codex", "deepseek", "claude"]
    # deepseek fails its opening, but the run should still record the other
    # two openings and end as failed (not crash).
    runner = _ConcurrencyTrackingRunner(fail_providers=("deepseek",))
    orchestrator = DeliberationOrchestrator(provider_runner=runner)

    run = asyncio.run(_run_deliberation(orchestrator, tmp_path / "r3", providers))

    assert run.status == "failed"
    opening_results = [s for s in run.stage_results if s.phase == "opening"]
    completed = [s for s in opening_results if s.status == "completed"]
    failed = [s for s in opening_results if s.status == "failed"]
    assert len(completed) == 2, "sibling openings should still complete"
    assert len(failed) == 1
    assert failed[0].provider_id == "deepseek"
