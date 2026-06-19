# 桌面 dmg 打包交接说明

> 2026-06-16 整理。用户希望打出含最新 UI（PR #79/#80）的 dmg，但发现打包是独立工程，决定暂停并整理。

> 2026-06-19 更新：当前 `main` 已包含 Tauri 桌面打包路径和 PyInstaller 后端运行时接入。后续打包交付必须同时执行 [`docs/release/dmg-ui-regression-guard.md`](./release/dmg-ui-regression-guard.md)，避免再次把静态设计/规格稿误认为已落地 React，也避免检查到旧的 `/Volumes/PatentAgent` 挂载卷。

## 项目桌面版的真实架构

**Tauri v2**（不是 Electron）。`desktop/` 目录是**废弃的 Electron 骨架**，不要用它。
完整实现已经在当前源码的 `src-tauri/` 和 `frontend/src/` 下。

### 关键文件
- `tauri.conf.json` — Tauri v2 配置，productName=PatentAgent，bundle target=dmg，`frontendDist=../frontend/dist`，build 前会自动跑 React build 和 PyInstaller backend build
- `Cargo.toml` — crate `patentagent-tauri` v1.1.0，依赖 tauri 2 + tauri-plugin-dialog/opener
- `src/main.rs` — Rust 主进程，含后端 supervisor、文件对话框、配置 IPC

### 后端启动方式
Rust supervisor 区分 packaged 和 source-dev 两种模式：

- packaged app：从 Tauri resource dir 下启动 `patentagent-backend/patentagent-backend`。
- source-dev：从当前仓库源码启动 `python -m uvicorn backend.app.main:app`。

不要让 source-dev 自动拾取仓库顶层 `build/backend/` 里的旧 PyInstaller 产物；这个目录只是构建输出。

## 已知阻塞

1. **tauri-cli 未装好**：`cargo install tauri-cli` 编译时被 SIGKILL（疑似内存不足）。替代方案：用 npm 的 `@tauri-apps/cli`（`npx @tauri-apps/cli build`）。
2. **npm install 环境损坏**：hermes 工具设置了 `NPM_CONFIG_GLOBALCONFIG=/Users/leo/.hermes/node/etc/npmrc` + `prefix=/Users/leo/.hermes/node`，导致 `npm install` 的 reify 失效（即使全新目录也只 "audited 1 package" 不真正安装）。
   - ** workaround**：用 `env -i PATH=/opt/homebrew/bin:/usr/bin:/bin HOME=$HOME npm install --prefix <dir>` 清空环境后可正常安装（已验证）。
   - `npx --yes` 不受影响，能正常下载运行。

## 已完成且可复用的工作

### PyInstaller 后端独立化（已验证可用）
Tauri packaged app 使用 PyInstaller sidecar，避免运行时依赖用户机器上的系统 Python。

- `scripts/backend_server.py` — PyInstaller 入口，解析 `--host/--port/--log-level`，加载 `backend.app.main:app` 跑 uvicorn
- `scripts/backend.spec` — 打包配置，onedir 模式，排除 chromadb/PyQt/matplotlib 等 anaconda 污染包；**httpx 必须保留**（openai 运行时依赖）
- 产物：`build/backend/patentagent-backend/`（生成物，不提交，不作为源码证据）
- **验证**：`/api/health` 返回 `{"ok":true}`，不依赖系统 Python
- 构建：`python3 -m PyInstaller scripts/backend.spec --noconfirm --distpath build/backend`

### 接入 supervisor 的方式
- Tauri Rust 版在 packaged resource dir 下检测 `patentagent-backend` 并直接 spawn。
- Dev 模式走当前源码 Python backend，保证本地验证反映 `frontend/src/`、`backend/` 和 `src-tauri/` 的当前代码。
- 前端资源路径由 Tauri `frontendDist` 配置处理。

## 推进步骤建议（交给专门会话）

1. **记录 source identity**：按 `AGENTS.md` 记录 branch、SHA、worktree 和 dirty 状态。
2. **安装 packaging 依赖**：使用包含 `.[packaging]` extra 的 Python 环境，确保 `python3 -m PyInstaller` 可用。
3. **打包**：`npm exec --yes --package @tauri-apps/cli@^2 -- tauri build`，产物在 `src-tauri/target/release/bundle/dmg/`。
4. **验证**：执行 release gate、DMG smoke、DOM smoke 和 UI regression guard。
5. **快速看 UI 效果的替代**：若只想看 UI，直接 `npm --prefix frontend run dev` 浏览器看，或 `npm run tauri:dev`（dev 模式，后端连当前源码 python）。

## 已废弃（本次 Electron 误工，可清理）

以下是基于错误假设（Electron）做的改动，与 Tauri 方向无关：
- `desktop/electron/backend-supervisor.ts`、`desktop/electron/main.ts` 的改动（已还原）
- `desktop/electron-builder.yml`（删除）
- `desktop/package-lock.json`、根 `package-lock.json`（删除）
- `desktop/node_modules/`（npm install 装的，可删）

**保留**：`scripts/backend_server.py`、`scripts/backend.spec`。`build/backend/` 是 PyInstaller 生成物，应按当前 source identity 重新生成。
