# PatentAgent Agent Guardrails

This file is the first checkpoint for Codex, Hermes workers, and any other agent working in this repository. Its purpose is to prevent repeat mistakes where a task is implemented or packaged from the wrong source, wrong branch, stale build artifact, or spec-only design.

## Session Start Checklist

Before editing, packaging, or assigning work, record the source identity:

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

State the branch, short SHA, worktree path, and whether the tree is dirty in the plan or handoff. If the branch or worktree is unexpected, stop and resolve that before continuing.

Do not assume the branch from a previous session is still active. Do not assume the app currently open on macOS was built from the source in the current terminal.

## Source Of Truth For UI Work

Production UI evidence must come from current React/Tauri source and the actual running app:

- Production React lives under `frontend/src/`.
- Tauri desktop packaging lives under `src-tauri/`.
- Specs under `docs/superpowers/`, screenshots, OpenDesign exports, and static prototypes are requirements or references, not implementation evidence.
- A UI change is not done until the relevant production files changed and the running app or packaged app proves the change.

For visual regressions, inspect the real files that render the surface. Common files:

- `frontend/src/App.tsx`
- `frontend/src/views/projectViews.tsx`
- `frontend/src/AgentProviderCards.tsx`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- `frontend/src/styles.css`
- `frontend/src/styles/tokens.css`

## Installed App Versus Current Source

When the user reports a bug from the installed DMG/app, verify both sides explicitly:

- The installed app path, usually `/Applications/PatentAgent.app`.
- The bundled backend health endpoint and data directory from `backend-startup.log`.
- The current source dev server with the same relevant user data when safe.
- Whether the screenshot came from installed app, dev server, or a mounted DMG copy.

If installed app behavior differs from current source behavior, say so directly. Do not patch blindly from screenshots without checking which artifact produced them.

## DMG Packaging Rules

Before handing any DMG to the user, read and apply:

- `docs/release/dmg-ui-regression-guard.md`
- `docs/release/v1.1.0-tauri-release-gate.md`
- `docs/release/v1.1.0-tauri-packaging.md`

Every DMG handoff must include:

- source branch and short SHA
- dirty worktree status and intentional local files included
- absolute DMG path
- DMG size and SHA256
- smoke summary path
- packaged UI evidence from the exact artifact, not from a stale `/Volumes/PatentAgent`

The default Tauri output filename is reused between builds, so avoid relying on filename alone. Detach stale volumes before inspection and prefer an identity-bearing copy name containing the short SHA and timestamp.

## Annotated Repair Editor Regression Gate

For the post-draft annotated repair editor, do not accept DOM-only evidence. Verify the real data flow:

- The selected project has a post-draft review run eligible to open the editor.
- `GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session` returns non-empty `issues` and non-empty draft `sections`.
- The "打开标注式修复编辑器" button is enabled when a repairable review exists.
- The editor shows the issue list, the middle draft sections, and the right issue detail panel.
- Clicking an issue updates the highlighted section and the inspector.
- Long issue lists scroll inside their own pane and do not push the draft editor off screen.

If the middle pane or inspector is blank, debug in this order: API payload, review-run selection, editor state selection, section fallback data, CSS visibility/overflow.

## Hermes And PR Workflow

Do not dispatch Hermes/worker tasks until the root cause and acceptance checks are clear. Each task must include:

- target branch and worktree path
- exact files or modules in scope
- commands to run
- screenshot or browser-verification requirements for UI work
- merge blocker conditions

The reviewing agent must inspect diffs, run the stated checks, and verify the integrated app before merging. Do not merge worker output just because tests pass in isolation.

## Anti-Patterns To Avoid

- Rebuilding the same source repeatedly when the bug is that the source is old or wrong.
- Treating specs, screenshots, or design exports as proof that production React changed.
- Inspecting a stale mounted `/Volumes/PatentAgent`.
- Saying a dirty build represents only `HEAD`.
- Testing only a fixture when the bug depends on real project data.
- Assigning implementation work before reproducing the failure and identifying the likely root cause.
- Reverting unrelated user changes while trying to get back to a known state.
