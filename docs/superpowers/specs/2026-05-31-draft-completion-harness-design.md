# v0.4 Draft Completion Harness 设计

## 目的

v0.4 将 `patentAgent` 从“生成专利初稿并做提交前检查”推进到“循环完善专利初稿”。它不追求无人值守直接产出可提交文件，而是把初稿拆成可审计、可补强、可复查的工作对象，持续提高以下三类质量：

1. 授权稳定性：核心区别特征是否清楚，是否降低 2-3 篇现有技术拼接风险。
2. 保护范围：独权是否过窄或过散，从权和替代实现是否覆盖合理绕开路径。
3. 提交成熟度：正式稿是否干净，说明书、附图、实施例和术语是否支撑权利要求。

本版本应延续 v0.3 的产品原则：**警告但允许导出**。系统可以给出红色风险、禁止直接提交的内部建议、未验证方案标签和补强任务，但不得硬性阻止用户导出正式稿。

## 灵感来源与批判性吸收

### `karpathy/autoresearch`

`autoresearch` 的可吸收点不是研究主题本身，而是 harness 结构：

- 受控循环：每一轮只做有限改动，然后运行评估。
- 指标驱动：改动是否保留，取决于验证指标，而不是模型自评。
- 过程记录：实验、结果、失败和保留理由被写入可追踪日志。
- 小步迭代：长期目标被拆成短预算、可回滚的尝试。

专利场景不能照搬单一实验指标。专利初稿没有类似 `val_bpb` 的唯一客观指标，因此 v0.4 使用多维评分和结构化缺口清单，而不是用单一分数决定“保留/丢弃”。

### `ARIS.md`

`ARIS.md` 对本项目更直接的启发是可信度保障：

- 三阶段证据-声明审计：对应到专利中的“权利要求特征-说明书支撑-证据材料”审计。
- 跨模型审查-修正闭环：对应到执行者生成补强建议，审查者按预设标准打分和提出行动项。
- 研究 Wiki：对应到项目级专利知识库，记录已验证结论、未验证但可行方案、失败检索路径和禁用表述。
- 人类最终决策：对应到用户或代理师决定是否采纳补丁、是否导出、是否提交。

需要避免的误用：

- 不把模型审查意见写入正式提交稿。
- 不把未核验现有技术结论当作法律状态事实。
- 不为了迎合评分器而牺牲真实保护范围。
- 不把“可行未验证方案”伪装成已经工程验证的实施例。

## 产品决策

- v0.4 新增 `Draft Completion Harness`，作为 v0.3 `提交成熟度` 和 `权利要求防线` 之后的完善工作台。
- 完善循环默认只生成补强任务和修订建议，不自动覆盖正式稿。
- 用户可选择将某个建议应用到内部草稿；正式稿导出仍走 Clean Filing Gate。
- 未验证但可行方案允许进入专利护城河，但必须带 `feasible_unverified` 证据状态。
- 未验证方案在正式文本中只能表述为可选实施方式、替代方案、变形例或待验证实施路径，不能表述为已完成工程效果。
- 所有风险判断均进入内部报告或侧车文件，不进入正式提交稿正文。
- 现有技术、法律状态和授权前景的外部信息必须有 `verification_status`，不能默认视为已核验。
- v0.4 不做自动长时间网络检索；Prior Art 任务只生成待核验队列和可导入结果结构。

## 非目标

v0.4 不实现：

- 自动提交专利申请。
- 自动替代专利代理师审查。
- 自动联网确认 CNIPA 法律状态。
- 自动生成可直接递交的正式附图线稿。
- 完整 OA 答复模拟器。
- 完整专利族/分案规划器。
- 无人值守多日运行。

这些能力可作为 v0.5 之后的扩展，但不能阻塞本版本的初稿完善目标。

## 核心概念

### DraftState

一次完善循环的输入快照，包含：

- `project_id`
- `draft_package`
- `latest_filing_readiness_report`
- `latest_claim_defense_worksheet`
- `patent_points`
- `disclosure_runs`
- `prior_art_hits`
- `project_materials`
- `created_at`
- `snapshot_hash`

`DraftState` 是审计对象，不直接等同于正式稿。

### CompletionIssue

初稿缺口或风险项：

