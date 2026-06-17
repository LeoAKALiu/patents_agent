# Code Review: PR #79 — fix: stop comparing snapshot_hash against source_draft_hash

**Branch:** `codex/fix-quality-gate-hash-mismatch` → `main`  
**Head:** `7329f55`  
**Date:** 2026-06-16 · **Reviewer:** Kimi Code CLI  

---

## 1. 概要

PR #78 新增的 `isQualityChecked` 把 `completionRun.snapshot_hash` 与 `currentSourceDraftHash` 直接对比，但后端两者使用**不同哈希公式**：

- `snapshot_hash` = `sha256(package + points + materials)`（`backend/app/draft_completion.py`）
- `currentSourceDraftHash` = `sha256(package)`（`backend/app/official_compile.py`）

结果：质量门禁永远不满足，用户卡在 quality 步骤无法进入 `officialCompile`。

**修复方案：**
- 在 `DraftCompletionRun` 中新增 `draft_package_hash` 字段，使用 `sha256(package)`；
- `isQualityChecked` 改为同时对比 `filingReport.draft_package_hash` 与 `completionRun.draft_package_hash`；
- 忽略 `snapshot_hash` 与当前源稿的算法差异。

---

## 2. 变更清单

| 文件 | 变更 |
|------|------|
| `backend/app/draft_completion.py` | +1 — 写入 `draft_package_hash=package_hash` |
| `backend/app/schemas.py` | +1 — `DraftCompletionRun` 新增 `draft_package_hash: str = ""` |
| `frontend/src/api.ts` | +1 — 前端类型同步 |
| `frontend/src/guidedFlow.ts` | +32/-19 — 重写 `isQualityChecked`，新增 `byNewest` / `createdAtTime` |
| `frontend/src/guidedFlow.test.ts` | +83 — 两个回归测试 |

---

## 3. 验证结果

| 检查项 | 结果 |
|--------|------|
| 后端测试 `pytest tests/` | ✅ 236 passed, 1 skipped |
| 前端测试 `npm test` | ✅ 62 passed |
| 前端构建 `npm run build` | ✅ 成功 |
| 与 PR #80 模拟合并 | ✅ 无冲突，合并后 62 passed + 构建成功 |

---

## 4. 详细审查

### 4.1 后端字段扩展

- `schemas.py` 中默认值 `""` 保证旧 storage 记录反序列化不报错；
- `draft_completion.py` 复用已计算的 `package_hash`，无额外开销；
- 新增字段与 `FilingReadinessReport.draft_package_hash` 语义一致，可直接比较。

### 4.2 `isQualityChecked` 重写

**优点：**
- 用 `Date.parse` 做数值比较替代 `localeCompare`，符合 ISO-8601 排序语义；
- 当 `currentSourceDraftHash` 为空时仍然放行，保持旧 API/开发阶段兼容；
- 明确注释 `snapshot_hash` 不参与对比，避免后续维护者再次踩坑。

**关注点：**
- `createdAtTime` 对无效日期返回 `0`，极端情况下如果全部记录日期损坏，排序会退化但不会产生错误决策；
- 旧记录 `draft_package_hash=""` 会被判为不新鲜，用户需要重新运行初稿完善，但 UI 阻断文案没有提示这一点。

### 4.3 测试覆盖

两个回归测试精准命中问题：
1. `snapshot_hash` 与 `currentSourceDraftHash` 算法不同，但 `draft_package_hash` 匹配时门禁应通过；
2. filing report 新鲜但 completion run 过期时，门禁应被重置。

---

## 5. 问题与建议

| # | 问题 | 严重度 | 建议 |
|---|------|--------|------|
| 1 | 旧 `DraftCompletionRun` 记录 `draft_package_hash=""` 静默失败，UI 未提示需重新运行初稿完善 | 🟡 建议 | 在 `OfficialCompilePanel` 的 blocked 文案中补充“初稿完善记录版本信息缺失，建议重新运行” |
| 2 | 两个 commit 的中间状态（`2a45168`）语义不完整 | 🟢  minor | 合并时建议 squash，避免中间状态进入 main |
| 3 | `byNewest` 每次调用都分配排序副本 | 🟢  minor | 当前数据量 < 10，可忽略；后续如数据量大可考虑 memo |

---

## 6. 结论

**建议 SQUASH MERGE。**

修复定位精准，测试与注释完整，前后端验证全部通过。与 PR #80 的合并路径干净，无冲突。

唯一需要在合并前或后续 PR 跟进的是：为旧记录 `draft_package_hash=""` 的场景提供更明确的 UI 提示。
