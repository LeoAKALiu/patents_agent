# Code Review: PR #80 — style(frontend): 中文排版、按钮统一与口语化文案

**Branch:** `codex/ui-cn-polish` → `main`  
**Head:** `e09d94f`  
**Date:** 2026-06-16 · **Reviewer:** Kimi Code CLI  

---

## 1. 概要

纯前端 UI 打磨 PR，聚焦四个方面：

1. **中文排版**：CJK 字体回退、行高、比例字形、长文本换行、圆角分级；
2. **按钮统一**：合并多套按钮尺寸（44/38/36px → 40px），统一字重与圆角；
3. **精简指引**：删除冗余说明，把暴露内部 run ID 的文案改为自然中文；
4. **消除程序内部用语**：清污→内部痕迹、侧车报告→风险说明、公式包→公式、哈希→版本等。

无业务逻辑变更，无新依赖。

---

## 2. 变更清单

| 文件 | 变更 |
|------|------|
| `frontend/src/styles.css` | +53/-94 — CJK 字体栈、按钮统一、radius 分级、去 uppercase/letter-spacing |
| `frontend/src/GuidedPatentFlow.tsx` | +32/-34 — 面板文案口语化 |
| `frontend/src/App.tsx` | +14/-14 — 状态/错误/会审文案口语化 |
| `frontend/src/guidedFlow.ts` | +9/-9 — 步骤描述与进度时间轴日志 |
| `frontend/src/SettingsPanel.tsx` | +4/-5 — 设置说明文案 |
| `frontend/src/guidedFlow.test.ts` | +1/-1 — 同步 postReview 描述断言 |

---

## 3. 验证结果

| 检查项 | 结果 |
|--------|------|
| 前端测试 `npm test` | ✅ 60 passed |
| 前端构建 `npm run build` | ✅ 成功（371.71 kB JS / 82.80 kB CSS） |
| 与 PR #79 模拟合并 | ✅ 无冲突，合并后 62 passed + 构建成功 |

---

## 4. 详细审查

### 4.1 中文排版

- 字体栈顺序合理：macOS 原生 → 跨平台 → Windows fallback；
- `line-height: 1.6`、`font-variant-east-asian: proportional-width`、`word-break/overflow-wrap` 均适配中文；
- 圆角分级 `--radius-sm/md/lg = 6/8/10px` 让卡片与控件视觉层次清晰；
- 移除 eyebrow/score-card/matrix 表头等处的 `text-transform: uppercase` 与 `letter-spacing`，对 CJK 无意义。

### 4.2 按钮统一

- 合并 `.btn / .primary / .icon-button / .export-link / .btn-primary / .btn-secondary / .btn-danger / .btn-ghost` 共享尺寸块；
- 高度统一为 `min-height: 40px`、padding `8px 14px`、radius-md、font-weight 600；
- `.btn-icon` 从 44px 改为 40px，与文字按钮等高；
- disabled opacity 统一为 0.54，消除之前 `.primary:disabled` 的 0.4 差异。

### 4.3 文案口语化

术语替换一致且自然：

| 原术语 | 新术语 | 评估 |
|--------|--------|------|
| 清污/清污检查 | 内部痕迹/内部痕迹检查 | ✅ 易懂 |
| 公式包 / LaTeX 公式包 | 公式 | ✅ 简洁 |
| 侧车报告 | 风险说明 | ✅ 自解释 |
| 成稿哈希 / 正式稿哈希 | 当前版本 / 正式稿版本 | ✅ 面向非技术用户 |
| 污染命中 | 问题项 | ✅ 去安全术语 |
| 编译正式稿 | 生成正式稿 | ✅ 符合中文直觉 |
| 主席裁决 | 综合裁决 | ✅ 不带组织架构暗示 |
| 暴露 run ID 的提示 | 自然中文 | ✅ 减少认知负担 |

---

## 5. 问题与建议

| # | 问题 | 严重度 | 建议 |
|---|------|--------|------|
| 1 | `App.tsx` 导出风险说明错误提示仍保留“需要先**编译**正式稿”，与其他处“生成正式稿”不一致 | 🟡 建议 | 改为“风险说明需要先生成正式稿。” |
| 2 | `text-spacing-trim: space-all` 是 CSS Text Level 4 实验属性 | 🟢 minor | 注释标注 `/* Chromium 124+; CSS Text Level 4 — Tauri-only */` |
| 3 | `operationLogSteps` 中“主席综合裁决”与面板标题“综合裁决”不完全一致 | 🟢 minor | 统一为“综合裁决并写入导出门禁” |
| 4 | `正式稿版本：{hash.slice(0, 12)}` 对非技术用户“版本”可能暗示语义化版本号 | 🟢 minor | 可接受，目标用户能理解 hex 指纹 |
| 5 | `sourceTypeLabel` 对未知 source 返回“模型生成”，需确认 `local` 等值是否需要额外标签 | 🟢 minor | 确认 `domain.ts` 已覆盖所有 `source_type` 取值 |

---

## 6. 交叉 PR 风险

- PR #79 与 PR #80 同时修改 `frontend/src/guidedFlow.ts` 与 `frontend/src/guidedFlow.test.ts`；
- **实际模拟合并结果：自动合并成功，无冲突，测试与构建均通过。**

建议合并顺序：先 PR #79（修复功能 bug），再 PR #80（纯 UI 打磨），降低 rebase 成本。

---

## 7. 结论

**建议 SQUASH MERGE。**

PR #80 是一次聚焦、低风险的前端打磨。排版、按钮、文案三方面实施到位，验证全部通过。

合并前建议顺手修正问题 #1（遗漏的“编译”→“生成”），其余问题可后续快速跟进。
