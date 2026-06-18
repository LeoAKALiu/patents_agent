# PatentAgent E2E Bug Fix Spec

来源：2026-06-18 端到端 QA。  
目标：修复阻塞真实桌面客户端使用的问题，并补齐导出、项目信息和工程质量缺口。

## PR-14: Fix packaged Tauri app black screen by bundling frontend assets

Hermes：`t_f2be2e01`
优先级：P0  
建议顺序：1

背景：

- `tauri build --debug` 成功生成 DMG。
- 从 DMG 启动 `PatentAgent.app` 后，后端健康但窗口持续黑屏。
- 挂载后的 `PatentAgent.app/Contents/Resources` 仅包含 `backend` 和 `icon.icns`，没有 React `index.html` 和 `assets`。

范围：

- 修复 `src-tauri/tauri.conf.json` 或 Tauri v2 打包配置，确保 `frontend/dist` 被纳入 app bundle。
- 增加打包产物 smoke：验证 app bundle 内存在前端入口和 assets。
- 增加非空渲染 smoke：启动 app 后 5 秒内窗口/DOM 非空。

验收标准：

- `npm exec --yes --package @tauri-apps/cli@^2 -- tauri build --debug` 通过。
- DMG 中 app 含 `index.html` 与 hashed JS/CSS assets。
- 启动 app 后能看到 PatentAgent UI，而不是黑屏。
- 后端 `/api/health` 显示 QA data dir、instance id、backend port。
- `cargo test`, `cargo check`, `npm run build`, 前端测试通过。

## PR-15: Add structured project metadata intake and persistence

Hermes：backend `t_21b014eb`; frontend `t_cf40449f`
优先级：P1  
建议顺序：2
状态：PR-15A backend 已审核并 cherry-pick 到集成分支 `741eacf`；PR-15B frontend 已在 Hermes promoted/running。

背景：

- 测试要求项目信息包含申请人、发明人、技术领域、背景、痛点、方案、创新点、实施例、有益效果。
- 当前 `ProjectCreate` 仅有 `name`, `draft_text`, `patent_type`。
- E2E 只能将结构化信息塞入 `draft_text`，无法独立校验、编辑或导出。

范围：

- PR-15A：扩展后端 schema、SQLite 存储、API 和迁移。
- PR-15B：在 PR-15A API contract 之后补前端表单、API client 和交互状态。
- 为旧项目提供默认值/迁移。
- 支持编辑后保存、刷新、重启后持久化。
- 明确申请人/发明人是否进入导出稿；若不进入，也要在 UI 上解释。

验收标准：

- 新建项目可填写并保存全部结构化字段。
- 刷新页面、重启后端后字段仍存在。
- 空字段有明确校验或提示。
- 后端 API 测试覆盖 create/list/get/migration。
- 前端测试覆盖表单输入、保存、回显。

## PR-16: Clarify official export gate and post-draft review CTA

Hermes：API readiness `t_241f3d03`; UI CTA `t_cf6c0876`
优先级：P2  
建议顺序：3
状态：PR-16A/PR-16B 均已审核并合入集成分支；PR-16B merge commit `6aa7d0e`，合并后前端 211 tests passed，生产构建通过。

背景：

- official compile 报告显示 `Blocked Items: 无`。
- 直接访问 official export 返回 409：需要 post-draft multi-agent review。
- 用户容易误解“正式编译完成”就是“可以正式导出”。

范围：

- PR-16A：在 official compile run 或导出 API/report metadata 中暴露 export readiness。
- PR-16B：UI 对“还需 post-draft review”显示明确状态、原因和操作按钮。
- API 错误保持机器可读，前端能映射成人话。

验收标准：

- official compile 完成但 post-draft review 未跑时，正式导出按钮不可用，并展示下一步。
- post-draft review 通过后，正式 docx/md 导出成功。
- API 测试覆盖 409 reason。
- 前端测试覆盖 locked CTA 和 unlocked export。

## PR-17: Improve ASCII fallback filenames for CJK downloads

Hermes：`t_c839241b`
优先级：P2/P3  
建议顺序：4

背景：

- RFC 5987 `filename*` 已正确包含中文名。
- 但 ASCII fallback 为 `-.docx` / `-.md`。
- 部分客户端会显示 fallback 文件名，体验差。

范围：

- 调整 `make_content_disposition` fallback 逻辑。
- 纯中文、危险字符、空名、混合名都生成非空、可读、带扩展名的 ASCII fallback。

验收标准：

- fallback 不再出现 `-.docx` 或 `-.md`。
- 保留 `filename*` 的 UTF-8 中文名。
- 更新 `tests/test_content_disposition.py`。
- 真实导出 header 通过验证。

## PR-18: Address frontend dependency audit and bundle-size warnings

Hermes：`t_3985a359`
优先级：P3  
建议顺序：5

背景：

- `npm --prefix frontend install` 报 3 个漏洞：2 low, 1 high。
- `npm run build` 报 JS chunk 557 kB，大于 500 kB。

范围：

- 运行 `npm audit`，安全升级可升级依赖。
- 对不可安全升级项写明例外。
- 拆分明显重型模块或给出合理 chunk 策略。

验收标准：

- 无 high vulnerability，或有明确风险接受记录。
- build 无 >500 kB warning，或有明确阈值理由。
- 前端全量 Vitest 通过。

## 已发现并在集成分支修复的缺口

集成提交：`b0299f3`

- PR-12 公式质量测试引用了未实现的 `_repair_formula_payload`, `_validate_formula_quality` 和 `CoreFormulaPackage` 质量字段。
- PR-12 相关测试缺 `json` import。
- PR-9 新增测试缺 `PatentType` 和 `_persist_disclosure_candidates` import。
- PR-7/PR-11B 集成后 `App.tsx` 引用缺失的 `persistLastSelectedProject`，前端 build 失败。
- `SystemStatusPanel.test.ts` fixture 与当前 `ProjectRecord`/`Health` 类型不一致，前端 build 失败。

处理建议：

- 将 `b0299f3` 拆为 PR-12B/PR-7B 集成修复，或回填到对应原 PR 分支。

## 非产品限制

- 本次 QA 环境没有真实 DeepSeek API key；生成内容由 Fake LLM 产生。
- macOS 锁屏阻止 Computer Use 继续真实 UI 操作。
