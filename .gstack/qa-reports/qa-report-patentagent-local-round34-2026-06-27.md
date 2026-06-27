# PatentAgent QA Report - Round34 Editable Long Text Inputs

## Metadata

- Date: 2026-06-27
- Source branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree: yes; includes pre-existing `README.md`, QA docs, `BUGS.md`, and local QA evidence
- Target: `http://127.0.0.1:5174/`
- Backend: `http://127.0.0.1:8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round34-clean","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Runtime data dir: `.gstack/qa-reports/runtime-data-round34-clean`
- Browser: local Chromium via Playwright
- Viewports: desktop 1440x1100, mobile 390x1100

## Scope

Round34 covered the remaining long-text editable-input case from the matrix:

- Desktop `项目名称` input and `一句话想法` textarea with a 680-character no-break token and 2225-character long idea.
- Desktop submit flow for a long-text project.
- Auto-generated `外部 Deep Research 提示词` textarea after project creation.
- Mobile `项目名称` input and `一句话想法` textarea at 390px width.

This run did not inspect or modify product source code.

## Result Summary

| Case | Result | Evidence |
|---|---|---|
| `TC-LONGTEXT-005` | Pass | `.gstack/qa-reports/round34-editable-long-text-state.json` |
| Desktop create form editables | Pass | no page horizontal overflow; textarea wraps and scrolls vertically |
| Mobile create form editables | Pass | no page horizontal overflow; textarea wraps and scrolls vertically |
| Desktop submit | Pass | project created: `f00a139b829441b6a2b06294d5752b70` |
| Auto-generated prompt textarea | Pass | `外部 Deep Research 提示词` has no horizontal overflow and scrolls vertically |

## Key Evidence

- Long token length: 680
- Long idea length: 2225
- Action failures: 0
- Page errors: 0
- Console errors: 0
- Page states with horizontal overflow: none
- Offscreen long-token editable controls: 0
- Request failures: 2 navigation-aborted `/api/agents/doctor` requests during page transitions; backend logs showed successful health/project/API responses and no product failure was observed.

Editable metrics:

- Desktop `一句话想法`: `width:639`, `scrollWidth:637`, `scrollHeight:973`, `whiteSpace:"pre-wrap"`, `overflowWrap:"break-word"`.
- Mobile `一句话想法`: `width:262`, `scrollWidth:260`, `scrollHeight:2387`, `whiteSpace:"pre-wrap"`, `overflowWrap:"break-word"`.
- Desktop `外部 Deep Research 提示词`: `width:1005`, `scrollWidth:1003`, `scrollHeight:1270`, `whiteSpace:"pre-wrap"`, `overflowWrap:"break-word"`.

The `项目名称` input naturally has large internal `scrollWidth` as a single-line input, but it remained inside the viewport on desktop and mobile and did not create page-level horizontal overflow.

## Existing Issue Observed

After desktop project creation, the long project name also reproduced the already-known current-project selector/topbar overflow class tracked as `BUG-013`. This was not opened as a new bug because it is duplicate coverage of an existing finding.

## Baseline Update

No new bug was added. Baseline remains:

- Health score: 58
- Issue totals: `P1=3`, `P2=11`, `P3=6`

## Artifacts

- Probe: `.gstack/qa-reports/round34_editable_long_text_probe.js`
- State: `.gstack/qa-reports/round34-editable-long-text-state.json`
- Screenshots:
  - `.gstack/qa-reports/screenshots/round34-editable/01-start-desktop.png`
  - `.gstack/qa-reports/screenshots/round34-editable/02-create-form-empty-desktop.png`
  - `.gstack/qa-reports/screenshots/round34-editable/03-create-form-filled-desktop.png`
  - `.gstack/qa-reports/screenshots/round34-editable/04-after-create-desktop.png`
  - `.gstack/qa-reports/screenshots/round34-editable/06-create-form-empty-mobile.png`
  - `.gstack/qa-reports/screenshots/round34-editable/07-create-form-filled-mobile.png`
