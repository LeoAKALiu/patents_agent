# CNIPA 官方导出接入与 Provider 骨架设计

## Source Identity

| 项 | 值 |
| --- | --- |
| Worktree | `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design` |
| Git top-level | `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design` |
| Branch | `codex/cnipa-official-export-design` |
| Short SHA | `93fff8da` |
| Worktree 状态 | Clean before writing this spec |

## 背景

GrantAtlas 已经有项目级现有技术库、`PatentSearchProvider` 抽象、WIPO Patentscope provider，以及一个 `CNIPA_EPUB_SEARCH_SCRIPT` helper 入口。问题是：CNIPA helper 并不随产品交付，用户也不知道脚本从哪里来；当 helper 不存在时，界面会展示配置警告，而中文专利主流程仍然依赖 WIPO/Google 等非 CNIPA 来源，结果常常不稳定或相关度差。

用户目标不是“配置一个本地脚本”，而是让 GrantAtlas 真实接入中国专利证据。当前最稳妥的路径是把 CNIPA 官方检索/公开渠道导出的文件作为第一阶段真实数据源，同时把 provider 结构整理成可接入未来授权 API 的骨架。

相关外部事实以保守方式处理：CNIPA 有官方专利检索系统入口，但本设计不假设普通桌面用户已经拥有可直接调用的后台 API key。若后续通过官方或商业渠道获得接口授权，应接入 `cnipa_authorized_api`，而不是把网页抓取当作长期基础设施。

## 目标

1. 将 CNIPA 官方导出物变成一等项目证据来源，source id 使用 `cnipa_official_export`。
2. Agent 根据项目题目、一句话介绍和发明点生成 CNIPA 检索包，包括中文检索式、排除词、IPC/CPC、时间范围和策略组。
3. 用户导入 CNIPA 官方导出的 CSV/XLSX/ZIP 元数据文件后，系统解析为真实候选文献池；XML/PDF 在存在结构化字段或配套元数据时作为增强附件处理，而不是 fake 或脚本占位。
4. 每条候选文献必须可追溯到原始导出文件、检索式、行号或文件名、导入时间和文件 hash。
5. 建立 provider registry/broker 骨架，后续 CNIPA 授权 API、商业专利 API 或半自动浏览器采集可以复用同一套 source/status/quality 语义。
6. 保持授权判断 fail-closed：没有真实专利来源、没有候选文献或全文/权利要求覆盖不足时，不给高置信授权结论。

## 非目标

- 不绕过 CNIPA 登录、验证码、访问控制或反自动化机制。
- 不在第一阶段承诺 CNIPA 后台 live API 检索；官方接口需要用户或项目方另行获得授权。
- 不把 Google/WIPO 命中伪装成 CNIPA 命中。
- 不把 metadata-only 文献直接视为完整全文证据。
- 不移除 WIPO Patentscope provider；它仍可作为非中文或补充来源。
- 不要求用户编写或安装 `CNIPA_EPUB_SEARCH_SCRIPT`。

## 产品原则

1. **真实优先**
   CNIPA 候选必须来自官方导出文件、授权 API 或可审计的采集流程。没有真实来源时，界面应提示“等待导入 CNIPA 官方导出物”，而不是生成占位候选。

2. **手动导入不是退步，而是可靠入口**
   第一阶段允许用户从 CNIPA 官方系统导出文件再导入 GrantAtlas。关键改进是 Agent 负责生成检索包、解析导出物、去重、建库和证据门控，用户不再手工整理候选文献。

3. **Provider 能力显式化**
   不同来源能力不同：live search、official export、assisted capture、authorized API。系统要展示每个来源的可用状态，而不是只暴露底层环境变量。

4. **证据账本不可省略**
   每条候选和每个 corpus version 都需要保留原始来源痕迹，方便后续授权分析、复核和回滚。

## 核心概念

