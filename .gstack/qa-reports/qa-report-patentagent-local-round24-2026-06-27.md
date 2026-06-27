# QA Report: PatentAgent Local Round 24

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Project list stress and responsive layout:

- Seed 30 projects through the local API, including 7 utility-model projects and several long project names.
- Open `项目` from the UI.
- Verify desktop counters, utility-model filtering, and top current-project selection.
- Switch to mobile `390x1100`.
- Verify filter chips and project action buttons stay inside the viewport before and after selecting a project.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round24 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round24","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright
- Viewports: desktop `1440x1100`, mobile `390x1100`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round24 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round24_projects_stress_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PROJECTS-002 | 30 个项目、长项目名、实用新型筛选、桌面/移动端选择项目 | 失败；桌面统计/筛选/选择通过，但移动端筛选 chip 和操作按钮越界，复现 `BUG-008` |

## Findings

### Existing BUG-008: Mobile project list controls exceed viewport

Severity: P2

Round24 reproduced the existing mobile project list layout defect with fresh isolated data. Desktop checks passed: 30 seeded projects were visible, `实用新型 7` was shown, utility filtering displayed utility projects, and the top selector could switch to the target project.

On mobile, the page document width remained `390`, but clipped controls inside the content exceeded the visible viewport:

- `实用新型 7` chip: `left=384`, `right=485`
- First visible `选择项目` button before selection: `width=1011`, `right=1073`
- After selecting a project, `全部项目 30` chip shifted to `left=-17`

## Positive Evidence

- `seededThirtyProjects: true`
- `apiShowsThirtyProjects: true`
- `desktopShowsThirtyProjects: true`
- `desktopShowsSevenUtilityModels: true`
- `desktopUtilityFilterApplied: true`
- `topSelectorCanChooseProject: true`
- `desktopNoHorizontalOverflow: true`
- No page errors, request failures, or console errors were recorded.

## Failed Assertions

- `mobileFilterChipsWithinViewport: false`
- `mobileActionButtonsWithinViewport: false`
- `mobileAfterSelectElementsWithinViewport: false`

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round24/01-projects-many-desktop.png`
- `.gstack/qa-reports/screenshots/round24/02-projects-utility-filter-desktop.png`
- `.gstack/qa-reports/screenshots/round24/03-projects-after-top-select-desktop.png`
- `.gstack/qa-reports/screenshots/round24/04-projects-many-mobile.png`
- `.gstack/qa-reports/screenshots/round24/05-projects-mobile-after-select.png`

State evidence:

- `.gstack/qa-reports/round24-projects-stress-state.json`

## Baseline Update

- New bug ID opened: none.
- Existing `BUG-008` updated with Round24 repro evidence.
- `TC-PROJECTS-002` now has a concrete Round24 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The 30 projects were seeded by API as scenario setup; list navigation, filtering, top selection, and mobile selection were exercised through the UI.
