from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.llm import FakeLLMClient
from backend.app.main import _execute_deliberation, create_app
from backend.app.schemas import DeliberationRun, PostDraftReviewRun
from flow_driver import FlowDriver, FlowState


@dataclass(frozen=True)
class TraceAction:
    name: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class AdversarialTrace:
    seed: int
    actions: list[TraceAction]
    final_state: FlowState
    action_gate_deltas: list[dict[str, Any]] | None = None

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "seed": self.seed,
            "actions": [asdict(action) for action in self.actions],
            "action_gate_deltas": self.action_gate_deltas or [],
            "final_state": asdict(self.final_state),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path


def run_adversarial_trace(
    *,
    seed: int,
    data_dir: Path,
    action_count: int,
    action_names: tuple[str, ...] | None = None,
    force_ready: bool = False,
) -> AdversarialTrace:
    rng = random.Random(seed)
    driver = _new_driver(data_dir, seed)
    actions: list[TraceAction] = []
    action_gate_deltas: list[dict[str, Any]] = []
    for name in action_names or ():
        _run_and_record_action(driver, actions, action_gate_deltas, name, rng=rng, payload=None)
    for _index in range(action_count):
        name = rng.choice(_RANDOM_ACTION_NAMES)
        _run_and_record_action(driver, actions, action_gate_deltas, name, rng=rng, payload=None)
    if force_ready:
        for name in ("intake", "quality", "compile", "pass_review"):
            _run_and_record_action(driver, actions, action_gate_deltas, name, rng=rng, payload=None)
    return AdversarialTrace(
        seed=seed,
        actions=actions,
        final_state=driver.state(),
        action_gate_deltas=action_gate_deltas,
    )


def replay_adversarial_trace(path: Path, *, data_dir: Path) -> AdversarialTrace:
    payload = json.loads(path.read_text(encoding="utf-8"))
    seed = int(payload["seed"])
    actions = [
        TraceAction(name=str(entry["name"]), payload=dict(entry.get("payload") or {}))
        for entry in payload.get("actions") or []
    ]
    return replay_adversarial_actions(seed=seed, actions=actions, data_dir=data_dir)


def replay_adversarial_actions(
    *,
    seed: int,
    actions: list[TraceAction],
    data_dir: Path,
) -> AdversarialTrace:
    driver = _new_driver(data_dir, seed)
    action_gate_deltas: list[dict[str, Any]] = []
    replayed_actions: list[TraceAction] = []
    for action in actions:
        _run_and_record_action(
            driver,
            replayed_actions,
            action_gate_deltas,
            action.name,
            rng=random.Random(seed),
            payload=action.payload,
        )
    return AdversarialTrace(
        seed=seed,
        actions=replayed_actions,
        final_state=driver.state(),
        action_gate_deltas=action_gate_deltas,
    )


def shrink_adversarial_actions(
    actions: list[TraceAction],
    reproduces: Callable[[list[TraceAction]], bool],
) -> list[TraceAction]:
    minimized = list(actions)
    changed = True
    while changed:
        changed = False
        for index in range(len(minimized)):
            candidate = [action for candidate_index, action in enumerate(minimized) if candidate_index != index]
            if not candidate:
                continue
            if reproduces(candidate):
                minimized = candidate
                changed = True
                break
    return minimized


def write_failure_triage(
    trace_path: Path,
    *,
    output_dir: Path,
    failure_message: str,
    reproduces: Callable[[list[TraceAction]], bool],
) -> Path:
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    seed = int(payload["seed"])
    original_actions = [
        TraceAction(name=str(entry["name"]), payload=dict(entry.get("payload") or {}))
        for entry in payload.get("actions") or []
    ]
    action_gate_deltas = list(payload.get("action_gate_deltas") or [])
    minimized_actions = shrink_adversarial_actions(original_actions, reproduces)
    output_dir.mkdir(parents=True, exist_ok=True)
    minimized_trace_path = output_dir / f"trace-{seed}-minimized.json"
    final_state = dict(payload.get("final_state") or {})
    removed_actions = _removed_actions(original_actions, minimized_actions)
    minimized_gate_deltas, removed_gate_deltas = _partition_action_gate_deltas(
        original_actions,
        action_gate_deltas,
        minimized_actions,
    )
    _write_trace_payload(
        minimized_trace_path,
        seed=seed,
        actions=minimized_actions,
        final_state=final_state,
        action_gate_deltas=minimized_gate_deltas,
    )
    summary = {
        "seed": seed,
        "failure_message": failure_message,
        "original_trace": str(trace_path),
        "minimized_trace": str(minimized_trace_path),
        "original_action_count": len(original_actions),
        "minimized_action_count": len(minimized_actions),
        "original_action_names": [action.name for action in original_actions],
        "minimized_action_names": [action.name for action in minimized_actions],
        "minimized_actions": [asdict(action) for action in minimized_actions],
        "removed_action_names": [action.name for action in removed_actions],
        "original_action_category_counts": _action_category_counts(original_actions),
        "minimized_action_category_counts": _action_category_counts(minimized_actions),
        "removed_action_category_counts": _action_category_counts(removed_actions),
        "action_gate_deltas": action_gate_deltas,
        "minimized_action_gate_deltas": minimized_gate_deltas,
        "removed_action_gate_deltas": removed_gate_deltas,
        "final_state": final_state,
        "failure_tags": _failure_tags(final_state),
        "replay_hint": f"replay_adversarial_trace(Path({str(minimized_trace_path)!r}), data_dir=...)",
        "replay_command": _replay_command(minimized_trace_path, seed=seed),
    }
    summary_path = output_dir / f"trace-{seed}-triage.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_failure_triage_markdown(summary_path.with_suffix(".md"), summary)
    return summary_path