| 概念 | 定义 |
| --- | --- |
| CNIPA 检索包 | Agent 为 CNIPA 官方检索系统生成的可复制检索式和过滤条件集合。 |
| 官方导出导入 | 用户从 CNIPA 官方渠道导出结果文件后导入 GrantAtlas，由系统解析并转成候选文献。 |
| Source capability | 某个 provider/source 支持的模式、辖区、配置状态和可信级别。 |
| Evidence origin | 候选文献的证据来源类型，例如 `official_export`、`authorized_api`、`public_web`。 |
| Import ledger | 一次导入的审计记录，包含文件名、hash、解析结果、错误和候选文献 id。 |

## 架构设计

### 1. 保留现有 live search provider

现有 `PatentSearchProvider` 继续服务于 WIPO、Google fallback 和未来 live API：

```python
class PatentSearchProvider(Protocol):
    name: str
    source_id: str

    def available(self) -> tuple[bool, str | None]: ...
    def search(self, query: str, *, filters: PatentSearchFilters, limit: int) -> tuple[list[PatentSearchHit], list[str]]: ...
```

`CnipaEpubPatentProvider` 暂时降级为 legacy advanced provider，不再作为普通用户默认理解里的“CNIPA 接入”。如果仍保留，UI 文案应说明它是高级可选 helper，而不是必需配置。

### 2. 新增官方导出 importer

新增 `CnipaOfficialExportImporter`，它不是 live search provider，而是 evidence import provider：

```python
class PatentEvidenceImporter(Protocol):
    source_id: str
    evidence_origin: str

    def can_parse(self, filename: str, content_type: str | None) -> bool: ...
    def parse(self, payload: bytes, *, context: ImportContext) -> ImportResult: ...
```

`ImportResult` 输出：

- `hits: list[PatentSearchHit]`
- `warnings: list[str]`
- `failures: list[ImportFailure]`
- `raw_file_hash`
- `detected_schema`
- `row_count`
- `parsed_count`

第一阶段必须支持：

- CSV
- XLSX
- ZIP 内的 CSV/XLSX 元数据文件

第一阶段可以识别 ZIP 内 XML/PDF 附件，但只有在能从 XML 或同包元数据中读取专利字段时才生成候选。PDF 在首版主要作为附件和全文增强来源；如果 PDF 是扫描件或无法提取结构化字段，导入记录应保留文件并给出质量警告，不应凭文件名生成候选。

PDF 全文可作为增强附件。扫描 PDF 不能让全文覆盖率变成 100%，但可保留为文献附件并打质量标记。

### 3. 新增 provider registry/broker

新增 source capability registry，用于统一描述来源状态：

```python
class PatentSourceCapability(BaseModel):
    source_id: str
    display_name: str
    jurisdictions: list[str]
    modes: list[Literal["live_search", "official_export", "assisted_capture", "authorized_api"]]
    availability: Literal["available", "manual_import", "config_required", "unavailable"]
    trusted_patent_source: bool
    evidence_origin: Literal["official_export", "authorized_api", "public_web", "third_party", "legacy_helper"]
    setup_hint: str = ""
```

初始 registry：

| source_id | 模式 | 状态 | 说明 |
| --- | --- | --- | --- |
| `cnipa_official_export` | `official_export` | `manual_import` | 默认 CNIPA 中文专利真实来源。 |
| `cnipa_epub` | `live_search` | `config_required` | legacy helper，仅高级用户可配置。 |
| `wipo_patentscope` | `live_search` | `available` | 国际补充来源。 |
| `google_patents` | `live_search` | `config_required` | fallback，不作为默认强依赖。 |
| `cnipa_authorized_api` | `authorized_api` | `unavailable` | 未来授权接口占位。 |

项目知识服务不再只根据 provider chain 判断“可检索”，而是根据 source capability 决定下一步主动作：live search、等待官方导出导入、或配置来源。

### 4. 当前代码触点

实现应优先沿用现有模块：

