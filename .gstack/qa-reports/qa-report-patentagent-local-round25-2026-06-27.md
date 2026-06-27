# QA Report: PatentAgent Local Round 25

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Guided new-user flow with bad LLM configuration:

- Save a deliberately unreachable local LLM Base URL in `设置 · LLM 服务`.
- Return to `开始`.
- Create a new invention project from `从技术想法撰写发明专利`.
- Verify project creation and entry into the invention-point confirmation step.
- Click `提炼发明点`.
- Verify only one disclosure run starts, the failed run is contained to the current project, retry is available, and user-facing error copy is checked for internal details.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round25 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round25","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Project: `Round25 Guided 错误配置项目 1782497651354`
- Bad LLM config: `provider=qa-bad-guided`, `base_url=http://127.0.0.1:9/v1`, `model=qa-guided-bad-model`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round25 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round25_guided_create_bad_llm_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-GUIDED-001 | 新手从技术想法创建项目，并在错误 LLM 配置下点击 `提炼发明点` | 部分通过；项目创建、单次 run、失败关闭和重试恢复通过，但错误提示暴露内部 stage/provider 和英文建议 |

## Findings

### BUG-016: Guided extraction failure exposes internal details

Severity: P3

The project was created exactly once and entered the invention-point confirmation step. Clicking `提炼发明点` submitted exactly one `POST /api/projects/{project_id}/disclosures`; the backend run reached terminal `status:"failed"` with `message:"Connection error."`; the UI stayed on the same project and showed a retryable state.

The defect is the user-facing red error copy:

`exception / disclosure scan / llm:Connection error. 建议:Retry after fixing the disclosure provider or prompt/schema issue.`

This exposes implementation terms and English operational guidance instead of a clear Chinese instruction to check Base URL, network/proxy, or API key.

## Positive Evidence

- `settingsSavedAsBadLocalConfig: true`
- `projectCreateResponseOk: true`
- `projectCreatedExactlyOnce: true`
- `enteredDisclosureStep: true`
- `disclosurePostCount: 1`
- `exactlyOneDisclosurePost: true`
- `disclosureReachedTerminalState: true`
- `disclosureFailedClosed: true`
- `retryButtonAvailable: true`
- `uiStillOnProjectContext: true`
- No page errors, request failures, or console errors were recorded.

## Failed Assertion

- `rawSdkErrorVisible: true`

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round25/00-home.png`
- `.gstack/qa-reports/screenshots/round25/03-settings-bad-llm-saved.png`
- `.gstack/qa-reports/screenshots/round25/05-guided-form-filled.png`
- `.gstack/qa-reports/screenshots/round25/06-after-create.png`
- `.gstack/qa-reports/screenshots/round25/07-after-click-extract.png`
- `.gstack/qa-reports/screenshots/round25/08-after-run-terminal-or-timeout.png`

State evidence:

- `.gstack/qa-reports/round25-guided-create-bad-llm-state.json`

## Baseline Update

- New bug ID opened: `BUG-016`.
- `TC-GUIDED-001` now has a concrete Round25 probe command.
- Baseline health score changed from `62` to `61`.
- Current cumulative issues: `P1=3`, `P2=8`, `P3=5`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The bad LLM endpoint was intentionally saved through the UI to exercise the user-visible failure path.