def _write_failure_triage_markdown(path: Path, summary: dict[str, Any]) -> Path:
    lines = [
        "# Adversarial Failure Triage",
        "",
        f"- Seed: {summary['seed']}",
        f"- Failure: {summary['failure_message']}",
        f"- Tags: {', '.join(summary.get('failure_tags') or [])}",
        f"- Original actions: {summary['original_action_count']}",
        f"- Minimized actions: {summary['minimized_action_count']}",
        f"- Export allowed: {summary.get('final_state', {}).get('export_allowed')}",
        f"- Minimized trace: `{summary['minimized_trace']}`",
        "",
        "## Final Gates",
        "",
        "| Gate | State |",
        "| --- | --- |",
    ]
    for gate, state in sorted((summary.get("final_state", {}).get("gates") or {}).items()):
        lines.append(f"| {_md_cell(gate)} | {_md_cell(state)} |")

    lines.extend(
        [
            "",
            "## Minimized Actions",
            "",
            "| Index | Action | Category | Payload |",
            "| --- | --- | --- | --- |",
        ]
    )
    minimized_deltas = summary.get("minimized_action_gate_deltas") or []
    for index, action in enumerate(summary.get("minimized_actions") or []):
        delta = minimized_deltas[index] if index < len(minimized_deltas) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    _md_cell(action.get("name", "")),
                    _md_cell(delta.get("category", "")),
                    _md_cell(_json_inline(action.get("payload") or {})),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Gate Deltas",
            "",
            "| Index | Action | Changed Gates | Export Allowed |",
            "| --- | --- | --- | --- |",
        ]
    )
    for delta in minimized_deltas:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(delta.get("index", "")),
                    _md_cell(delta.get("name", "")),
                    _md_cell(_changed_gates_text(delta.get("changed_gates") or {})),
                    _md_cell(_export_allowed_delta_text(delta.get("export_allowed") or {})),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Removed Actions",
            "",
            ", ".join(summary.get("removed_action_names") or []) or "None",
            "",
            "## Replay",
            "",
            "```bash",
            summary["replay_command"],
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _changed_gates_text(changed_gates: dict[str, Any]) -> str:
    if not changed_gates:
        return "none"
    return ", ".join(
        f"{gate}: {change.get('before')} -> {change.get('after')}"
        for gate, change in sorted(changed_gates.items())
        if isinstance(change, dict)
    )


def _export_allowed_delta_text(export_allowed: dict[str, Any]) -> str:
    if not export_allowed:
        return ""
    return f"{export_allowed.get('before')} -> {export_allowed.get('after')}"


def _json_inline(value: Any) -> str:
    if value in ({}, [], None):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _removed_actions(original_actions: list[TraceAction], minimized_actions: list[TraceAction]) -> list[TraceAction]:
    removed: list[TraceAction] = []
    minimized_index = 0
    for action in original_actions:
        if minimized_index < len(minimized_actions) and action == minimized_actions[minimized_index]:
            minimized_index += 1
            continue
        removed.append(action)
    return removed