- `backend/app/knowledge/patent_search.py`
  继续承载 `PatentSearchHit` 转换、去重、provider chain 和 future live providers。
- `backend/app/services/project_knowledge_service.py`
  接入 CNIPA 检索包、导入后的候选写入、建库质量门控和 source whitelist。
- `backend/app/schemas.py`
  增加 source capability、import ledger、query pack 或导入结果所需 schema。
- `backend/app/storage.py`
  持久化 import ledger；候选文献仍使用现有 prior-art candidate 表。
- `frontend/src/views/projectKnowledgeView.tsx`
  呈现 CNIPA 检索包、官方导出导入入口、导入结果和 source copy。

## 数据流

### 默认 CNIPA 官方导出流程

1. 用户创建或选择专利项目。
2. Agent 生成 `SearchIntent` 和 `AgentSearchPlan`。
3. 系统从计划生成 CNIPA 检索包：
   - 宽召回检索式
   - 最接近现有技术检索式
   - 排除词
   - IPC/CPC 建议
   - 时间范围
   - CN jurisdiction 固定提示
4. 知识库页显示“导入 CNIPA 官方导出物”主动作，并提供“复制检索式”。
5. 用户在 CNIPA 官方检索系统执行检索并导出结果文件。
6. 用户把导出文件导入 GrantAtlas。
7. `CnipaOfficialExportImporter` 解析文件，生成 `PatentSearchHit`。
8. 系统通过现有 `patent_hit_to_candidate` 转成 `PriorArtCandidate`，source 为 `cnipa_official_export`。
9. 候选文献池进入 `candidates_pending`。
10. 用户纳入或排除候选文献。
11. 建库时只把真实专利来源计入 patent evidence；metadata-only 或全文缺失文献影响覆盖率，但不被当作 fake。

### 未来授权 API 流程

当项目获得 CNIPA 官方接口或商业数据源授权时，新增 `cnipa_authorized_api` provider：

1. Provider registry 将该 source 标为 `authorized_api` + `available`。
2. `default_project_patent_providers()` 可按配置加入该 provider。
3. `AgentSearchPlan` 的同一组 query/filter 被 provider 消费。
4. 返回结果仍转为 `PatentSearchHit`，后续 candidate、ledger、corpus 逻辑不变。

## 字段映射

CNIPA 导出物字段名称可能存在中文/英文差异，解析器应使用别名表而不是固定列名。

| 标准字段 | 常见别名 |
| --- | --- |
| `publication_number` | 公开号、公开公告号、申请公布号、授权公告号、Publication Number |
| `application_number` | 申请号、Application Number |
| `title` | 名称、发明名称、专利名称、Title |
| `applicant` | 申请人、专利权人、Applicant |
| `inventor` | 发明人、Inventor |
| `publication_date` | 公开日、公开公告日、Publication Date |
| `application_date` | 申请日、Application Date |
| `abstract` | 摘要、Abstract |
| `ipc` | IPC、国际分类号 |
| `claims` | 权利要求、Claims |
| `description` | 说明书、Description |
| `url` | 链接、详情页、URL |

最小可入候选要求：

- `publication_number` 或 `application_number` 至少一个存在；
- `title` 或 `abstract` 至少一个存在；
- source 必须记录为 `cnipa_official_export`；
- metadata 必须包含 `raw_file_hash` 和 `import_ledger_id`。

## 质量门控

`cnipa_official_export` 是可信专利来源，但不同完整度对应不同质量状态：

| 条件 | 状态影响 |
| --- | --- |
| 只有元数据，无摘要/权利要求/说明书 | 可进入候选池；建库后 `fulltext_coverage < 1.0`。 |
| 有摘要但无权利要求 | 可用于粗筛；`claim_coverage < 1.0`。 |
| 有权利要求或可解析全文 | 可计入权利要求覆盖。 |
| 文件无法解析 | 不生成候选，import ledger 记录失败。 |
| 全部候选都没有真实 CN 公开/申请号 | 本次导入失败，不改变 ready 语料库。 |

