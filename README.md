<p align="center">
  <img src="frontend/public/logo.svg" alt="PatentAgent logo" width="112" />
</p>

<h1 align="center">PatentAgent</h1>

<p align="center">
  面向中国发明专利的授权导向专利工程系统。
</p>

<p align="center">
  <strong>从一句技术想法出发，完成发明点确认、专利初稿生成、质量检查和导出。</strong>
</p>

---

## 项目定位

PatentAgent 是以桌面应用形式交付的专利工程系统，面向中国发明专利和实用新型的授权导向撰写。它把技术交底、发明点提炼、现有技术差异、权利要求防线、说明书支撑、初稿完善、提交成熟度检查和导出组织成一个可执行流程。

当前版本提供 **macOS 桌面应用**，内置自管理后端，无需手动启动 Python 或 Node.js。开发者和高级用户仍可通过命令行本地启动全部服务。

当前版本重点服务两类用户：

- 专利负责人：把产品或研究中的技术想法快速转成可审阅的专利申请材料。
- 学生和实习生：在清晰流程中并行探索候选发明点、补充证据、完善交底和初稿。

系统允许用户登记 `可行未验证` 或 `需实验` 的技术方案，用于专利布局和分案策略；但会保留证据状态，不把未验证方案写成已验证工程事实。

> PatentAgent 生成内容是专利撰写辅助材料，不替代专利代理师、律师或正式法律意见。

## 当前版本

当前发布版本：`v1.0.0`

本版重点：

- 首屏只保留三个默认入口：`从技术想法撰写发明专利`、`从结构方案撰写实用新型`、`导入已有稿件进行润色提升`。
- 左侧主导航收敛为 `开始 / 项目 / 设置`；语料库、护城河地图、质检和导出等高级能力移入二级 `专家工具`。
- 新增授权导向目标模式：`授权稳健`、`保护范围优先`、`快速初稿`、`专利护城河`；`实用新型轻量版` 作为独立主入口。
- 新增提交成熟度、权利要求防线、初稿完善的串行质量检查入口。
- 正式稿、内部策略稿和侧车报告分离导出；正式稿必须通过正式稿编译和匹配哈希的成稿会审。
- UI 更新为 Apple-inspired Liquid Glass 风格，并加入新 logo。

## 默认工作流

普通用户只需要在首屏选择一种路径：

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

3. **生成初稿**  
   生成摘要、权利要求书、说明书和附图说明。

4. **质量检查**  
   自动运行审查意见、提交成熟度、权利要求防线和初稿完善。

5. **导出**  
   导出正式提交稿、内部策略稿和侧车报告。正式提交稿只在正式稿编译完成、成稿会审通过且哈希匹配后放行；所有导出文件提交前仍需专利代理师或律师复核。

高级用户可以进入 `专家工具` 使用旧工作台，包括语料库建设、知识库检索、护城河地图、前置材料、多 Agent 会审、分步撰写、提交成熟度、权利要求防线、初稿完善、审查修改和导出。

## 核心能力

### 1. 交底书与现有技术差异

- 从项目 draft 和补充材料生成技术交底书。
- 提炼 5-10 个候选发明点。
- 记录公开现有技术命中、差异点和待核验事项。
- 支持导出交底书 DOCX/Markdown。

### 2. 专利护城河地图

- 维护候选专利点和分案方向。
- 标记证据状态：`已验证`、`可行未验证`、`需实验`、`模型生成`。
- 记录可行依据、支撑缺口、实验需求和 Claim Chart。
- 防止未验证方案被误写成已验证事实。

### 3. 权利要求防线

- 将权利要求技术特征拆成 feature records。
- 标记已知基础、区别特征、核心组合、从属兜底和支撑需求。
- 输出防线建议和说明书支撑缺口。

### 4. 初稿完善循环

- 生成 `DRAFT_COMPLETION_REPORT.md`。
- 输出授权稳定性、保护范围、支撑强度、现有技术差异清晰度、提交成熟度和正式稿清洁度评分。
- 建立权利要求-说明书-附图-实施例-公式-数据结构-伪代码支撑矩阵。
- 生成局部修订建议，默认作为内部建议，不自动覆盖正式稿。

### 5. 提交成熟度检查

- 检查 Markdown、Mermaid、prompt、生成日志和内部会审痕迹。
- 检查不利陈述、未核验定量效果、客体风险弱表述。
- 正式稿只保留摘要、权利要求书、说明书和附图说明。
- 高风险会锁定正式提交稿入口；内部稿和侧车报告仅用于内部复核。

### 6. 官方导出优先的语料库

- 支持导入 CNIPA 或其他系统的官方导出物。
- 支持 ZIP、CSV/XLSX、PDF、XML、TXT、DOCX。
- 按摘要、权利要求书、说明书、技术领域、背景技术、发明内容、附图说明、具体实施方式切分语料。
- 维护 SQLite 元数据和本地检索索引；安装 `.[chroma]` 后可启用 Chroma。

