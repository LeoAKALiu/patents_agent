# 场景测试与问题记录完成度审计

审计时间：2026-06-27

源码身份：

- 分支：`fix/code-review-hardening`
- 短 SHA：`045b042`
- Worktree：`/Users/leo/Projects/patents_agent`
- 工作树状态：dirty，包含既有 `README.md` 修改、`BUGS.md`、`docs/qa/` 和本地 QA 证据

本审计只验证“测试并记录问题”阶段是否完成，不验证产品修复是否完成。

## 结论

测试与问题记录阶段已闭环：

- 已建立场景测试流水线文档。
- 已建立用户场景清单。
- 已建立测试用例矩阵。
- 已完成多轮人工/AI 探索并保存可复查证据。
- 已建立 `BUGS.md` 模板和缺陷台账。
- 已登记 20 个已复现问题，每个问题都有截图/日志、已复现事实和回归测试条目。
- 已完成第一轮归因和分级。
- 已保存 baseline、轮次报告、探针脚本和项目级跨会话副本。

未执行产品修复；修复阶段应从 `docs/qa/bug-triage-round1-2026-06-27.md` 的 P1 组开始。

## 模板要求对照

| 模板要求 | 当前证据 | 审计结果 |
|---|---|---|
| 开始前记录源码身份 | 本审计记录 branch、SHA、worktree、dirty 状态；各 bug 条目也记录源码身份 | 已完成 |
| 写《用户场景清单》 | `docs/qa/user-scenarios.md`，包含 `SCN-001` 至 `SCN-006`，覆盖新手、熟练用户、误操作用户、极端数据用户、本地后端异常和修复编辑器 | 已完成 |
| 生成测试用例矩阵 | `docs/qa/test-case-matrix.md`，包含 32 个 `TC-*` 用例 | 已完成 |
| 覆盖正常路径 | `TC-GUIDED-001`、`TC-EXPORT-001`、`TC-SETTINGS-001`、`TC-DESKTOP-001` | 已完成 |
| 覆盖边界条件 | `TC-EXPORT-002`、`TC-NAV-001`、`TC-PROJECTS-003` | 已完成 |
| 覆盖错误输入 | `TC-FORM-VALIDATION-001`、`TC-INTAKE-002`、`TC-UPLOAD-002`、`TC-SETTINGS-002` | 已完成 |
| 覆盖空数据/超大数据 | `TC-PROJECTS-001`、`TC-PROJECTS-002`、`TC-INTAKE-001`、`TC-LONGTEXT-001` 至 `TC-LONGTEXT-005` | 已完成 |
| 覆盖网络/文件/权限异常 | `TC-NETWORK-001`、`TC-UPLOAD-003`、`TC-UPLOAD-004`、`TC-SETTINGS-003` | 已完成；`TC-UPLOAD-004` 固化为桌面/Tauri 人工用例 |
| 覆盖 UI 显示异常 | `TC-LONGTEXT-*`、`TC-REPAIR-002`、`TC-MONKEY-001`、`TC-PROJECTS-002` | 已完成 |
| 覆盖连续操作和重复点击 | `TC-DOUBLE-CLICK-001`、`TC-DOUBLE-CLICK-002`、`TC-SWITCH-001`、`TC-PANEL-001` | 已完成 |
| 覆盖中途取消、返回、刷新、关闭窗口 | `TC-CANCEL-001`、`TC-NAV-001`、`TC-NETWORK-001`、`TC-DESKTOP-001` | 已完成 |
| 建立 BUGS.md 模板 | `BUGS.md` 包含 `BUG-000` 模板、状态流转和严重级别定义 | 已完成 |
| AI 用户猴子探索 | `TC-MONKEY-001`、Round31 报告和 `.gstack/qa-reports/round31_monkey_navigation_probe.js` | 已完成 |
| 每个问题按模板记录 | `BUGS.md` 中 `BUG-001` 至 `BUG-020` 均有模块、触发场景、复现步骤、实际/预期结果、严重级别、证据、已复现事实、影响范围、回归测试和状态 | 已完成 |
| 第一轮只归因和分级 | `docs/qa/bug-triage-round1-2026-06-27.md`，覆盖全部 20 个 baseline bug | 已完成 |
| 第二轮修复 | 本目标为“测试并记录问题”；未执行产品代码修复 | 后续独立阶段 |
| 补自动化测试证据 | `.gstack/qa-reports/round*_probe.js`、状态 JSON、pytest/smoke 记录和 `baseline.json` | 已完成 |
| 发布前冒烟记录 | Round28 `scripts/v1_smoke.sh` 记录；Round29 installed app smoke 记录 | 已完成记录 |

## 数量核对

- 用户场景：`SCN-001` 至 `SCN-006`，共 6 个真实场景；另有 `SCN-000` 模板。
- 测试用例：32 个。
- baseline 问题：20 个。
- 严重级别：`P1=3`、`P2=11`、`P3=6`。
- 当前 health score：58。
- Round 报告：`.gstack/qa-reports/qa-report-patentagent-local-round*.md`。
- 探针脚本：`.gstack/qa-reports/round*_probe.js`。

## 当前未修复问题分布

| 严重级别 | 数量 | 代表问题 |
|---|---:|---|
| P1 | 3 | `BUG-001` 外部稿导入丢模式；`BUG-004` 正式稿污染仍显示已清理；`BUG-005` 成稿会审超时阻断修复编辑器 |
| P2 | 11 | 上传异常、状态恢复、后端断线、移动布局、长文本预览裁切 |
| P3 | 6 | 错误文案、字段校验反馈、触控尺寸、材料行可读性 |

## 后续修复入口

建议下一阶段按根因组推进：

1. P1 主路径组：`BUG-001`、`BUG-005`、`BUG-004`。
2. 文件上传错误组：`BUG-002`、`BUG-003`、`BUG-009`、`BUG-017`。
3. 状态恢复和断线组：`BUG-006`、`BUG-010`、`BUG-012`。
4. 长文本和移动端布局组：`BUG-008`、`BUG-013`、`BUG-018`、`BUG-019`、`BUG-020`。
5. 错误文案和轻量 UX 组：`BUG-007`、`BUG-011`、`BUG-014`、`BUG-015`、`BUG-016`。

修复阶段必须读取产品源码、修改生产文件、补测试并运行回归；这些不属于本次“测试并记录问题”完成证据。
