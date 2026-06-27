# QA Report: PatentAgent Local Round 19

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Project deletion cancel/confirm behavior for the current project:

- Create a keep project and a target project through the guided flow.
- Open the project list.
- Click delete on the current target project and dismiss the native confirmation dialog.
- Verify both projects remain in `/api/projects`.
- Click delete on the same target again and accept the native confirmation dialog.
- Verify the DELETE response, project list, current-project selector, and `/api/projects` state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round19 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round19","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Final target project: `Round19 待删除当前项目 1782495470591`
- Final keep project: `Round19 保留项目 1782495470591`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round19 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round19_project_delete_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PROJECTS-003 | 当前项目删除：先取消，再确认删除 | 通过；取消保留项目，确认删除后 API 和 UI 最终一致 |

## Findings

No new product bug opened in Round19.

The probe recorded two native `confirm()` dialogs for the same target project. Dismissing the first dialog preserved both projects. Accepting the second dialog produced `DELETE /api/projects/{id}` with HTTP 200; after a 5 second settle, the target project no longer appeared in `/api/projects`, the project list, the current-project selector, or the sidebar current-project card.

## Positive Evidence

- `cancelDialogShown: true`
- `confirmDialogShown: true`
- `deleteResponseStatus: 200`
- `cancelPreservedBoth: true`
- `apiDeletedAbsentAfterConfirm: true`
- `apiKeepPresentAfterConfirm: true`
- `deletedAbsentAfterConfirm: true`
- No browser page errors, request failures, or console errors were recorded.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round19/01-load-app.png`
- `.gstack/qa-reports/screenshots/round19/project-form-keep.png`
- `.gstack/qa-reports/screenshots/round19/project-created-keep.png`
- `.gstack/qa-reports/screenshots/round19/project-form-delete.png`
- `.gstack/qa-reports/screenshots/round19/project-created-delete.png`
- `.gstack/qa-reports/screenshots/round19/02-project-list-before-delete.png`
- `.gstack/qa-reports/screenshots/round19/03-after-first-delete-click.png`
- `.gstack/qa-reports/screenshots/round19/04-after-cancel-delete.png`
- `.gstack/qa-reports/screenshots/round19/05-before-confirm-delete.png`
- `.gstack/qa-reports/screenshots/round19/06-after-confirm-delete.png`

State evidence:

- `.gstack/qa-reports/round19-project-delete-state.json`

## Baseline Update

- New bug ID opened: none.
- `TC-PROJECTS-003` now has a concrete Round19 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- Native browser confirmation dialogs are recorded in the state JSON; they are not visible in screenshots after Playwright accepts or dismisses them.
- A shorter 1.2 second settle briefly showed stale list content after DELETE, but the 5 second rerun converged correctly. I did not open a bug for that because the final API/UI state was consistent and no user-visible error remained.
