# QA Report: PatentAgent Local Round 23

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Empty project list for a new user / clean data directory:

- Start the app with isolated Round23 data.
- Confirm `/api/projects` returns an empty project list.
- Navigate to `项目` from the UI.
- Verify empty-state copy, summary counters, current-project selector, and absence of horizontal overflow on desktop and mobile.
- Return to `开始` and confirm the patent-generation entry cards remain reachable.
- Confirm viewing the empty list does not create a project.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round23 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round23","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright
- Viewports: desktop `1440x1100`, mobile `390x1100`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round23 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round23_empty_projects_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PROJECTS-001 | 无项目数据时进入项目页查看空列表 | 通过；空状态可理解，桌面/移动无横向溢出，可返回开始页创建项目 |

## Findings

No new product bug opened in Round23.

The Projects page showed zero counters and the empty-state message `暂无项目。进入“专利生成”输入想法即可创建。` The current-project selector showed `暂无项目`, and returning to `开始` restored the three patent-generation entry cards. The API stayed empty before and after visiting the page.

## Positive Evidence

- `initialProjectsEmpty: true`
- `projectsAfterNavEmpty: true`
- `projectsPageShowsEmptyState: true`
- `desktopNoHorizontalOverflow: true`
- `mobileNoHorizontalOverflow: true`
- `currentProjectSelectorShowsNoProject: true`
- `canReturnToStart: true`
- `noProjectCreatedByViewingEmptyList: true`
- No page errors, request failures, or console errors were recorded.

API evidence before and after navigation:

```json
{"projects":[]}
```

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round23/01-home-empty-data.png`
- `.gstack/qa-reports/screenshots/round23/02-projects-empty-desktop.png`
- `.gstack/qa-reports/screenshots/round23/03-projects-empty-mobile.png`
- `.gstack/qa-reports/screenshots/round23/04-return-to-start.png`

State evidence:

- `.gstack/qa-reports/round23-empty-projects-state.json`

## Baseline Update

- New bug ID opened: none.
- `TC-PROJECTS-001` now has a concrete Round23 probe command.
- `TC-SWITCH-001` matrix row was also linked to the existing Round12 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The first script run used an overly narrow API-shape assertion; `/api/projects` correctly returned `{"projects":[]}`. The probe was corrected and rerun successfully.