def _partition_action_gate_deltas(
    original_actions: list[TraceAction],
    action_gate_deltas: list[dict[str, Any]],
    minimized_actions: list[TraceAction],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    minimized: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    minimized_index = 0
    for index, action in enumerate(original_actions):
        delta = action_gate_deltas[index] if index < len(action_gate_deltas) else {}
        if minimized_index < len(minimized_actions) and action == minimized_actions[minimized_index]:
            minimized.append(delta)
            minimized_index += 1
            continue
        removed.append(delta)
    return minimized, removed


def _action_category_counts(actions: list[TraceAction]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        category = _action_category(action.name)
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _action_category(name: str) -> str:
    if name in {"intake", "disclosure", "formula"}:
        return "setup"
    if name in {"filing", "worksheet", "completion", "quality"}:
        return "quality_gate"
    if name in {"compile", "pass_review", "block_review"}:
        return "official_gate"
    if name in {"readiness", "export"}:
        return "export_probe"
    if name == "edit":
        return "mutation"
    if name.startswith("generated_") and name.endswith("_honesty"):
        return "honesty_probe"
    if "cancel" in name or name.endswith("_retry"):
        return "runtime_control"
    return "other"


def _replay_command(minimized_trace_path: Path, *, seed: int) -> str:
    replay_dir = Path("/tmp") / f"patentagent-adversarial-replay-{seed}"
    return "\n".join(
        [
            "PYTHONPATH=tests python - <<'PY'",
            "from pathlib import Path",
            "from adversarial_flow_harness import replay_adversarial_trace",
            f"trace = replay_adversarial_trace(Path({str(minimized_trace_path)!r}), data_dir=Path({str(replay_dir)!r}))",
            "print(trace.final_state)",
            "PY",
        ]
    )


def _failure_tags(final_state: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    if final_state.get("export_allowed") is False:
        tags.append("export_blocked")
    gates = final_state.get("gates") or {}
    for gate in ("quality", "official_compile", "post_draft_review"):
        state = gates.get(gate)
        if state and state != "current":
            tags.append(f"{gate}_{state}")
    return tags


def _write_trace_payload(
    path: Path,
    *,
    seed: int,
    actions: list[TraceAction],
    final_state: dict[str, Any],
    action_gate_deltas: list[dict[str, Any]] | None = None,
) -> Path:
    path.write_text(
        json.dumps(
            {
                "seed": seed,
                "actions": [asdict(action) for action in actions],
                "action_gate_deltas": action_gate_deltas or [],
                "final_state": final_state,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _new_driver(data_dir: Path, seed: int) -> FlowDriver:
    client = TestClient(
        create_app(
            data_dir=data_dir,
            llm_client=_review_llm(),
            prior_art_provider=StaticPriorArtProvider(),
            load_env_file=False,
        )
    )
    driver = FlowDriver(client)
    driver.create_project(
        f"对抗流程 {seed}",
        "一种输入数据处理方法，解决处理结果不可追溯的问题。",
        patent_type="invention",
    )
    return driver


def _run_named_action(
    driver: FlowDriver,
    name: str,
    *,
    rng: random.Random,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if name not in _ACTIONS:
        raise ValueError(f"Unknown adversarial action: {name}")
    return _ACTIONS[name](driver, rng, payload or {})


def _run_and_record_action(
    driver: FlowDriver,
    actions: list[TraceAction],
    action_gate_deltas: list[dict[str, Any]],
    name: str,
    *,
    rng: random.Random,
    payload: dict[str, Any] | None,
) -> None:
    before = driver.state()
    action_payload = _run_named_action(driver, name, rng=rng, payload=payload)
    action = TraceAction(name=name, payload=action_payload)
    actions.append(action)
    _assert_export_readiness_consistency(driver)
    after = driver.state()
    action_gate_deltas.append(
        _action_gate_delta(
            index=len(actions) - 1,
            name=name,
            before=before,
            after=after,
        )
    )


def _action_gate_delta(*, index: int, name: str, before: FlowState, after: FlowState) -> dict[str, Any]:
    changed_gates = {
        gate: {"before": before.gates.get(gate), "after": after.gates.get(gate)}
        for gate in sorted(set(before.gates) | set(after.gates))
        if before.gates.get(gate) != after.gates.get(gate)
    }
    return {
        "index": index,
        "name": name,
        "category": _action_category(name),
        "gates_before": before.gates,
        "gates_after": after.gates,
        "changed_gates": changed_gates,
        "export_allowed": {
            "before": before.export_allowed,
            "after": after.export_allowed,
        },
    }


def _assert_export_readiness_consistency(driver: FlowDriver) -> None:
    readiness = driver.client.get(f"/api/projects/{driver.project_id}/export-readiness")
    assert readiness.status_code == 200
    export = driver.client.get(f"/api/projects/{driver.project_id}/official-export.md")
    assert export.status_code == (200 if readiness.json()["export_allowed"] else 409)


def _intake(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    if not driver.client.get(f"/api/projects/{driver.project_id}").json().get("package"):
        driver.intake_external_draft(_external_draft_text())
    return {}


def _disclosure(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    response = driver.client.post(f"/api/projects/{driver.project_id}/disclosures", json={})
    if response.status_code == 200:
        return {"status": response.json().get("status"), "run_id": response.json().get("id")}
    return {"status_code": response.status_code}


def _formula(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    response = driver.client.post(f"/api/projects/{driver.project_id}/formula-runs", json={})
    if response.status_code == 200:
        return {"status": response.json().get("status"), "run_id": response.json().get("id")}
    return {"status_code": response.status_code}


def _filing(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.post(f"/api/projects/{driver.project_id}/filing-readiness")
    return {}


def _worksheet(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.post(f"/api/projects/{driver.project_id}/claim-defense-worksheets")
    return {}


def _completion(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.post(f"/api/projects/{driver.project_id}/completion-runs")
    return {}


def _quality(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    _filing(driver, _rng, {})
    _worksheet(driver, _rng, {})
    _completion(driver, _rng, {})
    return {}


def _compile(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.post(f"/api/projects/{driver.project_id}/official-compile-runs", json={})
    return {}


def _pass_review(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.app.state.llm = _review_llm(export_allowed=True)
    driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    return {}


def _block_review(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.app.state.llm = _review_llm(export_allowed=False)
    driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews", json={})
    return {}


def _deliberation_queued_cancel(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _payload_run_id(payload, rng, key="run_id", prefix="queued-delib")
    run = DeliberationRun(
        id=run_id,
        project_id=driver.project_id,
        status="queued",
        providers=["codex"],
        run_mode="minimal",
    )
    driver.client.app.state.store.create_deliberation_run(run)

    cancelled = driver.client.post(f"/api/projects/{driver.project_id}/deliberations/{run.id}/cancel").json()
    return {
        "run_id": run.id,
        "status": cancelled.get("status"),
        "cancel_requested": cancelled.get("cancel_requested"),
        "failure_reason": _first_failure_reason(cancelled),
    }


def _deliberation_cancel_exception(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _payload_run_id(payload, rng, key="run_id", prefix="running-delib-cancel")
    store = driver.client.app.state.store
    project = store.get_project(driver.project_id)
    if project is None:
        return {"run_id": run_id, "status": "missing_project"}
    run_dir = driver.client.app.state.settings.data_dir / "deliberation-runs" / driver.project_id / run_id
    run = DeliberationRun(
        id=run_id,
        project_id=driver.project_id,
        status="queued",
        providers=["codex", "deepseek", "kimicode"],
        run_mode="full",
        run_dir=str(run_dir),
    )
    store.create_deliberation_run(run)
    runner = _CancelThenFailDeliberationProviderRunner()
    runner.store = store
    runner.project_id = driver.project_id
    runner.run_id = run_id
    completed = _execute_deliberation(
        store=store,
        index=driver.client.app.state.index,
        provider_runner=runner,
        project=project,
        run=run,
        trace=False,
        task_timeout_ms=30_000,
        run_timeout_ms=30_000,
    )
    payload = completed.model_dump(mode="json")
    provider_error_leaked = _provider_error_leaked(payload)
    return {
        "run_id": completed.id,
        "status": completed.status,
        "cancel_requested": completed.cancel_requested,
        "failure_reason": _first_failure_reason(payload),
        "provider_error_leaked": provider_error_leaked,
    }


def _post_review_cancel_retry(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    _intake(driver, rng, {})
    _quality(driver, rng, {})
    compile_run = driver.compile_official()
    driver.client.app.state.llm = _review_llm(export_allowed=True)

    run_id = _payload_run_id(payload, rng, key="cancelled_run_id", prefix="queued-post-review")
    queued = PostDraftReviewRun(
        id=run_id,
        project_id=driver.project_id,
        status="queued",
        providers=["codex", "deepseek", "claude"],
        draft_package_hash=compile_run["source_draft_hash"],
        official_compile_run_id=compile_run["id"],
        official_package_hash=compile_run["official_package_hash"],
    )
    driver.client.app.state.store.create_post_draft_review_run(queued)

    cancelled = driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews/{queued.id}/cancel").json()
    retry = driver.client.post(f"/api/projects/{driver.project_id}/post-draft-reviews/{queued.id}/retry").json()
    return {
        "cancelled_run_id": queued.id,
        "cancel_status": cancelled.get("status"),
        "cancel_requested": cancelled.get("cancel_requested"),
        "cancel_failure_reason": _first_failure_reason(cancelled),
        "retry_run_id": retry.get("id"),
        "retry_status": retry.get("status"),
        "retry_of": retry.get("retry_of"),
        "export_allowed": retry.get("export_allowed"),
    }


def _formula_cancel_exception(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    _intake(driver, rng, {})
    version = int(payload.get("version") if "version" in payload else rng.randrange(10_000))
    formula_text = (
        f"本发明涉及数据处理技术领域。版本 {version} 根据置信度增益、贡献矩阵和后验概率生成补采任务包。"
    )
    driver.client.app.state.store.update_project(driver.project_id, {"draft_text": formula_text})
    driver.edit_source_draft(formula_text)
    llm = _CancelThenFailFormulaLLM(_review_llm(export_allowed=True).responses)
    llm.store = driver.client.app.state.store
    llm.project_id = driver.project_id
    driver.client.app.state.llm = llm

    response = driver.client.post(f"/api/projects/{driver.project_id}/formula-runs", json={"run_timeout_ms": 30_000})
    if response.status_code != 200:
        return {"version": version, "status_code": response.status_code}
    run = response.json()
    provider_error_leaked = any("Connection error" in event for event in run.get("events") or []) or any(
        "Connection error" in failure.get("message", "")
        for failure in run.get("failure_details") or []
        if isinstance(failure, dict)
    )
    return {
        "version": version,
        "run_id": run.get("id"),
        "status": run.get("status"),
        "cancel_requested": run.get("cancel_requested"),
        "failure_reason": _first_failure_reason(run),
        "provider_error_leaked": provider_error_leaked,
    }


def _generated_evidence_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_inline_evidence_llm(),
        project_name_prefix="证据污染隔离项目",
    )


def _generated_chinese_evidence_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_chinese_evidence_llm(),
        project_name_prefix="中文证据污染隔离项目",
    )


def _generated_url_evidence_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_url_evidence_llm(),
        project_name_prefix="URL证据污染隔离项目",
    )


def _generated_bracketed_citation_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_bracketed_citation_llm(),
        project_name_prefix="括号证据引用隔离项目",
    )


def _generated_parenthetical_citation_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_parenthetical_citation_llm(),
        project_name_prefix="括号来源引用隔离项目",
    )


def _generated_xml_tag_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_xml_tag_llm(),
        project_name_prefix="XML证据标签隔离项目",
    )


def _generated_html_comment_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_comment_llm(),
        project_name_prefix="HTML注释证据隔离项目",
    )


def _generated_html_attribute_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_attribute_llm(),
        project_name_prefix="HTML属性证据隔离项目",
    )


def _generated_html_meta_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_meta_llm(),
        project_name_prefix="HTML元信息证据隔离项目",
    )


def _generated_markdown_footnote_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_footnote_llm(),
        project_name_prefix="Markdown脚注证据隔离项目",
    )


def _generated_markdown_reference_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_reference_llm(),
        project_name_prefix="Markdown引用定义证据隔离项目",
    )


def _generated_markdown_table_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_table_llm(),
        project_name_prefix="Markdown表格证据隔离项目",
    )


def _generated_markdown_list_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_list_llm(),
        project_name_prefix="Markdown列表证据隔离项目",
    )


def _generated_markdown_blockquote_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_blockquote_llm(),
        project_name_prefix="Markdown引用块证据隔离项目",
    )


def _generated_markdown_link_title_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_link_title_llm(),
        project_name_prefix="Markdown链接标题证据隔离项目",
    )


def _generated_markdown_image_alt_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_markdown_image_alt_llm(),
        project_name_prefix="Markdown图片替代文本证据隔离项目",
    )


def _generated_html_image_attribute_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_image_attribute_llm(),
        project_name_prefix="HTML图片属性证据隔离项目",
    )


def _generated_html_accessible_attribute_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_accessible_attribute_llm(),
        project_name_prefix="HTML可访问属性证据隔离项目",
    )


def _generated_html_visible_text_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_visible_text_llm(),
        project_name_prefix="HTML可见证据文本隔离项目",
    )


def _generated_html_caption_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_caption_llm(),
        project_name_prefix="HTML图表标题证据隔离项目",
    )


def _generated_svg_title_desc_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_svg_title_desc_llm(),
        project_name_prefix="SVG标题描述证据隔离项目",
    )


