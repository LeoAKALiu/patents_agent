# BUGS Round1 归因与分级

本轮只做归因和分级，不修改产品代码。分析依据为 `BUGS.md`、`.gstack/qa-reports/baseline.json`、各轮 QA 报告、截图和状态 JSON；未读取产品源码。因此“可能根因”是基于现象的工程推断，不作为源码事实。

## 汇总

- 源码身份：`fix/code-review-hardening` / `045b042`
- Worktree：`/Users/leo/Projects/patents_agent`
- 工作树：dirty，包含既有 `README.md` 修改、`BUGS.md`、`docs/qa/` 和本地 QA 证据
- 当前 baseline：health score `58`
- 当前问题数：`P1=3`、`P2=11`、`P3=6`
- 修复顺序建议：先处理 P1 主路径阻断和正式稿门禁可信度，再处理 P2 的状态恢复、上传异常和响应式裁切，最后集中收口 P3 文案/可访问性。

## P1

| Bug | 可能根因 | 影响范围 | 推荐修复策略 | 回归测试 |
|---|---|---|---|---|
| BUG-001 外部稿导入选择项目后丢模式 | 当前项目切换动作可能重置 guided flow 的入口模式，只按项目当前阶段重新渲染，未保留“外部稿导入”意图。 | 已有项目导入外部初稿主路径中断，用户可能误把初稿作为补充材料上传。 | 把入口模式和目标项目选择解耦；选择项目后仍保留 external-draft intake 状态，直到用户显式返回或完成导入。 | E2E：第三入口 -> 选择已有项目 -> 仍显示外部初稿上传/解析/确认工作稿。 |
| BUG-004 正式稿编译声称清理但污染仍在 | 编译结果可能只记录清理统计或浅层扫描，未对 official package 最终文本执行阻断式污染校验。 | 正式稿质量门禁可信度受损，可能给用户“已清理”的错误安全感。 | 在正式稿编译输出最终包后做确定性污染复扫；仍命中时标记 blocked/high risk，不展示清理成功。 | Integration：污染 draft 编译后必须清理或阻断；UI 不得在污染仍存在时显示“已清理”。 |
| BUG-005 成稿会审超时并阻断修复编辑器 | 超时参数可能没有贯穿到实际 provider/run 调度；失败 run 没有生成可修复 issue fallback。 | 成稿会审和标注式修复编辑器主路径阻断，正式导出长期无法放行。 | 让 stage/run timeout 严格生效； deterministic/provider 失败时写入结构化 failure，并为污染命中生成 repair-session issues 或明确不可修复原因。 | API：短 timeout 按配置失败；repair-session 对污染正式稿返回非空 `issues` 和 `sections`；UI 按钮启用。 |

## P2

| Bug | 可能根因 | 影响范围 | 推荐修复策略 | 回归测试 |
|---|---|---|---|---|
| BUG-002 空 Markdown 被当作 processed 材料 | 上传解析层只按扩展名和文件存在判断，空文本仅降级为 warning。 | 空材料污染项目上下文和材料计数，影响后续发明点提炼输入可信度。 | 对 `.md/.txt` 解析后做 trimmed text 非空校验；空文本返回 4xx 或 failed 且不计入可用材料。 | 上传空 Markdown/TXT 不写入 processed，不增加材料计数，显示中文错误。 |
| BUG-003 伪 DOCX 返回 500 | DOCX 解包异常未被业务层捕获并映射为文件格式错误。 | 损坏 DOCX、改后缀文件会暴露 500，用户无法自助修正。 | 捕获解析异常，返回结构化 4xx；前端映射为“文件格式错误/无法解析 DOCX”。 | 非 zip DOCX 上传返回 4xx；UI 不出现 `Internal Server Error`。 |
| BUG-006 刷新丢当前项目和步骤 | 当前项目和 guided flow step 仅保存在内存状态，刷新后未从 URL、localStorage 或服务端项目状态恢复。 | 刷新/关闭重开后用户丢上下文，可能重复创建项目。 | 持久化 current project id 和当前入口/步骤，启动时恢复；恢复失败时给明确选择项目提示。 | 创建项目进入第 2 步 -> 刷新 -> 当前项目和步骤保持一致。 |
| BUG-008 移动端项目列表按钮越界 | 项目卡片操作区或筛选 chips 使用了不可换行/固定宽布局，长项目名和按钮组共同撑宽。 | 移动端历史项目管理不可可靠点击，选择/删除状态可见性差。 | 移动端改为纵向按钮组或可换行 chips；项目名、按钮和 chips 设置明确 max-width/min-width 约束。 | 390px、30 项目、长项目名下所有 chip/button bounding box 在视口内。 |
| BUG-009 failed 上传计入材料数量 | 材料列表和计数没有区分 `processed` 与 `failed` 状态。 | 用户误以为失败文件参与后续提炼，材料详情与真实可用输入不一致。 | 可用材料计数只统计 processed；failed 项进入单独失败区或以错误状态展示。 | 上传 unsupported 文件后计数不增；详情区区分 failed/processed。 |
| BUG-010 后端断开仍显示能力可用/空列表 | API error 被降级为空数据或沿用缓存能力状态，缺少全局 offline 状态。 | 用户把服务不可达误判为空项目或功能可用，断线场景不可解释。 | 引入明确 backend unavailable 状态；项目页区分 load failed、empty、cached；能力标识依赖最新 health。 | 后端未启动/中途停止时不显示 `可用`，项目页显示加载失败或缓存标记。 |
| BUG-012 Browser Back 到 about:blank | SPA 没有管理应用内 history，初始历史栈里可能只有外部空白页，Back 直接离开应用。 | 浏览器/桌面系统返回键会造成空白页和上下文丢失。 | 为关键导航写入应用内 history 或拦截恢复；当前项目/步骤从持久状态恢复。 | 创建项目 -> 项目页 -> Back/Forward 不出现 about:blank，项目上下文仍有效。 |
| BUG-013 长项目名撑坏 topbar | 当前项目 select 按 option 文本自然宽度扩展，topbar flex 子项缺少 max-width/min-width:0。 | 长案件名/技术编号破坏顶部导航可读性。 | 给 topbar 项目选择器稳定 max-width，内部文本 ellipsis；父 flex 项允许收缩。 | 超长项目名下 label 和右侧工具仍在视口内，select 宽度受限。 |
| BUG-017 无读权限文件显示原始 API/Failed to fetch | 浏览器读取本地文件失败被当作普通网络失败展示，未识别 `ERR_ACCESS_DENIED`/文件读取异常。 | 无权限、云盘占位或系统限制文件让用户无法判断应重新选择文件。 | 文件上传前/失败时映射本地读取错误为“无法读取文件/检查权限”；清空或提示重新选择。 | 无读权限文件不增加材料，UI 不含 `/api/projects` 或 `Failed to fetch`。 |
| BUG-019 导出包预览长 token 被裁切 | app 内预览使用 `white-space: pre` 且父容器 `overflow-x:hidden`，长 token 撑宽但滚动不可达。 | 正式导出前人工复核无法看到完整权利要求/说明书。 | 预览 pane 使用 `pre-wrap`/`overflow-wrap:anywhere`，或在 pane 内提供可达横向滚动，避免撑宽外层布局。 | 长 token 正式稿包在桌面和 390px 下不被静默裁切。 |
| BUG-020 分步撰写预览长 token 撑坏工具布局 | 与 BUG-019 同类预览容器问题，长 token 还会把专家工具卡片列整体撑宽。 | 分步撰写工具和申请文本预览在移动端不可完整操作。 | 抽出共享 report/preview 容器样式，统一处理长 token 换行或 pane 内滚动。 | 长 token 外部稿在分步撰写预览不撑宽 `.workspace`。 |

