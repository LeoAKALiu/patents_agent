# 智慧芽与万方证据源配置骨架设计

## Source Identity

| 项目 | 当前值 |
| --- | --- |
| Worktree | `/Users/leo/Projects/patents_agent` |
| Git top-level | `/Users/leo/Projects/patents_agent` |
| Branch | `codex/grantatlas-readme-branding` |
| Short SHA | `57390e50` |
| Worktree 状态 | Dirty：存在未跟踪截图产物 `output/playwright/grantatlas-no-first-mile-no-topbar-subtitle.png` |

本文档只新增设计说明，不把上述未跟踪文件纳入本设计范围。当前 checkout 尚未包含 PR #130 的 CNIPA official export 模块；本设计应作为项目证据源体系的下一层能力，实施时以最新 `origin/main` 为准。

## 背景

GrantAtlas 的项目级现有技术库已经从“用户上传官方导出物”转向“Agent 根据项目自动生成检索计划、候选文献池和项目语料库”。但仅依赖公开网页或 Google Patents 不足以支撑授权导向检索：召回不稳定、结构化字段不足、中文专利覆盖不可控，也很难区分专利证据和非专利文献证据。

用户确认选择两个国内商业/开放平台作为下一阶段重点：

- 智慧芽 PatSnap：专利主检索源，承担项目语料库进入“专利证据 ready”的核心证据责任。
- 万方：非专利文献补强源，补充论文、期刊、会议、学位、科技文献和标准线索，但不能单独使授权判断通过证据门控。

本阶段采取“配置骨架优先，真实调用延后接入”。也就是说，App 先具备数据源配置、状态展示、检索计划编排、证据等级和接入指引；没有 API key 时显示清晰引导，不把未配置误判为检索失败。真实 API 字段映射、签名和分页逻辑留给后续接入阶段。

## 目标

1. 在产品和代码结构中显式纳入 `patsnap_api` 与 `wanfang_api` 两个数据源。
2. 支持用户在设置页配置 API key/base URL，并测试本地配置状态。
3. 没有 key 时显示接入指引和申请链接，而不是触发 `no_hits` 或检索失败。
4. 让 Agent 检索计划能区分“专利主证据源”和“非专利文献补强源”。
5. 在知识库页展示不同来源的证据等级、覆盖状态和启用状态。
6. 保持授权判断 fail-closed：只有万方命中时，不能让项目语料库变为专利证据 ready。
7. 为后续真实 API 调用预留稳定 provider 接口、配置模型、测试缝和 UI 状态。

## 非目标

- 本阶段不实现智慧芽真实检索 API 调用。
- 本阶段不实现万方真实检索 API 调用。
- 不绕过平台授权，不爬取付费页面，不模拟人工登录。
- 不把万方论文/期刊等非专利文献当成专利现有技术主证据。
- 不要求用户现在已经拥有智慧芽或万方 API key。
- 不改变 PR #130 中 CNIPA official export 的导入/兜底定位。

## 证据源定位

| Source ID | 名称 | 类型 | 证据等级 | 是否可让语料库 ready | 本阶段行为 |
| --- | --- | --- | --- | --- | --- |
| `patsnap_api` | 智慧芽 PatSnap | 专利商业库 | 主证据 | 是 | 配置骨架、状态、接入指引、stub provider |
| `wanfang_api` | 万方 | 非专利文献库 | 补强证据 | 否 | 配置骨架、状态、接入指引、stub provider |
| `cnipa_official_export` | CNIPA 官方导出 | 官方专利数据 | 主证据 | 是 | 保持现有/PR #130 能力 |
| `wipo_patentscope` | WIPO PATENTSCOPE | 官方/公开专利数据 | 主证据 | 是 | 保持兜底/补充 |
| `google_patents` | Google Patents | 公开网页专利索引 | 辅助专利证据 | 条件性 | 保持兜底，低置信标记 |
| `web_discovery` | Exa/Brave/Tavily 等 | 通用网页 | 发现线索 | 否 | 不作为本阶段重点 |

## 配置模型

新增数据源配置对象 `EvidenceSourceConfig`：

- `source_id`: `patsnap_api` 或 `wanfang_api`
- `display_name`: 用户可读名称
- `source_type`: `patent` 或 `non_patent_literature`
- `enabled`: 是否启用
- `status`: `not_configured`、`configured`、`unavailable`、`quota_limited`
- `base_url`: 可选；默认使用官方开放平台地址
- `api_key_masked`: 只返回脱敏后的 key
- `last_checked_at`: 最近配置检查时间
- `last_error`: 最近错误摘要，不包含 secret
- `application_url`: 申请/开放平台入口
- `docs_url`: 文档入口

