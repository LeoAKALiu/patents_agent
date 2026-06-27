# QA Report: PatentAgent Local Round 12

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Project switching while a long task is running:

- Prepare two ordinary invention projects in isolated Round 12 data.
- Select project A in the UI.
- Start `提炼发明点` on project A.
- While project A shows a running disclosure run, switch the current project selector to project B.
- Verify run ownership, UI isolation, console health, and API state for both projects.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round12 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round12","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round12 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round12_switch_project_during_run_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-SWITCH-001 | A 项目运行 `提炼发明点` 时切换到 B 项目 | 通过；A 的 run 未写入 B，B UI 不显示 A 的运行卡片 |

## Positive Evidence

- Project A selected successfully and showed `提炼发明点`.
- Starting `提炼发明点` on A produced exactly one observed mutating UI request: `POST /api/projects/6f569c14914844d69c8e23772ff22cf6/disclosures`.
- Switching the top current-project selector to B succeeded while A was still running.
- API evidence: `GET /api/projects/6f569c14914844d69c8e23772ff22cf6/disclosures` returned one run for A.
- API evidence: `GET /api/projects/6aed0468047642b798d4d0ee119edd5b/disclosures` returned `{"runs":[]}` for B.
- UI evidence: after switching to B, the selected project is B and the page shows B's normal `提炼发明点` button, not A's running card.
- 本轮无浏览器 console error、无 page error、无 failed request。

## Findings

No new unique bug was found in this round.

The tested project-switch flow preserved project/run isolation. A continued owning its disclosure run, while B remained clean and operable after the switch.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round12-project-a-before-run.png`
- `.gstack/qa-reports/screenshots/round12-project-a-running.png`
- `.gstack/qa-reports/screenshots/round12-project-b-after-switch.png`

State evidence:

- `.gstack/qa-reports/round12-switch-project-during-run-state.json`

## Baseline Update

- No new bug ID was opened.
- Baseline health score remains `65`.
- Current cumulative issues remain: `P1=3`, `P2=6`, `P3=2`.

## Notes

- I did not repair any code.
- The two test projects were prepared through the local API as scenario setup; the project selection, run start, and project switch were exercised through the UI.
