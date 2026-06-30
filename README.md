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

当前版本提供 **macOS 桌面应用**，内置自管理后端，无需手动启动 Python 或 Node.js。开发者和高级用户仍可通过命令行本地启动全部服务。

当前版本重点服务两类用户：

- 专利负责人：把产品或研究中的技术想法快速转成可审阅的专利申请材料。
- 学生和实习生：在清晰流程中并行探索候选发明点、补充证据、完善交底和初稿。

系统允许用户登记 `可行未验证` 或 `需实验` 的技术方案，用于专利布局和分案策略；但会保留证据状态，不把未验证方案写成已验证工程事实。

> 权衡 GrantAtlas 生成内容是专利撰写辅助材料，不替代专利代理师、律师或正式法律意见。

## 当前版本

当前发布版本：`v1.0.0`

本版重点：

- `工作台` 聚合三条起步路径：`从技术想法撰写发明专利`、`从结构方案撰写实用新型`、`导入已有稿件进行润色提升`。
- 左侧主导航按任务工作区组织为 `工作台 / 项目 / 文稿与修复 / 知识库 / 专家工具 / 导出 / 设置`；正文修复、版本链路和导出门禁从旧专家工具中独立出来。
- 新增授权导向目标模式：`授权稳健`、`保护范围优先`、`快速初稿`、`专利护城河`；`实用新型轻量版` 作为独立主入口。
- 新增提交成熟度、权利要求防线、初稿完善的串行质量检查入口。
- 正式稿、内部策略稿和侧车报告分离导出；正式稿必须通过正式稿编译和匹配哈希的成稿会审。
- UI 更新为 Apple-inspired Liquid Glass 风格，并加入新 logo。

## 默认工作流

普通用户只需要在 `工作台` 选择一种路径：

1. **从技术想法撰写发明专利**
   适合从产品、论文、算法或工程方案出发，完整走发明点、会审、公式、初稿、质量检查和正式导出。

2. **从结构方案撰写实用新型**
   适合产品结构、部件连接、安装位置和附图方案，优先生成结构化说明和权利要求，跳过发明专属重步骤。

3. **导入已有稿件进行润色提升**
   适合已有 Markdown、DOCX 或粘贴文本，系统先解析章节并确认内部工作稿，再进入质量检查和正式稿清理。

进入向导后，默认流程为：

1. **想法与材料**
   输入技术想法或导入已有稿件，创建项目，可上传补充材料。

2. **发明点**
   系统生成候选发明点、证据状态和护城河方向，并暂停等待用户确认主线。

3. **多智能体会审**
   收敛权利要求边界、说明书支撑和规避路径。

4. **核心公式**
   当项目包含算法或指标信号时，凝练公式、变量定义和权利要求落点。

5. **生成初稿**
   生成摘要、权利要求书、说明书和附图说明。

6. **质量检查**
   自动运行审查意见、提交成熟度、权利要求防线和初稿完善。

7. **正式稿编译**
   清除内部痕迹，生成只包含正式申请内容的提交包。

8. **成稿会审**
   多智能体复核正式稿质量、说明书支撑、内部痕迹和技术硬度。

9. **导出**
   在 `导出` 工作区导出正式提交稿、内部复核材料和风险说明。正式提交稿只在正式稿编译完成、成稿会审通过且哈希匹配后放行；所有导出文件提交前仍需专利代理师或律师复核。

高级用户可以进入 `知识库`、`专家工具`、`文稿与修复` 和 `导出` 等工作区，处理语料库建设、知识库检索、护城河地图、前置材料、多 Agent 会审、分步撰写、质量检查、审查修改、标注式修复和正式导出。

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
