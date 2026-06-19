# 标注式修复编辑器 QA 报告

> PR5A: Patent text QA, browser QA, and merge hardening
> 审查日期: 2026-06-19
> 审查人: kimiworker (Kimi K2.7)
> 父 PR: PR-4 (merged in #106, commit bf0452f)

## 1. 中文专利污染词检查

### 1.1 污染词覆盖面

以下 7 组污染词均在 `backend/app/post_draft_repair.py` 的检测逻辑中得到覆盖：

| 污染词 | CONTAMINATION_TERMS 匹配 | UNSAFE_PATCH_TERMS 匹配 | 章节定位 | 补丁清洗 |
|---|---|---|---|---|
| `好的，根据技术交底书` | `好的，根据` | `好的，根据` | claims（文本精确定位） | 去除引导语，保留`技术交底书` |
| `主席修订补强` | `主席修订` | `主席` | description（文本精确定位） | 完全去除主席相关片段 |
| `补充实施方式` | `补充实施方式`（精确） | `补充实施方式`（精确） | 降级为污染词全文匹配 | 完全去除 |
| `待验证` | `待验证`（精确） | `待验证`（精确） | 降级为污染词全文匹配 | 完全去除 |
| `需在提交前补充` | `提交前补充` | `提交前补充` | description（文本精确定位） | 去除`提交前补充` |
| `方法方法` | `方法方法`（精确） | N/A | title（文本精确定位） | `方法方法`→`方法` |
| `颠覆了固定航线模式` | `颠覆` | N/A | description（文本精确定位） | `颠覆`→`改变` |

### 1.2 检测机制分析

**CONTAMINATION_TERMS**（10 项）：`好的，根据`, `注：`, `待验证`, `补充实施方式`, `主席修订`, `主席补充`, `需补充`, `提交前补充`, `方法方法`, `颠覆`

- 用于 `locate_issue_anchor` 的全文污染词扫描（优先级 3）
- 当精确 snippet 未匹配时，回退扫描所有章节中的污染词

**UNSAFE_PATCH_TERMS**（9 项）：`好的，根据`, `注：`, `待验证`, `主席`, `补充实施方式`, `需补充`, `提交前补充`, `{"action"`, `"patched"`

- 用于 `validate_repair_patch_text` 的补丁安全检查
- 使用比 CONTAMINATION_TERMS 更宽泛的匹配（如 `主席` 而非 `主席修订`）

**差异说明：**
- `方法方法` 和 `颠覆` 不在 UNSAFE_PATCH_TERMS 中 —— 它们是遣词问题（重复/不当用词），而非内部痕迹，由 `_deterministic_patch_text` 函数做确定性清洗
- `主席` 在 UNSAFE_PATCH_TERMS 中比 `主席修订` 更宽，确保捕获 `主席批注`、`主席建议` 等变体
- JSON 注入标记 `{"action"` 和 `"patched"` 仅出现在补丁检查中，不在普通污染词中

### 1.3 章节目录推断

`infer_target_section` 通过关键词映射定位问题章节：

- 标题：`标题`、`方法方法`
- 摘要：`摘要`
- 权利要求书：`权利要求`、`权利要求书`、`claim`
- 说明书：`说明书`、`具体实施方式`、`有益效果`、`背景技术`
- 附图说明：`附图说明`、`图1`、`图2`、`图3`
- 无法识别：返回 `unknown`

测试覆盖：`test_infer_target_section_from_chinese_messages` 验证了所有 5 个章节 + None/空字符串 → unknown。

### 1.4 精确定位优先级

`locate_issue_anchor` 采用三阶段回退策略：
1. **文本精确匹配**：在目标章节中搜索 snippet，成功则返回 `type: "text"`
2. **污染词全文扫描**：在所有章节中搜索 CONTAMINATION_TERMS，找到即返回
3. **章节级降级**：有目标章节则返回 `type: "section"`，否则 `type: "missing"`

此行为在以下测试中验证：
- `test_locate_issue_anchor_matches_snippet_in_section`（精确匹配）
- `test_locate_issue_anchor_falls_back_to_contamination_terms`（保持目标章节不跳跃）
- `test_locate_issue_anchor_can_search_all_sections_for_unknown_target`（unknown 时搜索全部）

### 1.5 contamination_hits 字典格式支持

`normalize_post_draft_issues` 通过 `_append_review_item` 支持两种 contamination_hits 格式：
- 字符串：`["待验证的文本"]`
- 字典（含 snippet）：`[{"content": "待验证的段落", "snippet": "待验证"}]`

测试覆盖：`test_normalize_contamination_hits_with_dict_payload`。

## 2. 前端 UX 文案检查

### 2.1 编辑主界面（PostDraftRepairEditor）

- 标题：`标注式修复编辑器` ✓（与设计 spec "标注式修复编辑器" 一致）
- 正常提示：`手动修订各段落，保存后请重新编译正式稿并重新成稿会审。` ✓
- 过期提示：`当前初稿已变更，AI 修正不可用。请使用人工修正。` ✓
- 保存按钮：`保存当前初稿` ✓（含 loading 态 `正在保存`）
- 底部提示：`保存后请重新编译正式稿并重新成稿会审。` ✓

### 2.2 问题导航栏（PostDraftIssueRail）

- 头部：`问题列表` + 计数 Badge ✓
- 分组标签：`阻断`、`命中`、`建议`、`未定位` ✓（与 spec "阻断、命中、建议、已修复、无法定位" 基本一致，当前实现跳过"已修复"分组）
- 严重程度：`严重`、`高`、`中`、`低` ✓
- 空状态：`暂无问题` / `运行成稿会审后，这里会显示需要处理的问题。` ✓

### 2.3 修复面板（DraftRepairInspector）

- 无选中状态：`未选择问题` / `从左侧问题列表中选择一个，查看详情和操作。` ✓
- 问题详情字段：
  - `严重程度` ✓
  - `目标段落` ✓
  - `定位方式`：`文本匹配` / `段落推断` / `未定位` ✓
  - `问题描述` ✓
  - `匹配片段` ✓
- 过期警告：`初稿已变更` / `当前初稿与生成此修复会话时的初稿不同。AI 修正功能已被禁用，请使用人工修正。` ✓
- 补丁状态标签：`等待应用`、`初稿已过期`、`不安全`、`已应用` ✓
- 补丁展示：`变更摘要`、`原始文本`、`修正后文本`、`风险提示` ✓
- 应用成功：`已写回当前初稿` / `已写回当前初稿，请重新编译正式稿并重新成稿会审。` ✓
- 操作按钮：
  - `人工修正`（始终可用）✓
  - `生成 AI 修正`（stale 或 unknown section 时 disabled）✓
  - `应用 AI 修正`（仅 proposed 状态可用）✓
  - unsafe/stale 时有明确的 disabled 原因提示 ✓

### 2.4 章节编辑区（AnnotatedDraftSection）

- 章节标签：`标题`、`摘要`、`权利要求书`、`说明书`、`附图说明` ✓
- 定位徽章：`文本定位`、`段落定位`、`未定位` ✓
- 片段提示：`片段：{snippet}` ✓

### 2.5 文案一致性

所有组件中的章节标签一致性：
- `DraftRepairInspector.SECTION_LABELS` = `{title: "标题", abstract: "摘要", claims: "权利要求书", description: "说明书", drawing_description: "附图说明", unknown: "未知"}`
- `AnnotatedDraftSection.SECTION_LABELS` = 同上（不含 unknown）
- `PostDraftRepairEditor.DRAFT_SECTION_KEYS` = `["title", "abstract", "claims", "description", "drawing_description"]`

无中英文混用、无错别字、无缺字漏字。✓

## 3. 浏览器适配 QA

### 3.1 桌面布局 (≥760px)

CSS 规则 `.repair-editor-grid`：
```css
grid-template-columns: minmax(220px, 280px) minmax(420px, 1fr) minmax(260px, 340px);
```

三栏为：问题导航 (220-280px) | 文档编辑 (420px-1fr) | 修复面板 (260-340px)

验证点：
- ✓ 三栏 grid 布局
- ✓ 宽度约束使用 minmax，保证最小可用宽度
- ✓ 整体 shell 限制 `width: min(1320px, 96vw)`，避免超宽屏变形
- ✓ 各栏独立 `overflow-y: auto` 滚动
- ✓ 问题栏 `.repair-issue-scroll` 独立滚动（`overflow-y: auto`）
- ✓ 文档编辑区 `.repair-document-pane` 独立滚动（`overflow-y: auto`）

### 3.2 移动端布局 (<760px)

CSS 媒体查询 `@media (max-width: 760px)`：
```css
grid-template-columns: minmax(0, 1fr);
grid-template-rows: auto minmax(200px, 1fr) auto;
```

降级为单列纵向排列：
- ✓ 问题栏在上（border-bottom 替代 border-right，max-height: 180px 限制高度）
- ✓ 文档编辑区在中（`max-height: none` 自适应）
- ✓ 修复面板在下（border-top 替代 border-left）
- ✓ 所有文字通过 word-break/overflow-wrap 避免重叠

### 3.3 检查项总结

| 检查项 | 桌面 (1440x1100) | 移动 (390x1100) | 状态 |
|---|---|---|---|
| 三栏布局 | grid 三栏 | grid 单列 | ✓ CSS 已配置 |
| 文字不重叠 | 各栏独立宽度 | 单列纵向排列 | ✓ |
| 问题列表独立滚动 | `.repair-issue-scroll` | max-height: 180px | ✓ |
| 保存提示可见 | footer 区域 | footer 区域 | ✓ |
| stale 状态提示 | header + inspector 警告 | header + inspector 警告 | ✓ |
| 对话框尺寸 | 1320×900px max | 96vw × 92vh | ✓ |

> **注**：本节为 CSS 与布局规则检查；第 7 节补充了 Playwright 浏览器截图和运行时指标验收结果。

## 4. 测试与构建验证

### 4.1 后端测试

```
python3 -m pytest tests/test_post_draft_repair.py -q
→ 25 passed in 2.24s

python3 -m pytest tests/test_post_draft_review.py -q
→ 16 passed in 2.17s
```

### 4.2 前端测试

```
npm --prefix frontend test -- PostDraftRepairEditor.test.tsx PostDraftReviewPanel.test.tsx
→ 2 files passed, 9 tests passed in 1.50s
```

### 4.3 前端构建

```
npm --prefix frontend run build
→ tsc -b && vite build → built in 1.46s (7 output assets)
```

### 4.4 测试覆盖总结

| 测试文件 | 数量 | 覆盖内容 |
|---|---|---|
| `test_post_draft_repair.py` | 25 | issue anchoring, contamination detection, patch creation, stale hash, unsafe rejection, repair-session endpoint, apply endpoint |
| `test_post_draft_review.py` | 16 | post-draft review lifecycle, multi-agent orchestration, export gate |
| `PostDraftRepairEditor.test.tsx` | 8 | editor rendering, save, close/null states, AI button enable/disable, stale warnings, issue selection |
| `PostDraftReviewPanel.test.tsx` | 1 | panel rendering and workbench interactions |

## 5. 门禁验证

### 5.1 过期 hash 阻止 AI 补丁

- `POST repair-patches`：当 `payload.draft_package_hash != current_hash` 返回 409 ✓
- `POST repair-patches/apply`：当 `patch.draft_package_hash != current_hash` 返回 409 ✓
- 测试覆盖：`test_repair_session_stale_when_hash_mismatches` ✓

### 5.2 unsafe 补丁不写回

- UNSAFE_PATCH_TERMS 检测在 `create_repair_patch_payload` 中执行
- unsafe 状态补丁在 endpoint 层返回 422，不写入存储
- 测试覆盖：`test_create_repair_patch_payload_unsafe` ✓

### 5.3 导出仍需重新编译+会审

- 导出 readiness 检查链：compile → review → export
- 应用 AI patch 后 `current_source_hash` 变化 → 旧 compile run 不再匹配
- 无已知门禁放松点 ✓

## 6. 发现项

### 6.1 轻微不一致（非阻塞）

1. **问题导航栏缺少"已修复"分组**
   - Spec 提到分组包括 `阻断、命中、建议、已修复、无法定位`
   - 当前实现只有 `阻断、命中、建议、未定位`
   - 影响：修复后的问题不会移至专用"已修复"分组
   - 建议：在后续 PR 中实现 issue status 驱动的分组动态更新

2. **`postDraftRepairAnchors.ts` 未实现**
   - Plan 提到 `frontend/src/flow/postDraftRepairAnchors.ts` 作为前端纯函数回退
   - 当前定位逻辑完全在后端 `post_draft_repair.py` 中
   - 影响：离线或弱网环境无法执行前端回退定位
   - 建议：当前阶段可接受（后端为主路径已完整），后续可考虑添加

3. **`主席` 与 `主席修订` 的 UNSAFE_PATCH_TERMS 覆盖粒度**
   - CONTAMINATION_TERMS 使用 `主席修订` 和 `主席补充`（精确匹配）
   - UNSAFE_PATCH_TERMS 使用 `主席`（宽泛匹配）
   - 这意味着含"主席"的正常文本（如某专利权人的姓）也会被标记为 unsafe
   - 风险：低。专利文本中"主席"一词出现在正文的概率极低，且补丁标记为 unsafe 只是阻止自动应用，用户仍可手动修改
   - 建议：当前策略保持，后续可从宽泛匹配改为上下文感知

### 6.2 确认正常项

- `方法方法` 不在 UNSAFE_PATCH_TERMS 中 —— 这是正确的，它是重复用词而非内部痕迹
- `颠覆` 不在 UNSAFE_PATCH_TERMS 中 —— 正确，它是用词选择问题而非 memo 标记
- 所有 7 组指定污染词均被 CONTAMINATION_TERMS 覆盖 ✓
- 后端 API 类型与前端 API 类型完全一致 ✓
- `locate_issue_anchor` 的三阶段回退逻辑正确实现了 spec 中的定位优先级 ✓

## 7. Playwright 浏览器截图验证

使用本地 Vite dev server 和 reviewer-only fixture 页面渲染 `PostDraftRepairEditor`，fixture 包含 24 条阻断/命中/建议问题、stale 状态和 AI patch diff 预览。

截图产物：

- `/tmp/patents-repair-editor-desktop.png`
- `/tmp/patents-repair-editor-mobile-stale.png`

采样视口：

| 视口 | 布局结果 | 横向溢出 | 关闭按钮 | Grid 列 |
|---|---|---|---|---|
| 1440×1100 | 三栏 | false | 40×40 | `280px 698px 340px` |
| 390×1100 | 单列 | false | 40×40 | `372.391px` |

验收项：

- [x] 桌面 1440×1100 实际渲染三栏：问题列表、正文编辑区、修复面板同时可见。
- [x] 移动端 390×1100 实际渲染单列，无横向滚动和文字重叠。
- [x] 长问题列表（24 项）限制在独立滚动区域，不挤压正文编辑区。
- [x] 保存按钮和“保存后请重新编译正式稿并重新成稿会审”提示在 footer 中可见。
- [x] stale 状态顶部提示和 inspector 警告均可见，AI 修正入口按预期禁用。
- [x] AI 补丁预览 diff 在桌面 inspector 中正常渲染。
- [x] 移动端关闭按钮固定为 40×40 并右对齐，避免挤占标题文本。

未纳入本轮截图：深色/浅色主题切换。当前应用未在该编辑器中新增主题逻辑，本轮只验证现有主题变量下的布局与交互门禁。

## 8. 总结

- **污染词覆盖**：7/7 指定 fixture 全部覆盖，检测逻辑正确 ✓
- **UX 文案**：中文本地化完整，无错别字，术语一致 ✓
- **布局适配**：Playwright 桌面/移动截图验证通过，CSS 三栏/单列切换无横向溢出 ✓
- **测试通过**：后端 41 测试 + 前端 9 测试 + 构建全绿 ✓
- **门禁完整**：hash 过期阻止、unsafe 拒绝、导出链完整 ✓
- **发现项**：3 个轻微不一致（非阻塞），建议在后续 PR 中处理
