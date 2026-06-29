# Task 5 Fix Report

## Source identity

- `pwd`: `/Users/leo/Projects/patents_agent`
- branch: `codex/automation-test-plan`
- short SHA before fixes: `e06ee9f9`
- worktree root: `/Users/leo/Projects/patents_agent`
- dirty tree before fixes: yes
- untouched out-of-scope dirty files:
  - `backend/app/official_compile.py`
  - `docs/qa/automation-test-plan-execution-2026-06-27.md`
  - `tests/adversarial_flow_harness.py`
  - `tests/test_adversarial_flow_explorer.py`
  - `tests/test_official_compile.py`
  - `.superpowers/sdd/task-3-report.md`
  - `.superpowers/sdd/task-4-report.md`

## Fixes applied

1. Updated `frontend/src/views/projectKnowledgeView.tsx` so candidate review is two-way:
   - shows Agent recommendation and current user decision
   - supports both `include` and `exclude` decisions through `onCandidateDecision`
2. Added fail-closed evidence messaging:
   - renders `state.quality_flags`
   - surfaces stale, synthetic, empty, needs-search, and failed-state guidance
   - keeps grantability messaging explicitly evidence-gated
3. Rendered corpus-version readiness details:
   - latest corpus version metrics
   - created-at details
   - quality report block when present
4. Fixed the misleading no-op CTA contract:
   - `ready`, `needs_supplemental_search`, and `stale` now advertise and trigger rerunning the latest plan when one exists
   - no longer labels a no-op initialization call as “补充检索”
5. Added targeted frontend coverage:
   - candidate include/exclude actions and displayed decision state
   - fail-closed quality/stale messaging and build-corpus action
   - stale-state rerun CTA wiring
   - `CorpusWorkspace` build-tab defaulting to `ProjectKnowledgeView` with reachable advanced fallback

## Files changed

- `frontend/src/views/projectKnowledgeView.tsx`
- `frontend/src/projectKnowledgeView.test.tsx`
- `frontend/src/features/corpus/CorpusWorkspace.test.tsx`

## Verification

- `npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx` -> PASS
- `npm --prefix frontend test -- --run src/features/corpus/CorpusWorkspace.test.tsx` -> PASS
- `npm --prefix frontend run build` -> PASS

## Commit

- planned commit message: `fix: repair project knowledge workspace review flow`
