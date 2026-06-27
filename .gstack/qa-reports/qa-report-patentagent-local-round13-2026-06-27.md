# QA Report: PatentAgent Local Round 13

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Navigation/history behavior for a user who returns or goes forward mid-flow:

- Start from the guided invention entry.
- Create a project through the UI.
- Navigate to the project list.
- Use browser Back and Forward.
- Attempt to return to the three-entry guided start state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round13 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round13","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round13 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round13_navigation_history_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-NAV-001 | 创建项目后项目页 -> browser Back -> browser Forward -> 应用内返回入口 | 失败；Back 进入 `about:blank` 空白页，Forward 后项目/工作流上下文丢失且 `返回三选一` 不可见 |

## Findings

### BUG-012: Browser Back navigates the SPA to about:blank and loses workflow context

Severity: P2

After creating a project and navigating to the project list, browser Back sends the page to `about:blank` with an empty body. Browser Forward restores `http://127.0.0.1:5174/`, but the app returns to the start screen with lost workflow context, and the in-app `返回三选一` control is not visible.

Evidence from `.gstack/qa-reports/round13-navigation-history-state.json`:

- `round13-after-browser-back.url` is `about:blank`.
- `round13-after-browser-back.bodyText` is empty.
- `round13-after-browser-back.htmlSnippet` is `<html><head></head><body></body></html>`.
- `round13-after-browser-forward.forwardResult.status` is `200`.
- `returnThreeChoicesError` is `Could not find visible control for return three choices`.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round13-start-page.png`
- `.gstack/qa-reports/screenshots/round13-create-form.png`
- `.gstack/qa-reports/screenshots/round13-after-create.png`
- `.gstack/qa-reports/screenshots/round13-projects-page.png`
- `.gstack/qa-reports/screenshots/round13-after-browser-back.png`
- `.gstack/qa-reports/screenshots/round13-after-browser-forward.png`
- `.gstack/qa-reports/screenshots/round13-return-three-choices-unavailable.png`

State evidence:

- `.gstack/qa-reports/round13-navigation-history-state.json`

## Console / Network Notes

- Browser console errors: 0
- Page errors: 0
- Failed requests: 2 navigation-aborted `GET /api/agents/doctor` requests during route/history transitions
- Mutating requests observed: 1 `POST /api/projects`

## Baseline Update

- New bug ID opened: `BUG-012`.
- Baseline health score changed from `65` to `64`.
- Current cumulative issues: `P1=3`, `P2=7`, `P3=2`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was updated only to preserve evidence after failure and does not affect product behavior.
