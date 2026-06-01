from __future__ import annotations

import asyncio
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from backend.app.deliberation.prompts import build_dossier, chair_prompt, opening_prompt, pair_prompt
from backend.app.deliberation.providers import AgentProviderRunner, ProviderFailure
from backend.app.schemas import (
    AgentFailure,
    DeliberationRun,
    DeliberationStageResult,
    InventionBrief,
    PatentChunk,
    PatentStrategyBrief,
)


class DeliberationOrchestrator:
    def __init__(self, provider_runner: Any | None = None) -> None:
        self.provider_runner = provider_runner or AgentProviderRunner()

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
    ) -> DeliberationRun:
        run_dir.mkdir(parents=True, exist_ok=True)
        events: list[str] = []
        failures: list[AgentFailure] = []
        stage_results: list[DeliberationStageResult] = []
        dossier = build_dossier(brief, context_chunks)
        openings: dict[str, dict] = {}

        for provider_id in providers:
            try:
                result = await self.provider_runner.run_json_task(
                    provider_id=provider_id,
                    prompt=opening_prompt(provider_id, dossier),
                    workdir=run_dir,
                    label=f"opening {provider_id}",
                    trace=trace,
                    task_timeout_ms=task_timeout_ms,
                )
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
            except ProviderFailure as exc:
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

        pair_results: list[dict] = []
        completed_providers = list(openings.keys())
        for provider_a, provider_b in combinations(completed_providers, 2):
            label = f"pair {provider_a}-vs-{provider_b}"
            try:
                result = await self.provider_runner.run_json_task(
                    provider_id="codex",
                    prompt=pair_prompt(provider_a, provider_b, dossier, {provider_a: openings[provider_a], provider_b: openings[provider_b]}),
                    workdir=run_dir,
                    label=label,
                    trace=trace,
                    task_timeout_ms=task_timeout_ms,
                )
                pair_payload = {"pair": [provider_a, provider_b], **result.payload}
                pair_results.append(pair_payload)
                stage_results.append(
                    DeliberationStageResult(
                        phase="pair",
                        provider_id="codex",
                        label=label,
                        payload=pair_payload,
                        status="completed",
                    )
                )
                events.append(f"pair completed: {provider_a} vs {provider_b}")
            except ProviderFailure as exc:
                failure = _failure("codex", "pair", exc)
                failures.append(failure)
                stage_results.append(
                    DeliberationStageResult(
                        phase="pair",
                        provider_id="codex",
                        label=label,
                        payload={"pair": [provider_a, provider_b]},
                        status="failed",
                        failure=failure,
                    )
                )
                events.append(f"pair failed: {provider_a} vs {provider_b} {exc.reason}")

        chair_payload: dict[str, Any]
        try:
            chair = await self.provider_runner.run_json_task(
                provider_id="codex",
                prompt=chair_prompt(dossier, openings, pair_results),
                workdir=run_dir,
                label="chair synthesis",
                trace=trace,
                task_timeout_ms=task_timeout_ms,
            )
            chair_payload = chair.payload
            events.append("chair synthesis completed")
        except ProviderFailure as exc:
            failure = _failure("codex", "chair", exc)
            failures.append(failure)
            chair_payload = _fallback_strategy(openings, pair_results)
            events.append(f"chair synthesis failed: {exc.reason}; fallback strategy generated")

        strategy_brief = PatentStrategyBrief(**chair_payload)
        stage_results.append(
            DeliberationStageResult(
                phase="chair",
                provider_id="codex",
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
            status="completed" if strategy_brief else "failed",
            providers=providers,
            run_mode=run_mode,
            trace=trace,
            run_dir=str(run_dir),
            stage_results=stage_results,
            strategy_brief=strategy_brief,
            failures=failures,
            events=events,
        )


def run_deliberation_sync(*args: Any, **kwargs: Any) -> DeliberationRun:
    return asyncio.run(DeliberationOrchestrator(*args, **kwargs).run)


def _failure(provider_id: str, phase: str, exc: ProviderFailure) -> AgentFailure:
    return AgentFailure(provider_id=provider_id, phase=phase, reason=exc.reason, message=str(exc))


def _run_mode(active_count: int) -> str:
    if active_count >= 3:
        return "full"
    if active_count == 2:
        return "partial"
    if active_count == 1:
        return "minimal"
    return "blocked"


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
