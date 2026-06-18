# PatentAgent Hermes Kanban Tasks

测试日期：2026-06-18  
看板：`patentagent-qa-bugfix`  
说明：本清单仅同步到 Hermes Kanban，不涉及 Linear。

## 同步状态

| PR | Hermes ID | 优先级 | 状态 | 分派 | 建议分支 |
| --- | --- | --- | --- | --- | --- |
| PR-14 | `t_7cacda4e` | P0 | running | `bigmodelworker` | `codex/pr-14-tauri-frontend-assets` |
| PR-15 | `t_2cd4aef4` | P1 | running | `kimiworker` | `codex/pr-15-project-metadata` |
| PR-16 | `t_39af97b4` | P2 | running | `kimiworker` | `codex/pr-16-official-export-gate-ux` |
| PR-17 | `t_a3c29562` | P2 | ready | `deepseekworker` | `codex/pr-17-download-ascii-fallback` |
| PR-18 | `t_bfa3a9cd` | P3 | ready | `kimiworker` | `codex/pr-18-frontend-deps-bundle` |

已回填并完成的既有卡片：

| PR | Hermes ID | 结果 |
| --- | --- | --- |
| PR-4A v3 | `t_f33a3fe6` | 已评论验证结果并标记完成 |
| PR-11B | `t_9165260e` | 已评论验证结果并标记完成 |
| PR-12 v3 | `t_5d22c454` | 已评论说明原 PR 未完整覆盖，集成修复已在 `b0299f3` 完成；未标记完成 |

## 建议执行顺序

1. PR-14：先修复 Tauri 打包黑屏，恢复真实客户端 E2E 能力。
2. PR-15：补齐结构化项目信息输入，减少文档/导出元数据遗漏。
3. PR-16：优化官方导出门禁和复审 CTA，降低用户卡住概率。
4. PR-17：修复 CJK 下载文件名 ASCII fallback。
5. PR-18：处理依赖审计和前端 bundle 体积告警。

## PR-14：Fix Packaged Tauri App Black Screen

优先级：P0  
Hermes ID：`t_7cacda4e`  
分派：`bigmodelworker`  
建议分支：`codex/pr-14-tauri-frontend-assets`

### 背景

通过 debug DMG 启动 `PatentAgent.app` 后窗口为全黑。挂载包体检查发现 `Contents/Resources` 中仅包含后端资源与图标，缺少前端 `index.html` 和 `assets`。这会直接阻断真实 Tauri 客户端端到端测试。

### 复现步骤

1. 执行 Tauri debug build。
2. 挂载 `src-tauri/target/debug/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg`。
3. 启动 `PatentAgent.app/Contents/MacOS/patentagent-tauri`。
4. 观察应用窗口。

### 实际结果

应用窗口黑屏；Computer Use 只能看到黑色窗口。包内缺少前端构建产物。

### 预期结果

打包后的 Tauri 应用应展示 PatentAgent 前端首页，并可完成新建项目、生成、预览和导出流程。

### 范围

- 修正 Tauri 配置中的前端构建产物路径。
- 保证 `frontend/dist/index.html` 和 `frontend/dist/assets/*` 被打进 app bundle。
- 添加可自动检查 bundle 前端资产存在性的测试或脚本。

### 验收标准

- debug/release DMG 启动后不黑屏。
- `Contents/Resources` 或 Tauri 对应资源目录中存在前端入口和 assets。
- 通过 Computer Use 可看到首屏 UI。
- 手动或自动 smoke test 能创建项目并进入主流程。

### 测试方式

- `npm run build`
- `npm exec --yes --package @tauri-apps/cli@^2 -- tauri build --debug`
- 挂载 DMG 并启动 app。
- 使用 Computer Use 截图确认 UI 可见。

## PR-15：Add Structured Project Metadata Intake

优先级：P1  
Hermes ID：`t_2cd4aef4`  
分派：`kimiworker`  
建议分支：`codex/pr-15-project-metadata`

### 背景

当前 API 流程可以通过 `draft_text` 输入申请人、发明人、技术领域等信息，但缺少结构化字段。用户在真实专利撰写流程中会期望项目信息、申请人、发明人、技术领域、专利类型等可单独输入、保存、编辑并导出复用。

### 复现步骤

1. 新建项目。
2. 尝试分别填写项目名称、技术领域、申请人、发明人、申请类型。
3. 保存、刷新或重启后检查字段。
4. 导出初稿后检查元数据是否稳定出现。

### 实际结果

结构化元数据入口不足，主要依赖正文文本承载，后续质量检查和导出模板难以稳定消费。

