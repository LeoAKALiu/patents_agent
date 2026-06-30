# 项目级现有技术语料库设计

## Source Identity

| 项目 | 当前值 |
| --- | --- |
| Worktree | `/Users/leo/Projects/patents_agent` |
| Git top-level | `/Users/leo/Projects/patents_agent` |
| Branch | `codex/automation-test-plan` |
| Short SHA | `08033696` |
| Worktree 状态 | Dirty |

当前 dirty 内容包括既有未提交改动：`.superpowers/sdd/task-3-report.md`、`.superpowers/sdd/task-4-report.md`、`backend/app/official_compile.py`、`docs/qa/automation-test-plan-execution-2026-06-27.md`、`tests/adversarial_flow_harness.py`、`tests/test_adversarial_flow_explorer.py`、`tests/test_official_compile.py`。本文档只新增项目级语料库设计，不把这些未提交改动视为已发布能力。

## 背景

当前知识库/语料库入口仍以“官方导出物批量建库”为核心。用户需要先创建导入任务，再上传 ZIP、CSV/XLSX、PDF/XML/TXT/DOCX 等官方导出物，然后运行导入。这个模型适合高级兜底，但不符合普通用户的专利撰写心智。

用户真正想做的是：创建一个专利项目，用题目和一句话介绍描述发明，然后让 Agent 自动提取关键词、检索现有技术、建立项目级证据底座，并在后续撰写中告诉用户哪些判断已经有证据支撑，哪些仍然证据不足。

因此，语料库应从“手动导入工具”升级为“项目级现有技术证据层”。用户不主动创建检索任务；检索任务是 Agent 从项目理解中自动生成的后台工作流。

## 目标

1. 让项目创建自然触发 Agent 现有技术检索链路。
2. 用项目名称、一句话介绍和补充材料自动生成检索意图。
3. 让 Agent 创建可查看、可编辑、可追踪的检索计划。
4. 通过官方/公开源检索候选文献，而不是要求用户上传官方导出物。
5. 将候选文献沉淀为项目级语料库版本，支撑授权导向撰写。
6. 在撰写流程中明确哪些步骤强依赖语料库，哪些步骤可先行。
7. 保留手动导入作为高级兜底能力，但不作为默认主路径。

## 非目标

- 不在本设计中实现具体 CNIPA、Google Patents、WIPO 或 Espacenet 适配器。
- 不承诺所有官方源都有稳定公开 API；首版允许以可配置 helper、公开页面解析或半自动接口接入。
- 不把语料库检索结论作为法律意见或授权保证。
- 不自动提交专利申请。
- 不把候选文献在未经确认或质量校验前直接作为高置信授权结论。
- 不移除现有批量导入管线；它应降级为高级/兜底路径。

## 产品原则

1. **用户创建项目，Agent 创建检索任务**
   普通用户的主动作是描述发明，不是填写检索表单或准备导出物。

2. **语料库是项目证据底座，不是全局资料夹**
   每个项目都应有自己的检索意图、候选文献池、语料库版本和知识状态。

3. **可以先写，但不能无证据定稿**
   项目创建、初步交底和初稿骨架可以在语料库未就绪时先行；最接近现有技术、授权前景、权利要求防线和正式稿前现有技术核验必须依赖语料库。

4. **检索计划要可解释、可编辑、可重跑**
   Agent 自动生成检索计划，但用户应能看到关键词、同义词、IPC/CPC、检索范围和策略组，并可扩大、缩小或补充。

5. **证据新鲜度必须可见**
   发明点、技术方案或保护重点发生明显变化时，旧语料库应标记为“需要补充检索”或“语料库过期”。

6. **低证据时必须诚实关闭高置信判断**
   如果语料库为空、候选不足、全文覆盖差或权利要求覆盖不足，授权前景和权利要求策略必须提示证据不足。

## 核心术语

