# Code Review: `codex/remove-electron-tauri-only`

**Base:** `origin/release/v1.1.0` · **Branch:** `codex/remove-electron-tauri-only` (commit `679ba39`)
**Scope:** Remove Electron desktop runtime, keep Tauri as sole desktop shell
**Status:** Already merged as PR #73 — this is a retrospective review

---

## 1. Change Summary

| Metric | Value |
|--------|-------|
| Files changed | 25 |
| Lines added | 77 |
| Lines deleted | 4,221 |
| Net | −4,144 |

The commit removes the entire `desktop/electron/` workspace (6 TypeScript source files, 556-line test suite, smoke script, CI job, `package.json`/lockfile) and updates docs, tests, scripts, and backend origin config to reflect Tauri as the sole desktop runtime.

### Deleted files

| File | Lines | Role |
|------|-------|------|
| `desktop/electron/main.ts` | 888 | Electron main process — window, menu, backend lifecycle, smoke |
| `desktop/electron/desktop-dialogs.ts` | 444 | Native open/save dialog IPC |
| `desktop/electron/startup-diagnostics.ts` | 407 | Structured boot telemetry |
| `desktop/electron/backend-supervisor.ts` | 309 | FastAPI sidecar spawn + health poll |
| `desktop/electron/preload.ts` | 262 | contextBridge API surface |
| `desktop/electron/desktop-config.ts` | 200 | LLM config IPC (redacted) |
| `desktop/package-lock.json` | 897 | Electron dependency lock |
| `tests/test_desktop_electron_skeleton.py` | 556 | Structural assertions for Electron workspace |
| `desktop/scripts/smoke.mjs` | 78 | Electron launch smoke |
| `desktop/package.json` | 19 | Desktop npm workspace |
| `desktop/tsconfig.json` | 21 | TS config for Electron main |
| `desktop/.gitignore` | 6 | Build output exclusions |

### Modified files

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Remove `desktop` CI job (Electron build + xvfb smoke) |
| `backend/app/main.py` | Remove `"null"` and `"file://"` from `LOCAL_RENDERER_ORIGINS` |
| `scripts/v1_smoke.sh` | Remove `run_electron_smoke_if_feasible()` + desktop npm steps |
| `scripts/v1_api_smoke.py` | Remove `"electron"` and `"xvfb"` from environment markers |
| `scripts/bootstrap_v1_agent_pipeline.py` | Label `electron` → `tauri`; profile text updated |
| `scripts/tauri_dmg_smoke.py` | Add `invalid-resource-directory` spctl classification |
| `tests/test_api_settings.py` | `"null"` origin now expects 403 (was 200) |
| `tests/test_tauri_desktop_skeleton.py` | Assert `desktop/` no longer exists; remove Electron smoke checks |
| `tests/test_tauri_dmg_smoke_script.py` | Add spctl classification test |
| `CHANGELOG.md` | Rewrite Electron references to Tauri |
| `README.md` | Full desktop section rewrite (Tauri commands, DMG, smoke) |
| `docs/release/v1.1.0-release-handoff.md` | Packaging checklist updated for Tauri |
| `docs/release/v1.1.0-tauri-release-gate.md` | Remove Electron rollback path; add DOM smoke step |

---

## 2. Feature Parity Matrix

| Concern | Electron (removed) | Tauri (preserved) | Status |
|---------|--------------------|--------------------|--------|
| **Packaging** | `npm run build` → `dist-electron/` | `tauri build` → `src-tauri/target/release/bundle/dmg/` | ✅ |
| **Backend supervision** | Node.js `ChildProcess` + health poll | Rust `BackendSupervisor` + `Drop` cleanup | ✅ |
| **Backend health check** | `fetchJsonWithTimeout()` → `/api/health` | `TcpStream` poll → `/api/health` | ✅ |
| **File import (draft)** | `dialog.showOpenDialog` + `readFile` → base64 | `DialogExt.file().pick()` + `fs::read` → base64 | ✅ |
| **File export (official)** | `dialog.showSaveDialog` + HTTP stream to disk | `DialogExt.file().save()` + `reqwest` to disk | ✅ |
| **Reveal in Finder** | `shell.showItemInFolder` | `OpenerExt.reveal_in_default_app` | ✅ |
| **Desktop config** | IPC → HTTP proxy to backend | Tauri command → HTTP proxy to backend | ✅ |
| **API key redaction** | Regex scrub in TS + backend redaction | Backend redaction only (Rust passes through) | ⚠️ |
| **Frontend bridge** | `contextBridge.exposeInMainWorld("desktop", api)` | `installTauriDesktopBridge()` via `__TAURI__.core.invoke` | ✅ |
| **Smoke test** | Preload probe + backend health + frontend asset check | Cargo check/test + DMG smoke + env-gated DOM smoke | ✅ |
| **Startup diagnostics** | Structured JSON lines, `StartupReport` schema, Help menu | DOM smoke only (root/sidebar/topbar check) | ⚠️ Degraded |
| **Menu → renderer events** | `ipcRenderer.on("desktop:menu")` | `onMenuAction: () => () => undefined` (no-op) | ⚠️ Dead path |
| **CI desktop gate** | Ubuntu: `xvfb-run -a npm run smoke` | Ubuntu: `cargo check` + `cargo test` (no webview launch) | ⚠️ |

