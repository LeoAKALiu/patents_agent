# 成稿会审标注式修复编辑器设计

## 背景

`2026-06-19-post-draft-review-repair-workbench-design.md` 已覆盖渐进版体验：阻断列表独立滚动、当前内部初稿可打开大编辑器、阻断项具备人工修正和一键 AI 修正入口。

本 spec 覆盖尚未完成的终极形态：把“阻断修复工作台”和“当前内部初稿”合并成一个全功能修复窗口，类似邮件撰写或简版 Word 文档编辑器。阻断项直接标注在初稿正文上，用户可以围绕每个标注执行人工修正或一键 AI 修正。

## 目标

- 用户在一个窗口内完成阅读、定位、修订、预览差异、保存和重新流转。
- 阻断项、命中项、改写建议不再只作为旁边列表存在，而是能定位到标题、摘要、权利要求书、说明书或附图说明中的具体文本。
- 每个问题点提供两个明确动作：`人工修正` 和 `一键 AI 修正`。
- 所有修订仍写回内部工作稿，旧正式稿和旧成稿会审自动失效；正式导出仍必须重新编译正式稿并重新成稿会审。

## 非目标

- 不做完整 Word 级排版、分页、页眉页脚、批注气泡导出。
- 不直接把 AI 修复后的稿件放行正式导出。
- 不要求首版 100% 精准定位所有问题；无法定位时允许降级为章节级标注。
- 不引入协同多人实时编辑。
- 不替代专利代理师的最终法律复核。

## 用户体验

### 入口

成稿会审页保留当前“阻断修复工作台”，新增主按钮：

- `打开标注式修复编辑器`
- 若当前没有内部初稿，按钮置灰。
- 若会审结果与当前初稿 hash 不匹配，按钮仍可打开，但顶部显示“会审结果已过期，仅供参考”。

### 编辑器布局

采用三栏结构：

1. 左侧：问题导航栏
   - 分组：阻断、命中、建议、已修复、无法定位。
   - 每个问题显示来源角色、严重性、目标章节、定位状态。
   - 支持点击问题后滚动到正文标注。

2. 中间：正文编辑区
   - 以章节形式展示标题、摘要、权利要求书、说明书、附图说明。
   - 正文可编辑，字号比当前 textarea 更大，行距更适合长文阅读。
   - 命中的文本使用高亮标注；章节级问题在章节标题旁显示标记。
   - 当前选中问题使用更明显描边或侧边指示。

3. 右侧：修复面板
   - 显示当前问题详情、原文片段、会审建议、AI patch 预览。
   - 提供 `人工修正`、`生成 AI 修正`、`应用 AI 修正`、`跳过`。
   - 对可安全应用的官方安全补丁显示“来自主席安全补丁”标签。

移动端降级为上下结构：

- 顶部为问题筛选与章节切换。
- 中部为正文编辑区。
- 底部抽屉展示当前问题和修复动作。

## 问题定位规则

系统把 post-draft review 的输出统一转成 `DraftReviewIssue`：

- `id`
- `kind`: `blocking | hit | suggestion`
- `severity`: `critical | high | medium | low`
- `source`: `chair | claims_reviewer | spec_cleaner | technical_hardness`
- `message`
- `snippet`
- `target_section`: `title | abstract | claims | description | drawing_description | unknown`
- `anchor`
- `status`: `open | fixed | skipped | stale | unanchored`

定位优先级：

1. 若会审输出包含结构化 `location` 和 `snippet`，优先在目标章节内精确匹配 snippet。
2. 若只有中文描述，使用关键词映射推断章节：
   - “标题”“方法方法” -> `title`
   - “权利要求”“权利要求1/6/7” -> `claims`
   - “摘要” -> `abstract`
   - “说明书”“具体实施方式”“有益效果” -> `description`
   - “附图说明”“图1” -> `drawing_description`
3. 对常见污染词执行全文定位：
   - `好的，根据`
   - `注：`
   - `待验证`
   - `补充实施方式`
   - `主席修订`
   - `主席补充`
   - `需补充`
   - `提交前补充`
