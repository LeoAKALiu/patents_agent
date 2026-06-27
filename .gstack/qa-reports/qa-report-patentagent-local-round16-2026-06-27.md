# QA Report: PatentAgent Local Round 16

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Panel, detail, and return-flow behavior in the guided patent drafting flow:

- `专家工具` open, return to guide, reopen, return again.
- `查看前置材料详情` open, return, reopen, return again.
- `查看护城河地图` open, return, reopen, return again.
- `查看完整提示词` collapse and reopen.
- `返回三选一` from a fully-created project state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round16 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round16","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round16 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round16_modal_panel_probe.js
```

Additional strict wait check for `返回三选一`: created a fresh project, waited until `查看前置材料详情` appeared, then clicked `返回三选一`.

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PANEL-001 | 专家工具、详情页、地图页、提示词区域、返回三选一 | 通过；未发现新增缺陷 |

## Findings

No new bugs were opened in this round.

The first probe iteration briefly suggested `返回三选一` might not navigate, but a stricter reproduction showed the earlier observation clicked during project creation churn. With an explicit wait for the created project state, `返回三选一` returned to the three-entry selection page as expected.

## Positive Evidence

- `专家工具` changes to the expert tools surface and `返回向导` restores the guided flow. Reopening and returning again remained stable.
- `查看前置材料详情` and `查看护城河地图` open the corresponding expert modules and can return to the guide. Reopening did not duplicate panels or leave visible overlays.
- `查看完整提示词` collapses the prompt textarea and reopens it without layout breakage.
- `返回三选一` returns from the project guided flow to the three-entry start page after the project is fully created.
- Browser console errors: 0.
- Page errors: 0.
- Failed requests: 0.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round16/expert-tools-open.png`
- `.gstack/qa-reports/screenshots/round16/expert-tools-final-guide.png`
- `.gstack/qa-reports/screenshots/round16/trigger-查看前置材料详情-open.png`
- `.gstack/qa-reports/screenshots/round16/trigger-查看前置材料详情-final-close.png`
- `.gstack/qa-reports/screenshots/round16/trigger-查看护城河地图-open.png`
- `.gstack/qa-reports/screenshots/round16/trigger-查看护城河地图-final-close.png`
- `.gstack/qa-reports/screenshots/round16/prompt-details-collapsed.png`
- `.gstack/qa-reports/screenshots/round16/prompt-details-reopened.png`
- `.gstack/qa-reports/screenshots/round16/return-three-choice-project-before.png`
- `.gstack/qa-reports/screenshots/round16/return-three-choice-project-after.png`

State evidence:

- `.gstack/qa-reports/round16-modal-panel-state.json`

## Baseline Update

- No new `BUGS.md` entry.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=3`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was added only to collect browser evidence and does not affect product behavior.
