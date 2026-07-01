# Merged Task 1 Reports

This file records reports from two independent SDD plans that both used the same task report path. The merge preserves both original reports.

## Project Evidence Corpus / PR #123 branch

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

---

## UI Refactor / origin/main

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

---

## Document Repair Follow Export Readiness / 2026-07-01

### Repository identity

- `pwd`: `/Users/leo/Projects/patents_agent`
- `git branch --show-current`: `codex/grantatlas-readme-branding`
- `git rev-parse --short HEAD` at start: `f566fc09`
- Dirty worktree at start: `yes`

### What changed

- Updated `frontend/src/features/documentRepair/selectors.ts` so document-repair quality gating now prefers `ExportReadiness` over artifact presence when export readiness reports unfinished, stale, failed, or unknown quality checks.
- Added `hasAnyQualityGap`, `qualityPrimaryActionLabel`, and `primaryActionFromNextAction` to make the selector follow backend `next_action` and quality check state details.
- Changed `deriveTopConclusion(...)` to prefer backend `exportReadiness.reason` for locked or incomplete flows when export is not ready.
- Adjusted the fallback quality gate detail copy so the `待重新验证` state explicitly references quality checks.
- Added the required regression test in `frontend/src/features/documentRepair/selectors.test.ts` for the quality-readiness precedence case.

### TDD evidence

#### RED

Added the required test first, then ran:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts -t "uses export-readiness quality state before artifact presence"
```

Observed failing output summary:

- `1 failed | 6 skipped`
- failure surfaced on `expect(state.gates.quality.detail).toContain("质量检查")`
- this confirmed the selector was still returning the old quality revalidation copy and not yet aligned with the new export-readiness-driven behavior

#### GREEN

After the selector changes, reran:

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts -t "uses export-readiness quality state before artifact presence"
```

Result summary:

- `1 passed | 6 skipped`

### Tests and output

1. Focused RED check

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts -t "uses export-readiness quality state before artifact presence"
```

- failed as expected before implementation

2. Focused GREEN check

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts -t "uses export-readiness quality state before artifact presence"
```

- passed after implementation

3. Full task-required selector suite

```bash
npm --prefix frontend test -- --run src/features/documentRepair/selectors.test.ts
```

- passed: `1 file, 7 tests`

### Files changed

- `frontend/src/features/documentRepair/selectors.ts`
- `frontend/src/features/documentRepair/selectors.test.ts`

### Self-review

- Scope stayed within the two owned source files for the task implementation.
- The new helpers remain selector-local and preserve existing fallback behavior for older flows without `exportReadiness`.
- `failed_quality_checks` still wins over the new quality-gap branch, preserving the existing `运行失败` gate state.
- `next_action` now drives the primary CTA before older gate-derived fallbacks, matching the task brief.

### Concerns

- No blocking concerns. The RED failure surfaced first on updated copy rather than the exact assertion order described in the brief, but it still demonstrated the pre-change misalignment and the task-required behavior is now covered and passing.

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

## Third fix after final re-review

- Repair worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Repair branch: `codex/ui-refactor-2026-06-29`
- Repair starting HEAD: `905ab8fb`
- Dirty at repair start: no

### Reviewer blocker addressed

- Fixed the Task 1 routing regression where `activeSection === "documents"` / `文稿与修复` appeared as a top-level navigation item but had no independent route kind or page title and fell through to the workbench/guided route.

### Changes made

- Updated `frontend/src/app/routes.tsx` so `resolveRoute()` returns a dedicated minimal `documents` route kind.
- Updated `frontend/src/app/AppRoot.tsx` so:
  - `documents` uses title `文稿与修复`
  - `documents` uses subtitle `处理当前项目的正文、问题和版本链路`
  - `documents` renders the existing project workspace surface via `projectWorkspace(props, props.startChoice === "utility" ? "utility" : "generate")`
- Updated `frontend/src/app/routes.test.tsx` with route/title/rendering coverage for the `documents` section.

### TDD evidence

1. `cd frontend && npm test -- app/routes.test.tsx`
   - RED: failed as expected because `resolveRoute("documents", ...)` returned `start-choice` and AppRoot still rendered the `工作台` title.
2. `cd frontend && npm test -- app/routes.test.tsx`
   - GREEN: passed: 1 file, 7 tests

### Verification

1. `cd frontend && npm run build`
   - passed
2. `cd frontend && npm test -- app/routes.test.tsx guidedFlow.test.ts domain.test.ts AppStateRecovery.test.ts`
   - passed: 4 files, 81 tests
3. `cd frontend && npm test`
   - passed: 28 files, 196 tests

## Fourth fix after final review

- Repair worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Repair branch: `codex/ui-refactor-2026-06-29`
- Repair starting HEAD: `e9af36b3`
- Dirty at repair start: no

### Reviewer blocker addressed

- Fixed the persisted-state migration edge case where stale expert-tool ids under legacy `activeSection: "expert"` were sanitized to `build` before section migration, incorrectly restoring the top-level section as `knowledge`.

### Changes made

- Added regression coverage in `frontend/src/AppStateRecovery.test.ts` for stale `activeExpertTool` with legacy `activeSection: "expert"`.
- Updated `frontend/src/App.tsx` so `sanitizePersistedAppState()` stores the sanitized fallback expert tool but only uses a valid raw expert-tool id to drive legacy section migration. Invalid raw expert-tool ids now keep legacy expert state in neutral `expert`.
- Preserved valid migrations for `expert + build/corpus -> knowledge` and `expert + export -> export`.

### TDD evidence

1. `cd frontend && npm test -- AppStateRecovery.test.ts`
   - RED: failed as expected because the stale expert-tool case restored `activeSection: "knowledge"` instead of `expert`.
2. `cd frontend && npm test -- AppStateRecovery.test.ts`
   - GREEN: passed: 1 file, 10 tests

### Verification

1. `cd frontend && npm test -- AppStateRecovery.test.ts guidedFlow.test.ts app/routes.test.tsx`
   - passed: 3 files, 72 tests
2. `cd frontend && npm run build`
   - passed
3. `cd frontend && npm test`
   - passed: 28 files, 197 tests