def _generated_svg_text_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_svg_text_llm(),
        project_name_prefix="SVG可见文本证据隔离项目",
    )


def _generated_html_style_tag_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_style_tag_llm(),
        project_name_prefix="HTML样式证据隔离项目",
    )


def _generated_html_inline_style_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_inline_style_llm(),
        project_name_prefix="HTML内联样式证据隔离项目",
    )


def _generated_html_entity_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_entity_llm(),
        project_name_prefix="HTML转义证据标签隔离项目",
    )


def _generated_yaml_front_matter_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_yaml_front_matter_llm(),
        project_name_prefix="YAML证据头信息隔离项目",
    )


def _generated_csv_metadata_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_csv_metadata_llm(),
        project_name_prefix="CSV证据元数据隔离项目",
    )


def _generated_toml_front_matter_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_toml_front_matter_llm(),
        project_name_prefix="TOML证据头信息隔离项目",
    )


def _generated_ini_section_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_ini_section_llm(),
        project_name_prefix="INI证据分节隔离项目",
    )


def _generated_html_json_ld_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_html_json_ld_llm(),
        project_name_prefix="JSONLD证据脚本隔离项目",
    )


def _generated_fenced_json_metadata_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_fenced_json_metadata_llm(),
        project_name_prefix="代码围栏JSON证据隔离项目",
    )


