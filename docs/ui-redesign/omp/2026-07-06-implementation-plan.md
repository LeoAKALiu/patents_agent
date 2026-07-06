---
status: ready-for-omp
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/grantatlas-readme-branding
  short_sha: ae767161
  worktree: /Users/leo/Projects/patents_agent
  dirty_at_capture: true
model:
  runtime: omp
  implementation_model: google-antigravity/gemini-3.5-flash
related:
  - docs/ui-redesign/omp/2026-07-06-ui-spec.md
  - docs/ui-redesign/omp/2026-07-06-pr-slices.md
  - docs/ui-redesign/04-workbench-document-repair-spec.md
  - AGENTS.md
---

# OMP UI Refactor Implementation Plan

This plan turns the current UI refactor state into OMP-sized implementation slices. OMP should implement; Codex should review and integrate.

## Current Baseline

Recorded on 2026-07-06:

```text
worktree: /Users/leo/Projects/patents_agent
branch: codex/grantatlas-readme-branding
short SHA: ae767161
dirty: true
```

Dirty tracked files at capture:

```text
frontend/src/app/AppRoot.tsx
frontend/src/app/routes.test.tsx
frontend/src/features/workbench/WorkbenchWorkspace.test.tsx
frontend/src/features/workbench/WorkbenchWorkspace.tsx
frontend/src/flow/panels/QualityPanel.test.tsx
frontend/src/flow/panels/QualityPanel.tsx
frontend/src/styles.css
```

Targeted baseline tests passed:

```bash
cd frontend && npm test -- app/routes.test.tsx features/workbench/WorkbenchWorkspace.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx PostDraftRepairEditor.test.tsx flow/panels/QualityPanel.test.tsx
```

Result: 5 test files passed, 55 tests passed.

## Implementation Rule

Do not let OMP write directly into `/Users/leo/Projects/patents_agent` while the dirty tracked files above remain uncommitted. Use one of these baseline choices first:

1. Commit or stash the current WIP as PR-0, then create an OMP worktree from that baseline.
2. Create an OMP worktree from `ae767161` and explicitly exclude the current dirty changes from the implementation.

The recommended path is option 1 if the current dirty changes are intentional.

## OMP Runtime Boundary

Use this shape for implementation tasks:

```bash
omp --model google-antigravity/gemini-3.5-flash \
  --cwd <omp-worktree> \
  --thinking=medium \
  --approval-mode=write \
  --max-time=1200 \
  "<task prompt>"
```

Do not use OMP with unrestricted task scope. Each prompt must name exact files, tests, visual evidence, and merge blockers.

## Shared OMP Guardrails

Every OMP implementation prompt must include:

```text
Read AGENTS.md first.
Record pwd, git status --short --branch, git rev-parse --show-toplevel, git branch --show-current, and git rev-parse --short HEAD before editing.
Do not modify files outside the listed scope.
Do not revert unrelated changes.
Specs and screenshots are requirements, not proof of implementation.
Production UI proof must come from frontend/src source changes and the running app.
Do not inspect a stale /Volumes/PatentAgent for packaged evidence.
If the worktree is dirty before you start, stop and report the dirty files.
```

## Phase 0 - Baseline And Worktree Setup

Goal: create a safe implementation lane for OMP.

Actions:

- Decide whether the seven current dirty files are intentional WIP.
- If yes, commit or stash them as a baseline before OMP writes.
- Create an implementation branch with the `codex/` prefix, for example `codex/omp-ui-hardening`.
- Create or switch to a clean worktree for OMP implementation.

Acceptance:

- OMP worktree starts clean.
- `git status --short --branch` is recorded in the OMP task report.
- The implementation branch includes or intentionally excludes the current WIP.

## Phase 1 - Workbench Density And State Clarity

Goal: make the workbench feel like a current-project command center without redundant right-rail content or decorative bulk.

Scope:

