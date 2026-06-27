# QA Report: PatentAgent Local Round 10

Status: DONE_WITH_CONCERNS

Date: 2026-06-26

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Duplicate-click handling for a running task:

- Enter the invention-patent guided flow from the three-choice start page.
- Create a fresh project.
- Delay `POST /api/projects/{project_id}/disclosures` to simulate a slow local service.
- Rapidly double-click `提炼发明点`.
- Verify request count, busy/disabled state, run state, console health, and resulting API state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round10 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round10","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round10 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round10_patent_points_duplicate_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-DOUBLE-CLICK-001 | 慢网络下快速重复点击 `提炼发明点` | 通过；只产生 1 个 disclosure run POST，运行按钮进入 disabled/busy 状态 |

## Positive Evidence

- 真实用户路径可从三选一入口进入发明专利创建表单。
- 项目创建成功并进入发明点确认页。
- `提炼发明点` 双击期间，页面显示 `正在提炼发明点`，按钮 disabled，并显示运行日志。
- Network evidence: `disclosureRequestCount === 1`。
- Mutating request evidence: only one `POST /api/projects` and one `POST /api/projects/{project_id}/disclosures` were observed in the successful probe.
- API evidence: `GET /api/projects/639f3595b2b643ca86726267c8f9a4a6/disclosures` returned one running disclosure run.
- `GET /api/projects/639f3595b2b643ca86726267c8f9a4a6/patent-points` returned `{"points":[]}` during the running state, so no duplicate candidate records were created in the observed window.
- 本轮无浏览器 console error、无 page error、无 failed request。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round10-create-before.png`
- `.gstack/qa-reports/screenshots/round10-points-before-submit.png`
- `.gstack/qa-reports/screenshots/round10-points-during-submit.png`
- `.gstack/qa-reports/screenshots/round10-points-after-submit.png`

State evidence:

- `.gstack/qa-reports/round10-patent-points-duplicate-state.json`

## Findings

No new unique bug was found in this round.

The `提炼发明点` flow correctly guarded against duplicate submission in the tested slow-network double-click scenario. The final observed state was still running after roughly 5 seconds and exposed `取消运行`; that is recorded as async task behavior, not a new defect in this duplicate-click test.

## Baseline Update

- No new bug ID was opened.
- Baseline health score remains `66`.
- Current cumulative issues remain: `P1=3`, `P2=6`, `P3=1`.

## Notes

- I did not repair any code.
- The first probe attempt failed before interaction because the page was on the three-choice entry screen; the final probe now follows that real entry path.
- A second intermediate probe used the wrong endpoint pattern for counting, then backend logs showed the correct action endpoint is `POST /api/projects/{project_id}/disclosures`.
