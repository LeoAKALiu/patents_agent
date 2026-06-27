# QA Report: PatentAgent Local Round 9

Status: DONE_WITH_CONCERNS

Date: 2026-06-26

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Duplicate-click handling for project creation:

- Enter invention-patent guided flow.
- Fill project name and one-sentence idea.
- Delay `POST /api/projects` to simulate slow local service.
- Rapidly click `创建并继续` twice.
- Verify request count, UI busy state, created project count, and final selected project.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round9 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round9","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round9 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round9_duplicate_create_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-DOUBLE-CLICK-002 | 慢网络下快速重复点击 `创建并继续` | 通过；只产生 1 个项目创建请求和 1 个项目记录 |

## Positive Evidence

- 提交前 `创建并继续` 可用。
- 第一次点击后，页面显示 `正在创建专利项目`，按钮进入提交中 disabled 状态。
- 第二次强制点击没有触发第二个 `POST /api/projects`。
- Network evidence: `projectPosts.length === 1`。
- API evidence: `GET /api/projects` 只返回一个名为 `Round9 双击创建项目` 的项目。
- 顶部项目选择器选中唯一创建出的项目。
- 本轮无浏览器 console error、无 page error、无 failed request。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round9-home-before-create.png`
- `.gstack/qa-reports/screenshots/round9-create-form-initial.png`
- `.gstack/qa-reports/screenshots/round9-duplicate-create-before-submit.png`
- `.gstack/qa-reports/screenshots/round9-duplicate-create-during-submit.png`
- `.gstack/qa-reports/screenshots/round9-duplicate-create-after-submit.png`

State evidence:

- `.gstack/qa-reports/round9-duplicate-create-state.json`

## Findings

No new unique bug was found in this round.

The project creation flow correctly guarded against duplicate submission in the tested slow-network double-click scenario.

## Baseline Update

- No new bug ID was opened.
- Baseline health score remains `66`.
- Current cumulative issues remain: `P1=3`, `P2=6`, `P3=1`.

## Notes

- I did not repair any code.
- This round covers create-project duplicate clicks only. Running-task duplicate clicks remain tracked under `TC-DOUBLE-CLICK-001`.
