# QA Report: PatentAgent Local Round 29

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` and `.artifacts` contain ignored local QA evidence.

Important distinction: this round tested the installed macOS app at `/Applications/PatentAgent.app`, not a freshly packaged artifact from the current dirty source tree.

## Scope

Installed app desktop smoke for `TC-DESKTOP-001`:

- Verify installed app exists and identify bundle metadata.
- Launch installed app.
- Verify packaged sidecar backend starts from the installed app bundle.
- Verify sidecar `/api/health` returns `ok: true` and uses the installed app support data directory.
- Quit app and verify both app and backend sidecar processes exit.

## Installed App Identity

- Path: `/Applications/PatentAgent.app`
- Bundle display name: `PatentAgent`
- Bundle identifier: `xin.liubo.patentagent`
- Version: `1.1.0`
- Bundle version: `1.1.0`
- App bundle mtime observed: `Jun 26 13:51 2026`

## Commands / Probes

```bash
pgrep -x patentagent-tauri || true
open -a /Applications/PatentAgent.app
pgrep -x patentagent-tauri || true
pgrep -x patentagent-backend || true
tail -n 80 "$HOME/Library/Application Support/xin.liubo.patentagent/backend-startup.log"
curl -sS http://127.0.0.1:64207/api/health
osascript -e 'quit app "PatentAgent"'
pgrep -x patentagent-tauri || true
pgrep -x patentagent-backend || true
curl -sS --max-time 2 http://127.0.0.1:64207/api/health || true
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-DESKTOP-001 | 启动已安装 app，等待后端就绪，关闭 app | 通过；sidecar health 正常，关闭后 app 和 backend 进程退出 |

## Findings

No new product bug opened in Round29.

Startup evidence from `backend-startup.log`:

```text
setup: begin
backend root: /Applications/PatentAgent.app/Contents/Resources (Packaged)
trying bundled backend: /Applications/PatentAgent.app/Contents/Resources/patentagent-backend/patentagent-backend
backend ready: http://127.0.0.1:64207/api/health
```

Health response:

```json
{"ok":true,"llm_configured":true,"data_dir":"/Users/leo/Library/Application Support/xin.liubo.patentagent","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}
```

Process evidence while running:

```text
22192 /Applications/PatentAgent.app/Contents/MacOS/patentagent-tauri
22199 /Applications/PatentAgent.app/Contents/Resources/patentagent-backend/patentagent-backend
```

After `osascript -e 'quit app "PatentAgent"'`, exact `pgrep -x patentagent-tauri` and `pgrep -x patentagent-backend` returned no process IDs. The health endpoint then failed to connect:

```text
curl: (7) Failed to connect to 127.0.0.1 port 64207
```

## Positive Evidence

- Installed app existed at `/Applications/PatentAgent.app`.
- Installed bundle metadata identified version `1.1.0`.
- Packaged backend launched from `/Applications/PatentAgent.app/Contents/Resources`.
- `/api/health` returned `ok: true`.
- Health data directory was `/Users/leo/Library/Application Support/xin.liubo.patentagent`.
- Quitting the app stopped both app and backend sidecar processes.
- No new bug ID opened.

## State Evidence

- `.gstack/qa-reports/round29-installed-app-smoke-state.json`
- Backend startup log: `/Users/leo/Library/Application Support/xin.liubo.patentagent/backend-startup.log`

## Baseline Update

- New bug ID opened: none.
- Baseline health score unchanged: `61`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=5`.

## Notes

- I did not repair any code.
- I did not build or hand off a new DMG in this round.
- This installed-app evidence should not be represented as proof that the current dirty source tree is packaged; it proves the currently installed `/Applications/PatentAgent.app` starts and shuts down correctly.
