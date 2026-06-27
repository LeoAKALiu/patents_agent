# QA Report: PatentAgent Local Round 22

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Settings page normal save/clear path and API key privacy:

- Open `设置 · LLM 服务`.
- Fill Provider, Base URL, Model, and a unique fake API Key.
- Save the desktop config.
- Verify the UI shows configured state and fingerprint without displaying the fake key.
- Verify `/api/desktop-config` reports `api_key_present:true` and does not return the fake key.
- Click `清除密钥`.
- Verify UI and `/api/desktop-config` return to an unconfigured key state without leaking the fake key.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round22-rerun python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round22-rerun","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Fake provider config: `provider=qa-settings-save-clear`, `base_url=http://127.0.0.1:65534/v1`, `model=qa-settings-model`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round22-rerun python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round22_settings_save_clear_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-SETTINGS-001 | 设置页保存 Provider/Base URL/Model/API Key 后清除密钥 | 通过；保存和清除均成功，页面、可见输入框、`/api/desktop-config` 均未泄露 API Key 明文 |

## Findings

No new product bug opened in Round22.

The settings page correctly used `PATCH /api/desktop-config` for save and clear. After saving, the status cards showed local configuration and a masked key fingerprint, while the API Key input stayed empty with the configured placeholder. After clearing, the fingerprint changed to unconfigured, the API Key input stayed empty, and the clear button became disabled.

## Positive Evidence

- `saveRequestSucceeded: true`
- `clearButtonVisibleBeforeClear: true`
- `afterSaveShowsConfiguredKey: true`
- `afterSaveBodyLeaksKey: false`
- `afterSaveInputLeaksKey: false`
- `afterSaveApiLeaksKey: false`
- `afterClearBodyLeaksKey: false`
- `afterClearInputLeaksKey: false`
- `afterClearApiLeaksKey: false`
- `afterClearUnconfigured: true`
- No page errors, request failures, or console errors were recorded.

After save, `/api/desktop-config` returned:

```json
{
  "provider": "qa-settings-save-clear",
  "base_url": "http://127.0.0.1:65534/v1",
  "model": "qa-settings-model",
  "api_key_present": true,
  "api_key_source": "desktop_config"
}
```

After clear, `/api/desktop-config` returned `api_key_present:false` and an empty `api_key_fingerprint`.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round22/01-settings-initial.png`
- `.gstack/qa-reports/screenshots/round22/02-settings-filled.png`
- `.gstack/qa-reports/screenshots/round22/03-settings-after-save.png`
- `.gstack/qa-reports/screenshots/round22/04-settings-after-clear.png`

State evidence:

- `.gstack/qa-reports/round22-settings-save-clear-state.json`

## Baseline Update

- New bug ID opened: none.
- `TC-SETTINGS-001` now has a concrete Round22 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The fake API Key was generated inside the probe and is redacted from the saved QA payload.
