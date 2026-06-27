# PatentAgent QA Report - Round36 Missing Path File Selection

## Metadata

- Date: 2026-06-27
- Source branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree: yes; includes pre-existing `README.md`, QA docs, `BUGS.md`, and local QA evidence
- Target: `http://127.0.0.1:5174/`
- Backend: `http://127.0.0.1:8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round36","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Runtime data dir: `.gstack/qa-reports/runtime-data-round36`
- Browser: local Chromium via Playwright
- Installed app path checked: `/Applications/PatentAgent.app` exists

## Scope

Round36 covered the final remaining matrix note for nonexistent local file paths:

- Created a project through the real UI.
- Waited until the supplemental-material upload area was visible.
- Tried to pass a definitely nonexistent Markdown path through the browser file chooser.
- Verified material counts and upload requests after the attempt.

This run did not inspect or modify product source code. It did not use computer-use for the native macOS picker because GUI file upload requires explicit confirmation and the normal picker path does not allow a user to select a nonexistent file directly.

## Result Summary

| Item | Result | Evidence |
|---|---|---|
| Project created through UI | Pass | Project `39e5ee5e97a249afaab9f19f39c12a8c` |
| Upload controls ready before attempt | Pass | `uploadControlWait.ok=true`, `fileInputCount=1`, `uploadButtonVisible=true` |
| Missing path exists on disk | Pass | `missingPathExists=false` |
| Browser file chooser blocks nonexistent path | Pass | `setInputFiles.ok=false`, `via=filechooser`, `ENOENT: no such file or directory` |
| App receives no material upload | Pass | `materialPostCountBefore=0`, `materialPostCountAfter=0` |
| Material count unchanged | Pass | `materialCountBefore=0`, `materialCountAfter=0` |
| Runtime errors | Pass | 0 page errors, 0 request failures, 0 console errors |

## Finding

No new bug was opened. Browser automation cannot truthfully reproduce a user selecting a nonexistent local file path because Chromium/Playwright rejects the path before the app receives any upload event. The app therefore had no product behavior to evaluate in this run.

The coverage is now represented as manual desktop/Tauri case `TC-UPLOAD-004`: choose a nonexistent path if possible, or choose a file and delete/move it before the app reads it. The expected product behavior remains a friendly file-not-found/read-failure message, no internal stack/path leak, and no material count increase.

## Baseline Update

No new bug was added. Baseline remains:

- Health score: 58
- Issue totals: `P1=3`, `P2=11`, `P3=6`

## Artifacts

- Probe: `.gstack/qa-reports/round36_missing_path_file_probe.js`
- State: `.gstack/qa-reports/round36-missing-path-file-state.json`
- Screenshots:
  - `.gstack/qa-reports/screenshots/round36-missing-path/01-start.png`
  - `.gstack/qa-reports/screenshots/round36-missing-path/02-create-form-filled.png`
  - `.gstack/qa-reports/screenshots/round36-missing-path/03-project-created.png`
  - `.gstack/qa-reports/screenshots/round36-missing-path/03c-upload-control-ready.png`
  - `.gstack/qa-reports/screenshots/round36-missing-path/04-after-missing-path-attempt.png`
