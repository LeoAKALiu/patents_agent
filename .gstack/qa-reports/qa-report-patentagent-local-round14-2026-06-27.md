# QA Report: PatentAgent Local Round 14

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Extreme long-text display behavior:

- Create an invention project through the UI.
- Use a 417-character project name containing a 390-character unbroken technical identifier.
- Use a 3249-character technical idea.
- Check desktop and mobile topbar/current-project UI, sidebar project context, workflow body, and page-level horizontal overflow.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round14 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round14","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 and 390x1100 viewports

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round14 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round14_long_text_overflow_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-LONGTEXT-001 | 超长项目名、连续无空格技术标识符、长技术想法在桌面/移动端展示 | 失败；项目可创建，但桌面 topbar 当前项目选择器被长名称撑到视口外 |

## Findings

### BUG-013: Long project names push the topbar current-project selector offscreen

Severity: P2

The project is created successfully and the page itself does not gain horizontal scroll, but the desktop topbar current-project selector expands to the full option width. The label and left side of the select are pushed outside the viewport, leaving the user with only the tail of the long project name.

Evidence from `.gstack/qa-reports/round14-long-text-overflow-state.json`:

- `.topbar-actions-group`: `left:-2534`, `right:1416`, `width:3950`
- `当前项目` label: `left:-2534`, `right:-2482`
- `select`: `left:-2474`, `right:1095`, `width:3569`
- Page-level scroll remained `bodyScrollWidth:1440`, `docScrollWidth:1440`; the offscreen left content is not reachable via horizontal scrolling.

Mobile note: at 390px width the select remains within the viewport (`left:70`, `right:380`, `width:310`) but its internal `scrollWidth` is 3538px. That is visually clipped rather than pushing the page horizontally.

## Positive Evidence

- The app accepted and persisted the 417-character project name.
- The app accepted and persisted the 3249-character technical idea.
- No page-level horizontal overflow was detected in desktop or mobile viewports.
- No browser console errors, page errors, or failed requests were observed.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round14-start-desktop.png`
- `.gstack/qa-reports/screenshots/round14-filled-long-form-desktop.png`
- `.gstack/qa-reports/screenshots/round14-after-create-desktop.png`
- `.gstack/qa-reports/screenshots/round14-projects-desktop.png`
- `.gstack/qa-reports/screenshots/round14-projects-mobile.png`
- `.gstack/qa-reports/screenshots/round14-start-mobile-with-long-project.png`

State evidence:

- `.gstack/qa-reports/round14-long-text-overflow-state.json`

## Console / Network Notes

- Browser console errors: 0
- Page errors: 0
- Failed requests: 0
- Mutating requests observed: `POST /api/projects` and one workflow `POST /api/projects/{id}/disclosures` during navigation/exploration

## Baseline Update

- New bug ID opened: `BUG-013`.
- Baseline health score changed from `64` to `63`.
- Current cumulative issues: `P1=3`, `P2=8`, `P3=2`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was added only to collect browser evidence and does not affect product behavior.
