# Merged Task 6 Reports

This file records reports from two independent SDD plans that both used the same task report path. The merge preserves both original reports.

## Project Evidence Corpus / PR #123 branch

Task 6 report: Writing-Flow Gates

Source identity
- Branch: `codex/automation-test-plan`
- Short SHA at start: `05388c1b`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty at start: yes; only the pre-existing out-of-scope files listed in the task dispatch were already dirty

What changed
- Corrected the grantability gate to look for the real project-corpus flag, `synthetic_evidence`, instead of the stale `synthetic_only` name.
- Added regression coverage proving a `ready` project knowledge state with `document_count >= 2` still fail-closes when `quality_flags=["synthetic_evidence"]`.
- Hardened the grantability API regression so it seeds a distinctive `ProjectKnowledgeState` and proves the endpoint passes that state through to grantability generation.
- Tightened the quality view copy so “语料库已就绪” only appears when the corpus is truly analysis-ready: `status === "ready"`, at least 2 documents, and no blocking quality flags.

Behavior summary
- A synthetic-only corpus now fail-closes even if the knowledge state says `ready` and has 2 or more documents.
- The grantability report API now proves that stored project-knowledge state can drive low-evidence grantability output.
- The grantability UI no longer treats every `ready` status as analysis-ready; blocking flags and low document counts keep the copy in an evidence-gated state.

Verification
- `python3 -m pytest tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing tests/test_grantability.py tests/test_api.py::test_grantability_report_api_generates_persists_and_exports -q`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test -- qualityViews`

Files changed
- `backend/app/grantability.py`
- `tests/test_grantability.py`
- `tests/test_api.py`
- `frontend/src/views/qualityViews.tsx`
- `frontend/src/views/qualityViews.test.tsx`

---

## UI Refactor / origin/main

## Task 6 Report

### Source identity at start
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- HEAD: `15a8c937`
- Dirty worktree: `no`

### Files changed
- `frontend/src/features/documentRepair/AnnotatedRepairTab.tsx`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- `frontend/src/flow/panels/PostDraftIssueRail.tsx`
- `frontend/src/flow/panels/DraftRepairInspector.tsx`
- `frontend/src/PostDraftRepairEditor.test.tsx`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- `frontend/src/styles.css`
- `.superpowers/sdd/task-6-report.md`

### Behavior implemented
- Embedded the annotated repair editor as the real `标注修复` tab inside `文稿与修复`.
- Added `AnnotatedRepairTab` to load repair-session data from `getPostDraftRepairSession` using the existing `selectLatestRepairablePostDraftReview` helper.
- Preserved `PostDraftRepairEditor` modal compatibility by keeping `mode="modal"` as the default and only removing overlay/dialog chrome in `mode="embedded"`.
- Added embedded loading, error, empty, and no-repairable-review states.
- Rendered the full three-part workspace from non-empty repair-session data: `问题队列`, `正文定位`, and `修复面板`.
- Kept save and patch-apply behavior on the existing `onSaveDraftPackage` / `onPatchApplied` path.
- After patch application, marked the affected issue as `待复核` in the local display state without exposing raw internals.
- Adjusted layout so desktop stays three-column while widths below `920px` stack queue, document, and inspector vertically.

### Tests/build run and results
- `cd frontend && npm test -- PostDraftRepairEditor.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx` — passed (`22` tests)
- `cd frontend && npm run build` — passed
- `cd frontend && npm test` — passed (`230` tests)
- `git diff --check` — passed

### Self-review notes
- Modal compatibility: existing modal entry points keep overlay behavior because `PostDraftRepairEditor` still defaults to `modal`; embedded mode is opt-in.
- Real repair-session flow: the workspace tab uses `selectLatestRepairablePostDraftReview` and `getPostDraftRepairSession`, then the existing patch creation/application APIs already owned by `PostDraftRepairEditor`.
- No raw logs, raw JSON, generation internals, or safe-patch internals were surfaced in the new tab states or tests.

### Concerns
- `待复核` is implemented as a local UI marker layered on top of the existing API issue model, since the current `DraftReviewIssue.status` type does not include a server-backed `pending_revalidation` enum value.

### Fixes After Review
- Finding: duplicate persisted save after patch apply in embedded `AnnotatedRepairTab`.
  Fix: removed the `onSaveDraftPackage` call from the embedded `onPatchApplied` handler so patch apply now only updates local editor state plus the local `待复核` marker.
- Finding: missing regression coverage for patch apply behavior.
  Fix: added editor-level mocks for `createDraftRepairPatch` and `applyDraftRepairPatch`, asserted `onPatchApplied` receives the patched fields plus issue id, and asserted `onSave` is not called during patch apply. Added workspace coverage that the embedded tab marks `待复核` without calling `onSaveDraftPackage`.
- Commands:
  - `cd frontend && npm test -- PostDraftRepairEditor.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx` — passed (`24` tests).
  - `cd frontend && npm run build` — passed.
  - `cd frontend && npm test` — passed (`232` tests).
  - `git diff --check` — passed.