- `id`
- `category`
- `severity`: `low | medium | high`
- `target`: `claim | description | drawing | embodiment | term | evidence | prior_art | export`
- `source_refs`
- `message`
- `why_it_matters`
- `suggested_action`
- `blocks_submission`: 始终为建议字段，不作为导出硬阻断。

建议的 `category`：

- `claim_support_gap`
- `specification_sufficiency_gap`
- `figure_consistency_gap`
- `term_definition_gap`
- `prior_art_distinction_gap`
- `unverified_scheme_gap`
- `unfavorable_statement`
- `format_pollution`
- `subject_matter_risk`
- `claim_scope_risk`

### CompletionTask

从 issue 派生的可执行补强任务：

- `id`
- `issue_id`
- `task_type`
- `priority`
- `input_refs`
- `expected_output`
- `draft_section_target`
- `status`: `open | proposed | accepted | rejected | superseded`

示例任务：

- 为反投影特征补公式。
- 为 `IfcRelVoidsElement` 补伪 IFC 片段。
- 为清单回链补 `BillTraceRecord` 数据结构。
- 为增量更新补 GUID 依赖图遍历伪代码。
- 将“人工智能软件方法领域”改为更稳定的技术领域表述。
- 删除正式稿中的 Mermaid、prompt、会审日志或不利自认。

### ProposedPatch

系统建议的局部修订包：

- `id`
- `task_id`
- `target_section`
- `patch_kind`: `insert | replace | delete | rewrite | sidecar_only`
- `before_text`
- `after_text`
- `rationale`
- `risk_delta`
- `evidence_refs`
- `can_enter_official_draft`

`ProposedPatch` 默认不自动应用。用户接受后，可进入内部草稿或下一轮生成输入。

### CompletionScoreCard

每轮循环输出的评分：

- `authorization_stability`
- `protection_scope`
- `support_strength`
- `prior_art_distinction`
- `filing_maturity`
- `official_hygiene`
- `overall`

评分只用于排序和改进追踪，不作为法律结论。

## 审计流程

一次 `Draft Completion Run` 包含以下步骤：

1. 构建 `DraftState` 快照。
2. 复用 v0.3 Clean Filing Gate，生成格式污染、内部痕迹、不利陈述和客体风险 issues。
3. 复用 Claim Defense Worksheet，抽取权利要求技术特征和核心组合。
4. 建立 `Claim-Support Matrix`：每个权利要求特征映射到说明书段落、附图、实施例、公式、数据结构、伪代码和证据状态。
5. 运行 `Specification Sufficiency Audit`：检查公式、伪代码、数据结构、端到端实施例是否足以支撑核心特征。
6. 运行 `Figure Consistency Audit`：检查图号、模块名、步骤号、说明书引用和权利要求特征是否一致。
7. 运行 `Term Ontology Audit`：检查关键术语是否有定义、可计算表达和统一用语。
8. 运行 `Prior Art Distinction Audit`：检查核心区别点是否清楚落在组合闭环，而不是孤立单点。
9. 运行 `Unverified Scheme Audit`：检查可行未验证方案是否被写成已验证实施例或量化效果。
10. 生成 `CompletionIssue`、`CompletionTask`、`ProposedPatch` 和 `CompletionScoreCard`。
11. 用户选择接受、拒绝或暂存 patch。
12. 下一轮 run 基于更新后的内部草稿或原始草稿重新评分。

## 支撑矩阵

`ClaimSupportMatrixRow` 字段：

- `claim_ref`
- `feature_text`
- `feature_classification`
- `description_refs`
- `figure_refs`
- `embodiment_refs`
- `formula_refs`
- `data_structure_refs`
- `pseudo_code_refs`
- `prior_art_refs`
- `evidence_status`
- `risk_tags`
- `completion_status`: `supported | partial | missing`

导出时：

- 正式稿不包含支撑矩阵。
- 内部策略稿包含支撑矩阵。
- 完善报告包含矩阵摘要和补强任务。

## API 设计

新增接口：

- `POST /api/projects/{project_id}/completion-runs`
- `GET /api/projects/{project_id}/completion-runs`
- `GET /api/projects/{project_id}/completion-runs/{run_id}`
- `GET /api/projects/{project_id}/completion-runs/{run_id}/report.md`
- `POST /api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/accept`
- `POST /api/projects/{project_id}/completion-runs/{run_id}/patches/{patch_id}/reject`

