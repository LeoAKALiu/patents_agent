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

PatentAgent 不是“专利文本生成器”，而是一个面向专利护城河建设的工作流系统。它把技术交底、发明点提炼、现有技术差异、权利要求防线、说明书支撑、初稿完善、提交成熟度检查和导出组织成一个可执行流程。

当前版本重点服务两类用户：

- 专利负责人：把产品或研究中的技术想法快速转成可审阅的专利申请材料。
- 学生和实习生：在清晰流程中并行探索候选发明点、补充证据、完善交底和初稿。

系统允许用户登记 `可行未验证` 或 `需实验` 的技术方案，用于专利布局和分案策略；但会保留证据状态，不把未验证方案写成已验证工程事实。

> PatentAgent 生成内容是专利撰写辅助材料，不替代专利代理师、律师或正式法律意见。

## 当前版本

当前发布版本：`v0.6.0`

本版重点：

- 默认入口改为五步专利生成向导。
- 左侧导航收敛为 `专利生成 / 实用新型轻量版 / 项目 / 专家工具`。
- 新增授权导向目标模式：`授权稳健`、`保护范围优先`、`快速初稿`、`专利护城河`；`实用新型轻量版` 作为独立主入口。
- 新增提交成熟度、权利要求防线、初稿完善的串行质量检查入口。
- 正式稿和内部策略稿分离导出，采用“警告但允许导出”。
- UI 更新为 Apple-inspired Liquid Glass 风格，并加入新 logo。

## 默认工作流

普通用户只需要从 `专利生成` 入口开始：

1. **想法与材料**  
   输入一段技术想法，创建项目，可上传补充材料。

2. **发明点**  
   系统生成候选发明点、证据状态和护城河方向，并暂停等待用户确认主线。

3. **生成初稿**  
   生成摘要、权利要求书、说明书和附图说明。

4. **质量检查**  
   自动运行审查意见、提交成熟度、权利要求防线和初稿完善。

5. **导出**  
   导出正式提交稿、内部策略稿和侧车报告。

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
- 红色风险会提示，但不硬性阻止导出。

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

## 本地启动

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

当前 release 前验证结果：

- `python3 -m pytest -q`：`79 passed, 1 skipped`
- `npm test -- --run`：`18 passed`
- `npm run build`：通过
- Chrome headless smoke：默认新建入口、四项导航、项目创建、发明点步骤、材料上传入口、专家工具入口均通过

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

## 许可证与责任

当前仓库尚未声明开源许可证。正式公开前请根据商业计划选择合适许可证。

PatentAgent 仅提供专利撰写、检索、质检和导出辅助，不构成法律意见。正式提交前应由专利代理师或律师审查。
