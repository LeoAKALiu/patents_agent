# QA Report: PatentAgent Local Round 21

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Slow project-creation response plus rapid repeated submit:

- Create an invention project from the first guided-flow entry.
- Delay `POST /api/projects` by 1.8 seconds in the browser route.
- Click `创建并继续`.
- Attempt a second click before the delayed response returns.
- Verify POST count, final project count, submit disabled/busy state, and browser error health.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round21 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round21","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Project: `Round21 慢创建双击项目 1782496061413`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round21 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round21_create_double_click_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-DOUBLE-CLICK-002 | 慢网络下重复点击创建项目 | 通过；只产生一个创建 POST，最终只有一个同名项目 |

## Findings

No new product bug opened in Round21.

During the delayed create response, the page showed `正在创建专利项目`, the submit control was disabled, and the second click attempt did not create another request. After the response returned, `/api/projects` contained exactly one project with the Round21 name.

## Positive Evidence

- `firstCreateResponseStatus: 200`
- `postRequestCount: 1`
- `postResponseCount: 1`
- `matchingProjectCount: 1`
- `onlyOneCreatePost: true`
- `onlyOneMatchingProject: true`
- `submitDisabledAfterFirstClick: true`
- `secondClickBlockedOrIgnored: true`
- No page errors, request failures, or console errors were recorded.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round21/01-load-app.png`
- `.gstack/qa-reports/screenshots/round21/02-filled-project-form.png`
- `.gstack/qa-reports/screenshots/round21/03-after-first-click-before-response.png`
- `.gstack/qa-reports/screenshots/round21/04-after-second-click-attempt.png`
- `.gstack/qa-reports/screenshots/round21/05-after-create-response.png`

State evidence:

- `.gstack/qa-reports/round21-create-double-click-state.json`

## Baseline Update

- New bug ID opened: none.
- `TC-DOUBLE-CLICK-002` now has a concrete Round21 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The slow network condition was simulated by delaying the browser route for `POST /api/projects`.
