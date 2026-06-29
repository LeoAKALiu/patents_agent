# Task 1 Report: Backend Schemas And Storage

## Repository identity

- `pwd`: `/Users/leo/Projects/patents_agent`
- `git status --short --branch` at start:
  - `## codex/automation-test-plan...origin/codex/automation-test-plan [ahead 2]`
  - ` M .superpowers/sdd/task-3-report.md`
  - ` M .superpowers/sdd/task-4-report.md`
  - ` M backend/app/official_compile.py`
  - ` M docs/qa/automation-test-plan-execution-2026-06-27.md`
  - ` M tests/adversarial_flow_harness.py`
  - ` M tests/test_adversarial_flow_explorer.py`
  - ` M tests/test_official_compile.py`
- `git rev-parse --show-toplevel`: `/Users/leo/Projects/patents_agent`
- `git branch --show-current`: `codex/automation-test-plan`
- `git rev-parse --short HEAD`: `824f41a9`
- Dirty worktree at start: `yes`

## Scope followed

- Modified: `backend/app/schemas.py`
- Modified: `backend/app/storage.py`
- Created: `tests/test_project_knowledge.py`
- Left unrelated dirty files untouched and unstaged.

## RED step

Added `tests/test_project_knowledge.py` with the exact round-trip storage tests from the task brief, then ran:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Observed failure:

- `ImportError: cannot import name 'AgentSearchPlan' from 'backend.app.schemas'`

This matched the expected RED state because the new schema classes and store methods did not yet exist.

## Implementation

### `backend/app/schemas.py`

Added the required Pydantic models after `CorpusImportJob`:

- `ProjectKnowledgeState`
- `SearchIntent`
- `SearchPlanStrategyGroup`
- `AgentSearchPlan`
- `PriorArtCandidate`
- `ProjectCorpusVersion`
- `ProjectKnowledgeOverview`
- `CandidateDecisionPatch`
- `CandidateBulkDecision`

### `backend/app/storage.py`

Imported the new schema types and added the required SQLite persistence:

- Migration tables:
  - `project_knowledge_states`
  - `search_intents`
  - `agent_search_plans`
  - `prior_art_candidates`
  - `project_corpus_versions`
- Store methods:
  - `upsert_project_knowledge_state`
  - `get_project_knowledge_state`
  - `create_search_intent`
  - `get_latest_search_intent`
  - `create_agent_search_plan`
  - `update_agent_search_plan`
  - `get_agent_search_plan`
  - `get_latest_agent_search_plan`
  - `upsert_prior_art_candidate`
  - `list_prior_art_candidates`
  - `update_prior_art_candidate_decision`
  - `create_project_corpus_version`
  - `get_latest_project_corpus_version`
- Extended `delete_project` so knowledge-state rows are deleted with the project.

## GREEN step

Ran the exact task command again:

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Result:

- `2 passed in 0.18s`

## Commit

Staged only the owned task files and created the required commit:

```bash
git add backend/app/schemas.py backend/app/storage.py tests/test_project_knowledge.py
git commit -m "feat: persist project knowledge state"
```

Created commit:

- `5f5a0172 feat: persist project knowledge state`

## Final workspace note

After the commit, the worktree still contains the same unrelated dirty files called out in the task context. They were not modified, staged, or included in the Task 1 commit.

## Review finding fix

- Added a regression test in `tests/test_project_knowledge.py` that verifies `update_prior_art_candidate_decision("project-1", "candidate-1", "bogus")` raises `ValueError` and leaves the stored candidate in `pending`.
- Updated `backend/app/storage.py` to reject invalid prior art candidate decisions before any persistence happens.

## Verification

```bash
python3 -m pytest tests/test_project_knowledge.py -q
```

Output:

```text
3 passed in 0.19s
```