---

## 3. Critical Issues

### 3.1 `withGlobalTauri: true` + CSP `null` — XSS → command injection

**File:** `src-tauri/tauri.conf.json:12`

```json
"withGlobalTauri": true
```

```json
"security": { "csp": null }
```

`withGlobalTauri: true` injects `window.__TAURI__` into every page loaded in the webview. Combined with `csp: null` (no Content Security Policy), any XSS in the React frontend can directly invoke Tauri commands — including `desktop_config_update` (write LLM settings), `open_folder` (reveal paths), or `save_official` (write files to disk).

The old Electron setup used `contextIsolation: true` + `sandbox: true` + `contextBridge` as defense layers. Tauri's command system is the equivalent trust boundary, but `withGlobalTauri` bypasses the import-level access control.

**Recommendation:**
1. Set `withGlobalTauri: false`.
2. Import `invoke` from `@tauri-apps/api/core` in `tauriDesktopBridge.ts` instead of accessing `window.__TAURI__`.
3. Add a restrictive CSP (at minimum `default-src 'self'; script-src 'self'`).

### 3.2 Tauri webview origin `tauri://localhost` not whitelisted

**File:** `backend/app/main.py:123-130`

The commit removes `"null"` and `"file://"` from `LOCAL_RENDERER_ORIGINS`, but does not add the Tauri webview origin. Tauri v2 webviews send `Origin: tauri://localhost` for `fetch()` calls from the frontend.

If the Tauri frontend makes `PATCH /api/desktop-config` requests (which it does, via `desktop_config_update` → HTTP proxy), the backend's `_enforce_desktop_config_origin` check will see `Origin: tauri://localhost`, find it not in `LOCAL_RENDERER_ORIGINS`, and reject with 403.

The test `test_desktop_config_rejects_legacy_file_renderer_origin` confirms `"null"` → 403, but there is no test for `tauri://localhost` → 200.

**Recommendation:**
1. Add `"tauri://localhost"` to `LOCAL_RENDERER_ORIGINS`.
2. Add a test:
   ```python
   def test_desktop_config_allows_tauri_webview_origin(client: TestClient) -> None:
       response = client.patch(
           "/api/desktop-config",
           json={"model": "test"},
           headers={"Origin": "tauri://localhost"},
       )
       assert response.status_code == 200
   ```

---

## 4. Important Issues

### 4.1 No Rust tests for backend supervisor or dialog logic

**File:** `src-tauri/src/main.rs` (951 lines)

The Rust source contains critical logic:
- `BackendSupervisor::shutdown()` — process kill + wait
- `start_backend()` — spawn uvicorn, health poll with timeout
- `open_draft()` — file picker + base64 encode
- `save_official()` — HTTP stream to user-selected path
- `desktop_config_update()` — HTTP PATCH proxy with error handling

`cargo test` has no visible unit tests for any of these. The deleted Electron test suite (`test_desktop_electron_skeleton.py`) had 556 lines of structural assertions covering IPC channels, preload contracts, smoke probes, and security defaults.

**Recommendation:** Add Rust unit tests for:
- `BackendSupervisor` spawn + health poll + timeout
- Config proxy error handling (timeout, non-200, invalid JSON)
- `open_draft` / `save_official` with mock file paths

### 4.2 `onMenuAction` is a no-op in Tauri bridge

**File:** `frontend/src/tauriDesktopBridge.ts:111`

```typescript
onMenuAction: () => () => undefined,
```

The Electron preload relayed native menu clicks (`desktop:menu` IPC) to the renderer. The Tauri bridge silently drops these. If the frontend has code paths triggered by menu actions (import draft, export official, open settings), they are dead in the Tauri build.