| 术语 | 定义 |
| --- | --- |
| 项目现有技术库 | 某个项目专属的现有技术证据集合，包含检索计划、候选文献、已入库文献、全文片段、质量报告和版本状态。 |
| 检索意图 | Agent 从项目名称、一句话介绍、补充材料和发明点中提取的检索目标，包括技术对象、问题、手段、效果、关键词、排除词和分类号。 |
| Agent 检索计划 | Agent 基于检索意图生成的可查看任务草案，包含多组检索策略和目标来源。 |
| 候选文献池 | 官方/公开源检索返回的候选专利集合。候选文献尚未等同于语料库，需要去重、筛选、全文获取和质量校验。 |
| 项目语料库版本 | 经过确认、全文拉取、分段、去重、索引和质量评估后形成的可检索版本。 |
| 知识状态 | 项目级语料库当前所处状态，例如未生成计划、检索中、候选待确认、语料库就绪、需要补充检索或过期。 |
| 补充检索 | 当项目范围变化或证据覆盖不足时，在已有语料库基础上追加检索、更新候选池和新版本。 |

## 用户旅程

### 默认旅程

1. 用户在“开始”或“项目”中创建项目。
2. 用户填写项目名称和一句话介绍，可选填写技术领域、应用场景和核心创新点。
3. 系统创建 `ProjectRecord`。
4. Agent 自动提取检索意图。
5. 系统自动创建 Agent 检索计划，并将项目知识状态设为“检索计划待确认”。
6. 用户查看计划摘要，可以直接开始检索，也可以调整关键词、扩大范围或缩小范围。
7. Agent 执行官方/公开源检索，将结果写入候选文献池。
8. 用户查看候选文献池，确认入库范围或采用 Agent 推荐筛选。
9. Agent 拉取全文和元数据，执行去重、过滤、分段、权利要求识别和向量化。
10. 系统生成项目语料库版本和质量报告，将知识状态设为“语料库就绪”或“需要补充检索”。
11. 撰写流程中的发明点确认、授权前景、权利要求防线和正式稿前质检消费该语料库。

### 快速旅程

如果用户只想先写：

1. 用户创建项目。
2. Agent 提取发明理解和初步交底结构。
3. 系统后台同时生成检索计划。
4. 用户可以继续完善交底和补充材料。
5. 到发明点确认、授权前景或权利要求策略时，如果语料库未就绪，系统展示证据门禁。

门禁文案示例：

> 当前项目尚未完成现有技术检索。可以继续完善交底，但最接近现有技术、授权前景和权利要求防线需要项目语料库就绪后再给出高置信结论。

### 高级兜底旅程

高级用户可以从知识库页进入“手动导入官方导出物”。该路径复用现有导入管线：

1. 用户创建或选择导入任务。
2. 上传官方导出物或本地整理文件。
3. 运行导入。
4. 生成项目语料库版本。

该能力应作为高级模式或“从本地文件补充语料”，不应占据普通用户默认主路径。

## 信息架构

知识库页建议从当前“语料库建设 / 知识库检索”重构为项目级证据工作区。

### 顶部状态区

展示：

- 当前项目
- 知识状态
- 最近检索时间
- 已入库文献数
- 候选文献数
- 全文覆盖率
- 权利要求覆盖率
- 是否需要补充检索

主按钮根据状态变化：

| 知识状态 | 主按钮 |
| --- | --- |
| 未生成检索计划 | 让 Agent 生成检索计划 |
| 检索计划待确认 | 开始官方源检索 |
| 官方源检索中 | 查看检索进度 |
| 候选文献待确认 | 查看候选文献 |
| 语料库建库中 | 查看建库进度 |
| 语料库就绪 | 检索项目语料库 |
| 需要补充检索 | 补充检索 |
| 语料库过期 | 重新生成检索计划 |

### Agent 检索计划

展示：

- Agent 对项目的技术理解
- 核心关键词
- 英文关键词
- 同义词/近义表达
- 排除词
- 可能 IPC/CPC
- 检索时间范围
- 目标来源
- 每组策略的目的

用户可操作：

- 开始检索
- 调整关键词
- 扩大范围
- 缩小范围
- 添加排除词
- 重新生成计划

### 候选文献池

候选文献字段：

- 标题
- 公开号/授权号
- 申请人
- 公开日/授权日
- 摘要
- 来源
- URL
- 相关度
- 命中关键词
- 是否重复
- 是否可获取全文
- 建议动作：入库、排除、待确认
- 排除/入库原因

