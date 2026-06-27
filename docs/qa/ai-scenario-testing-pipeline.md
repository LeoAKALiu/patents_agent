# AI 场景测试流水线

本文档把日常 QA 固定为一条可重复的闭环：

```text
场景清单 -> 测试矩阵 -> 人工/AI 探索 -> BUGS.md -> 分级 -> 修复 -> 回归测试 -> 发布前冒烟测试
```

首次使用这条流水线时，先创建本页后续章节列出的场景、矩阵和缺陷台账文件；完成一次完整测试后，再按需新增带日期的 completion audit 文档。

适用范围：

- React/Tauri 桌面主流程：开始、项目、设置、专家工具。
- 专利撰写主路径：想法与材料、发明点、生成初稿、质量检查、正式稿编译、成稿会审、导出。
- 外部稿件导入、后草稿质量检查、标注式修复编辑器、文件上传和桌面 sidecar 启动。

## 0. 开始前固定源码身份

任何测试、归因、修复或打包前，先记录当前源码身份：

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

记录项：

- 分支：
- 短 SHA：
- worktree 路径：
- 工作树是否 dirty：
- 测试对象：源码开发环境 / 已安装 app / 挂载 DMG / 其他：
- 数据目录：默认 `data/` / 桌面端 `PATENTAGENT_BACKEND_DATA_DIR` / 其他：

如果用户截图来自已安装 app，必须同时核对 `/Applications/PatentAgent.app`、`backend-startup.log` 中的后端端口和数据目录，不要只凭当前源码判断。

## 1. 用户场景清单

先创建并维护 `docs/qa/user-scenarios.md`。按真实用户角色补全场景：

- 新手用户：第一次打开应用，只有一句技术想法。
- 熟练用户：已有材料，反复运行质量检查和导出。
- 误操作用户：重复点击、返回、取消、关闭窗口、上传错文件。
- 极端数据用户：空数据、超长文本、超大文件、缺失权限、网络不可用。

每个场景必须写清：

- 目标
- 前置条件
- 操作步骤
- 预期结果
- 可能失败点
- 需要的数据或文件
- 是否需要真实运行 app 证明

## 2. 测试用例矩阵

创建 `docs/qa/test-case-matrix.md` 维护测试矩阵。生成矩阵时使用以下提示词：

```text
你是一名软件测试工程师。请阅读本项目代码和 README，基于真实用户使用场景设计测试用例矩阵。
要求覆盖：
1. 正常路径
2. 边界条件
3. 错误输入
4. 空数据/超大数据
5. 网络/文件/权限异常
6. UI 显示异常
7. 连续操作和重复点击
8. 用户中途取消、返回、刷新、关闭窗口
输出字段：
用例ID、用户角色、场景、前置条件、操作步骤、预期结果、风险等级、是否可自动化。
不要修改代码。
```

矩阵要标出自动化层级：

- `unit`：后端规则、前端纯函数、Tauri command 单元。
- `integration`：FastAPI TestClient、SQLite 持久化、文件解析、导出。
- `frontend`：Vitest/React 组件和状态流。
- `e2e`：Playwright、Tauri DOM smoke、tauri-driver 或人工桌面验证。
- `manual`：需要真实系统权限、真实文件选择器、签名/公证、真实 LLM provider 的检查。

## 3. AI 用户猴子探索

探索阶段只记录缺陷，不直接修复。使用以下提示词：

```text
请扮演一个不熟悉本软件的真实用户，基于现有功能随机探索。
重点寻找：
- 按钮无响应
- 弹窗关闭异常
- 表单校验缺失
- 重复点击导致重复提交
- 页面跳转后状态丢失
- 长文本溢出
- 空列表/空表格异常
- 文件不存在、格式错误、权限不足
每发现一个问题，按 BUGS.md 模板记录，不要直接修复。
```

探索证据最低要求：

- UI 问题：说明测试环境、窗口尺寸、页面位置；能截图时保存截图路径。
- API 问题：记录请求、响应状态、关键 payload、日志路径。
- 桌面问题：记录 app 来源、后端 health、`backend-startup.log` 路径。
- 数据相关问题：记录项目 id、run id、输入文件类型和是否可复现。

## 4. BUGS.md 台账

创建根目录 `BUGS.md` 作为缺陷台账，所有发现项进入该文件。不要把“猜测的根因”当作事实，必须区分：

- 已复现事实
- 影响范围
- 可能原因
- 推荐修复方案
- 回归测试
- 当前状态

严重级别：

- `P0`：数据损坏、无法启动、错误放行正式提交稿、严重安全/隐私问题。
- `P1`：核心流程中断、导出/质量门禁错误、用户无法完成主路径。
- `P2`：重要功能异常但有绕过路径，明显 UI 错乱或状态错误。
- `P3`：轻微文案、视觉、可用性问题。

状态流转：

```text
待复现 -> 已复现 -> 已分级 -> 修复中 -> 已修复 -> 已验证 -> 关闭
```

## 5. 两轮处理规则

第一轮只归因和分级，不改代码：

```text
请读取 BUGS.md，按严重程度排序。先不要改代码，只分析每个 bug 的可能根因、影响范围、推荐修复策略和需要补充的回归测试。
```

第二轮从 P0/P1 开始修复：

```text
请从 P0/P1 bug 开始修复。每修复一个 bug：
1. 说明修改了哪些文件
2. 补充或更新测试
3. 运行相关测试
4. 更新 BUGS.md 状态
```

修复规则：

- 每次只修同一根因或同一用户路径的一组缺陷。
- 修复前写清预期验证命令。
- UI 修复必须验证真实生产 React/Tauri 源码和运行 app，不接受只看设计稿或静态 prototype。
- 标注式修复编辑器必须验证 repair-session API 返回非空 `issues` 和非空 draft `sections`，不能只做 DOM 截图。

## 6. 推荐自动化层

常规开发验证：

```bash
python3 -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
cargo check --manifest-path src-tauri/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml
```

发布前确定性门禁：

```bash
bash scripts/v1_smoke.sh
```

DMG 交付前：

```bash
scripts/package_dmg.sh --with-smoke
```

如果要做桌面 E2E，优先复用已有 Tauri DOM smoke 和 Playwright 浏览器检查；只有需要覆盖原生窗口、文件选择器、菜单或权限弹窗时，再引入 tauri-driver 或人工桌面验证。

## 7. 发布前冒烟检查

发布前至少覆盖：

- 新建项目：一句技术想法 -> 发明点 -> 初稿 -> 质量检查。
- 外部稿件：导入 Markdown/DOCX -> 解析确认 -> 质量检查 -> 导出。
- 后草稿会审：正式稿编译 -> 成稿会审 -> repair-session -> 标注式修复编辑器。
- 导出门禁：未编译、未会审、hash 过期时都不能导出正式稿。
- 设置：缺少 API key 时功能失败关闭，并给出可理解提示。
- 桌面启动：sidecar health 通过，Tauri DOM smoke 通过，关闭 app 后后端进程退出。

交付 DMG 时仍以 `docs/release/dmg-ui-regression-guard.md`、`docs/release/v1.1.0-tauri-release-gate.md` 和 `docs/release/v1.1.0-tauri-packaging.md` 为最终发布规则。
