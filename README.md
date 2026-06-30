<p align="center">
  <img src="frontend/public/logo.svg" alt="权衡 GrantAtlas logo" width="112" />
</p>

<h1 align="center">权衡 GrantAtlas</h1>

<p align="center">
  国际专利授权工程系统
</p>

<p align="center">
  Grant-oriented patent engineering for China today, Europe/PCT tomorrow.
</p>

---

## 项目定位

权衡 GrantAtlas 是桌面优先的专利工程系统。它围绕“能否授权”组织交底、检索、证据、权利要求、初稿、质检和导出，而不是只做文本生成。

当前重点支持中国发明专利和实用新型流程。品牌和架构已为欧洲、PCT 和国际授权工作流预留空间。

## 核心能力

- 从技术想法、结构方案或已有稿件创建项目。
- 生成候选发明点、证据状态和授权风险判断。
- 建设项目语料库，纳入或排除候选现有技术。
- 组织权利要求防线、说明书支撑和提交成熟度检查。
- 生成初稿、正式稿、内部策略稿和侧车报告。
- 通过 Tauri 桌面壳启动本地 FastAPI 后端。

## 快速启动

### 后端开发

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端开发

```bash
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

访问：

```text
http://127.0.0.1:5174/
```

### 桌面开发

```bash
npm --prefix frontend ci
npm exec --yes --package @tauri-apps/cli@^2 -- tauri dev
```

Tauri 会启动本地 Python/FastAPI 后端，等待 `/api/health` 通过后加载 React 前端。

## 桌面打包

本地 DMG 交付请使用固定入口：

```bash
scripts/package_dmg.sh
```

脚本会记录 source identity、dirty 状态、DMG 路径、SHA256、smoke 结果和报告路径。正式交付前可加 `--full` 运行完整门禁。

Tauri 展示名是 `GrantAtlas` / `权衡 GrantAtlas`。为兼容已有安装和数据，bundle identifier 仍保留 `xin.liubo.patentagent`，后端 sidecar 仍叫 `patentagent-backend`。

## 配置

常用环境变量：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `LLM_MODEL`
- `PATENTAGENT_PYTHON`
- `PATENTAGENT_BACKEND_PORT`
- `PATENTAGENT_BACKEND_DATA_DIR`
- `GRANTATLAS_TAURI_DOM_SMOKE`
- `GRANTATLAS_TAURI_DOM_SMOKE_REPORT`

旧的 `PATENTAGENT_TAURI_DOM_SMOKE*` 变量仍兼容。

## 目录结构

```text
GrantAtlas
├── backend/      FastAPI 后端、规则引擎、生成逻辑和存储
├── frontend/     React + Vite 前端
├── src-tauri/    Tauri v2 桌面壳和后端 sidecar 管理
├── scripts/      构建、打包和 smoke 脚本
├── tests/        后端、桌面和脚本测试
└── docs/         设计、发布和品牌资料
```

## 验证

常用检查：

```bash
npm --prefix frontend test
npm --prefix frontend run build
python3 -m pytest
cargo test --manifest-path src-tauri/Cargo.toml
```

## 免责声明

权衡 GrantAtlas 只提供专利撰写、检索、质检和导出辅助，不构成法律意见。正式提交前应由专利代理师或律师审查。
