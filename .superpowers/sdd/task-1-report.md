# Task 1 Report: Navigation Model And Persisted-State Migration

- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- Starting HEAD: `aba070d0`
- Dirty at start: no

## What I implemented

- Updated `frontend/src/guidedFlow.ts` to define the new top-level navigation model:
  - `MainSectionId = "workbench" | "projects" | "documents" | "knowledge" | "expert" | "export" | "settings"`
  - `mainSections` labels: `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, `设置`
  - `defaultMainSectionId = "workbench"`
  - added `normalizeMainSectionId(value, activeExpertTool)` with the legacy migration rules from the brief
- Updated `frontend/src/App.tsx` persisted-state recovery to use `normalizeMainSectionId(record.activeSection, activeExpertTool)` instead of the old hard-coded section allowlist.
- Updated `handleStartChoice()` and `returnToStartChoices()` to route back to `workbench`.
- Updated `openExpertTool()` so:
  - `build` / `corpus` open `knowledge`
  - `export` opens `export`
  - all other expert tools stay under `expert`
- Updated native menu actions so:
  - import draft actions still open `expert` + `materials`
  - export actions open `export` + `export`

## TDD Evidence

### RED

Command:

```bash
cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts
```

Result summary:

- failed as expected
- 3 test files failed
- 9 tests failed, 65 passed
- failures showed:
  - old nav labels still returned `开始 / 项目 / 设置`
  - `defaultMainSectionId` still returned `generate`
  - `normalizeMainSectionId` was missing
  - persisted state still restored `generate` / `expert` instead of `workbench` / `export`

### GREEN

Command:

```bash
cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts
```

Result summary:

- passed
- 3 test files passed
- 74 tests passed

## Test commands and results

1. `cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts`
   - RED: 3 files failed, 9 tests failed, 65 passed
2. `cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts`
   - GREEN: 3 files passed, 74 tests passed
3. `cd frontend && npm test`
   - full suite passed: 28 files, 191 tests passed

## Files changed

- `frontend/src/guidedFlow.ts`
- `frontend/src/App.tsx`
- `frontend/src/guidedFlow.test.ts`
- `frontend/src/domain.test.ts`
- `frontend/src/AppStateRecovery.test.ts`

## Self-review findings

- The implementation stayed scoped to the navigation constants, legacy section normalization, persisted-state recovery, and the section-selection call sites named in the brief.
- Full frontend regression coverage stayed green after the change.

## Issues or concerns

- No blocking issues found during this task.

## Fix after review

- Repair worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Repair branch: `codex/ui-refactor-2026-06-29`
- Repair starting HEAD: `fa1b4256`
- Dirty at repair start: yes (`.superpowers/sdd/task-1-report.md` already modified)

### Reviewer blocker addressed

- Fixed the Task 1 TypeScript break caused by shell/router references that still treated the removed top-level sections `generate` and `utility` as `MainSectionId` values.

### Changes made

- Updated `frontend/src/app/AppRoot.tsx` so shell-level navigation uses `workbench` instead of the removed `generate` section where it refers to the top-level main section.
- Preserved guided-flow behavior by continuing to pass `ProjectWorkspace` the internal section variant:
  - `"utility"` when `startChoice === "utility"`
  - otherwise `"generate"`
- Updated `frontend/src/app/routes.tsx` so `fixedGoalModeFor()` no longer checks `activeSection === "utility"` and still returns `"utility"` when `startChoice === "utility"`.
- Updated `frontend/src/app/routes.test.tsx` fixtures and shell assertions to use the valid top-level section `workbench` and the label `工作台`.
- Updated the AppRoot fallback page title for the new workbench label without broadening route coverage into Task 2.

### Verification

1. `cd frontend && npm run build`
   - passed
2. `cd frontend && npm test -- guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts app/routes.test.tsx`
   - passed: 4 files, 76 tests
3. `cd frontend && npm test`
   - passed: 28 files, 191 tests

## Second fix after re-review

- Repair worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Repair branch: `codex/ui-refactor-2026-06-29`
- Repair starting HEAD: `2970bad2`
- Dirty at repair start: no

### Reviewer blocker addressed

- Fixed the Task 1 routing regression where `activeSection === "knowledge"` and `activeSection === "export"` fell through the shell/router and rendered the guided workspace instead of the existing corpus/export workspaces.

### Changes made

- Updated `frontend/src/app/routes.tsx` so `resolveRoute()` returns minimal dedicated route kinds for `knowledge` and `export` instead of letting those section ids fall through to `guided`.
- Updated `frontend/src/app/AppRoot.tsx` so:
  - `knowledge` renders the existing `CorpusWorkspace`
  - `export` renders the existing `PostDraftWorkspace`
  - `knowledge` preserves `build` / `corpus` when already active and otherwise defaults safely to `build`
  - `export` always renders the existing export tool
- Updated `frontend/src/app/routes.test.tsx` with direct route assertions plus render coverage for:
  - `knowledge` -> corpus workspace
  - non-corpus expert tool + `knowledge` -> corpus `build`
  - `export` -> post-draft export workspace

### Verification

1. `cd frontend && npm run build`
   - passed
2. `cd frontend && npm test -- app/routes.test.tsx guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts`
   - passed: 4 files, 80 tests
3. `cd frontend && npm test`
   - passed: 28 files, 195 tests
