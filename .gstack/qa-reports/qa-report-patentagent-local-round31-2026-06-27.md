# QA Report: PatentAgent Local Round 31

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

User-monkey navigation smoke:

- Open a clean workspace.
- Visit `项目`, `设置`, `开始`.
- Rapidly click `刷新运行状态`.
- Create one invention project.
- Open the expert tools entry.
- Switch to mobile 390px and navigate current workflow, settings, projects, and start.
- Check console errors, page errors, request failures, horizontal overflow, and mobile touch target sizes.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round31 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round31","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright
- Viewports: desktop `1440x1100`; mobile `390x1100`
- Project: `Round31 用户猴子导航 1782499213859`

## Commands / Probes

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round31 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
node .gstack/qa-reports/round31_monkey_navigation_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-MONKEY-001 | 新手/误操作用户连续切换导航、创建项目、进入专家工具、移动端来回切换 | 失败；无崩溃和无横向溢出，但移动端触控目标不足 |

## Findings

### New BUG-018: Mobile navigation and settings controls use sub-44px touch targets

Severity: P3

Round31 found no page errors, request failures, console errors, or page-level horizontal overflow. However, the mobile pass recorded 29 visible controls below 44px height, including the top project selector, topbar buttons, settings inputs/buttons, project filter chips, and the mobile primary action.

The script also recorded one action failure: it attempted to find `查看前置材料详情` after entering the expert tools workbench. That button exists in the guided-flow context, not in the expert-tools workbench view reached by the probe, so this is not logged as a product bug.

## Positive Evidence

- `pageErrors: 0`
- `requestFailures: 0`
- `consoleErrors: 0`
- `desktopHorizontalOverflow: false`
- `mobileHorizontalOverflow: false`
- `projectNameVisibleAfterCreate: true`
- `settingsReached: true`
- `projectsReached: true`
- `expertToolsReached: true`

## Failure Evidence

- `mobileControlsBelow44Count: 29`
- Examples from the state file:
  - Current-project selector: 40px high.
  - `专家工具` / `返回向导` / `返回三选一`: 32px high.
  - Refresh icon button: 32px high.
  - Settings inputs/buttons: 40px high.
  - Project filter chips: 36px high.
  - Mobile primary action `提炼发明点`: 40px high.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round31/01-home-desktop.png`
- `.gstack/qa-reports/screenshots/round31/02-projects-empty-desktop.png`
- `.gstack/qa-reports/screenshots/round31/03-settings-desktop.png`
- `.gstack/qa-reports/screenshots/round31/04-after-rapid-refresh-status.png`
- `.gstack/qa-reports/screenshots/round31/05-create-form-empty.png`
- `.gstack/qa-reports/screenshots/round31/06-after-project-create.png`
- `.gstack/qa-reports/screenshots/round31/07-expert-tools-open.png`
- `.gstack/qa-reports/screenshots/round31/08-material-detail-empty.png`
- `.gstack/qa-reports/screenshots/round31/09-mobile-current-workflow.png`
- `.gstack/qa-reports/screenshots/round31/10-mobile-settings.png`
- `.gstack/qa-reports/screenshots/round31/11-mobile-projects.png`
- `.gstack/qa-reports/screenshots/round31/12-mobile-start-after-navigation.png`

State evidence:

- `.gstack/qa-reports/round31-monkey-navigation-state.json`

## Baseline Update

- New bug ID opened: `BUG-018`.
- Added matrix case: `TC-MONKEY-001`.
- Baseline accessibility score changed from `85` to `82`.
- Baseline health score remains `60` after rounding.
- Current cumulative issues: `P1=3`, `P2=9`, `P3=6`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- This was exploratory monkey-style navigation, not a deterministic feature-specific regression.
