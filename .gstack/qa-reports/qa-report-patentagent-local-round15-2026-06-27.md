# QA Report: PatentAgent Local Round 15

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Project creation form validation:

- Empty project name and empty idea.
- Whitespace-only project name and whitespace-only idea.
- Whitespace-only project name with valid idea.
- Valid project name with whitespace-only idea.
- Verify project API writes, button state, visible validation feedback, and console/network health.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round15 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round15","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round15 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round15_project_create_validation_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-FORM-VALIDATION-001 | 创建项目表单空值/纯空白输入 | 部分通过；未创建污染项目，但没有字段级校验提示 |

## Findings

### BUG-014: Project create form disables submit for blank input without field-level validation feedback

Severity: P3

All invalid cases were safely blocked at the UI layer: no `POST /api/projects` was sent and no project was created. The usability gap is that the user receives no field-level reason. The visible controls are not marked as native required fields, and Playwright captured `required:false`, `valid:true`, and an empty `validationMessage` for the visible project-name input and idea textarea.

Evidence from `.gstack/qa-reports/round15-project-create-validation-state.json`:

- `projects: []`
- Each case had `postRequestsDuringCase: 0`
- Each case had `createButtonDisabled: true`
- Empty and whitespace controls had no native validation message

## Positive Evidence

- Empty form did not create a project.
- Whitespace-only project name and idea did not create a project.
- Whitespace-only project name with valid idea did not create a project.
- Valid project name with whitespace-only idea did not create a project.
- No browser console errors or page errors were observed.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round15-empty-after-submit.png`
- `.gstack/qa-reports/screenshots/round15-both-whitespace-after-submit.png`
- `.gstack/qa-reports/screenshots/round15-name-whitespace-after-submit.png`
- `.gstack/qa-reports/screenshots/round15-idea-whitespace-after-submit.png`

State evidence:

- `.gstack/qa-reports/round15-project-create-validation-state.json`

## Console / Network Notes

- Browser console errors: 0
- Page errors: 0
- `POST /api/projects`: 0
- Failed requests: 4 repeated `GET /api/agents/doctor net::ERR_ABORTED` from repeated page navigation during the probe; no user-visible failure was observed.

## Baseline Update

- New bug ID opened: `BUG-014`.
- Baseline health score changed from `63` to `62`.
- Current cumulative issues: `P1=3`, `P2=8`, `P3=3`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was added only to collect browser evidence and does not affect product behavior.