候选池操作：

- 全部采用 Agent 推荐
- 只入库高相关
- 排除低相关
- 按来源筛选
- 按年份筛选
- 按 IPC/CPC 筛选
- 查看最接近现有技术候选

### 项目语料库

展示：

- 当前语料库版本
- 入库文献列表
- 文献详情
- 片段检索
- 质量报告
- 失败清单
- 版本历史
- 补充检索入口

### 对比矩阵

当语料库就绪后，系统应支持从项目语料库生成对比矩阵：

- 我方技术特征
- 最接近现有技术
- 已公开特征
- 区别技术特征
- 可能创造性攻击
- 建议收窄/规避方向
- 证据来源链接

该矩阵供发明点确认、授权前景、权利要求防线和初稿完善消费。

## 知识状态机

```text
未生成检索计划
  -> 检索计划待确认
  -> 官方源检索中
  -> 候选文献待确认
  -> 语料库建库中
  -> 语料库就绪
```

异常和回流状态：

```text
官方源检索中 -> 需要补充检索
候选文献待确认 -> 官方源检索中
语料库就绪 -> 需要补充检索
语料库就绪 -> 语料库过期
需要补充检索 -> 官方源检索中
语料库过期 -> 检索计划待确认
```

状态说明：

| 状态 | 说明 | 用户可做 |
| --- | --- | --- |
| 未生成检索计划 | 项目刚创建，尚未提取检索意图 | 生成检索计划，继续完善项目 |
| 检索计划待确认 | Agent 已生成计划，但未开始检索 | 开始检索，调整计划 |
| 官方源检索中 | 正在检索官方/公开源 | 查看进度，取消或稍后回来 |
| 候选文献待确认 | 已有候选，但尚未建库 | 确认入库范围，排除误命中 |
| 语料库建库中 | 正在拉全文、分段、索引 | 查看建库进度 |
| 语料库就绪 | 可支撑授权导向撰写 | 检索、生成对比矩阵、进入授权分析 |
| 需要补充检索 | 检索覆盖不足或失败较多 | 扩大检索、补充关键词、重试失败项 |
| 语料库过期 | 项目发明点或技术方案变化使旧检索不再充分 | 重新生成计划或补充检索 |

## 与撰写流程的依赖关系

### 不强依赖语料库

这些步骤可以在语料库未就绪时先行：

- 创建项目
- 一句话介绍
- 项目材料上传
- 初步技术理解
- 结构化交底
- 初稿骨架
- 术语整理
- 实施例材料补充

### 强依赖语料库

这些步骤必须消费项目语料库或明确输出证据不足：

- 最接近现有技术判断
- 新颖性/创造性分析
- 发明点确认
- 权利要求保护范围设计
- 权利要求防线
- 授权前景分析
- 背景技术中可核验现有技术引用
- 正式稿前现有技术引用核验
- 审查意见答复中的对比论证

### 门禁规则

| 功能 | 语料库未就绪时行为 |
| --- | --- |
| 发明点确认 | 可生成候选，但必须标注“未完成现有技术检索”，不能给出高置信差异判断。 |
| 授权前景 | 阻断高概率结论，输出低证据关闭说明。 |
| 权利要求防线 | 可展示草案，但必须要求完成现有技术检索后再确认保护范围。 |
| 初稿完善 | 可补结构和支撑，但不得虚构现有技术事实。 |
| 正式稿编译 | 不因语料库未就绪必然阻断，但现有技术引用必须可核验；高风险项目应提示补检。 |
| 导出 | 继续遵循正式稿编译和成稿会审门禁；若报告中存在未核验现有技术引用，应阻断或要求清理。 |

## 数据模型建议

现有模型包括 `CorpusImportJob`、`CorpusVersion`、`PatentAsset`、`PatentDocument` 和 `PatentChunk`。新设计可以在兼容现有模型的基础上增加项目级对象。

### `ProjectKnowledgeState`

项目当前知识状态摘要：

