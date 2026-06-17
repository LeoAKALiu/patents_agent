# 桌面 dmg 打包交接说明

> 2026-06-16 整理。用户希望打出含最新 UI（PR #79/#80）的 dmg，但发现打包是独立工程，决定暂停并整理。

## 项目桌面版的真实架构

**Tauri v2**（不是 Electron）。`desktop/` 目录是**废弃的 Electron 骨架**，不要用它。
完整实现在独立分支 `agent/v1.1-tauri-desktop-migration`。

### 关键文件（在该分支的 `src-tauri/`）
- `tauri.conf.json` — Tauri v2 配置，productName=PatentAgent，bundle target=dmg，`frontendDist=../frontend/dist`，build 前会自动跑 `npm --prefix ../frontend run build`
- `Cargo.toml` — crate `patentagent-tauri` v1.1.0，依赖 tauri 2 + tauri-plugin-dialog/opener
- `src/main.rs` — Rust 主进程，含后端 supervisor、文件对话框、配置 IPC
- worktree: `/private/tmp/patents-agent-v1-1-tauri-impl`（target 有 1.5G 缓存但无最终产物）

### 后端启动方式（main.rs:343-388）
Rust supervisor spawn 系统 `python3 -m uvicorn backend.app.main:app`，依赖系统已装 Python + `pip install -e .`。**后端尚未独立化打包**。

## 分支关系（关键）
- Tauri 分支从 `b5cfdb8`（PR #35，v1.0.0）分叉
- **落后 main 12 个提交**：不含 #74-#80 的所有改动（知识门禁、主席修订、hash 门禁修复、本次 UI 优化）
- Tauri 分支自身领先 20 个提交（scaffold、supervisor、打包、release 文档）

**要打"含本次 UI"的 dmg，必须先把 main 合进 Tauri 分支。**

## 已知阻塞

1. **tauri-cli 未装好**：`cargo install tauri-cli` 编译时被 SIGKILL（疑似内存不足）。替代方案：用 npm 的 `@tauri-apps/cli`（`npx @tauri-apps/cli build`）。
2. **npm install 环境损坏**：hermes 工具设置了 `NPM_CONFIG_GLOBALCONFIG=/Users/leo/.hermes/node/etc/npmrc` + `prefix=/Users/leo/.hermes/node`，导致 `npm install` 的 reify 失效（即使全新目录也只 "audited 1 package" 不真正安装）。
   - ** workaround**：用 `env -i PATH=/opt/homebrew/bin:/usr/bin:/bin HOME=$HOME npm install --prefix <dir>` 清空环境后可正常安装（已验证）。
   - `npx --yes` 不受影响，能正常下载运行。

## 已完成且可复用的工作

### PyInstaller 后端独立化（已验证可用）
Tauri 和 Electron 两个 supervisor 都依赖系统 Python。独立化是打包真独立 dmg 的前提。**这部分已做并验证通过，可复用到 Tauri 工程的任何一种。**

- `scripts/backend_server.py` — PyInstaller 入口，解析 `--host/--port/--log-level`，加载 `backend.app.main:app` 跑 uvicorn
- `scripts/backend.spec` — 打包配置，onedir 模式，排除 chromadb/PyQt/matplotlib 等 anaconda 污染包；**httpx 必须保留**（openai 运行时依赖）
- 产物：`build/backend/patentagent-backend/`（142MB，冷启动 ~8s）
- **验证**：`/api/health` 返回 `{"ok":true}`，不依赖系统 Python
- 构建：`python3 -m PyInstaller scripts/backend.spec --noconfirm --distpath build/backend`

### 接入 supervisor 的方式（供 Tauri Rust 侧参考）
- Electron 版（`desktop/electron/backend-supervisor.ts`）已实现 `backendExecutable` 选项：传入二进制路径则直接 spawn 它而非 `python -m uvicorn`，cwd 设为二进制所在目录
- Tauri Rust 版 `start_backend`（main.rs:343）需做类似改造：检测 `app.handle().path().resource_dir()` 下是否有 `patentagent-backend`，有则 `Command::new(exe).args(["--host","127.0.0.1","--port",port,"--log-level","warning"])`，无则走现有 python 路径
- 前端资源路径同理：Tauri 用 `frontendDist` 配置自动处理，无需手动 resolve

## 推进步骤建议（交给专门会话）

1. **装 tauri-cli**：优先试 `npx @tauri-apps/cli@latest --version`，或用 clean-env npm 在 Tauri worktree 装
2. **在 Tauri worktree merge main**：`git merge origin/main`，解决 frontend 冲突（Tauri 分支用旧 frontend，应整体采用 main 版本）
3. **（可选，做真独立）后端独立化**：把 `scripts/backend.spec` + `backend_server.py` 拿到该分支，跑 PyInstaller，改 Rust supervisor 调二进制
4. **打包**：`cd src-tauri && cargo tauri build`（或 `npx @tauri-apps/cli build`），产物在 `src-tauri/target/release/bundle/dmg/`
5. **快速看 UI 效果的替代**：若只想看 UI，直接 `cd frontend && npm run dev` 浏览器看，或 Tauri worktree `cargo tauri dev`（dev 模式，后端连系统 python）

## 已废弃（本次 Electron 误工，可清理）

以下是基于错误假设（Electron）做的改动，与 Tauri 方向无关：
- `desktop/electron/backend-supervisor.ts`、`desktop/electron/main.ts` 的改动（已还原）
- `desktop/electron-builder.yml`（删除）
- `desktop/package-lock.json`、根 `package-lock.json`（删除）
- `desktop/node_modules/`（npm install 装的，可删）

**保留**：`scripts/backend_server.py`、`scripts/backend.spec`、`build/backend/`（PyInstaller 产物，可复用）
