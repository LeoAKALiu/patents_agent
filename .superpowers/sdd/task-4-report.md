# Task 4 Report: Add CLI Entrypoint And QA Documentation Hook

## Source identity
- Branch: `codex/automation-test-plan`
- Base commit: `60fd12ab`
- Worktree: `/Users/leo/Projects/patents_agent`
- Working tree: dirty before edits (pre-existing changes from other tasks, unchanged)

## RED: failing test command
Command:
```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_main_runs_selected_journey_and_returns_zero -q
```

Output (relevant):
```text
F
E   ImportError: cannot import name 'main' from 'agent_journey_runner' (.../tests/agent_journey_runner.py)
```

## GREEN: passing test command
Command:
```bash
python3 -m pytest tests/test_agent_journey_runner.py::test_main_runs_selected_journey_and_returns_zero -q
```

Output:
```text
.                                                                        [100%]
1 passed, 2 warnings in 1.40s
```

## CLI evidence
Commands:
```bash
python3 tests/agent_journey_runner.py --journey all --output-dir /tmp/patentagent-agent-journeys
```

Printed report paths:
```text
/tmp/patentagent-agent-journeys/20260628T043952790572Z-invention_from_idea.json
/tmp/patentagent-agent-journeys/20260628T043952943670Z-utility_model_from_structure.json
/tmp/patentagent-agent-journeys/20260628T043953095921Z-polish_existing_draft.json
```

Validation command:
```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in sorted(Path('/tmp/patentagent-agent-journeys').glob('*-*.json')):
    payload = json.loads(p.read_text(encoding='utf-8'))
    print(p.name, payload['execution']['status'], payload['execution']['llm_mode'], bool(payload['hashes'].get('current_source_draft_hash')))
PY
```

Output:
```text
20260628T043952790572Z-invention_from_idea.json passed fake True
20260628T043952943670Z-utility_model_from_structure.json passed fake True
20260628T043953095921Z-polish_existing_draft.json passed fake True
```

## Docs/CLI test command
Command:
```bash
python3 -m pytest tests/test_agent_journey_runner.py tests/test_qa_docs.py -q
```

Output:
```text
.........                                                                [100%]
9 passed, 5 warnings in 1.88s
```

## Files changed
- `tests/agent_journey_runner.py`
- `tests/test_agent_journey_runner.py`
- `docs/qa/ai-scenario-testing-pipeline.md`

## Self-review findings / concerns
- Added a small `sys.path` bootstrap in `tests/agent_journey_runner.py` so direct CLI invocation (`python3 tests/agent_journey_runner.py ...`) can import `backend` and `flow_driver` modules. This is scoped to the test runner and does not change product APIs.
- Command output contains `DeprecationWarning` from `chromadb` in pytest runs, pre-existing and non-failing.

## Task 4 Follow-up: Gate CLI repo-root bootstrap

- What fixed:
  - Updated `tests/agent_journey_runner.py` so repository-root path injection runs only when the module is executed as a script (`__name__ == "__main__"`), avoiding `sys.path` mutation for pytest/import consumers.
- Commands run:
  - `python3 -m pytest tests/test_agent_journey_runner.py::test_main_runs_selected_journey_and_returns_zero -q`
  - `python3 -m pytest tests/test_agent_journey_runner.py tests/test_qa_docs.py -q`
  - `python3 tests/agent_journey_runner.py --journey utility_model_from_structure --output-dir /tmp/patentagent-agent-journey-cli-fix`
- Results:
  - `python3 -m pytest ...::test_main_runs_selected_journey_and_returns_zero -q` → `1 passed, 2 warnings in 1.50s`
  - `python3 -m pytest tests/test_agent_journey_runner.py tests/test_qa_docs.py -q` → `9 passed, 5 warnings in 1.81s`
  - CLI run prints one report path at `/tmp/patentagent-agent-journey-cli-fix/20260628T044302088703Z-utility_model_from_structure.json`
- Files changed:
  - `tests/agent_journey_runner.py`
  - `.superpowers/sdd/task-4-report.md`
- Concerns:
  - Only one pre-existing warning class observed (`chromadb` `DeprecationWarning`), same as before and non-failing.
