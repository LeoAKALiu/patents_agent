# Agent Runtime Adapter Design

## Authoring Context

- Branch: `codex/grantatlas-readme-branding`
- Short SHA: `001c8e9f`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty status at authoring: untracked `.gstack/`, `.reasonix/`, `.worktrees/`, and `output/`; no tracked file modifications were included in this spec commit.

## Background

GrantAtlas currently has a working multi-agent deliberation path implemented as hand-written Python orchestration. The core flow lives in `backend/app/deliberation/orchestrator.py`: providers produce independent openings, pairwise comparisons run concurrently, and a chair synthesis creates the final patent strategy brief. The API layer in `backend/app/main.py` adds run creation, status persistence, retry, cancellation, runtime heartbeat, provider diagnostics, and strict generation gates.

That design is effective for the current provider set, but future agent runtimes may arrive as Hermes workers, OMP tasks, local model-native CLIs, remote hosted agents, LangGraph graphs, or other tools. GrantAtlas should adapt quickly when the runtime changes without rewriting patent-specific workflow logic.

## Goal

Create a stable GrantAtlas-owned agent runtime module that lets patent workflows depend on GrantAtlas concepts rather than any one agent framework. LangGraph should be usable for complex graph execution, but it should be an adapter behind the GrantAtlas interface, not the product's primary abstraction.

## Non-Goals

- Do not rewrite the whole backend around LangGraph.
- Do not migrate React, Tauri, storage, export, patent parsing, or patent domain models.
- Do not replace existing Pydantic schemas for deliberation, draft packages, reviews, or runtime failures in the first increment.
- Do not require user-editable workflow configuration in the first increment.
- Do not assume all future agents are LLM chat completions; some may be CLI tools, worker queues, or framework-native agents.

## Design Principles

- GrantAtlas owns the external interface. Frameworks such as LangGraph, Hermes, OMP, Codex CLI, and Claude CLI are adapters.
- Code-defined workflows come first. The patent flows still evolve quickly, so Python workflow definitions are safer than a broad user-editable workflow spec.
- Keep the module deep. Callers should submit task or workflow intent and receive structured run results, events, and artifacts. They should not know process arguments, prompt transport, checkpoint implementation, or retry mechanics.
- Preserve current acceptance gates. A generated draft should still require a strict completed deliberation with required providers, completed openings, completed pair comparisons, and chair synthesis.
- Make provider capability explicit. Agent selection should be based on declared roles and capabilities, not hard-coded CLI names scattered across workflow code.

## Proposed Architecture

Add a new backend package:

```text
backend/app/agents/
├── __init__.py
├── runtime.py
├── models.py
├── registry.py
└── adapters/
    ├── __init__.py
    ├── cli.py
    ├── langgraph.py
    ├── hermes.py
    └── fake.py

backend/app/workflows/
├── __init__.py
└── deliberation.py
```

`backend/app/agents/runtime.py` defines the GrantAtlas agent runtime interface. `backend/app/agents/adapters/*` contains concrete adapters. `backend/app/workflows/deliberation.py` defines the patent deliberation graph in code and calls the runtime interface.

The existing `backend/app/deliberation/providers.py` should first move behind `CliAgentAdapter` with minimal behavior changes. The existing `DeliberationOrchestrator` can then either wrap the new workflow or be replaced once the tests prove parity.

## Runtime Interface

The first interface should support two levels of work:

1. Single agent task execution.
2. Code-defined workflow execution.

Conceptual Python shape:

```python
class AgentRuntime:
    def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        ...

    def run_workflow(self, request: WorkflowRunRequest) -> WorkflowRunResult:
        ...

    def cancel(self, run_id: str) -> WorkflowRunResult:
        ...

    def resume(self, run_id: str, input: HumanInput | None = None) -> WorkflowRunResult:
        ...
```

The interface facts callers may rely on:

- Requests contain GrantAtlas roles, prompt packs, context artifacts, output schema, timeout, trace flag, and retry policy.
- Results contain status, structured payload, raw output reference, events, logs, failures, artifact references, elapsed time, and provider metadata.
- Adapters normalize errors into existing `RuntimeFailure` and `DeliberationLogEntry` compatible shapes.
- Callers do not pass CLI arguments, subprocess environment, LangGraph checkpoint objects, Hermes queue names, or OMP-specific task handles.

## Provider Capabilities

Add provider capability metadata to the registry:

```python
class AgentCapability:
    role: str
    output_modes: set[str]
    supports_streaming: bool
    supports_resume: bool
    supports_cancel: bool
    supports_artifacts: bool
    max_context_tokens: int | None
```

Examples:

- `codex-cli`: roles `deliberation`, `critic`; output mode `json`.
- `deepseek-reasonix`: roles `deliberation`, `formula`, `review`.
- `hermes-worker`: roles `deliberation`, `research`, `repair`; supports artifacts and async resume.
- `langgraph-local`: roles `workflow`; supports checkpoint, resume, stream events.
- `omp-cli`: roles depend on local install; may support long-running tasks but not structured resume.

