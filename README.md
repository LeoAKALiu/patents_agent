# 专利写作 Agent

本项目是一个本地 Web 工作台，用于辅助撰写中国发明专利初稿。第一版聚焦 AI/软件方法类方案，支持导入授权专利语料、检索相似片段、生成完整申请文本、审查漏洞与提升点，并导出 DOCX/Markdown/Mermaid/绘图提示词。

生成内容是专利撰写辅助材料，不替代专利代理师或律师审查。默认使用 DeepSeek 云端模型，生成时会把用户 draft 和检索片段发送给配置的模型服务。

## 功能

- “语料库建设”工作区支持创建批量导入任务、上传官方导出的 ZIP/CSV/XLSX/PDF/XML/TXT/DOCX、查看失败清单、质量报告和语料版本统计。
- 导入 PDF/DOCX/TXT/Markdown 专利文件；扫描版 PDF 需要先 OCR。
- 按摘要、权利要求书、说明书、技术领域、背景技术、发明内容、附图说明、具体实施方式切分语料。
- 解析申请号、公开号/授权公告号、申请日、申请人、发明人、IPC/CPC、法律状态、来源系统和全文哈希；抽取权利要求编号、引用关系和方法/系统/装置/介质类别。
- AI/软件语料默认筛选 `G06F`、`G06N`、`G06V`、`G06Q`、`H04L` 及人工智能、神经网络、模型训练、缺陷检测等关键词，并排除实用新型和外观设计。
- 维护 SQLite 元数据和本地检索索引；安装 `.[chroma]` 时启用 Chroma 持久化向量库。
- 创建专利项目并基于 draft 生成题名、摘要、权利要求书、说明书、附图说明、Mermaid 流程图和绘图提示词。
- 可在生成前启动本机多 Agent 会审，默认调用 Codex、Gemini、Claude 围绕保护范围、权利要求布局、实施例支撑和风险控制生成策略 brief。
- 输出清楚性、支持性、单一性、保护范围、实施例缺口、术语一致性等审查意见。
- 导出 DOCX、Markdown、Mermaid `.mmd` 和绘图提示词。

## 专利护城河工作流

系统支持把“已经可行但尚未完成验证”的技术方案先加入专利护城河地图，用于规划保护范围、现有技术差异和后续实验。此类方案会保留证据状态和支撑缺口，系统不会把未验证方案伪装成已经验证的工程实现。

推荐流程：

1. 创建专利项目，录入 draft、技术背景和已有材料。
2. 添加护城河专利点，包括已实现方案、可行但未验证方案、待实验方案和模型生成候选。
3. 为每个专利点标记 `已验证`、`可行未验证` 或 `需实验`，同步填写可行依据、支撑缺口和实验需求。
4. 运行前置材料交底和现有技术差异分析，形成候选专利点、公开现有技术和 Claim Chart。
5. 运行撰写生成；未验证方案只能进入可选实施例、变体、从属限定或待验证方案，不应作为已完成实施例的确定事实。
6. 导出 DOCX/Markdown，交给专利代理师或律师做专业审查后再提交。

## v0.3 提交成熟度与权利要求防线

v0.3 增加两个正式提交前的检查入口：

1. `提交成熟度`：生成 `FILING_READINESS_REPORT.md`，检查 Markdown/Mermaid/prompt/日志残留、内部会审痕迹、不利陈述、未核验定量效果和客体风险弱表述。系统采用“警告但允许导出”，不会阻止导出正式提交稿。
2. `权利要求防线`：生成可持久化、多版本的 Claim Defense Worksheet，列出技术特征、已知基础、区别特征、核心组合、从属兜底和说明书支撑缺口。

导出文件分为：

- 正式提交稿：只包含摘要、权利要求书、说明书、附图说明。
- 内部策略稿：可保留会审、现有技术、Claim Chart、护城河评分和生成日志。
- `FILING_READINESS_REPORT.md`：记录命中规则、风险级别和修改建议。

## v0.4 初稿完善循环

v0.4 增加 `初稿完善` 工作台，用于把专利初稿拆成可审计、可补强、可复查的工作对象。它会生成：

1. `DRAFT_COMPLETION_REPORT.md`：内部侧车完善报告。
2. 多维评分：授权稳定性、保护范围、支撑强度、现有技术差异清晰度、提交成熟度和正式稿清洁度。
3. 权利要求-支撑矩阵：把权利要求特征映射到说明书、附图、实施例、公式、数据结构、伪代码和证据状态。
4. 补强任务队列：把缺口转化为可执行任务，例如补充 `BillTraceRecord`、伪 IFC 片段或 GUID 依赖图算法。
5. 局部修订建议：默认只作为建议，不自动覆盖正式稿。

本功能延续“警告但允许导出”的原则。红色风险不会禁用正式稿导出；风险、未验证方案和修订建议保存在内部报告中。可行但未验证方案可以进入护城河，但必须保留 `可行未验证` 或 `需实验` 状态，不能在正式稿中写成已验证工程效果。

## 启动

后端：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 配置

- `DEEPSEEK_API_KEY`：DeepSeek API 密钥。缺失时应用可启动，但生成、交底书和审查接口会返回 503。
- `DEEPSEEK_BASE_URL`：DeepSeek OpenAI-compatible API 地址，默认 `https://api.deepseek.com`。
- `LLM_MODEL`：默认 `deepseek-v4-pro`，可按需改为其他 DeepSeek Chat API 模型。
- `EMBEDDING_MODEL`：预留给后续云端向量化；当前默认使用本地确定性嵌入，安装 `.[chroma]` 后写入 Chroma。

## 多 Agent 会审

后端提供 `GET /api/agents/doctor` 检查本机 CLI 状态。`codex` 为必需 provider；`gemini` 和 `claude` 缺失时会降级运行。

启动会审：

```bash
curl -X POST http://127.0.0.1:8000/api/projects/<project_id>/deliberations \
  -H 'Content-Type: application/json' \
  -d '{"trace": false, "round_depth": "converged_two_round"}'
```

默认只保存结构化摘要和事件日志到 `data/deliberation-runs/`；传入 `"trace": true` 时会额外保存完整 prompt、stdout 和 stderr，便于调试但会落盘敏感 draft。

## 中国发明专利语料库

第一版采用“官方导出优先”，不绕过登录、验证码或批量限制做自动网页爬取。建议先在 CNIPA 专利检索及分析系统、地方专利检索系统或公共数据服务平台完成检索和下载，再把导出的 ZIP、元数据表和全文文件交给本系统处理。

批量导入 API：

```bash
curl -X POST http://127.0.0.1:8000/api/corpus/jobs \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"cnipa_export","source_name":"CNIPA","query":"G06V 神经网络 图像缺陷","domain":"ai_software","version_name":"ai-software-v1"}'

curl -X POST http://127.0.0.1:8000/api/corpus/jobs/<job_id>/files \
  -F 'file=@/path/to/cnipa-export.zip'

curl -X POST http://127.0.0.1:8000/api/corpus/jobs/<job_id>/run
```

CLI：

```bash
python -m backend.app.corpus import --input /path/to/export.zip --version ai-software-v1 --source cnipa-export
python -m backend.app.corpus stats --version ai-software-v1
```

统计与查看：

- `GET /api/corpus/versions`：语料版本和质量报告。
- `GET /api/corpus/stats?version=ai-software-v1`：专利数、chunk 数、章节覆盖率、IPC/年份/来源分布。
- `GET /api/corpus/documents/<document_id>`：规范化后的专利全文、章节、权利要求元数据。

## 验证

```bash
python3 -m pytest -q
cd frontend
npm test -- --run
npm run build
```