- `project_id`
- `status`
- `active_plan_id`
- `active_candidate_set_id`
- `active_corpus_version_id`
- `last_search_at`
- `last_indexed_at`
- `staleness_reason`
- `document_count`
- `candidate_count`
- `claim_coverage`
- `fulltext_coverage`
- `quality_flags`

### `SearchIntent`

Agent 提取的检索意图：

- `id`
- `project_id`
- `source_project_hash`
- `technical_object`
- `technical_problem`
- `technical_means`
- `technical_effect`
- `keywords_zh`
- `keywords_en`
- `synonyms`
- `negative_keywords`
- `ipc_candidates`
- `cpc_candidates`
- `jurisdictions`
- `date_range`
- `created_by`
- `created_at`

### `AgentSearchPlan`

可执行检索计划：

- `id`
- `project_id`
- `intent_id`
- `status`
- `strategy_groups`
- `target_sources`
- `target_result_count`
- `filters`
- `created_at`
- `confirmed_at`
- `run_started_at`
- `run_finished_at`
- `warnings`

`strategy_groups` 示例：

```json
[
  {
    "id": "broad-recall",
    "label": "宽召回检索",
    "purpose": "尽量找全相近技术方向",
    "queries": ["城市体检 智能体 任务编排", "urban health agent task orchestration"],
    "sources": ["cnipa", "google_patents"]
  },
  {
    "id": "closest-prior-art",
    "label": "最接近现有技术检索",
    "purpose": "寻找可用于新颖性和创造性对比的高相关文献",
    "queries": ["城市体检 报告 证据链 复核", "urban diagnosis evidence chain review"],
    "sources": ["cnipa", "google_patents", "wipo"]
  }
]
```

### `PriorArtCandidate`

候选文献：

- `id`
- `project_id`
- `plan_id`
- `source`
- `title`
- `publication_number`
- `application_number`
- `applicant`
- `publication_date`
- `grant_date`
- `abstract`
- `url`
- `relevance_score`
- `matched_terms`
- `ipc`
- `cpc`
- `family_id`
- `duplicate_of`
- `fulltext_status`
- `recommended_action`
- `recommendation_reason`
- `user_decision`
- `metadata`

### `ProjectCorpusVersion`

项目语料库版本。可以扩展现有 `CorpusVersion`，也可以先通过字段约定实现：

- `id`
- `project_id`
- `name`
- `source_plan_id`
- `candidate_set_id`
- `status`
- `document_count`
- `chunk_count`
- `claim_coverage`
- `fulltext_coverage`
- `quality_report`
- `created_at`
- `superseded_by`

### `PriorArtComparisonMatrix`

授权导向分析消费的对比矩阵：

- `id`
- `project_id`
- `corpus_version_id`
- `source_project_hash`
- `rows`
- `closest_prior_art_refs`
- `created_at`

每行包含：

- `feature_text`
- `feature_source`
- `closest_prior_art_refs`
- `disclosed_by_prior_art`
- `distinguishing_point`
- `inventive_step_risk`
- `claim_drafting_advice`
- `evidence_urls`

## API 边界建议

### 项目触发

```text
POST /api/projects
  -> 创建项目
  -> 异步或同步触发 SearchIntent 草案生成
```

首版也可以不在 `POST /api/projects` 内直接执行 Agent，而是在项目创建后由前端调用：

```text
POST /api/projects/{project_id}/knowledge/search-intent
```

### 知识状态

```text
GET /api/projects/{project_id}/knowledge
```

返回 `ProjectKnowledgeState`、最新检索计划摘要、最新候选池摘要和当前语料库版本摘要。

### 检索意图和计划

```text
POST /api/projects/{project_id}/knowledge/search-intent
GET /api/projects/{project_id}/knowledge/search-intent/{intent_id}
POST /api/projects/{project_id}/knowledge/search-plans
PATCH /api/projects/{project_id}/knowledge/search-plans/{plan_id}
POST /api/projects/{project_id}/knowledge/search-plans/{plan_id}/run
```

### 候选文献

```text
GET /api/projects/{project_id}/knowledge/candidates
PATCH /api/projects/{project_id}/knowledge/candidates/{candidate_id}
POST /api/projects/{project_id}/knowledge/candidates/bulk-decision
```