**Recommendation:** Either:
1. Implement Tauri menu event forwarding (via `tauri::menu::MenuEvent`), or
2. Confirm the frontend only uses toolbar/sidebar buttons (not menu actions) and document this as intentional.

### 4.3 Startup diagnostics downgraded

**Electron (removed):**
- Structured `[startup]` JSON lines on stdout
- `StartupReport` schema: python version, backend command/port/duration, renderer load time, failed subresources, crash details
- Help → 诊断信息 menu → `showMessageBox` with human-readable report
- Renderer-accessible via `window.desktop.diagnostics.getReport()`

**Tauri (replaced):**
- `PATENTAGENT_TAURI_DOM_SMOKE=1` checks React root, `.app-shell`, `.sidebar`, `.topbar` rendered
- Writes a JSON report to `PATENTAGENT_TAURI_DOM_SMOKE_REPORT` path
- No structured boot telemetry, no user-facing diagnostics

**Impact:** Regressions in backend startup time, python resolution, or renderer asset loading won't be captured in production. Users have no way to inspect boot health.

**Recommendation:** Port the `StartupReport` schema to Tauri as a `tauri::command` that collects the same fields. Wire it to a Help menu item.

### 4.4 API key redaction gap in Tauri commands

**File:** `src-tauri/src/main.rs`

The Electron `desktop-config.ts` had a regex scrubber (`RAW_KEY_PATTERN = /sk-[A-Za-z0-9_-]{6,}/g`) that replaced raw keys in error messages before they reached the renderer. The Tauri `desktop_config_*` commands propagate backend errors directly:

```rust
fn desktop_config_get(state: State<'_, BackendState>) -> Result<Value, String> {
    // ...
    Err(e) => Err(format!("backend error: {e}"))
}
```

If the backend returns an error containing a raw API key (e.g., in a validation message), it passes through to the renderer unsanitized.

**Recommendation:** Add a `redact_secrets(text: &str) -> String` helper in Rust that scrubs `sk-...` patterns from error strings, matching the Electron behavior.

---

## 5. Minor Issues

### 5.1 CI gap: no Linux desktop smoke

The removed CI job ran `xvfb-run -a npm run smoke` on Ubuntu, exercising the full Electron stack headlessly. The Tauri CI job only runs `cargo check` and `cargo test` — no actual webview launch on Linux.

**Impact:** Low for now (macOS-only target). If Linux support is added later, there's no regression net.

### 5.2 Doc migration is complete

All references to "Electron" in README, CHANGELOG, handoff docs, release gate, and bootstrap script labels are updated to "Tauri". No stale Electron references found.

### 5.3 spctl classification additions are correct

`tauri_dmg_smoke.py` adds `assessment-tool-error-invalid-resource-directory` — good defensive addition for macOS signing edge cases.

---

## 6. Risk Matrix

| # | Risk | Severity | Likelihood | Fix Effort |
|---|------|----------|------------|------------|
| 3.1 | `withGlobalTauri` + null CSP → XSS → command injection | 🔴 High | Medium | Low (config change) |
| 3.2 | Missing `tauri://localhost` origin → config writes blocked | 🔴 High | Low–Medium | Low (one string + test) |
| 4.1 | No Rust test coverage for supervisor/dialogs | 🟡 Important | Medium | Medium |
| 4.2 | Dead `onMenuAction` code path | 🟡 Important | Low | Medium |
| 4.3 | Startup diagnostics degraded | 🟡 Important | Medium | Medium |
| 4.4 | API key redaction gap in Rust errors | 🟡 Important | Low | Low |
| 5.1 | No Linux CI smoke | 🟢 Minor | Low | Low |

---

## 7. Verdict

The Electron removal is **structurally clean** — feature parity is preserved through Tauri's command system and the frontend bridge adapter (`tauriDesktopBridge.ts`). The migration is well-scoped: no frontend code changes needed, all IPC surfaces have 1:1 Tauri command equivalents, and the Rust backend supervisor with `Drop`-based cleanup is arguably more reliable than the Node.js equivalent.

**Before the next release gate, address:**
1. `withGlobalTauri: false` + CSP (critical security)
2. `tauri://localhost` origin whitelist (critical functionality)

**Before v1.1 GA, address:**
3. Rust unit tests for supervisor and dialog logic
4. Confirm or implement menu event forwarding
5. Port startup diagnostics to Tauri