- `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
- `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`
- `frontend/src/features/workbench/selectors.ts`
- `frontend/src/styles.css`

Work:

- Preserve the existing single-column workbench direction unless the right rail adds distinct value.
- Ensure no-project, selected-project, export-ready, export-locked, and busy states each have a clear next action.
- Replace remaining generic `button` elements with existing shadcn `Button` only where it improves consistency and does not churn unrelated markup.
- Ensure secondary action disclosure does not create layout shift or mobile overflow.
- Keep raw implementation keys and hashes out of the default view.

Tests:

```bash
cd frontend && npm test -- features/workbench/WorkbenchWorkspace.test.tsx
cd frontend && npm test -- features/workbench/selectors.test.ts
```

Visual acceptance:

- Desktop width shows one clear primary action.
- Mobile width has no horizontal overflow.
- Long project names do not overlap status or action controls.

## Phase 2 - Annotated Repair Real Data-Flow And Layout Gate

Goal: harden the embedded annotated repair editor against blank panes, stale review selection, and long issue lists.

Scope:

- `frontend/src/features/documentRepair/AnnotatedRepairTab.tsx`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- `frontend/src/flow/panels/PostDraftIssueRail.tsx`
- `frontend/src/flow/panels/DraftRepairInspector.tsx`
- `frontend/src/PostDraftRepairEditor.test.tsx`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- `frontend/src/styles.css`

Work:

- Verify the selected repair review is current for `currentSourceDraftHash`.
- Preserve explicit loading, error, no-project, no-repairable-review, and empty-session states.
- Ensure `PostDraftRepairEditor mode="embedded"` uses a stable three-pane layout.
- Make the issue rail independently scroll for 10 or more issues.
- Selecting an issue must update the selected draft section and inspector.
- Applying a repair patch must show pending revalidation for that issue.

Tests:

```bash
cd frontend && npm test -- PostDraftRepairEditor.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx
```

Runtime acceptance:

- With a real repairable post-draft review, the repair-session API returns non-empty `issues` and `sections`.
- The editor displays issue rail, draft sections, and inspector.
- A long issue list scrolls inside the rail and does not push the editor below the viewport.

## Phase 3 - Quality Panel Control Polish

Goal: close the current QualityPanel state and responsive-control loop.

Scope:

- `frontend/src/flow/panels/QualityPanel.tsx`
- `frontend/src/flow/panels/QualityPanel.test.tsx`
- `frontend/src/styles.css`

Work:

- Keep the three quality entry cards readable and equally weighted.
- Ensure card action controls fit on mobile.
- Keep `一键接受补强` disabled without proposed patches.
- Ensure it calls `onAcceptAllPatches(completionRun.id)` exactly when proposed patches exist and no busy state blocks it.
- Avoid broad visual restyling outside this panel.

Tests:

```bash
cd frontend && npm test -- flow/panels/QualityPanel.test.tsx
```

Visual acceptance:

- The three cards collapse cleanly from three columns to one or two columns.
- Buttons do not overflow cards.
- Disabled state is visually clear.

## Phase 4 - Shell And Document Repair Visual QA

Goal: verify the shell and document workspace as an integrated product surface.

Scope:

- `frontend/src/app/AppRoot.tsx`
- `frontend/src/app/routes.test.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- `frontend/src/ui/SystemStatusPanel.tsx`
- `frontend/src/features/documentRepair/*`
- `frontend/src/styles.css`

Work:

- Confirm all seven sidebar destinations remain visible and selectable.
- Confirm topbar chip order and diagnostics trigger.
- Confirm document tabs preserve state and route requests from workbench/export.
- Add or update tests only when they protect actual behavior.

Tests:

```bash
cd frontend && npm test -- app/routes.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx
cd frontend && npm run build
```

Visual acceptance:

- Desktop and mobile screenshots for workbench, document repair overview, annotated repair, quality panel, and export.
- No horizontal overflow.
- No overlapping buttons, chips, or tab labels.
- Solid editor surfaces remain readable.

## Codex Review Gate

After each OMP slice, Codex reviews:

- Diff scope against the named files.
- Test command output.
- Screenshot or runtime evidence.
- Whether AGENTS.md source identity was recorded.
- Whether any dirty unrelated files were modified.

Merge blockers:

- Missing source identity.
- OMP edited outside scope.
- Tests fail or were skipped without a concrete blocker.
- UI evidence comes only from docs or static screenshots, not current running source.
- Annotated repair was verified only with DOM mocks.
- Raw JSON, full hashes, run IDs, or logs became visible by default.