### 建库

```text
POST /api/projects/{project_id}/knowledge/corpus-versions
GET /api/projects/{project_id}/knowledge/corpus-versions
GET /api/projects/{project_id}/knowledge/corpus-versions/{version_id}
```

### 检索和对比

```text
GET /api/projects/{project_id}/knowledge/search
POST /api/projects/{project_id}/knowledge/comparison-matrix
GET /api/projects/{project_id}/knowledge/comparison-matrix/latest
```

### 高级导入兼容

现有接口可以继续存在：

```text
POST /api/corpus/jobs
POST /api/corpus/jobs/{job_id}/files
POST /api/corpus/jobs/{job_id}/run
```

但 UI 应把它们定位为“从本地文件补充语料”。

## 前端设计要求

### 普通用户路径

在项目创建完成后，前端应展示轻量提示：

> Agent 正在根据项目题目和一句话介绍生成现有技术检索计划。

用户不需要离开主流程。系统可以在后台准备知识状态，并在发明点确认或授权分析前提醒用户。

### 知识库页

知识库页首屏应优先显示项目证据状态，而不是上传表单。

推荐结构：

1. 项目证据状态条
2. Agent 检索计划
3. 候选文献池
4. 项目语料库
5. 质量报告和失败清单

### 撰写流程内提示

在以下位置展示语料库状态：

- 发明点确认面板
- 多智能体会审输入摘要
- 授权前景报告
- 权利要求防线
- 初稿完善
- 正式稿前质检

提示应短而具体：

```text
项目语料库已就绪：已入库 82 件专利，权利要求覆盖 74%，可用于最接近现有技术分析。
```

或：

```text
项目语料库未就绪：当前只能生成发明点草案，不能给出高置信授权前景。
```

## 后端设计要求

### 检索意图生成

输入：

- `ProjectRecord.name`
- `ProjectRecord.idea`
- `ProjectRecord.technical_field`
- 用户上传材料摘要
- 已有发明点候选

输出：

- `SearchIntent`
- `AgentSearchPlan`

### 官方源检索

首版可采用 provider 抽象：

```text
PriorArtSearchProvider
  search(query, filters, limit) -> PriorArtCandidate[]
  fetch_fulltext(candidate) -> FulltextResult
```

候选 provider：

- CNIPA helper
- Google Patents public search
- WIPO Patentscope
- Espacenet
- 本地导入兜底 provider

每个 provider 必须返回 warnings，不得把失败静默吞掉。

### 建库管线

现有 `CorpusImportService` 可继续负责：

- 全文读取
- 分段
- 权利要求抽取
- 去重
- 过滤
- 索引
- 质量报告

但输入来源应扩展为候选文献的全文缓存，而不是仅依赖 `input_paths`。

### 过期判断

项目语料库至少应绑定：

- 项目名称 hash
- 一句话介绍 hash
- 选中发明点 hash
- 主要技术特征 hash

当这些内容发生明显变化时：

- 小变化：标记“需要补充检索”
- 大变化：标记“语料库过期”

首版可以采用确定性规则：

- 项目 idea 文本变化超过阈值
- 主发明点变化
- 核心技术特征列表变化
- 用户主动选择重新生成检索计划

## 错误和空状态

| 场景 | UI 行为 |
| --- | --- |
| 没有项目 | 提示先创建或选择项目。 |
| 项目描述太短 | 提示补充一句话介绍或技术领域，允许用户先保存项目。 |
| 检索计划生成失败 | 显示失败原因，允许重试或手动编辑关键词。 |
| 官方源不可用 | 显示 provider warning，允许使用可用来源继续检索。 |
| 候选结果太少 | 标记“需要补充检索”，建议扩大关键词或增加英文检索。 |
| 全文拉取失败 | 候选仍保留，进入失败清单，可重试或手动补充。 |
| 扫描版 PDF | 标记全文不可解析，不计入全文覆盖。 |
| 语料库为空 | 授权分析输出低证据关闭，禁止高置信结论。 |
| 语料库过期 | 保留旧版本，但在强依赖步骤展示补检门禁。 |

## 验收标准

