# DMG UI Regression Guard

This document records the release mistakes that caused a packaged DMG to show an older or visually regressed UI even though design/spec work existed elsewhere. Treat it as a mandatory guardrail before handing a DMG to a user for visual review.

Agent-facing development rules live in [`../../AGENTS.md`](../../AGENTS.md). Read that file before packaging or delegating UI work.

## Core Rule

Do not claim a packaged UI is current unless the exact DMG was built from the exact source revision under review and the packaged app itself has been launched or smoke-tested.

Specs, screenshots, OpenDesign exports, static HTML prototypes, and planning docs are not implementation evidence. A UI change is only implemented when the current React/Tauri source diff contains the change and the generated DMG proves it.

## Pre-Build Source Identity

Record these before any DMG build:

```bash
git status --short --branch
git rev-parse --short HEAD
git diff --stat
```

Required release note fields:

- branch name
- short commit SHA
- whether the worktree is clean
- if dirty, the exact files that are intentionally included
- DMG path that will be produced

If the worktree is dirty, do not say the DMG represents only `HEAD`; say it represents `HEAD + local changes` and list those changes.

If a previous task used a temporary worktree, stale branch, or installed app, re-run these commands in the current terminal before building. The source identity must be gathered from the same checkout that runs `tauri build`.

## Spec-To-Implementation Check

Before packaging a UI change, map every visual requirement to the actual frontend files that changed.

For the post-draft/workbench UI family, at minimum inspect these files when relevant:

- `frontend/src/views/projectViews.tsx`
- `frontend/src/AgentProviderCards.tsx`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/styles.css`
- `frontend/src/styles/tokens.css`

Failure mode to avoid: treating `docs/ui-redesign/*`, `docs/superpowers/specs/*`, or an OpenDesign artifact as proof that the production React app has the same UI.

For bugs reported from screenshots, also identify the artifact that produced the screenshot: installed `/Applications/PatentAgent.app`, dev server, copied smoke app, or mounted DMG. If the artifact is not known, the screenshot is a symptom, not release evidence.

## Stale DMG And Mounted Volume Guard

macOS can keep an older `/Volumes/PatentAgent` mounted while a new DMG with the same name is generated. That makes manual inspection ambiguous.

Before inspecting a newly built DMG:

```bash
hdiutil info
hdiutil detach /Volumes/PatentAgent
```

If `/Volumes/PatentAgent` is not mounted, `detach` may fail harmlessly. After rebuilding, mount or smoke-test the specific DMG path and check the mounted volume timestamp.

Do not inspect an already-mounted `/Volumes/PatentAgent` unless its mount time and source image path match the just-built artifact.

## Artifact Naming

The default Tauri output name is reusable:

```text
src-tauri/target/release/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg
```

For human review handoff, also create or report an identity-bearing name:

```text
PatentAgent_1.1.0_<short-sha>_<yyyymmdd-hhmm>.dmg
```

This prevents a reviewer from opening a stale DMG with the same default filename.

## Required Packaged UI Checks

Run the normal build and smoke commands first:

```bash
npm --prefix frontend run test
npm --prefix frontend run build
cargo tauri build --bundles dmg --ci
hdiutil verify src-tauri/target/release/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg
python3 scripts/tauri_dmg_smoke.py src-tauri/target/release/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg --keep-artifacts
```

Then perform a visual or browser-level check against the packaged renderer. At minimum cover these regressions:

- Start screen: entry choices are compact workbench rows, not oversized three-column cards.
- Agent provider cards: labels such as `必选席不可关闭` and `加入本轮` remain one horizontal line or ellipsize; they must not collapse into vertical text.
- Sidebar: no horizontal scrollbar; long project names and footer controls do not widen the shell.
- Workbench pages: the right-side draft editor and repair panel remain usable at normal desktop widths.
- Annotated repair editor: issue list, middle draft sections, and right issue detail panel are all visible from a real repair-session payload.

When browser automation is available, capture these facts:

```js
document.body.scrollWidth === window.innerWidth
getComputedStyle(document.querySelector(".agent-provider-toggle-label")).whiteSpace === "nowrap"
```

For the start screen, save a screenshot of the actual running app or packaged app, not a static mockup.

## Complete DMG Contents

A "complete DMG" means the app contains both renderer and backend runtime resources. Verify package contents after mounting or from the smoke directory:

```bash
find PatentAgent.app/Contents/Resources -maxdepth 2 -type f -name patentagent-backend -print
find PatentAgent.app/Contents/Resources -maxdepth 3 -type f -name main.py -print
codesign --verify --deep --strict --verbose=2 PatentAgent.app
```

The smoke report must show:

- `bundled_backend_ok: true`
- `bundled_backend_executable_ok: true`
- `backend_startup.log` contains `trying bundled backend:`
- `health.ok: true`
- `app_alive_after_quit: false`
- `backend_alive_after_quit: false`

## Release Report Template

Use this short block in handoff notes:

```text
Source: <branch>@<short-sha> (+ local changes: yes/no)
DMG: <absolute path>
Size: <du -h>
SHA256: <shasum -a 256>
Build: cargo tauri build --bundles dmg --ci => pass/fail
DMG verify: pass/fail
DMG smoke: pass/fail
Bundled backend: pass/fail
UI screenshots checked:
- start screen compact rows: pass/fail
- agent labels horizontal: pass/fail
- no shell horizontal overflow: pass/fail
Notarization: not run / pass / fail
```

## Incident Memory

On 2026-06-19, a DMG was handed off after design/spec work existed, but the current React components still rendered older oversized start cards, agent cards with vertical labels, and a horizontally overflowing sidebar. The correct fix was not to rebuild the same source repeatedly; it was to patch the actual production React components and CSS, rebuild the DMG, unload stale mounted volumes, and smoke-test the exact artifact.

The same incident also showed why workers must not continue from an assumed branch or stale build directory. Future handoffs must state whether the artifact came from `HEAD`, `HEAD + local changes`, or a separate worktree/branch, and must include the exact SHA and DMG hash.

Keep this document updated whenever a packaging or UI handoff mistake happens.
