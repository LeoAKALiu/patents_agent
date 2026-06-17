# PR Review: #79 & #80

## PR #79 — `fix(guidedFlow): stop comparing snapshot_hash against source_draft_hash`

### 结论：LGTM，建议合并

### 哈希公式验证（后端源码确认）

| 函数 | 位置 | 公式 |
|------|------|------|
| `_package_hash` | `draft_completion.py:188-189` | `sha256(package.model_dump_json())` |
| `source_draft_hash` | `official_compile.py:44-45` | `sha256(package.model_dump_json())` |
| `_snapshot_hash` | `draft_completion.py:177-185` | `sha256(package + points + materials)` |

公式声明准确：`_package_hash` 与 `source_draft_hash` 完全相同（都是 `sha256(package)`），`_snapshot_hash` 额外拼接了 points 和 materials。旧代码用 `snapshot_hash` 比较 `currentSourceDraftHash`，公式不同，永远不等 → 质量门禁锁死。

### 需开发者确认的问题

#### P2 — `createdAtTime` 对无时间戳 item 的排序不稳定性

`guidedFlow.ts` 新增的 `createdAtTime` 在 `created_at` 为空时返回 `0`。若多个 item 均无时间戳，`Array.sort` 结果不确定。

**当前状态**：后端总生成 `created_at`，实际不会触发。
**建议**：可接受现状，或在 `byNewest` 中对 `0` 值做 insertion-order 保底：

```typescript
const byNewest = <T extends { created_at?: string }>(items: T[]): T[] =>
  [...items].sort((a, b) => createdAtTime(b) - createdAtTime(a));
// 若需严格稳定：加一个 original index 比较作为 tiebreaker
```

---

## PR #80 — `style(frontend): 中文排版、按钮统一与口语化文案`

### 结论：LGTM（需确认 1 处设计意图），建议合并

### 需开发者确认的问题

#### P1 — `.top-actions .btn` 新增了边框

旧代码 `.top-actions .btn` 显式设置 `border: 0`（无边框按钮）。PR #80 删除该行后，按钮继承共享块的 `border: 1px solid transparent`，但随后被 `.top-actions .btn { border: 1px solid var(--border-subtle); }` 覆盖。

**效果**：顶栏按钮从无边框变为有可见边框。

请确认这是有意的视觉调整。若无意，修复方式：

```css
.top-actions .btn {
  border: 0; /* 或 1px solid transparent，保持无边框 */
}
```

#### P2 — `text-spacing-trim: space-all` 浏览器兼容性

`styles.css` body 规则新增 `text-spacing-trim: space-all`。当前支持：Chrome 123+, Safari 18.4+。**Firefox 不支持**（会忽略该属性）。

降级安全（不影响功能），但 Firefox 用户缺少 CJK 标点间距优化。无需修改，知晓即可。

#### P2 — `.nav-link` 高度从 36px 改为 34px

PR 描述说按钮统一为 40px，但 `.nav-link` 高度实际从 36px 降为 34px。与按钮 40px 不一致。

PR 描述已说明"侧边导航项与表单控件的触控高度保留（非操作按钮）"，逻辑合理，仅提醒注意。

---

## 交叉冲突分析

两个 PR 都修改 `guidedFlow.test.ts` 和 `guidedFlow.ts`：

| 文件 | PR #79 改动 | PR #80 改动 | 冲突风险 |
|------|------------|------------|----------|
| `guidedFlow.test.ts` fixture | 加 `draft_package_hash: "draft-hash"` (line 231) | 无 | 低 |
| `guidedFlow.test.ts` 新测试 | 加 2 个 `it()` 块 (line 1220+) | 改断言 (line 537) | 低（不同行） |
| `guidedFlow.ts` isQualityChecked | 重写 (line 493-522) | 改文案 (line 397 等) | 低（不同函数） |

**建议合并顺序**：先 #79（bug fix），再 #80（style）。Rebase 时 fixture 区域可能需手动合并（各加不同字段）。

---

## 合并后验证清单

- [ ] `npm test` 全量通过（含 PR #79 的 2 个新回归测试）
- [ ] `npx tsc --noEmit` 无类型错误
- [ ] `npm run build` 通过
- [ ] 确认顶栏按钮边框视觉效果符合设计意图（PR #80 P1）