本地配置优先级：

1. 用户在设置页保存的本地配置。
2. 环境变量覆盖：
   - `PATSNAP_API_KEY`
   - `PATSNAP_BASE_URL`
   - `WANFANG_API_KEY`
   - `WANFANG_BASE_URL`
3. 未配置时返回 `not_configured`，并附接入指引。

安全要求：

- API key 不进入前端日志、后端普通日志、质量报告或导出物。
- 前端只展示脱敏值，例如 `ps-****abcd`。
- “测试连接”在骨架阶段只验证配置存在与格式，不发起真实供应商请求。
- 后续真实接入时，默认只发送检索关键词、分类号和短查询，不发送完整未公开交底书；如需发送长文本，必须在设置中显式开启“允许向商业数据源发送完整技术摘要”。

## 后端设计

### Provider 能力注册

扩展现有专利检索 provider 体系，引入统一的数据源能力注册：

- `EvidenceSourceCapability`
  - 描述来源类型、证据等级、配置状态、是否支持实时检索、是否支持全文、是否支持法律状态。
- `PatentEvidenceProvider`
  - 用于智慧芽、CNIPA、WIPO、Google Patents 等专利候选。
- `NonPatentEvidenceProvider`
  - 用于万方等非专利文献候选。

骨架阶段新增两个 provider：

`PatSnapProvider`

- `source_id = "patsnap_api"`
- 没有 key 时 `available()` 返回 `False` 和接入指引。
- 有 key 时 `available()` 返回 `True`，但 `search()` 返回空候选和 warning：`patsnap_api_live_search_not_implemented`。
- 后续真实接入只替换 `search()` 内部，不改变服务层调用方式。

`WanfangProvider`

- `source_id = "wanfang_api"`
- 没有 key 时行为同上。
- 有 key 时 `search()` 返回空非专利文献候选和 warning：`wanfang_api_live_search_not_implemented`。
- 候选类型为 `non_patent_literature`，不能写入专利证据 ready 计数。

### 检索计划编排

Agent 检索计划增加来源分层：

- `primary_patent_sources`: 优先使用 `patsnap_api`，其次 `cnipa_official_export` / `wipo_patentscope` / `google_patents`。
- `supplemental_literature_sources`: 使用 `wanfang_api`。
- `fallback_sources`: 没有商业 key 时使用已启用的公开/官方兜底源。

计划文案示例：

> 智慧芽未配置：配置 API key 后可启用中文及全球专利主检索。当前将使用已可用的官方导出/公开源兜底。

> 万方未配置：配置 API key 后可补充论文、期刊、会议与科技文献。本项不影响专利证据门控。

### 状态语义

新增或复用质量信号时应区分：

- `source_not_configured`: 数据源未配置，不等于检索失败。
- `source_configured_not_implemented`: 已配置但真实调用尚未接入。
- `patent_source_unavailable`: 专利主源不可用，需要 fallback 或手动导入。
- `non_patent_only`: 只有非专利文献命中，授权判断仍证据不足。

如果智慧芽和其他专利源都未产生可用专利候选，而万方有命中，项目状态应是：

- `needs_supplemental_search` 或 `source_setup_required`
- `document_count` 的专利证据计数仍为 0
- `non_patent_document_count` 可大于 0
- 授权前景、权利要求防线和最接近现有技术分析继续 fail-closed

## 前端设计

### 设置页：数据源配置

新增“数据源”区块：

- 专利数据源
  - 智慧芽 PatSnap
  - 状态 badge：未配置 / 已配置 / 不可用 / 额度受限
  - API key 输入框
  - Base URL 高级输入
  - 保存
  - 测试配置
  - 申请 API key 链接
  - 文档链接
- 非专利文献源
  - 万方
  - 同样的配置控件

未配置时的文案应说明“不会影响基础功能，但授权检索覆盖会受限”。不要显示红色失败态，除非用户已经配置过但测试失败。

### 知识库页：来源覆盖

项目现有技术库顶部状态增加：

- 专利证据覆盖
- 非专利文献覆盖
- 主专利源状态：智慧芽未配置 / 已启用 / 不可用
- 补强文献源状态：万方未配置 / 已启用 / 不可用

候选文献池按证据类型分组：

- 专利候选
- 非专利文献候选
- 发现线索