Workflow code asks for roles and constraints. The registry selects compatible adapters or returns a diagnostic failure.

## Code-Defined Deliberation Workflow

The first migrated workflow is multi-agent deliberation because it already has graph-like structure and strong tests.

Workflow stages:

1. `prepare_context`
   - Build `InventionBrief`.
   - Retrieve patent context chunks.
   - Build the dossier.

2. `opening`
   - Run one task per selected provider.
   - Execute independent openings concurrently.
   - Require all strict providers to complete for a strict run.

3. `pair_compare`
   - Generate all provider pairs.
   - Run pair comparisons concurrently through a coordinator provider.
   - Preserve deterministic ordering in stored stage results.

4. `chair_synthesis`
   - Run final synthesis through the coordinator provider.
   - Validate output as `PatentStrategyBrief`.

5. `finalize`
   - Persist `DeliberationRun`.
   - Write trace artifacts when enabled.
   - Preserve strict generation gate compatibility.

This workflow remains Python code. It may use LangGraph internally once the interface exists, but the public GrantAtlas workflow function should not expose LangGraph types.

## LangGraph Adapter Role

LangGraph is valuable when a workflow needs checkpointing, branching, human input, and resumable execution. It should be introduced as `LangGraphWorkflowAdapter` after the runtime interface is in place.

The adapter should translate:

- GrantAtlas workflow nodes into LangGraph nodes.
- `WorkflowState` into LangGraph state.
- GrantAtlas events and logs from LangGraph callbacks or node outputs.
- LangGraph checkpoint identifiers into GrantAtlas run IDs and artifact references.

The adapter must not leak LangGraph state shape into API responses. FastAPI callers continue to receive existing GrantAtlas run models.

## Hermes, OMP, and CLI Adapters

`CliAgentAdapter` covers the current provider behavior:

- Resolve command path.
- Inject prompt through stdin or argument placeholder.
- Apply timeout.
- Extract or repair JSON payload.
- Write trace files.
- Normalize missing provider, timeout, empty output, process error, and invalid JSON failures.

`HermesAdapter` should cover worker-style execution:

- Submit a task with role, prompt pack, context artifacts, output schema, and timeout.
- Poll or subscribe for task events.
- Fetch structured result artifacts.
- Map Hermes cancellation and retry semantics into GrantAtlas statuses.

`OmpAdapter` should follow the same interface as CLI or worker depending on the actual OMP runtime shape. The important constraint is that OMP details remain inside the adapter.

## Persistence and Artifacts

The first increment should reuse existing SQLite tables and run directories:

- `deliberation_runs` remains the persisted API model.
- `run_dir` remains the trace and artifact directory.
- `stage_results_json`, `logs_json`, `events_json`, `runtime_state_json`, and `failure_details_json` remain compatible.

The new runtime layer may add internal artifact references, but it should not require a storage migration for the first deliberation migration. Storage migrations can be introduced later if workflow reuse across disclosure, formula, and post-draft review needs a shared `agent_runs` table.

## Error Handling

Adapters normalize runtime-specific errors into GrantAtlas categories:

- `provider_missing`
- `not_authenticated`
- `timeout`
- `cancelled`
- `process_error`
- `empty_output`
- `invalid_json`
- `schema_validation_error`
- `artifact_missing`
- `runtime_unavailable`

Each failure includes a repair suggestion. Existing UI surfaces should keep working because they already display diagnostic logs and failure details.

## Testing Strategy

Keep the first implementation narrow and parity-driven.

- Unit test `CliAgentAdapter` with fake spawn functions for success, timeout, missing provider, invalid JSON, and trace output.
- Unit test provider capability selection with strict and optional providers.
- Port current deliberation concurrency tests so openings and pair comparisons still overlap.
- Port current deliberation API lifecycle tests so completed runs still unlock draft generation.
- Add adapter contract tests shared by fake, CLI, and future LangGraph adapters.
- Add one no-network fake LangGraph adapter test if LangGraph becomes an optional dependency.

## Rollout Plan

1. Add `backend/app/agents` models, runtime interface, fake adapter, and CLI adapter behind tests.
2. Add provider registry and capability selection while preserving existing `/api/agents/doctor` behavior.
3. Rebuild deliberation as a code-defined workflow using the runtime interface and the CLI adapter.
4. Keep existing API responses and strict generation gates unchanged.
5. Add `LangGraphWorkflowAdapter` as optional dependency only after deliberation parity passes.
6. Add Hermes or OMP adapter when the first concrete runtime integration is needed.

## Success Criteria

- Existing deliberation tests pass with the new runtime path.
- A fake adapter can replace real providers in API tests without patching workflow internals.
- Adding a new runtime requires adding an adapter and registry metadata, not editing patent-specific workflow stages.
- LangGraph can be enabled for a workflow without changing FastAPI response models or frontend contracts.
- Generation remains blocked unless the strict deliberation gate is satisfied.

## Open Decision

GrantAtlas workflows are code-defined for the first phase. A declarative workflow spec may be introduced later only after the deliberation, formula, and post-draft review flows reveal stable shared structure.
