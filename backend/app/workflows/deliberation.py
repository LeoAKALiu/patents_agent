from __future__ import annotations

import asyncio
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

from backend.app.agents.adapters.cli import CliAgentAdapter, repair_suggestion_for_failure
from backend.app.agents.adapters.legacy import LegacyProviderRunnerAdapter
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

    async def run(
        self,
        *,
        run_id: str,
        project_id: str,
        brief: InventionBrief,
        context_chunks: list[PatentChunk],
        providers: list[str],
        run_dir: Path,
        trace: bool,
        task_timeout_ms: int,
        on_update: Callable[[DeliberationRun], None] | None = None,
    ) -> DeliberationRun:
        run_dir.mkdir(parents=True, exist_ok=True)
        events: list[str] = []
        failures: list[AgentFailure] = []
        stage_results: list[DeliberationStageResult] = []
        logs: list[DeliberationLogEntry] = []
        dossier = build_dossier(brief, context_chunks)
        openings: dict[str, dict] = {}

        def append_log(entry: DeliberationLogEntry) -> None:
            logs.append(entry)
            _emit_update(
                on_update,
                run_id=run_id,
                project_id=project_id,
                status="running",
                providers=providers,
                run_mode=_run_mode(len(openings)),
                trace=trace,
                run_dir=run_dir,
                stage_results=stage_results,
                strategy_brief=None,
                failures=failures,
                events=events,
                logs=logs,
            )

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
        for provider_id, outcome in zip(providers, opening_outcomes):
            if isinstance(outcome, AgentRuntimeFailure):
                exc = outcome
                failure = _failure(provider_id, "opening", exc)
                failures.append(failure)
                stage_results.append(
                    DeliberationStageResult(
                        phase="opening",
                        provider_id=provider_id,
                        label=f"opening {provider_id}",
                        payload={},
                        status="failed",
                        failure=failure,
                    )
                )
                events.append(f"opening failed: {provider_id} {exc.reason}")
                append_log(_failure_log(provider_id, "opening", exc))
                continue
            result = outcome
            openings[provider_id] = result.payload
            stage_results.append(
                DeliberationStageResult(
                    phase="opening",
                    provider_id=provider_id,
                    label=f"opening {provider_id}",
                    payload=result.payload,
                    status="completed",
                )
            )
            events.append(f"opening completed: {provider_id}")
            append_log(
                DeliberationLogEntry(
                    level="info",
                    phase="opening",
                    provider_id=provider_id,
                    message="opening completed",
                    detail=_payload_summary(result.payload),
                )
            )

        if failures:
            _write_json(run_dir / "openings.json", openings)
            _write_json(run_dir / "pair_results.json", [])
            _write_events(run_dir / "events.jsonl", events)
            return _build_run(
                run_id=run_id,
                project_id=project_id,
                status="failed",
                providers=providers,
                run_mode=_run_mode(len(openings)),
                trace=trace,
                run_dir=run_dir,
                stage_results=stage_results,
                strategy_brief=None,
                failures=failures,
                events=events,
                logs=logs,
            )

        pair_results: list[dict] = []
        completed_providers = list(openings.keys())
        coordinator_provider = _coordinator_provider(completed_providers)
        pair_pairs = list(combinations(completed_providers, 2))
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
        for (provider_a, provider_b), outcome in zip(pair_pairs, pair_outcomes):
            label = f"pair {provider_a}-vs-{provider_b}"
            if isinstance(outcome, AgentRuntimeFailure):
                exc = outcome
                failure = _failure(coordinator_provider, "pair", exc)
                failures.append(failure)
                stage_results.append(
                    DeliberationStageResult(
                        phase="pair",
                        provider_id=coordinator_provider,
                        label=label,
                        payload={"pair": [provider_a, provider_b]},
                        status="failed",
                        failure=failure,
                    )
                )
                events.append(f"pair failed: {provider_a} vs {provider_b} {exc.reason}")
                append_log(_failure_log(coordinator_provider, "pair", exc))
                continue
            result = outcome
            pair_payload = {"pair": [provider_a, provider_b], **result.payload}
            pair_results.append(pair_payload)
            stage_results.append(
                DeliberationStageResult(
                    phase="pair",
                    provider_id=coordinator_provider,
                    label=label,
                    payload=pair_payload,
                    status="completed",
                )
            )
            events.append(f"pair completed: {provider_a} vs {provider_b}")
            append_log(
                DeliberationLogEntry(
                    level="info",
                    phase="pair",
                    provider_id=coordinator_provider,
                    message=f"pair completed: {provider_a} vs {provider_b}",
                    detail=_payload_summary(result.payload),
                )
            )

        if failures:
            _write_json(run_dir / "openings.json", openings)
            _write_json(run_dir / "pair_results.json", pair_results)
            _write_events(run_dir / "events.jsonl", events)
            return _build_run(
                run_id=run_id,
                project_id=project_id,
                status="failed",
                providers=providers,
                run_mode=_run_mode(len(completed_providers)),
                trace=trace,
                run_dir=run_dir,
                stage_results=stage_results,
                strategy_brief=None,
                failures=failures,
                events=events,
                logs=logs,
            )

        try:
            chair = await self._run_agent_task(
                provider_id=coordinator_provider,
                prompt=chair_prompt(dossier, openings, pair_results),
                workdir=run_dir,
                label="chair synthesis",
                trace=trace,
                task_timeout_ms=task_timeout_ms,
                log_callback=append_log,
            )
            chair_payload = chair.payload
            events.append("chair synthesis completed")
            append_log(
                DeliberationLogEntry(
                    level="info",
                    phase="chair",
                    provider_id=coordinator_provider,
                    message="chair synthesis completed",
                    detail=_payload_summary(chair.payload),
                )
            )
        except AgentRuntimeFailure as exc:
            failure = _failure(coordinator_provider, "chair", exc)
            failures.append(failure)
            events.append(f"chair synthesis failed: {exc.reason}")
            append_log(_failure_log(coordinator_provider, "chair", exc))
            _write_json(run_dir / "openings.json", openings)
            _write_json(run_dir / "pair_results.json", pair_results)
            _write_events(run_dir / "events.jsonl", events)
            return _build_run(
                run_id=run_id,
                project_id=project_id,
                status="failed",
                providers=providers,
                run_mode=_run_mode(len(completed_providers)),
                trace=trace,
                run_dir=run_dir,
                stage_results=stage_results,
                strategy_brief=None,
                failures=failures,
                events=events,
                logs=logs,
            )

        strategy_brief = PatentStrategyBrief(**chair_payload)
        stage_results.append(
            DeliberationStageResult(
                phase="chair",
                provider_id=coordinator_provider,
                label="chair synthesis",
                payload=strategy_brief.model_dump(mode="json"),
                status="completed" if not any(f.phase == "chair" for f in failures) else "degraded",
            )
        )

        _write_json(run_dir / "openings.json", openings)
        _write_json(run_dir / "pair_results.json", pair_results)
        _write_json(run_dir / "strategy_brief.json", strategy_brief.model_dump(mode="json"))
        _write_events(run_dir / "events.jsonl", events)

        run_mode = _run_mode(len(completed_providers))
        return DeliberationRun(
            id=run_id,
            project_id=project_id,
            status="completed",
            providers=providers,
            run_mode=run_mode,
            trace=trace,
            run_dir=str(run_dir),
            stage_results=stage_results,
            strategy_brief=strategy_brief,
            failures=failures,
            events=events,
            logs=logs,
        )