v0.4 可以先实现 accept/reject 的状态记录，不必立即实现复杂的文本三方合并。

## 后端模块

新增：

- `backend/app/draft_completion.py`

负责：

- 构建 `DraftState`。
- 运行各类 audit。
- 生成 issue、task、patch 和 scorecard。
- 输出 Markdown 报告。

修改：

- `backend/app/schemas.py`：增加 completion 相关 Pydantic 模型。
- `backend/app/storage.py`：持久化 completion runs、issues、tasks 和 patches。
- `backend/app/main.py`：增加 completion API。
- `backend/app/filing_readiness.py`：暴露可复用 scan 结果，不改变警告导出原则。
- `backend/app/claim_defense.py`：暴露 feature records 给 support matrix。

## 前端设计

新增工作台入口：`初稿完善`

页面区块：

1. 最新完善评分：显示六项评分和整体趋势。
2. 高优先级缺口：按严重程度和目标章节排序。
3. 权利要求-支撑矩阵：紧凑表格展示每个核心特征的支撑状态。
4. 补强任务队列：展示任务类型、建议动作、状态。
5. 修订建议：展示 before/after、采纳按钮、拒绝按钮、是否可进入正式稿。
6. 导出区：导出 `DRAFT_COMPLETION_REPORT.md`，正式稿仍通过 v0.3 Exporter 导出。

交互约束：

- 红色风险不禁用导出按钮。
- 接受 patch 只更新内部草稿或生成下一轮输入，不直接跳过 Clean Filing Gate。
- `feasible_unverified` 用黄色状态展示，并提示只能作为可选实施方式或变形例。

## 测试策略

后端测试：

- Completion run 能基于已有 draft package 生成 scorecard。
- Mermaid、prompt、会审日志命中 `format_pollution` 或 `internal_trace`。
- 核心权利要求特征缺说明书支撑时生成 `claim_support_gap`。
- `feasible_unverified` 方案被写成已验证效果时生成 `unverified_scheme_gap`。
- `IfcRelVoidsElement`、清单回链、GUID 增量更新等核心组合缺少数据结构或伪代码时生成补强任务。
- `DRAFT_COMPLETION_REPORT.md` 包含风险和 patch，但 official export 不包含这些内部内容。

前端测试：

- 新增 `初稿完善` tab 顺序稳定。
- 评分、缺口、任务和 patch 卡片渲染正常。
- 高风险状态仍允许进入导出视图。
- 切换项目时清空旧 completion run 状态，避免跨项目污染。

验证命令：

```bash
python3 -m pytest -q
cd frontend
npm test -- --run
npm run build
```

## 与 v0.3 的关系

v0.3 是提交前闸门和权利要求防线工作表。v0.4 不替换它们，而是在它们之上增加循环完善层：

- Clean Filing Gate 继续负责正式稿清洁。
- Claim Defense Worksheet 继续负责技术特征分类。
- Draft Completion Harness 负责把检查结果转化成可执行补强任务和局部修订建议。

## 验收标准

v0.4 完成后，用户应能：

1. 对任一已有专利项目运行一次初稿完善审计。
2. 看到多维完善评分，而不是只有单一风险结论。
3. 看到权利要求特征到说明书、附图、实施例和证据的支撑矩阵。
4. 看到按优先级排序的补强任务。
5. 看到局部修订建议，但系统不会默认覆盖正式稿。
6. 对高风险草稿仍可导出正式稿，同时获得侧车完善报告。
7. 明确区分“已验证方案”和“可行未验证方案”。

## 后续扩展

v0.5 可考虑：

- Prior Art Task Queue：把待核验现有技术、公开号、权利要求 1、法律状态和同族去重做成任务队列。
- OA Rebuttal Simulator：基于 completion issues 生成驳回路径和答复策略。
- Portfolio Planner：把核心案、分案、从属兜底和绕开路径做成专利族布局。
- Figure Planner：把附图规划从文字清单推进到黑白线图草案。
- 多审查者模式：引入不同模型或规则审查者，但仍默认人类最终确认。
