# QA Report: PatentAgent Local Round 7

Status: DONE_WITH_CONCERNS

Date: 2026-06-26

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Settings page LLM configuration:

- Save Provider/Base URL/Model/API Key.
- Verify secret is not shown in plaintext after save.
- Test connectivity against a local mock provider returning 503.
- Clear API key and verify the UI returns to the unconfigured state.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round7 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round7","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Mock provider: `http://127.0.0.1:8766/v1`, returns HTTP 503 for all requests
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round7 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node -e "<localhost mock provider returning 503>"
node .gstack/qa-reports/round7_settings_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-SETTINGS-001 | 保存 fake API key 后再清除 | 通过；保存后只显示本机配置和遮蔽指纹，清除后回到 `尚未配置 API Key` |
| TC-SETTINGS-002 | provider 返回 503 时点击 `测试连通` | 失败；仍暴露 `InternalServerError` 和 provider 原始错误 JSON，归入既有 `BUG-007` |

## Positive Evidence

- `Provider`、`Base URL`、`Model` 和 fake API Key 可保存到本机配置。
- 保存后 UI 显示 `本机配置` 和遮蔽指纹，不回显明文 key。
- `清除密钥` 成功后，页面显示 `尚未配置 API Key`，按钮重新 disabled。
- 本轮无浏览器 console error、无 page error、无 failed request。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round7-settings-initial.png`
- `.gstack/qa-reports/screenshots/round7-settings-initial-confirmed.png`
- `.gstack/qa-reports/screenshots/round7-settings-before-save.png`
- `.gstack/qa-reports/screenshots/round7-settings-after-save.png`
- `.gstack/qa-reports/screenshots/round7-settings-after-provider-503.png`
- `.gstack/qa-reports/screenshots/round7-settings-after-clear-key.png`

State evidence:

- `.gstack/qa-reports/round7-settings-state.json`

## Findings

### Existing ISSUE-007 / BUG-007 Expanded: Provider 503 Shows Raw Internal Error

Severity: Low / P3

Repro:

1. Start a local mock provider at `http://127.0.0.1:8766/v1` that returns HTTP 503.
2. Open `设置 · LLM 服务`.
3. Save Provider=`qa-mock`, Base URL=`http://127.0.0.1:8766/v1`, Model=`qa-503-model`, and a fake API key.
4. Click `测试连通`.
5. Clear the key.

Actual:

The page displays:

`InternalServerError: Error code: 503 - {'error': {'message': 'QA mock provider unavailable', 'type': 'server_error', 'code': 'qa_503'}}`

Expected:

The page should display a user-facing Chinese message such as “供应商服务暂不可用，请稍后重试或检查 Base URL/模型配置”，without SDK exception class names or raw provider JSON.

Evidence:

- `.gstack/qa-reports/screenshots/round7-settings-after-provider-503.png`
- `.gstack/qa-reports/round7-settings-state.json`

## Baseline Update

- No new unique bug ID was opened.
- `BUG-007` was updated with provider 503 evidence.
- Baseline health score remains `66`.
- Current cumulative issues remain: `P1=3`, `P2=6`, `P3=1`.

## Notes

- I did not repair any code.
- The test API key was a fake local QA value and no real credential was used.
