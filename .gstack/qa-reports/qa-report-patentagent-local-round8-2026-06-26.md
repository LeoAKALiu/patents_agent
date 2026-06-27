# QA Report: PatentAgent Local Round 8

Status: DONE_WITH_CONCERNS

Date: 2026-06-26

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Project list state management:

- Multiple isolated projects.
- Project list filter switching.
- Current project selection.
- Delete confirmation cancel.
- Delete confirmation accept for the current project.
- Current-project selector and API state after deletion.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round8 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round8","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Seed projects:
  - `Round8 Alpha 删除目标`
  - `Round8 Beta 保留项目`
  - `Round8 Gamma 保留项目`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round8 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round8_project_delete_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PROJECTS-002 | 多项目桌面列表、实用新型筛选、项目选择 | 通过；统计、筛选、当前项目状态一致 |
| TC-PROJECTS-003 | 删除当前项目：先取消，再确认 | 通过；取消后项目数仍为 3，确认后目标项目删除，UI 和 API 均剩 2 个项目 |

## Positive Evidence

- `全部项目 3`、`仅有想法 3`、`实用新型 1` 与 seeded API 数据一致。
- `实用新型` 筛选只显示 `Round8 Beta 保留项目`。
- 选择 `Round8 Alpha 删除目标` 后，顶部选择器、侧边栏和项目列表当前行一致。
- 删除确认框文案包含目标项目名；dismiss 后 API 项目数仍为 3。
- accept 后目标项目从 API、列表和顶部选择器中移除。
- 删除当前项目后 UI 自动切换到有效保留项目 `Round8 Beta 保留项目`，没有保留已删除项目的 stale selection。
- 本轮无浏览器 console error、无 page error、无 failed request。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round8-projects-initial.png`
- `.gstack/qa-reports/screenshots/round8-projects-utility-filter.png`
- `.gstack/qa-reports/screenshots/round8-project-selected-before-delete.png`
- `.gstack/qa-reports/screenshots/round8-project-delete-dismiss.png`
- `.gstack/qa-reports/screenshots/round8-project-delete-accept.png`

State evidence:

- `.gstack/qa-reports/round8-seeded-projects.json`
- `.gstack/qa-reports/round8-project-delete-state.json`

## Findings

No new unique bug was found in this round.

The delete-confirmation flow behaved correctly on desktop with isolated data:

- Dismissed confirmation did not delete data.
- Accepted confirmation removed the target project from backend and UI.
- Current-project state moved to a valid remaining project.

## Baseline Update

- No new bug ID was opened.
- Baseline health score remains `66`.
- Current cumulative issues remain: `P1=3`, `P2=6`, `P3=1`.

## Notes

- I did not repair any code.
- Round 4 already covers the mobile project list visual issue in `BUG-008`; this round was desktop state consistency only.