## 技术架构

```text
PatentAgent
├── backend/              FastAPI 后端、生成逻辑、规则引擎和存储
├── frontend/             React + Vite 前端工作台
├── tests/                后端单元与接口测试
├── docs/superpowers/     设计规格和开发计划
├── data/                 本地运行数据，默认不入库
└── ARIS.md               外部研究与产品灵感材料
```

主要技术栈：

- Backend：FastAPI、Pydantic、SQLite、本地确定性 embedding、OpenAI-compatible LLM API。
- Frontend：React 19、TypeScript、Vite、Vitest、lucide-react。
- Export：DOCX、Markdown、Mermaid、Prompt 和侧车报告。

## 桌面应用安装与使用（非开发者）

### macOS

v1.0.0 release candidate 当前产物是可验证的 compiled bundle，不自动生成、签名或公证 DMG：

- `frontend/dist/`：React 渲染端静态 bundle。
- `desktop/dist-electron/`：Electron main/preload 编译产物。

release manager 可基于上述 bundle 打包 ZIP/DMG 后分发给非开发者。收到已打包的 macOS 应用后：

1. 将 PatentAgent 拖入 `/Applications` 或解压到本地应用目录。
2. 首次启动时，如果系统提示"无法验证开发者"，进入 `系统设置 → 隐私与安全性`，点击"仍要打开"。
3. 启动后，应用会自动在本地启动内置后端。首次启动可能需要 5–15 秒等待后端就绪。
4. 应用窗口打开后，选择一种撰写路径开始使用。

### 环境要求

- **macOS 13 Ventura 或更高版本**。
- Python 3.11+（应用内置自动检测；推荐通过 Homebrew 或 Anaconda 安装）。
- 有效的 DeepSeek API key（在应用设置中填入，或通过环境变量 `DEEPSEEK_API_KEY` 提供）。

### 设置 API Key

启动后进入 `设置` → 填入你的 DeepSeek API key。也可以创建 `~/.patentagent/.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

缺少 API key 时，应用仍可启动，但生成类功能会提示 503。

## 开发者本地启动

### 1. 后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

访问：

```text
http://127.0.0.1:5174/
```

### 3. Electron 桌面端（v1.0.0）

`desktop/` 工作区是 v1.0.0 桌面版。Electron 主进程会启动本地 Python/FastAPI 后端，等待 `http://127.0.0.1:<port>/api/health` 通过后再加载前端；生产模式加载 `frontend/dist/index.html`，并把渲染端的 `/api/*` 请求代理到本地后端：

```bash
cd frontend
npm run build        # 生产模式桌面端需要已有 frontend/dist/

cd ../desktop
npm install
npm run dev          # 编译 main/preload 并以开发模式启动 Electron + 后端
npm run build        # 仅编译 main/preload 到 dist-electron/
npm run smoke        # 启动 --smoke，校验后端 health + preload API
```

v1.1.0 release branch 额外加入桌面启动诊断：启动失败、前端资源缺失、渲染进程崩溃和后端 health 结果会记录为 `[startup]` JSON 行，并可在桌面端 `帮助 → 诊断信息` 中查看。生产模式若缺少 `frontend/dist/index.html`，窗口会显示诊断页而不是空白页。

可选覆盖项：`PATENTAGENT_PYTHON=/path/to/python` 指定 Python，`PATENTAGENT_BACKEND_PORT=8000` 固定本地端口，`PATENTAGENT_BACKEND_DATA_DIR=/path/to/data` 指定桌面端数据目录。`PATENTAGENT_SMOKE_SKIP_FRONTEND=1` 可让 `npm --prefix desktop run smoke` 跳过生产前端资源探测；默认在 `frontend/dist/index.html` 存在时会加载真实 production renderer 并捕获 asset/crash 失败。

桌面端详情、安全边界和 PR 范围见 `docs/release/v1.0.0-pr4-electron-skeleton.md` 与 `docs/release/v1.0.0-pr5-backend-supervision.md`。PR5 不修改 `.env`、凭证或自动合并策略。

### v1.1.0 确定性质量门禁

release/v1.1.0 使用单一 smoke 命令验证核心链路和 golden E2E 报告：

```bash
scripts/v1_smoke.sh
```

该命令默认不读取 live provider secrets，不调用外部模型，v1.1 质量趋势报告写入 `.artifacts/v1.1.0-quality/`。范围、报告字段和 live-provider opt-in 边界见 `docs/release/v1.1.0-quality-gates.md`。

## 配置

`.env` 中常用配置：

```env
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
EMBEDDING_MODEL=local-hash-128
```

说明：

