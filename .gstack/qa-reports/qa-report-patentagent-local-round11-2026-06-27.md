# QA Report: PatentAgent Local Round 11

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Cancel-running-task behavior for the guided invention-point flow:

- Enter the invention-patent guided flow from the three-choice start page.
- Create a fresh project.
- Start `提炼发明点`.
- Wait for `取消运行`, click it, and wait for cancellation to settle.
- Verify UI recovery, mutating request count, API run state, console health, and user-facing cancellation message.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round11 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round11","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round11 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round11_cancel_running_task_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-CANCEL-001 | 启动 `提炼发明点` 后点击 `取消运行` | 部分通过；取消成功且按钮可重试，但提示暴露内部英文实现细节 |

## Positive Evidence

- `取消运行` 在 run 启动后出现。
- 点击取消后发出一次 cancel request。
- API evidence: `GET /api/projects/a4f2589ff7cc4a76b036dcb0df4d2b4d/disclosures` 返回 `status:"interrupted"`。
- API events include `run started`, `cancel requested`, and `run cancelled`.
- `提炼发明点` 主按钮在稳定态恢复 enabled。
- 本轮无浏览器 console error、无 page error、无 failed request。

## Finding

### BUG-011: Cancel run success message exposes internal English implementation details

- Severity: P3
- Category: UX
- Repro: start `提炼发明点`, click `取消运行`, wait for cancellation to finish.
- Actual: cancellation succeeds, but the UI shows `cancelled / disclosure scan / llm:Run was cancelled by request; partial artifacts were preserved for retry. 建议:Review partial stage_results, then retry the run when ready.`
- Expected: a localized, user-facing cancellation message without internal stage/provider names or developer terms.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round11-create-before.png`
- `.gstack/qa-reports/screenshots/round11-before-run.png`
- `.gstack/qa-reports/screenshots/round11-running-before-cancel.png`
- `.gstack/qa-reports/screenshots/round11-after-cancel.png`

State evidence:

- `.gstack/qa-reports/round11-cancel-running-task-state.json`

## Baseline Update

- Added `BUG-011`.
- Baseline health score changed from `66` to `65`.
- Current cumulative issues: `P1=3`, `P2=6`, `P3=2`.

## Notes

- I did not repair any code.
- An early probe clicked before `取消运行` appeared; the final probe waits for the cancel button and uses the later settled-state evidence.