def run_deliberation_sync(*args: Any, **kwargs: Any) -> DeliberationRun:
    provider_runner = kwargs.pop("provider_runner", None)
    agent_runtime = kwargs.pop("agent_runtime", None)
    remaining_args = list(args)
    if remaining_args and provider_runner is None:
        provider_runner = remaining_args.pop(0)
    if remaining_args:
        raise TypeError("run_deliberation_sync accepts at most one positional argument: provider_runner")
    if agent_runtime is None:
        if provider_runner is not None and hasattr(provider_runner, "run_task"):
            agent_runtime = provider_runner
        elif provider_runner is not None:
            agent_runtime = LegacyProviderRunnerAdapter(provider_runner)
    return asyncio.run(DeliberationWorkflow(agent_runtime=agent_runtime).run(**kwargs))


def _failure(provider_id: str, phase: str, exc: AgentRuntimeFailure) -> AgentFailure:
    return AgentFailure(provider_id=provider_id, phase=phase, reason=exc.reason, message=str(exc))


def _failure_log(provider_id: str, phase: str, exc: AgentRuntimeFailure) -> DeliberationLogEntry:
    detail_parts = [str(exc)]
    if exc.stderr:
        detail_parts.append(f"stderr: {exc.stderr.strip()[:1200]}")
    if exc.stdout:
        detail_parts.append(f"stdout: {exc.stdout.strip()[:1200]}")
    return DeliberationLogEntry(
        level="error",
        phase=phase,
        provider_id=provider_id,
        message=f"{phase} failed: {exc.reason}",
        detail="\n".join(detail_parts),
        repair_suggestion=repair_suggestion_for_failure(exc.reason, provider_id),
    )


