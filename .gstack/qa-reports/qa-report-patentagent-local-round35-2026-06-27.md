# PatentAgent QA Report - Round35 Project List Search Entry Discovery

## Metadata

- Date: 2026-06-27
- Source branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree: yes; includes pre-existing `README.md`, QA docs, `BUGS.md`, and local QA evidence
- Target: `http://127.0.0.1:5174/`
- Backend: `http://127.0.0.1:8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round35-clean","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Runtime data dir: `.gstack/qa-reports/runtime-data-round35-clean`
- Browser: local Chromium via Playwright
- Viewports: desktop 1440x1100, mobile 390x1100

## Scope

Round35 covered the remaining matrix note for project-list search:

- Seeded 6 projects with distinct names and one `utility_model` project.
- Opened the real `项目` page on desktop and mobile.
- Enumerated visible inputs, selects, buttons, search-like controls, and filter chips.
- Checked for product search inputs/buttons by visible label, aria-label, and placeholder.

This run did not inspect or modify product source code.

## Result Summary

| Item | Result | Evidence |
|---|---|---|
| Desktop project list loads seeded projects | Pass | 6 seeded projects visible |
| Mobile project list loads seeded projects | Pass | 6 seeded projects visible |
| Status filters | Present | `全部项目 6`, `已有初稿 0`, `仅有想法 6`, `实用新型 1` |
| Project-list search input/button | Not present in current product | no visible input, search button, aria-label, or placeholder matching search/query terms |
| Runtime errors | Pass | 0 page errors, 0 request failures, 0 console errors |

## Finding

No new bug was opened. The current product does not expose a project-list search entry; it only exposes status filter chips. Therefore the previous matrix note is now archived as future-feature coverage: if a search input or search button is added later, add a dedicated project-list search test case.

Round35 also re-observed the known mobile project-list edge where controls at the right side can be partially clipped on narrow screens. That class is already tracked under existing mobile project-list findings and was not opened as a duplicate.

## Baseline Update

No new bug was added. Baseline remains:

- Health score: 58
- Issue totals: `P1=3`, `P2=11`, `P3=6`

## Artifacts

- Probe: `.gstack/qa-reports/round35_project_search_probe.js`
- State: `.gstack/qa-reports/round35-project-search-state.json`
- Screenshots:
  - `.gstack/qa-reports/screenshots/round35-project-search/01-start-desktop.png`
  - `.gstack/qa-reports/screenshots/round35-project-search/02-projects-desktop.png`
  - `.gstack/qa-reports/screenshots/round35-project-search/04-projects-mobile.png`