新增 quality flags：

- `cnipa_export_metadata_only`
- `cnipa_export_missing_claims`
- `cnipa_export_partial_fulltext`
- `cnipa_export_parse_warnings`

这些 flags 不等同于 `synthetic_evidence` 或 `non_patent_source`。它们表示真实专利来源存在，但覆盖度需要补强。

## UI 行为

知识库页在 CNIPA helper 未配置时，不再把 `CNIPA_EPUB_SEARCH_SCRIPT` 作为普通用户错误展示。普通路径展示：

- “Agent 已生成 CNIPA 检索包”
- “复制 CNIPA 检索式”
- “导入 CNIPA 官方导出物”
- “也可运行 WIPO 补充检索”

导入后展示：

- 导入文件名和导入时间
- 解析候选数
- 重复/跳过数量
- 解析警告
- 候选文献池

候选卡片展示 source copy：

- `CNIPA 官方导出`
- `WIPO Patentscope`
- `Google Patents`
- `CNIPA legacy helper`

## API 设计

建议新增或扩展接口：

- `GET /api/patent-sources`
  返回 source capability registry。
- `GET /api/projects/{project_id}/knowledge/cnipa-query-pack`
  返回当前计划对应的 CNIPA 检索包。
- `POST /api/projects/{project_id}/knowledge/cnipa-export-imports`
  上传 CNIPA 官方导出物并写入候选文献池。
- `GET /api/projects/{project_id}/knowledge/import-ledgers`
  查看历史导入记录。

如果已有上传管线足够接近，可以复用底层存储和文件校验，但 API 语义应明确为项目级 CNIPA evidence import，而不是全局语料上传任务。

## 测试策略

后端：

- CSV/XLSX 字段别名解析测试。
- ZIP 内多文件解析与去重测试。
- publication number 标准化测试。
- malformed file / unknown schema / empty result 测试。
- import ledger hash、row count、warning 记录测试。
- `cnipa_official_export` 候选建库后不触发 `synthetic_evidence` 或 `non_patent_source`。
- metadata-only 文献降低 coverage，但不被当成 fake。

前端：

- helper 未配置时显示 CNIPA 导出导入主路径，而不是环境变量错误。
- query pack 可复制。
- 导入成功后候选池显示 `CNIPA 官方导出`。
- 导入警告和解析失败可见。

集成：

- 使用固定 fixture 导出文件，不在 CI 中依赖 live CNIPA 网站。
- 现有 `tests/test_patent_search_providers.py` 和 `tests/test_project_knowledge.py` 保持通过。

## 验收标准

1. 没有配置 `CNIPA_EPUB_SEARCH_SCRIPT` 时，知识库主流程仍然可用，并引导导入 CNIPA 官方导出物。
2. 导入 CNIPA 官方导出 fixture 后，候选文献池出现真实中文专利候选，source 为 `cnipa_official_export`。
3. 候选文献可纳入建库，建库版本根据全文/权利要求完整度给出准确 coverage。
4. 授权前景报告可以识别 `cnipa_official_export` 为真实专利证据来源。
5. Provider registry 能清楚展示 `cnipa_official_export`、`cnipa_epub`、`wipo_patentscope`、`google_patents` 和未来 `cnipa_authorized_api` 的能力状态。
6. 不再生成 fake CNIPA 候选，不再要求普通用户寻找本地 CNIPA helper 脚本。

## 第一阶段边界

第一阶段实现 A + C 骨架：

- A：CNIPA 官方导出物真实入候选池、可建库、可被授权门控识别。
- C：Provider registry/broker 的 source capability 骨架，支持未来授权 API 接入。

暂不实现 B：

- 不做浏览器自动登录或网页自动导出。
- 不做验证码处理。
- 不做 live CNIPA API，除非后续拿到正式授权接口。
