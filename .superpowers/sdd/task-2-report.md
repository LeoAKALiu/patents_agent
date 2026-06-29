## Task 2 Report - Route Mapping And Shell Chrome

Status: DONE

Source identity:
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- Start HEAD: `c441c5e9`
- Dirty at start: false

Implementation:
- Normalized public `RouteKind` to `workbench | projects-overview | documents | knowledge | expert | export | settings`.
- Kept expert sub-tool classification private to `AppRoot` while preserving existing corpus, quality, and post-draft workspace rendering.
- Removed project-scoped `关键节点` sidebar chrome and the corresponding shell props.
- Replaced topbar global navigation buttons with project selector, export status, run status, backend status, refresh, and workbench-only `返回三选一` recovery.
- Reduced `SystemStatusPanel` default sidebar footprint to compact rows for model, agents, and backend with collapsed diagnostics.
- Kept `documents` on the existing project workspace surface with the distinct route title/subtitle, leaving Task 4 document repair workspace out of scope.

TDD evidence:
- RED: `cd frontend && npm test -- app/routes.test.tsx`
  - Failed as expected on old `start-choice` route, old `关键节点` shell block, missing topbar export/backend status, and tall status panel labels.
- GREEN: `cd frontend && npm test -- app/routes.test.tsx`
  - Passed: 1 file, 11 tests.

Verification:
- `cd frontend && npm test -- app/routes.test.tsx AppOfflineState.test.tsx`
  - Passed: 2 files, 14 tests.
- `cd frontend && npm run build`
  - Passed: `tsc -b && vite build`.
- `cd frontend && npm test`
  - Passed: 28 files, 201 tests.
- `git diff --check`
  - Passed.

Files changed:
- `frontend/src/app/routes.tsx`
- `frontend/src/app/AppRoot.tsx`
- `frontend/src/app/ShellLayout.tsx`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- `frontend/src/ui/SystemStatusPanel.tsx`
- `frontend/src/app/routes.test.tsx`
- `frontend/src/styles.css`

Self-review:
- Confirmed no lingering public `expert-corpus`, `expert-quality`, or `expert-post-draft` route kinds in app/ui code.
- Confirmed old `keySections` shell props and `关键节点` rendering path are removed.
- Confirmed `专家工具` and `返回向导` are not added as topbar global navigation controls.

Concerns:
- No callable subagent dispatch tool was exposed in this session, so implementation and review were performed locally while preserving the SDD report, TDD, verification, and commit workflow.

## Task 2 Review Fix - Diagnostics Surface

Status: DONE

Source identity:
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- Start HEAD: `2e9fcd05`
- Dirty at start: false

Review finding:
- Fixed P2 where `SystemStatusPanel` still embedded detailed diagnostics inline in the sidebar footer via `<details>`.

Implementation:
- Removed inline diagnostics from `SystemStatusPanel`; its default render is now only the compact model, agent, and backend rows.
- Added `SystemDiagnosticsDialog`, reusing `frontend/src/components/ui/dialog.tsx`, with backend status, project list status, model, embedding model, data dir, and agent status/mode where useful.
- Wired the existing `ShellTopbar` `onOpenDiagnostics` prop from `AppRoot`, so the topbar backend chip opens the diagnostics surface.
- Added route-shell tests proving diagnostics are absent from the sidebar by default and available only after opening the backend diagnostics dialog.

TDD evidence:
- RED: `cd frontend && npm test -- app/routes.test.tsx`
  - Failed as expected because `模型名称` was still present in the default footer DOM.
- GREEN: `cd frontend && npm test -- app/routes.test.tsx`
  - Passed: 1 file, 12 tests.

Verification:
- `cd frontend && npm test -- app/routes.test.tsx AppOfflineState.test.tsx`
  - Passed: 2 files, 15 tests.
- `cd frontend && npm run build`
  - Passed: `tsc -b && vite build`.
- `cd frontend && npm test`
  - Passed: 28 files, 202 tests.

Files changed:
- `frontend/src/app/AppRoot.tsx`
- `frontend/src/ui/SystemStatusPanel.tsx`
- `frontend/src/app/routes.test.tsx`
- `frontend/src/styles.css`
- `.superpowers/sdd/task-2-report.md`

Concerns:
- None.
