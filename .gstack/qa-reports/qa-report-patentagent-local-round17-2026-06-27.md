# QA Report: PatentAgent Local Round 17

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Settings page LLM provider rate-limit handling:

- Start a local mock provider at `http://127.0.0.1:8767/v1`.
- Mock `POST /v1/chat/completions` returns HTTP 429 with provider JSON and `Retry-After: 30`.
- Save fake Provider/Base URL/Model/API Key in `设置 · LLM 服务`.
- Click `测试连通` and wait for completion.
- Verify user-facing message, provider request, key privacy, and cleanup via `清除密钥`.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round17 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round17","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Mock provider: `http://127.0.0.1:8767/v1`, returns HTTP 429
- Browser: local Chromium/Playwright, 1440x1100 viewport

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round17 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round17_settings_rate_limit_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-SETTINGS-003 | Provider 429 / rate limit 时点击 `测试连通` | 失败；扩展既有 `BUG-007`，页面仍暴露 `RateLimitError` 和 provider 原始 JSON |

## Findings

### Existing BUG-007: Rate-limit failure exposes raw SDK/provider error

Severity: P3

The mock provider received one `POST /v1/chat/completions` request and returned HTTP 429. After waiting for the connectivity test to finish, the settings page displayed:

`RateLimitError: Error code: 429 - {'error': {'message': 'QA mock rate limit exceeded', 'type': 'rate_limit_error', 'code': 'rate_limit_exceeded'}}`

This is the same user-facing error handling gap already tracked as `BUG-007`, now confirmed for provider rate limiting in addition to unreachable endpoints and provider 503.

## Positive Evidence

- The fake API key did not appear in the page body after save or after the 429 result.
- The page showed a masked key fingerprint while configured.
- `清除密钥` returned the page to an unconfigured key state.
- No browser page errors or failed frontend requests were observed.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round17/settings-after-save-rate-limit.png`
- `.gstack/qa-reports/screenshots/round17/settings-after-rate-limit-test.png`
- `.gstack/qa-reports/screenshots/round17/settings-after-clear-rate-limit.png`

State evidence:

- `.gstack/qa-reports/round17-settings-rate-limit-state.json`

## Baseline Update

- New bug ID opened: none.
- `BUG-007` updated with Round17 provider 429 evidence.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=3`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was added only to collect browser evidence and does not affect product behavior.