候选卡片显示：

- 来源：智慧芽、万方、CNIPA、WIPO、Google Patents
- 证据等级：主证据 / 补强证据 / 发现线索
- 可用于授权门控：是 / 否

### 空状态与引导

当智慧芽未配置：

> 智慧芽未配置。配置 API key 后，GrantAtlas 可以使用商业专利库扩大中文和全球专利检索覆盖。当前仍可使用 CNIPA 导出、WIPO 或公开源兜底。

当万方未配置：

> 万方未配置。配置 API key 后，GrantAtlas 可以补充论文、期刊、会议和科技文献，用于背景技术和创造性论证补强。

当只有万方命中：

> 已找到非专利文献线索，但尚未形成可支撑授权判断的专利证据库。请配置或运行专利检索源。

## API 草案

后端新增或扩展端点：

- `GET /api/evidence-sources`
  - 返回所有证据源能力、配置状态和接入指引。
- `PUT /api/evidence-sources/{source_id}/config`
  - 保存本地配置；请求体包含 `api_key`、`base_url`、`enabled`。
- `POST /api/evidence-sources/{source_id}/check`
  - 骨架阶段只检查本地配置；真实接入阶段再做供应商连接测试。

项目知识接口扩展：

- `ProjectKnowledgeOverview.source_statuses`
- `ProjectKnowledgeState.non_patent_document_count`
- `ProjectKnowledgeState.patent_document_count`
- `PriorArtCandidate.evidence_kind`
- `PriorArtCandidate.can_satisfy_patent_gate`

## 供应商信息

智慧芽开放平台公开页面显示其提供 REST API、MCP 服务、Widget，并宣称整合全球专利数据与科技文献能力。设计使用其开放平台作为申请和文档入口：

- 入口：https://open.zhihuiya.com/
- 示例页面中出现 `connect.zhihuiya.com/search/patent/query-search-count?apikey={YOUR_API_KEY}` 形式的专利检索 API 示例。

万方开放平台公开页面提供“API目录”“我的API”“文档中心”等入口。设计使用其开放平台作为申请和文档入口：

- API 目录：https://apps.wanfangdata.com.cn/open/market/apis
- 文档中心：https://apps.wanfangdata.com.cn/open/docs

后续真实接入阶段需要以供应商账号实际可见文档为准，锁定鉴权方式、字段权限、分页、额度、错误码和全文授权边界。

## 测试策略

后端测试：

- 未配置智慧芽时，provider `available()` 返回 `False`，状态为 `not_configured`，并给出申请链接。
- 未配置万方时同上。
- 配置 key 后，骨架 provider 状态为 `configured`，但搜索返回 `*_live_search_not_implemented` warning。
- 万方候选不能让 `ProjectKnowledgeState.status` 进入 `ready`。
- 智慧芽被标记为专利主证据源，后续真实候选可计入专利 gate。
- 配置响应不泄露完整 API key。

前端测试：

- 设置页能展示智慧芽/万方配置卡片。
- 未配置时显示接入指引，不显示检索失败。
- 知识库页能区分专利证据覆盖和非专利文献覆盖。
- 只有非专利文献命中时，授权判断入口仍显示证据不足。
- 候选卡片显示来源、证据等级和是否可用于授权门控。

集成验收：

1. 全新安装、无任何 key：知识库页不再把商业源缺失显示为 `no_hits`。
2. 保存伪造智慧芽 key：状态显示“已配置，真实检索待接入”，不会产生假候选。
3. 保存伪造万方 key：状态显示“已配置，真实检索待接入”，不会影响专利 gate。
4. 运行项目检索计划：计划中能看到智慧芽为主专利源、万方为补强文献源。
5. 所有 secret 在日志、API response、截图和导出报告中均脱敏。

## 后续真实接入阶段

真实接入应拆成单独 PR：

1. 智慧芽真实专利检索
   - 锁定账号权限和 API 文档。
   - 实现 query、分页、字段映射、同族去重和错误码处理。
   - 将真实候选写入 `PriorArtCandidate`，来源为 `patsnap_api`。

2. 万方真实非专利文献检索
   - 锁定文献类型和字段权限。
   - 映射题名、作者、来源、年份、摘要、DOI/链接。
   - 写入非专利文献候选，不进入专利 gate。

3. 相关度与证据矩阵
   - 用智慧芽专利候选生成最接近现有技术对比。
   - 用万方文献补充技术背景、常识性技术启示和创造性攻击线索。