1. 创建项目后，系统能自动生成或触发生成检索意图。
2. 普通用户不需要上传官方导出物也能进入语料库建设流程。
3. 知识库页默认展示项目证据状态和 Agent 检索计划，而不是上传表单。
4. 用户可以查看并调整 Agent 检索计划。
5. 系统能展示候选文献池，并区分候选、已入库、排除和失败项。
6. 建库完成后生成项目语料库版本和质量报告。
7. 语料库状态能影响发明点确认、授权前景、权利要求防线和初稿完善。
8. 语料库未就绪时，授权前景不能给出高置信结论。
9. 项目技术方案明显变化后，语料库被标记为需要补充检索或过期。
10. 手动上传官方导出物仍可作为高级兜底路径使用。

## 测试计划

### 后端

- `POST /api/projects` 后可创建或触发知识状态。
- 检索意图生成能从项目名称和一句话介绍提取关键词。
- 检索计划包含至少一个宽召回策略和一个最接近现有技术策略。
- provider 失败返回 warnings，不导致整条链路静默成功。
- 候选文献去重稳定。
- 建库管线能消费候选全文缓存。
- 空语料库运行授权前景时输出证据不足。
- 项目 idea 或主发明点变化后，知识状态变为需要补充检索或过期。

### 前端

- 知识库页未选择项目时显示空状态。
- 创建项目后显示 Agent 正在生成检索计划。
- 检索计划待确认时主按钮为“开始官方源检索”。
- 候选文献待确认时展示候选列表和推荐动作。
- 语料库就绪时展示文献数、覆盖率和质量报告。
- 语料库未就绪时，授权前景入口展示证据门禁。
- 高级导入入口仍可访问，但不作为主按钮。

### 集成

- 使用 fake provider 跑完整链路：项目创建 -> 检索计划 -> 候选池 -> 建库 -> 授权前景。
- 使用空候选 provider 验证低证据关闭。
- 使用 provider timeout 验证 warnings 和重试。
- 使用项目变更验证语料库过期。

## 实施切片

### Slice 1: 产品状态和 UI 重构

- 新增项目知识状态模型的前后端类型。
- 知识库页从上传导入表单重构为项目证据状态页。
- 保留高级导入入口。

### Slice 2: 检索意图和计划

- 从项目名称和一句话介绍生成 `SearchIntent`。
- 生成 `AgentSearchPlan`。
- 支持用户查看和轻量编辑计划。

### Slice 3: 候选文献池

- 增加 fake provider 和公开 provider 抽象。
- 写入候选文献池。
- 支持推荐入库、排除和批量决策。

### Slice 4: 建库和质量报告

- 让现有导入管线消费候选全文缓存。
- 生成项目语料库版本。
- 展示覆盖率、失败清单和版本历史。

### Slice 5: 撰写门禁集成

- 发明点确认、授权前景、权利要求防线、初稿完善消费项目知识状态。
- 空语料库或过期语料库时输出证据不足。
- 项目变更触发补检或过期状态。

## 开放问题

1. CNIPA 官方检索能力首版应依赖已有 helper，还是先用可配置 provider 抽象和 fake provider 打通链路？
2. 候选文献是否需要用户确认后才建库，还是允许“Agent 推荐直接建库，用户事后排除”？
3. 项目语料库是否默认只保存专利文献，还是同时保存论文、标准、产品文档和开源项目？
4. 语料库过期阈值首版使用文本 hash/相似度规则，还是由 Agent 判断变化是否影响检索范围？
5. 正式稿导出是否要把“语料库未就绪”作为硬门禁，还是只对现有技术引用和高置信授权判断设门禁？

## 推荐决策

首版建议选择保守、可验证的路线：

1. 先以项目级知识状态和 fake provider 打通端到端链路。
2. 检索计划生成后允许用户确认，但默认推荐直接开始检索。
3. 候选文献先进入候选池，用户可以采用 Agent 推荐批量入库。
4. 正式稿导出不因语料库未就绪整体阻断，但所有现有技术事实必须可核验；授权前景和权利要求防线必须受语料库门禁约束。
5. 手动导入保留为高级兜底，不再作为知识库页默认主流程。