4. 若匹配不到具体文本，降级为章节级 anchor。
5. 若章节也无法判断，放入“无法定位”，允许用户手动选择章节。

## 人工修正流程

1. 用户点击问题的 `人工修正`。
2. 编辑器滚动到对应 anchor。
3. 若是文本级 anchor，光标选中命中片段。
4. 用户直接修改正文。
5. 系统实时把对应问题标为 `editing`，但不自动判定已修复。
6. 用户点击 `保存当前初稿`。
7. 后端保存五个正文字段并返回新 `draft_hash`。
8. 前端清空旧正式稿匹配状态，并提示“请重新编译正式稿并重新成稿会审”。

可选增强：

- 保存前运行轻量本地清污检查，对仍存在的内部标记给出红色提示。
- 对已消失的 snippet 自动标记为“疑似已修复”，但仍要求重新会审确认。

## 一键 AI 修正流程

### 官方安全补丁路径

若成稿会审已提供 `official_safe_patches`：

1. 问题卡显示 `一键 AI 修正` 可用。
2. 点击后展示 patch 预览，不直接写回。
3. 用户确认 `应用到当前初稿`。
4. 后端校验 `review.draft_package_hash == current_draft_hash`。
5. 应用 patch，保存工作稿，返回新 hash。
6. UI 标记旧正式稿和旧会审失效。

### 按问题生成 patch 路径

若没有安全补丁，但问题可定位：

1. 用户点击 `生成 AI 修正`。
2. 前端发送 `issue_id`、目标章节、附近上下文、当前 draft hash。
3. 后端生成 `DraftRepairPatch`，但状态为 `proposed`。
4. UI 展示 diff：
   - 删除内容
   - 新增内容
   - 影响章节
   - 风险说明
5. 用户点击 `应用 AI 修正` 后写回工作稿。

AI patch 必须满足：

- 不新增 `注：`、`待验证`、`主席`、`补充实施方式` 等内部痕迹。
- 不新增 attorney memo、system trace、JSON patch 文本。
- 不修改非目标章节，除非 patch 明确声明跨章节修改。
- 必须绑定当前 draft hash；hash 变化后 patch 变为 stale。

## 后端接口设计

### 保存人工编辑

沿用渐进版新增接口：

`PUT /api/projects/{project_id}/draft-package`

请求：

```json
{
  "title": "...",
  "abstract": "...",
  "claims": "...",
  "description": "...",
  "drawing_description": "..."
}
```

返回：更新后的 `DraftPackage`。

### 获取标注会话

新增：

`GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session`

返回：

```json
{
  "project_id": "...",
  "review_run_id": "...",
  "draft_package_hash": "...",
  "current_draft_hash": "...",
  "stale": false,
  "issues": [],
  "sections": {
    "title": "...",
    "abstract": "...",
    "claims": "...",
    "description": "...",
    "drawing_description": "..."
  }
}
```

### 生成单问题 AI patch

新增：

`POST /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches`

请求：

```json
{
  "issue_id": "...",
  "draft_package_hash": "...",
  "target_section": "claims",
  "selected_text": "...",
  "nearby_context": "..."
}
```

返回：

```json
{
  "id": "...",
  "issue_id": "...",
  "status": "proposed",
  "target_section": "claims",
  "original": "...",
  "patched": "...",
  "diff_summary": "...",
  "risk_notes": [],
  "draft_package_hash": "..."
}
```

### 应用单问题 patch

新增：

`POST /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-patches/{patch_id}/apply`

行为：

- 校验 patch hash 新鲜度。
- 校验 target section 仍包含 original。
- 应用 patch。
- 运行轻量清污规则。
- 保存内部工作稿。
- 返回新 `DraftPackage` 和新 `current_draft_hash`。

## 前端组件设计

新增或拆分：

- `PostDraftRepairEditor.tsx`
  - 顶层弹窗/全屏编辑器。
  - 管理选中 issue、编辑内容、保存状态。