- 缺少 `DEEPSEEK_API_KEY` 时，应用仍可启动，但生成、交底书和审查类接口会返回 503。
- 前端不应保存或暴露模型 API key。
- 云端部署时，应由后端读取模型密钥，并按用户身份隔离项目数据。

## 常用 API

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

创建语料导入任务：

```bash
curl -X POST http://127.0.0.1:8000/api/corpus/jobs \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"cnipa_export","source_name":"CNIPA","query":"G06V 神经网络 图像缺陷","domain":"ai_software","version_name":"ai-software-v1"}'
```

上传导入文件：

```bash
curl -X POST http://127.0.0.1:8000/api/corpus/jobs/<job_id>/files \
  -F 'file=@/path/to/cnipa-export.zip'
```

启动多 Agent 会审：

```bash
curl -X POST http://127.0.0.1:8000/api/projects/<project_id>/deliberations \
  -H 'Content-Type: application/json' \
  -d '{"trace": false, "round_depth": "converged_two_round"}'
```

## 验证

后端：

```bash
python3 -m pytest -q
```

前端：

```bash
cd frontend
npm test -- --run
npm run build
```

桌面壳：

```bash
cd desktop
npm run build        # tsc -p tsconfig.json
npm run smoke        # electron . --smoke → 校验 preload API
```

v1.0.0 发布烟测（推荐 release gate 单命令）：

```bash
bash scripts/v1_smoke.sh
```

该脚本会依次运行后端 `python3 -m pytest -q`、基于 `samples/` 三个 golden sample 的确定性 API smoke、前端 `npm test -- --run`、前端 build，以及桌面端 build。Electron launch smoke 会在当前环境可行时运行；Linux 无显示服务且无 `xvfb-run`、或 Electron 二进制未安装/未批准安装脚本时会记录跳过。整个 API smoke 使用本地 fake LLM，不读取 `.env`，不调用真实 LLM API，也不需要凭证。

当前 release 前验证结果：

- `python3 -m pytest -q`：`231 passed, 1 skipped`
- `npm test -- --run`：`58 passed`
- `npm run build`：通过
- `scripts/v1_smoke.sh`：全部通过（后端测试、API 烟测、前端测试、前端构建、桌面构建；Electron launch smoke 在当前环境可行时运行，否则记录跳过原因）

## v1.0.0 Agent Pipeline Bootstrap

v1.0.0 release automation uses GitHub as the audit trail and Hermes Kanban as the worker queue. The conservative bootstrap helper lives at:

```text
scripts/bootstrap_v1_agent_pipeline.py
```

Run it in dry-run mode first, then apply labels/profiles/board setup only after review:

```bash
python3 scripts/bootstrap_v1_agent_pipeline.py --no-detect
python3 scripts/bootstrap_v1_agent_pipeline.py --apply --repo LeoAKALiu/patents_agent --default-workdir /Users/leo/Projects/patents_agent
```

Details and safety boundaries are documented in `docs/release/v1.0.0-agent-bootstrap.md`. The helper does not configure secrets, enable auto-merge, or dispatch workers.

## 云端部署方向

后续云端版本建议按以下边界推进：

- 用户登录和项目数据隔离。
- 后端统一管理模型 API key。
- 上传文件大小、格式和敏感信息扫描。
- 生成任务队列和可恢复状态。
- 多学生并行使用，但默认不开放协作编辑。
- 导出文件和内部报告按用户/项目授权访问。

## Logo

Logo 位于：

```text
frontend/public/logo.svg
frontend/public/favicon.svg
```

设计含义：

- 玻璃护盾：专利护城河和授权稳定性。
- 专利文档：正式申请文件。
- 节点回链：权利要求、说明书、证据和现有技术之间的可追溯关系。
- 青绿色与暖金色：工程理性和授权价值。

## 已知局限

- **仅 macOS 桌面应用**：当前版本仅提供 macOS 桌面端。Linux 和 Windows 用户可使用开发者本地启动方式。
- **依赖本地 Python**：内置后端需要本地 Python 3.11+。未来版本计划打包独立后端二进制。
- **无签名安装包和自动更新**：当前仓库不会自动生成、签名或公证 DMG，也不含 Electron 自动更新。
- **单用户本地**：无用户登录、无多用户协作。项目数据存储在本地文件系统。
- **API Key 本地管理**：模型 API key 由用户在本地配置和保管，无云端密钥分发。
- **生成内容不替代法律意见**：所有生成内容均为专利撰写辅助材料，提交前应由专利代理师或律师审查。

## 许可证与责任

当前仓库尚未声明开源许可证。正式公开前请根据商业计划选择合适许可证。

PatentAgent 仅提供专利撰写、检索、质检和导出辅助，不构成法律意见。正式提交前应由专利代理师或律师审查。