def _payload_summary(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    return text if len(text) <= 1200 else text[:1200] + "...[truncated]"


def _build_run(
    *,
    run_id: str,
    project_id: str,
    status: str,
    providers: list[str],
    run_mode: str,
    trace: bool,
    run_dir: Path,
    stage_results: list[DeliberationStageResult],
    strategy_brief: PatentStrategyBrief | None,
    failures: list[AgentFailure],
    events: list[str],
    logs: list[DeliberationLogEntry],
) -> DeliberationRun:
    return DeliberationRun(
        id=run_id,
        project_id=project_id,
        status=status,
        providers=providers,
        run_mode=run_mode,
        trace=trace,
        run_dir=str(run_dir),
        stage_results=stage_results,
        strategy_brief=strategy_brief,
        failures=failures,
        events=events,
        logs=logs,
    )


def _emit_update(callback: Callable[[DeliberationRun], None] | None, **kwargs: Any) -> None:
    if callback is None:
        return
    callback(_build_run(**kwargs))


def _run_mode(active_count: int) -> str:
    if active_count >= 3:
        return "full"
    if active_count == 2:
        return "partial"
    if active_count == 1:
        return "minimal"
    return "blocked"


def _coordinator_provider(completed_providers: list[str]) -> str:
    if "codex" in completed_providers:
        return "codex"
    return completed_providers[0] if completed_providers else "codex"


def _fallback_strategy(openings: dict[str, dict], pair_results: list[dict]) -> dict[str, Any]:
    recommendations: list[str] = []
    risks: list[str] = []
    for opening in openings.values():
        recommendations.extend(opening.get("recommendations", []))
        risks.extend(opening.get("risks", []))
    return {
        "summary": "主席汇总失败，已基于可用 agent 立论生成保守策略。",
        "claim_strategy": recommendations[:4] or ["先限定独立权利要求的输入、处理步骤和输出结果"],
        "description_strategy": ["补足每项权利要求对应实施例"],
        "risk_controls": risks[:4] or ["避免纯功能性概括"],
        "agent_consensus": "；".join(item.get("resolved_recommendation", "") for item in pair_results if item.get("resolved_recommendation")),
        "disclosure_summary": None,
        "patent_point_summary": None,
        "prior_art_differences": None,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_events(path: Path, events: list[str]) -> None:
    path.write_text("".join(json.dumps({"event": event}, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
