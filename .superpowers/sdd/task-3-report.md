# Task 3 Report: Implement Three API Journeys With JSON Reports

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/automation-test-plan`
- Base commit from brief: `665afe37`
- Dirty status at start: dirty with unrelated existing automation changes already present in the worktree

## Files Changed

- `tests/agent_journey_runner.py`
- `tests/test_agent_journey_runner.py`

## TDD Evidence

### RED

Command:

```bash
python3 -m pytest tests/test_agent_journey_runner.py -q
```

Relevant failing output:

```text
ImportError while importing test module '/Users/leo/Projects/patents_agent/tests/test_agent_journey_runner.py'.
E   ImportError: cannot import name 'run_journey' from 'agent_journey_runner'
```

This matched the expected failure mode from the brief: the new journey tests were present, but `run_journey` and `run_journeys` were not implemented yet.

### GREEN

Focused command:

```bash
python3 -m pytest tests/test_agent_journey_runner.py -q
```

Relevant passing output:

```text
6 passed, 4 warnings in 2.06s
```

Combined verification command:

```bash
python3 -m pytest tests/test_flow_driver.py tests/test_agent_journey_runner.py -q
```

Relevant passing output:

```text
18 passed, 16 warnings in 3.01s
```

## Implementation Summary

- Added the brief’s failing journey tests for all three approved journey IDs plus unknown-ID rejection.
- Implemented deterministic `journey_llm()` responses for formula, draft generation, review, and post-draft review roles.
- Implemented `run_journey()` and `run_journeys()` using `TestClient(create_app(...))`, `FlowDriver`, temporary data dirs, and `JourneyReport` JSON output.
- Added the three journey execution helpers:
  - `invention_from_idea`
  - `utility_model_from_structure`
  - `polish_existing_draft`
- Added helper functions to seed a completed strict deliberation, assert official-export readiness, build step records, and provide deterministic external draft text.

## Self-Review Findings

- The implementation stays within the existing API contract and does not touch product API behavior.
- Export readiness remains based on `official_compile_required`; no product code was changed.
- The report runner captures source identity override, step evidence, current gates, and hashes from the actual API flow.
- Warnings observed were existing `chromadb` deprecation warnings during pytest, not task regressions.

## Concerns

- None within the scoped task files and focused verification run.

---

## Task 3 Review Fixes - 2026-06-28

### What I Fixed

- Updated `tests/agent_journey_runner.py` so persisted reports mark `execution.data_dir` as `ephemeral:<path>` instead of recording a deleted temporary directory as though it were durable.
- Added shared journey ID prevalidation in `run_journeys()` so any unknown ID fails before earlier reports can be written.
- Strengthened `tests/test_agent_journey_runner.py` to verify the full report gate/hash contract for every generated report:
  - `gates.quality == current`
  - `gates.official_compile == current`
  - `gates.post_draft_review == current`
  - non-empty `hashes.current_source_draft_hash`
  - non-empty `hashes.latest_official_package_hash`
  - non-empty `hashes.latest_review_draft_hash`
  - non-empty `hashes.latest_review_official_package_hash`
- Added a test that mixed valid/unknown batch IDs fail cleanly without writing any report files.

### Commands Run And Results

```bash
python3 -m pytest tests/test_agent_journey_runner.py -q
```

Result:

```text
7 passed, 4 warnings in 1.91s
```

```bash
python3 -m pytest tests/test_flow_driver.py tests/test_agent_journey_runner.py -q
```

Result:

```text
19 passed, 16 warnings in 2.90s
```

### Files Changed

- `tests/agent_journey_runner.py`
- `tests/test_agent_journey_runner.py`
- `.superpowers/sdd/task-3-report.md`

### Concerns

- Test runs still emit existing `chromadb` deprecation warnings; they did not block the scoped fixes.