## P3

| Bug | 可能根因 | 影响范围 | 推荐修复策略 | 回归测试 |
|---|---|---|---|---|
| BUG-007 设置连通失败暴露 SDK/provider 错误 | 设置页直接渲染后端/SDK exception 字符串，缺少错误分类和用户文案映射。 | 配置排错体验差，但保存/清除密钥主功能可用。 | 按 connection/5xx/429/auth 等类别映射中文提示，保留详细错误到日志或折叠详情。 | 127.0.0.1:9、503、429 均显示中文可操作错误，不回显 provider JSON。 |
| BUG-011 取消运行提示暴露内部英文 | run failure/cancel 的 failure_details 直接拼接到用户提示。 | 取消成功被呈现得像系统错误，增加误解。 | 为 cancelled/interrupted 分支单独映射中文提示；内部 stage/provider 只进日志。 | 取消 run 后按钮可重试，提示不含 `llm`、`stage_results`、英文异常。 |
| BUG-014 创建表单无字段级校验反馈 | 禁用 submit 由派生状态控制，字段没有 required/aria-invalid/错误文案。 | 新手和辅助技术用户不知道为何不能创建。 | 给项目名和一句话想法添加字段级校验、aria 关系和禁用原因说明。 | 空/纯空白输入不发 POST，字段显示中文错误且可访问。 |
| BUG-015 材料文件行 `mdmd` 拼接 | 文件名、类型和字数直接相邻渲染，缺少分隔符或 badge。 | 轻微可读性问题，可能误解文件名。 | 文件名、类型、字数用 `·` 或 badge 分隔；长文件名使用换行/截断。 | 上传 `.md` 后详情显示 `filename.md · md · N 字` 或等价结构。 |
| BUG-016 发明点提炼失败暴露内部 stage/provider | 长任务错误提示复用内部 failure_details，缺少面向用户的 LLM 连接错误映射。 | 新手遇到 LLM 配置错误时难以判断下一步。 | 对 LLM connection/auth/rate limit/schema 等错误做中文文案映射；保留重试入口。 | 不可达 LLM 下 run failed 后提示检查 Base URL/网络/API Key，不含内部 stage/provider。 |
| BUG-018 移动端触控高度低于 44px | 桌面紧凑控件样式直接用于移动端，未设置触控最小尺寸。 | 可访问性和误触问题，不阻断主流程。 | 移动断点下统一把主要 button/select/input/chip min-height 提到 44px，并检查 toolbar 密度。 | 390px 下主要控件高度 >= 44px，无横向 overflow。 |

## 建议执行顺序

1. P1 主路径组：`BUG-001`、`BUG-005`、`BUG-004`。
2. 文件上传错误组：`BUG-002`、`BUG-003`、`BUG-009`、`BUG-017`。
3. 状态恢复和断线组：`BUG-006`、`BUG-010`、`BUG-012`。
4. 长文本和移动端布局组：`BUG-008`、`BUG-013`、`BUG-018`、`BUG-019`、`BUG-020`。
5. 错误文案和轻量 UX 组：`BUG-007`、`BUG-011`、`BUG-014`、`BUG-015`、`BUG-016`。

## 下一轮修复入口

进入修复轮前先选一个根因组，并把对应回归命令写入修复计划。修复轮必须修改产品代码并补充自动化或浏览器回归；本文件不构成修复完成证据。