### 预期结果

项目信息应有独立字段，并持久化到项目模型，后续生成、预览、导出均可引用。

### 范围

- 后端扩展项目 schema 和持久化字段。
- 前端新建/编辑项目表单支持结构化字段。
- 导出或官方编排流程读取这些字段。
- 增加字段校验和空字段提示。

### 验收标准

- 结构化字段可创建、编辑、保存、重载后保留。
- 导出文件中可正确引用申请人、发明人、技术领域等信息。
- 空必填字段给出明确提示，不出现静默丢失。

### 测试方式

- 后端项目 API 测试。
- 前端表单测试。
- 一次从新建项目到导出的 E2E smoke test。

## PR-16：Clarify Official Export Gate and Review CTA

优先级：P2  
Hermes ID：`t_39af97b4`  
分派：`kimiworker`  
建议分支：`codex/pr-16-official-export-gate-ux`

### 背景

官方编排成功后，直接导出官方文件会返回 409，提示需要先完成 post-draft review。该规则合理，但用户需要在 UI 和报告中明确看到下一步，否则会误以为导出失败。

### 复现步骤

1. 完成初稿生成。
2. 执行官方编排。
3. 不执行 post-draft review，直接调用官方导出。

### 实际结果

导出返回 409，需要用户理解隐藏的门禁关系。

### 预期结果

官方编排完成后，UI 明确显示“需完成复审后可导出”，并提供直接启动复审的 CTA。报告中也应标注当前导出状态。

### 范围

- 前端展示官方导出门禁状态。
- 编排/复审/导出按钮状态和提示文案联动。
- 后端错误响应保持机器可读，前端转译为清晰用户文案。

### 验收标准

- 未复审时导出按钮不可用或提示明确。
- 完成复审且 `export_allowed=true` 后官方导出可用。
- 409 错误有可操作恢复路径。

### 测试方式

- API 门禁测试。
- 前端状态渲染测试。
- 一次官方编排 -> 复审 -> 导出 E2E 测试。

## PR-17：Improve ASCII Fallback Filenames for CJK Downloads

优先级：P2  
Hermes ID：`t_a3c29562`  
分派：`deepseekworker`  
建议分支：`codex/pr-17-download-ascii-fallback`

### 背景

导出中文项目名时，`Content-Disposition` 的 `filename*=` UTF-8 参数正确，但 ASCII fallback 退化为 `-.docx` / `-.md`。部分客户端仍会展示 fallback 文件名，体验较差。

### 复现步骤

1. 创建中文标题项目。
2. 导出 docx 或 md。
3. 检查响应头 `Content-Disposition`。

### 实际结果

ASCII fallback 文件名为 `-.docx` 或 `-.md`。

### 预期结果

fallback 应至少包含稳定可读前缀，例如 `patentagent-draft.docx` 或拼音/slug 形式，同时保留 `filename*=`。

### 范围

- 调整导出文件名 fallback 生成逻辑。
- 添加纯 CJK、混合中英文、特殊符号标题测试。

### 验收标准

- 纯中文标题不会产生 `-.ext`。
- `filename*=` 仍保留完整 UTF-8 文件名。
- 所有导出格式行为一致。

### 测试方式

- `tests/test_content_disposition.py`
- 导出 API smoke test。

## PR-18：Address Frontend Dependency Audit and Bundle Warning

优先级：P3  
Hermes ID：`t_bfa3a9cd`  
分派：`kimiworker`  
建议分支：`codex/pr-18-frontend-deps-bundle`

### 背景

`npm --prefix frontend install` 报告 3 个漏洞，其中 1 个 high。`npm run build` 通过，但 Vite 提示主 JS chunk 超过 500 kB。

### 复现步骤

1. 执行 `npm --prefix frontend install`。
2. 执行 `npm --prefix frontend run build`。
3. 查看 audit 和 bundle 警告。

### 实际结果

存在依赖审计问题和 bundle 体积警告。

### 预期结果

依赖漏洞被升级或确认豁免；bundle 体积有明确拆包或治理方案。

### 范围

- 审计依赖漏洞来源并升级可升级依赖。
- 对确需保留的风险给出注释或 issue。
- 评估 Vite dynamic import / manualChunks。

### 验收标准

- `npm audit` 无 high 级别漏洞，或有记录的可接受豁免。
- `npm run build` 不出现未解释的 chunk-size 警告，或有明确 bundle 策略。
- 前端测试仍全部通过。

### 测试方式

- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `npm --prefix frontend audit`

