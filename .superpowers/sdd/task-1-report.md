# Task 1 Report: Patent Source Registry And CNIPA Query Pack

- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Branch: `codex/cnipa-official-export-design`
- Base SHA at start: `eb720c19`
- Dirty at start: yes (`.superpowers/sdd/progress.md`)

## Completed

- Added backend patent source capability schemas to [backend/app/schemas.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/backend/app/schemas.py).
- Added focused patent source registry and CNIPA query pack builder in [backend/app/knowledge/patent_sources.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/backend/app/knowledge/patent_sources.py).
- Wired project knowledge service defaults and `get_cnipa_query_pack(...)` in [backend/app/services/project_knowledge_service.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/backend/app/services/project_knowledge_service.py).
- Added targeted tests in [tests/test_patent_sources.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/tests/test_patent_sources.py) and [tests/test_project_knowledge.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/tests/test_project_knowledge.py).

## TDD Notes

1. Added failing tests first for the patent source registry and CNIPA query pack.
2. Verified red state with:
   - `python3 -m pytest tests/test_patent_sources.py -q`
   - Failure: `ModuleNotFoundError: No module named 'backend.app.knowledge.patent_sources'`
3. Implemented minimal production code to satisfy the specified interfaces.
4. Verified green state with:
   - `python3 -m pytest tests/test_patent_sources.py tests/test_project_knowledge.py -q`
   - Result: `31 passed in 0.95s`

## Scope Guard

- Did not modify the dirty primary checkout.
- Did not commit `.superpowers` scratch/report files.
- Did not start Task 2 importer, API, or frontend work.

## Self Review

- Exact source IDs from the brief are preserved as constants.
- `build_cnipa_query_pack(...)` and `get_cnipa_query_pack(...)` match the requested signatures.
- Project knowledge defaults now expose `cnipa_official_export` and `wipo_patentscope` as provider sources while retaining `cnipa_epub` and `google_patents` in the wider corpus source set.
- No concerns found in the scoped diff after test pass.

## Review Fix Follow-up

- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Branch: `codex/cnipa-official-export-design`
- Start SHA for this fix pass: `1087ae77`
- Dirty at start: yes (`.superpowers/sdd/progress.md`, `.superpowers/sdd/task-1-report.md`)

### Reviewer Findings Addressed

1. Updated [backend/app/services/project_knowledge_service.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/backend/app/services/project_knowledge_service.py) so the default runtime provider chain is filtered by the plan's declared source IDs. Explicit `providers=[...]` injections still bypass that filtering for deterministic tests, but default execution now only runs live providers explicitly named by `target_sources` / strategy-group `sources`.
2. Updated [backend/app/knowledge/patent_sources.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/backend/app/knowledge/patent_sources.py) to remove the `CNIPA_EPUB_SEARCH_SCRIPT` env-var wording from shared `setup_hint` metadata. The legacy EPUB capability is now described as an advanced helper configured outside the ordinary workflow.
3. Added a focused regression test in [tests/test_project_knowledge.py](/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design/tests/test_project_knowledge.py) asserting that a plan targeting only `cnipa_official_export` does not execute the default `cnipa_epub` provider.

### Verification

- `python3 -m pytest tests/test_patent_sources.py tests/test_project_knowledge.py -q`
- Result: `32 passed in 0.80s`
