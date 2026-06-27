# QA Report: PatentAgent Local Round 6

Status: DONE_WITH_CONCERNS

Date: 2026-06-26

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Network and local backend failure handling:

- Frontend opens while the backend is not running.
- Backend is stopped after a real project has already been loaded.
- Home, project list, settings, global status cards, and cached project state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend-down path: no service on `127.0.0.1:8000`
- Mid-session path: `DATA_DIR=.gstack/qa-reports/runtime-data-round6 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Test project: `Round6 网络中断项目`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round6 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
curl -sS -X POST http://127.0.0.1:8000/api/projects -H 'Content-Type: application/json' -d '{"name":"Round6 网络中断项目","draft_text":"一种用于网络异常 QA 的临时专利想法。","patent_type":"invention"}'
node .gstack/qa-reports/round6_backend_stop_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-NETWORK-001 | 后端未启动时首次加载首页、项目页、设置页 | 失败；页面有 500 banner，但仍显示部分能力可用，项目页把加载失败表现为 0 项 |
| TC-NETWORK-001 | 已选择项目后停止后端，再刷新状态并切换页面 | 失败；顶部出现 500，但缓存项目和能力状态仍显示为可用/完整会审且没有离线标记 |

## Positive Evidence

- 后端正常时，前端可以加载项目并进入 guided flow。
- 后端断开后，页面没有崩溃或白屏，设置页提供了 `重试` 按钮。
- API 失败会通过顶部错误 banner 暴露 `GET /api/health 返回 500`。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round6-backend-down-home.png`
- `.gstack/qa-reports/screenshots/round6-backend-down-projects.png`
- `.gstack/qa-reports/screenshots/round6-backend-down-settings.png`
- `.gstack/qa-reports/screenshots/round6-before-backend-stop.png`
- `.gstack/qa-reports/screenshots/round6-selected-before-stop.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-refresh.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-projects.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-settings.png`

State evidence:

- `.gstack/qa-reports/round6-backend-down-state.json`
- `.gstack/qa-reports/round6-backend-stop-state.json`

## Findings

### ISSUE-010 / BUG-010: Backend Outage Leaves Stale Available States And Ambiguous Project Data

Severity: Medium / P2

Repro:

1. Start only the frontend with the backend unavailable.
2. Open home, projects, and settings.
3. Start backend, create/select `Round6 网络中断项目`, then stop backend.
4. Click `刷新运行状态`, then open projects and settings.

Actual:

- Backend-down first load records repeated 500 responses for `/api/health`, `/api/agents/doctor`, `/api/corpus`, `/api/projects`, and `/api/desktop-config`.
- The sidebar still displays `内部痕迹检查 可用`.
- In the mid-session path, after `/api/health` returns 500, the sidebar still displays `基础模型 可用`, `智能体 完整会审`, and `内部痕迹检查 可用`.
- The projects page renders failed `/api/projects` as `全部项目 0` / `暂无项目` on first load, and renders cached `全部项目 1` after disconnect without marking the data as stale.
- Settings shows raw `加载失败:GET /api/desktop-config 返回 500:` without a clear local-backend-unavailable explanation.

Expected:

- Global health failure should put the app into an explicit offline/backend-unavailable state.
- Capability badges should not show `可用` or `完整会审` while the backend is unavailable.
- Project list should distinguish load failure from a true empty list.
- Cached project data should be marked as stale/offline and backend-dependent actions should be disabled.

Evidence:

- `.gstack/qa-reports/screenshots/round6-backend-down-projects.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-refresh.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-projects.png`
- `.gstack/qa-reports/screenshots/round6-after-stop-settings.png`
- `.gstack/qa-reports/round6-backend-down-state.json`
- `.gstack/qa-reports/round6-backend-stop-state.json`

## Console / API Health

- Backend-down first load: 14 browser console resource errors, all from `/api/*` 500 responses.
- Mid-session backend stop: 8 browser console resource errors after the backend was stopped.
- No page-level JavaScript exceptions were observed.

## Baseline Update

- Added `BUG-010`.
- Baseline health score changed from `69` to `66`.
- Current cumulative issues: `P1=3`, `P2=6`, `P3=1`.

## Notes

- I did not repair any code.
- The backend used for this round was intentionally stopped by the Playwright probe to verify runtime outage behavior.