- `PostDraftIssueRail.tsx`
  - 左侧问题导航。
  - 负责分组、筛选、点击定位。
- `AnnotatedDraftSection.tsx`
  - 单章节正文编辑区。
  - 首版可用 textarea + 章节级标注；后续可升级为 contenteditable/token overlay。
- `DraftRepairInspector.tsx`
  - 右侧修复面板。
  - 展示当前 issue、patch diff、操作按钮。
- `postDraftRepairAnchors.ts`
  - 纯函数：把 review run + draft package 转换成 issue anchors。
  - 必须有单元测试。

首版建议不要直接引入复杂富文本库。可先使用“textarea 编辑 + 只读高亮预览”的组合：

- 编辑态：textarea 保证稳定输入和保存。
- 预览态：高亮渲染命中片段。
- 点击问题时，同步滚动到目标章节并显示命中上下文。

## 数据一致性与门禁

- repair session 绑定 `review_run_id` 和 `draft_package_hash`。
- 用户保存人工修改或应用 AI patch 后，生成新 draft hash。
- 新 hash 出现后：
  - 当前 official compile run 不再匹配。
  - 当前 post-draft review 不再匹配。
  - 导出继续锁定。
- UI 顶部必须显示下一步：
  1. 保存当前初稿
  2. 重新运行质量检查
  3. 重新编译正式稿
  4. 重新成稿会审

## 错误状态

- `stale_review`: 会审结果与当前稿不匹配，只能参考，不能应用 AI patch。
- `stale_patch`: patch 生成后正文已变，必须重新生成。
- `anchor_missing`: 无法定位问题，允许用户手动选择章节。
- `unsafe_patch`: patch 引入内部痕迹或非正式文本，只能作为右侧备忘，不允许应用。
- `save_failed`: 保留编辑器内容，提示重试。

## 测试计划

后端：

- repair session 能从 blocking issues、contamination hits、rewrite suggestions 生成统一 issues。
- 常见污染词能定位到正确章节。
- 无法定位的问题进入 `unanchored`。
- 单问题 patch 生成绑定 draft hash。
- draft hash 变化后应用 patch 返回 409。
- unsafe patch 不写回 package。

前端：

- 打开标注式编辑器后，左侧 issue、正文区、右侧 inspector 同时出现。
- 点击 issue 后选中对应章节。
- `人工修正` 能打开/聚焦可编辑正文。
- `生成 AI 修正` 在 stale review 下置灰。
- 保存后显示重新编译和重新会审提示。
- 移动端布局不出现文字重叠。

浏览器验收：

- 桌面 1440px：三栏可见，正文区宽度足够阅读权利要求。
- 窄屏 390px：问题导航、正文、修复面板以单列/抽屉方式呈现。
- 长阻断列表：只有问题栏滚动，正文编辑区不会被整页挤走。

## 分期建议

### Phase 1：标注数据层

- 新增 `postDraftRepairAnchors.ts` 纯函数。
- 后端可先不建新表，repair session 由 review run 和当前 package 即时计算。
- 前端在现有大编辑器中展示 issue anchors 和章节级定位。

### Phase 2：全屏三栏编辑器

- 新增 `PostDraftRepairEditor`。
- 支持 issue rail、章节编辑、右侧 inspector。
- 人工保存复用 `PUT /draft-package`。

### Phase 3：单问题 AI patch

- 新增 repair patch API。
- 支持生成、预览、应用、stale 校验。
- AI patch 不直接放行导出。

### Phase 4：高亮编辑体验增强

- 从 textarea 升级为 overlay 高亮或轻量 contenteditable。
- 增加“已修复/跳过/待复核”状态。
- 增加本地清污检查与保存前提醒。

## 验收标准

- 用户无需在页面右半幅和长阻断列表之间来回滚动，即可处理成稿会审问题。
- 至少 80% 的常见内部污染问题能自动定位到章节或文本片段。
- 所有 AI 修正必须先预览再应用。
- 任意修订都会使旧正式稿和旧成稿会审失效。
- 正式导出门禁逻辑不因编辑器增强而放松。