def _generated_asciidoc_attribute_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_asciidoc_attribute_llm(),
        project_name_prefix="AsciiDoc属性证据隔离项目",
    )


def _generated_latex_command_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_latex_command_llm(),
        project_name_prefix="LaTeX命令证据隔离项目",
    )


def _generated_bibtex_entry_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_bibtex_entry_llm(),
        project_name_prefix="BibTeX条目证据隔离项目",
    )


def _generated_rst_directive_honesty(
    driver: FlowDriver, rng: random.Random, payload: dict[str, Any]
) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_rst_directive_llm(),
        project_name_prefix="RST指令证据隔离项目",
    )


def _generated_json_wrapper_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_json_wrapper_llm(),
        project_name_prefix="JSON包装污染隔离项目",
    )


def _generated_source_footer_honesty(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    return _generated_evidence_honesty_with_llm(
        driver,
        rng,
        payload,
        llm=_generated_source_footer_llm(),
        project_name_prefix="来源脚注污染隔离项目",
    )


def _generated_evidence_honesty_with_llm(
    driver: FlowDriver,
    rng: random.Random,
    payload: dict[str, Any],
    *,
    llm: FakeLLMClient,
    project_name_prefix: str,
) -> dict[str, Any]:
    original_project_id = driver.project_id
    original_llm = driver.client.app.state.llm
    project_name = str(payload.get("project_name") or f"{project_name_prefix} {rng.randrange(1_000_000):06d}")
    try:
        project = driver.create_project(
            project_name,
            "一种声学视觉融合巡检结构，包括声学采集模块、视觉复检模块和状态记录模块。",
            patent_type="utility_model",
        )
        isolated_project_id = str(project["id"])
        driver.client.app.state.llm = llm
        generated = driver.client.post(f"/api/projects/{isolated_project_id}/generate", json={}).json()
        compile_run = driver.client.post(f"/api/projects/{isolated_project_id}/official-compile-runs", json={}).json()
        export_response = driver.client.get(f"/api/projects/{isolated_project_id}/official-export.md")
        return {
            "project_name": project_name,
            "project_id": isolated_project_id,
            "generate_status": generated.get("status") or "completed",
            "compile_status": compile_run.get("status"),
            "blocked_patterns": sorted({item.get("pattern", "") for item in compile_run.get("blocked_items") or []}),
            "export_status_code": export_response.status_code,
        }
    finally:
        driver.project_id = original_project_id
        driver.client.app.state.llm = original_llm


def _edit(driver: FlowDriver, rng: random.Random, payload: dict[str, Any]) -> dict[str, Any]:
    if not driver.client.get(f"/api/projects/{driver.project_id}").json().get("package"):
        return {}
    version = int(payload.get("version") if "version" in payload else rng.randrange(10_000))
    driver.edit_source_draft(f"本发明涉及数据处理技术领域。对抗编辑版本 {version}。")
    return {"version": version}


def _export(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.get(f"/api/projects/{driver.project_id}/official-export.md")
    return {}


def _readiness(driver: FlowDriver, _rng: random.Random, _payload: dict[str, Any]) -> dict[str, Any]:
    driver.client.get(f"/api/projects/{driver.project_id}/export-readiness")
    return {}


_ACTIONS: dict[str, Callable[[FlowDriver, random.Random, dict[str, Any]], dict[str, Any]]] = {
    "disclosure": _disclosure,
    "intake": _intake,
    "formula": _formula,
    "filing": _filing,
    "worksheet": _worksheet,
    "completion": _completion,
    "quality": _quality,
    "compile": _compile,
    "pass_review": _pass_review,
    "block_review": _block_review,
    "deliberation_queued_cancel": _deliberation_queued_cancel,
    "deliberation_cancel_exception": _deliberation_cancel_exception,
    "post_review_cancel_retry": _post_review_cancel_retry,
    "formula_cancel_exception": _formula_cancel_exception,
    "generated_evidence_honesty": _generated_evidence_honesty,
    "generated_chinese_evidence_honesty": _generated_chinese_evidence_honesty,
    "generated_url_evidence_honesty": _generated_url_evidence_honesty,
    "generated_bracketed_citation_honesty": _generated_bracketed_citation_honesty,
    "generated_parenthetical_citation_honesty": _generated_parenthetical_citation_honesty,
    "generated_xml_tag_honesty": _generated_xml_tag_honesty,
    "generated_html_comment_honesty": _generated_html_comment_honesty,
    "generated_html_attribute_honesty": _generated_html_attribute_honesty,
    "generated_html_meta_honesty": _generated_html_meta_honesty,
    "generated_markdown_footnote_honesty": _generated_markdown_footnote_honesty,
    "generated_markdown_reference_honesty": _generated_markdown_reference_honesty,
    "generated_markdown_table_honesty": _generated_markdown_table_honesty,
    "generated_markdown_list_honesty": _generated_markdown_list_honesty,
    "generated_markdown_blockquote_honesty": _generated_markdown_blockquote_honesty,
    "generated_markdown_link_title_honesty": _generated_markdown_link_title_honesty,
    "generated_markdown_image_alt_honesty": _generated_markdown_image_alt_honesty,
    "generated_html_image_attribute_honesty": _generated_html_image_attribute_honesty,
    "generated_html_accessible_attribute_honesty": _generated_html_accessible_attribute_honesty,
    "generated_html_visible_text_honesty": _generated_html_visible_text_honesty,
    "generated_html_caption_honesty": _generated_html_caption_honesty,
    "generated_svg_title_desc_honesty": _generated_svg_title_desc_honesty,
    "generated_svg_text_honesty": _generated_svg_text_honesty,
    "generated_html_style_tag_honesty": _generated_html_style_tag_honesty,
    "generated_html_inline_style_honesty": _generated_html_inline_style_honesty,
    "generated_html_entity_honesty": _generated_html_entity_honesty,
    "generated_yaml_front_matter_honesty": _generated_yaml_front_matter_honesty,
    "generated_csv_metadata_honesty": _generated_csv_metadata_honesty,
    "generated_toml_front_matter_honesty": _generated_toml_front_matter_honesty,
    "generated_ini_section_honesty": _generated_ini_section_honesty,
    "generated_html_json_ld_honesty": _generated_html_json_ld_honesty,
    "generated_fenced_json_metadata_honesty": _generated_fenced_json_metadata_honesty,
    "generated_asciidoc_attribute_honesty": _generated_asciidoc_attribute_honesty,
    "generated_latex_command_honesty": _generated_latex_command_honesty,
    "generated_bibtex_entry_honesty": _generated_bibtex_entry_honesty,
    "generated_rst_directive_honesty": _generated_rst_directive_honesty,
    "generated_json_wrapper_honesty": _generated_json_wrapper_honesty,
    "generated_source_footer_honesty": _generated_source_footer_honesty,
    "edit": _edit,
    "export": _export,
    "readiness": _readiness,
}
_RANDOM_ACTION_NAMES = tuple(_ACTIONS)


def _payload_run_id(payload: dict[str, Any], rng: random.Random, *, key: str, prefix: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return f"{prefix}-{rng.randrange(1_000_000):06d}"


def _first_failure_reason(payload: dict[str, Any]) -> str:
    failures = payload.get("failure_details") or []
    if isinstance(failures, list) and failures and isinstance(failures[0], dict):
        return str(failures[0].get("reason") or "")
    return ""


def _provider_error_leaked(payload: dict[str, Any]) -> bool:
    needles = ("Connection error", "object has no attribute")
    event_text = "\n".join(str(event) for event in payload.get("events") or [])
    failure_text = "\n".join(
        str(failure.get("message") or failure)
        for failure in payload.get("failure_details") or []
        if isinstance(failure, dict)
    )
    return any(needle in event_text or needle in failure_text for needle in needles)


def _external_draft_text() -> str:
    return """
发明名称
一种输入数据处理方法
摘要
本发明公开一种输入数据处理方法。
权利要求书
1. 一种输入数据处理方法，其特征在于，包括接收输入数据并输出处理结果。
说明书
本发明涉及数据处理技术领域。在一个实施例中，系统接收输入数据并输出处理结果。
附图说明
图1为输入数据处理方法流程图。
""".strip()


def _review_llm(*, export_allowed: bool = True) -> FakeLLMClient:
    role_status = "passed" if export_allowed else "blocked"
    blocking_issues = [] if export_allowed else ["对抗流程注入的阻断会审。"]
    chair_status = "passed" if export_allowed else "blocked"
    return FakeLLMClient(
        {
            "disclosure_scan": json.dumps(
                {
                    "summary": "输入数据处理项目",
                    "materials_summary": "无补充材料",
                    "technical_keywords": ["输入数据", "处理结果"],
                    "implementation_gaps": [],
                },
                ensure_ascii=False,
            ),
            "patent_points": json.dumps(
                {
                    "candidates": [
                        {
                            "id": "p1",
                            "title": "输入数据处理方法",
                            "technical_problem": "处理结果不可追溯。",
                            "innovation": "记录输入数据与处理结果的映射关系。",
                            "technical_solution": "接收输入数据，生成处理结果并记录映射关系。",
                            "beneficial_effects": ["提升处理结果可追溯性"],
                            "protection_focus": ["映射关系记录"],
                            "grantability_score": 0.72,
                            "rationale": "链条完整。",
                        }
                    ],
                    "selected_candidate_id": "p1",
                },
                ensure_ascii=False,
            ),
            "prior_art_terms": json.dumps(["输入数据 处理结果 映射"], ensure_ascii=False),
            "prior_art_relevance": json.dumps(
                {
                    "prior_art_differences": "未检索到完全相同的映射回链流程。",
                    "hits": [],
                },
                ensure_ascii=False,
            ),
            "disclosure_body": "技术方案正文：接收输入数据，生成处理结果并记录映射关系。",
            "disclosure_mermaid": "flowchart TD\nA[输入数据] --> B[处理结果]",
            "disclosure_image_prompt": "黑白线稿。",
            "disclosure_self_check": "[]",
            "core_formula": json.dumps(
                {
                    "summary": "以映射完整度评价处理结果追溯性。",
                    "formula_blocks": [
                        {
                            "id": "F1",
                            "name": "映射完整度",
                            "latex": "S=m/n",
                            "purpose": "衡量输入输出映射覆盖率",
                            "claim_hook": "映射关系记录",
                        }
                    ],
                    "variable_definitions": [
                        {"symbol": "S", "meaning": "映射完整度", "unit": ""},
                        {"symbol": "m", "meaning": "已记录映射数量", "unit": "条"},
                        {"symbol": "n", "meaning": "处理结果数量", "unit": "条"},
                    ],
                    "derivation_notes": ["由已记录映射数量与结果数量之比得到。"],
                    "claim_hooks": ["根据映射完整度触发复核"],
                    "description_insert": "映射完整度 S=m/n。",
                    "latex_markdown": "# 核心公式\n\nS=m/n",
                },
                ensure_ascii=False,
            ),
            "post_draft_claims_reviewer": _role_response("claims_reviewer", role_status, blocking_issues),
            "post_draft_spec_cleaner": _role_response("spec_cleaner", role_status, blocking_issues),
            "post_draft_technical_hardness": _role_response("technical_hardness", role_status, blocking_issues),
            "post_draft_chair_synthesis": json.dumps(
                {
                    "status": chair_status,
                    "export_allowed": export_allowed,
                    "blocking_issues": blocking_issues,
                    "contamination_hits": [],
                    "claim_1_rewrite": "",
                    "system_claim_rewrite": "",
                    "abstract_rewrite": "",
                    "description_rewrite_tasks": [],
                    "official_safe_patches": [],
                    "attorney_memo": [],
                    "next_actions": [],
                },
                ensure_ascii=False,
            ),
        }
    )


def _generated_inline_evidence_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "并根据source_id=CN222222A确定模块连接关系。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "该方案的内部支撑为source_label=实验记录.md，material_id=material-1。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_chinese_evidence_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                "证据编号：EV-ACOUSTIC-001\n"
                "材料编号：material-acoustic-1"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                "来源标签：实验记录.md\n"
                "引用来源：[CN111111A](https://example.test/patent/CN111111A)"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_url_evidence_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中校准参数来自[内部实验报告](https://internal.example/reports/acoustic-1.pdf)。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "补充材料参见 https://internal.example/materials/acoustic-source.docx。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_bracketed_citation_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中校准参数依据[evidence:EV-ACOUSTIC-001]确定。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器按照融合置信度执行复检【来源：实验记录.md】。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_parenthetical_citation_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值依据融合控制器确定（来源：实验记录.md）。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器按照融合置信度执行复检 (source: lab-note-001)。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_xml_tag_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "<source id=\"CN111111A\">内部对比文件</source>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "<evidence ref=\"EV-ACOUSTIC-001\">实验记录</evidence>用于确定声学阈值。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_comment_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
                "<!-- source: lab-note-001 -->"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "<!-- 证据：EV-ACOUSTIC-001 -->控制器根据声学阈值触发视觉复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_attribute_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "<span data-source=\"lab-note-001\">声学阈值</span>由控制器确定。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "<section evidence-ref=\"EV-ACOUSTIC-001\">控制器根据声学阈值触发视觉复检。</section>"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_meta_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                '<meta name="source" content="lab-note-001">声学阈值由控制器确定。'
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                '<meta property="evidence-ref" content="EV-ACOUSTIC-001">控制器根据声学阈值触发视觉复检。'
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_footnote_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值由控制器确定。[^source]\n\n"
                "[^source]: 来源：实验记录.md"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器按照融合置信度执行复检。[^1]\n\n"
                "[^1]: source: lab-note-001"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_reference_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值由控制器确定。\n\n"
                "[source]: internal-acoustic-test-record.md"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器按照融合置信度执行复检。\n\n"
                "[证据]: EV-ACOUSTIC-001"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_table_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值由控制器确定。\n\n"
                "| 字段 | 值 |\n"
                "| source | lab-note-001 |\n"
                "| evidence | EV-ACOUSTIC-001 |"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器按照融合置信度执行复检。\n\n"
                "| 字段 | 值 |\n"
                "| 证据 | 实验记录.md |"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_list_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                "- evidence: EV-ACOUSTIC-001\n"
                "- source: lab-note-001"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                "* 证据：EV-ACOUSTIC-002\n"
                "* 来源：实验记录.md"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_blockquote_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                "> evidence: EV-ACOUSTIC-001\n"
                "> source: lab-note-001"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                "> 证据：EV-ACOUSTIC-002\n"
                "> 来源：实验记录.md"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_link_title_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                '其中声学阈值依据[实验记录](lab-note-001 "evidence: EV-ACOUSTIC-001")确定。'
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                '控制器依据[采集日志](material-log "证据：EV-ACOUSTIC-002")执行复检。'
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": '图1为声学视觉融合巡检结构示意图。![结构示意](figure-1.png "source: lab-note-002")',
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_markdown_image_alt_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "并输出![evidence: EV-ACOUSTIC-001](threshold-map.png)。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据![证据：EV-ACOUSTIC-002](collection-log.png)执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。![source: lab-note-002](figure-1.png)",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_image_attribute_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                '<img src="threshold-map.png" alt="evidence: EV-ACOUSTIC-001" />。'
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                '控制器依据<img src="collection-log.png" title="证据：EV-ACOUSTIC-002" />执行复检。'
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": '图1为声学视觉融合巡检结构示意图。<img src="figure-1.png" alt="source: lab-note-002" />',
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_accessible_attribute_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                '<abbr title="evidence: EV-ACOUSTIC-001">声学阈值</abbr>由控制器确定。'
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                '<span aria-label="证据：EV-ACOUSTIC-002">控制器</span>执行复检。'
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": '图1为声学视觉融合巡检结构示意图。<a href="#fig1" title="source: lab-note-002">图1</a>',
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_visible_text_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值由控制器确定<sup>evidence: EV-ACOUSTIC-001</sup>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据<span>证据：EV-ACOUSTIC-002</span>执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。<small>source: lab-note-002</small>",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_caption_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "并生成状态摘要<figcaption>evidence: EV-ACOUSTIC-001</figcaption>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据<caption>证据：EV-ACOUSTIC-002</caption>执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。<figcaption>source: lab-note-002</figcaption>",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_svg_title_desc_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "并生成<svg><title>evidence: EV-ACOUSTIC-001</title></svg>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据<svg><desc>证据：EV-ACOUSTIC-002</desc></svg>执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。<svg><title>source: lab-note-002</title></svg>",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_svg_text_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "并生成<svg><text>evidence: EV-ACOUSTIC-001</text></svg>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据<svg><tspan>证据：EV-ACOUSTIC-002</tspan></svg>执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。<svg><text>source: lab-note-002</text></svg>",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_style_tag_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "<style>/* evidence: EV-ACOUSTIC-001 */ .threshold { color: #111; }</style>。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "<style>.review::after { content: '证据：EV-ACOUSTIC-002'; }</style>执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。<style>/* source: lab-note-002 */</style>",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_inline_style_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                '<span style="--evidence: EV-ACOUSTIC-001;">声学阈值</span>由控制器确定。'
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                '<span style="content: \'证据：EV-ACOUSTIC-002\';">控制器</span>执行复检。'
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": '图1为声学视觉融合巡检结构示意图。<span style="--source: lab-note-002;">图1</span>',
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_entity_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                "其中声学阈值由控制器确定"
                "&lt;evidence ref=&quot;EV-ACOUSTIC-001&quot;&gt;实验记录&lt;/evidence&gt;。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                "控制器依据&lt;source&gt;lab-note-001&lt;/source&gt;执行复检。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_yaml_front_matter_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "---\n"
                "evidence:\n"
                "  - EV-ACOUSTIC-001\n"
                "---\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                "---\n"
                "证据：\n"
                "  - 实验记录.md\n"
                "---\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_csv_metadata_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "evidence_id,source_label\n"
                "EV-ACOUSTIC-001,lab-note-001\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                "证据编号,来源标签\n"
                "EV-ACOUSTIC-002,实验记录.md\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_toml_front_matter_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "+++\n"
                'evidence = ["EV-ACOUSTIC-001"]\n'
                "+++\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                "+++\n"
                '证据 = ["实验记录.md"]\n'
                "+++\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_ini_section_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "[evidence]\n"
                "id = EV-ACOUSTIC-001\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                "[证据]\n"
                "编号 = EV-ACOUSTIC-002\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_html_json_ld_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                '<script type="application/ld+json">\n'
                '{"evidence": "EV-ACOUSTIC-001", "material": "lab-note-001"}\n'
                "</script>\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                '<script type="application/ld+json">\n'
                '{"证据": "EV-ACOUSTIC-002", "来源": "实验记录.md"}\n'
                "</script>\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_fenced_json_metadata_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "```json\n"
                '{"evidence_id": "EV-ACOUSTIC-001", "source_label": "lab-note-001"}\n'
                "```\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                "```json\n"
                '{"证据编号": "EV-ACOUSTIC-002", "来源标签": "实验记录.md"}\n'
                "```\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_asciidoc_attribute_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                ":evidence: EV-ACOUSTIC-001\n"
                ":source-label: lab-note-001\n"
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"
            ),
            "description": (
                ":证据: EV-ACOUSTIC-002\n"
                ":来源标签: 实验记录.md\n"
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_latex_command_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块，"
                r"其中声学阈值由控制器确定\cite{source=lab-note-001}。"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块；"
                r"控制器按照融合置信度执行复检\footnote{证据: EV-ACOUSTIC-002}。"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_bibtex_entry_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                "@misc{acoustic-source,\n"
                "  note = {source: lab-note-001}\n"
                "}"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                "@article{acoustic-evidence,\n"
                "  evidence = {EV-ACOUSTIC-002}\n"
                "}"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_rst_directive_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                ".. source:: lab-note-001"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                ".. evidence:: EV-ACOUSTIC-002"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_json_wrapper_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": '{"claims": "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。"}',
            "description": '{"description": {"technical_field": "本实用新型涉及巡检结构技术领域。"}}',
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


def _generated_source_footer_llm() -> FakeLLMClient:
    return FakeLLMClient(
        {
            "claims": (
                "1. 一种声学视觉融合巡检结构，其特征在于，包括声学采集模块、视觉复检模块和状态记录模块。\n"
                "Sources: internal-acoustic-test-record.md"
            ),
            "description": (
                "技术领域\n本实用新型涉及巡检结构技术领域。\n"
                "具体实施方式\n声学采集模块与视觉复检模块连接，并形成状态记录模块。\n"
                "参考资料：实验记录.md\n"
                "依据材料：采集日志-001"
            ),
            "abstract": "本实用新型公开一种声学视觉融合巡检结构。",
            "drawings": "图1为声学视觉融合巡检结构示意图。",
            "diagram": "flowchart TD\nA[声学采集模块] --> B[视觉复检模块]\nB --> C[状态记录模块]",
            "image_prompt": "黑白线稿，展示声学采集模块、视觉复检模块和状态记录模块。",
        }
    )


class _CancelThenFailFormulaLLM(FakeLLMClient):
    store = None
    project_id = None

    def complete_stage(self, stage: str, system_prompt: str, user_prompt: str) -> str:
        if stage == "core_formula" and self.store is not None and self.project_id is not None:
            run = self.store.list_formula_runs(self.project_id)[0]
            self.store.update_formula_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                        "events": [*run.events, "cancel requested"],
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return super().complete_stage(stage, system_prompt, user_prompt)


class _CancelThenFailDeliberationProviderRunner:
    store = None
    project_id = None
    run_id = None
    cancelled_once = False

    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if (
            label.startswith("opening codex")
            and not self.cancelled_once
            and self.store is not None
            and self.project_id is not None
        ):
            self.cancelled_once = True
            run = self.store.get_deliberation_run(self.project_id, self.run_id)
            if run is None:
                raise RuntimeError("Deliberation run not found.")
            self.store.update_deliberation_run(
                run.model_copy(
                    update={
                        "cancel_requested": True,
                        "events": [*run.events, "cancel requested"],
                    }
                )
            )
            raise RuntimeError("Connection error.")
        return await _FastDeliberationProviderRunner().run_json_task(
            provider_id,
            prompt,
            workdir,
            label,
            trace,
            task_timeout_ms,
            log_callback,
        )


class _FastDeliberationProviderRunner:
    async def run_json_task(self, provider_id, prompt, workdir, label, trace, task_timeout_ms, log_callback=None):
        if label.startswith("opening"):
            return _Result(
                {
                    "stance": f"{provider_id} ready",
                    "claim_scope": ["方法"],
                    "risks": [],
                    "recommendations": ["补充实施例"],
                }
            )
        if label.startswith("pair"):
            return _Result(
                {
                    "conflict_level": 0.1,
                    "agreements": ["范围一致"],
                    "disagreements": [],
                    "resolved_recommendation": "继续生成",
                }
            )
        return _Result(
            {
                "summary": "会审通过。",
                "claim_strategy": ["方法独权"],
                "description_strategy": ["补充实施例"],
                "risk_controls": ["人工复核"],
                "agent_consensus": "一致通过。",
            }
        )


class _Result:
    def __init__(self, payload):
        self.payload = payload


def _role_response(role: str, status: str, blocking_issues: list[str]) -> str:
    return json.dumps(
        {
            "role": role,
            "status": status,
            "blocking_issues": blocking_issues,
            "contamination_hits": [],
            "rewrite_suggestions": [],
            "official_safe_patches": [],
            "attorney_memo": [],
        },
        ensure_ascii=False,
    )
