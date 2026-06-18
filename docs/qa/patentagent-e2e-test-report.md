# PatentAgent E2E QA 测试报告

测试日期：2026-06-18  
测试分支：`codex/patentagent-e2e-qa-integration`  
集成提交：`b0299f3`  
测试项目：`一种基于多模态检索的专利草案生成方法`  
测试数据：全量虚构数据，未使用真实申请人、发明人或敏感材料。

## 结论

整体结论：核心后端链路跑通，真实 Tauri 打包客户端未跑通。

- Tauri 客户端：`tauri build --debug` 产物可启动后端，但窗口黑屏，真实 UI E2E 被阻塞。
- 降级链路：使用同一前端/后端代码、Fake LLM 和 deterministic provider runner 完成 API/前端服务链路验证。
- 导出结果：内部工作稿 docx/md、技术交底 md、正式编译报告、post-draft review 报告、正式提交稿 docx/md 均成功导出。
- 高优先级问题：P0/P1 2 个，P2 2 个，P3 1 个。

## 环境与验证

| 项 | 结果 |
| --- | --- |
| macOS Tauri 构建 | `npm exec --yes --package @tauri-apps/cli@^2 -- tauri build --debug` 成功 |
| Tauri app 启动 | 后端健康，窗口黑屏 |
| Tauri 后端健康 | `ok=true`, `data_dir=/tmp/patentagent-e2e-tauri-20260618`, `qa_profile=true`, `llm_configured=false` |
| Agent doctor | `status=ready`, active providers: `codex`, `deepseek`, `claude` |
| Codex CLI 删除影响 | 不影响会审前置检查：`codex` 解析到 `/Applications/Codex.app/Contents/Resources/codex`, `resolver_source=bundle` |
| 后端目标回归 | `214 passed, 1 skipped` |
| 前端全量 Vitest | `16 files / 193 tests passed` |
| 前端 build | passed，有 557 kB chunk warning |
| Tauri Rust test | 非沙箱 `7 passed` |
| cargo check | passed |

## 执行路径

真实 Tauri 路径：

1. 构建 DMG。
2. 挂载 DMG 到 `/tmp/patentagent-e2e-dmg-mount`。
3. 从 `PatentAgent.app` 启动。
4. 后端启动成功，健康接口端口为 `51561`。
5. 观察窗口持续黑屏，`Contents/Resources` 未包含 `index.html` 和前端 assets。
6. 因 macOS 进入锁屏，Computer Use 无法继续真实 UI 操作。

降级 E2E 路径：

1. 启动 QA 后端：`127.0.0.1:8000`，Fake LLM + deterministic provider runner。
2. 启动 Vite 前端：`127.0.0.1:5173`。
3. 空项目创建校验：`POST /api/projects` 空 name/draft_text 返回 422。
4. 新建测试项目：`a9cfa4e757474151bf08bd40eb60d3a2`。
5. 添加并选中用户发明点。
6. 生成发明交底书：`completed`。
7. 运行三方会审：`completed`。
8. 公式需求判断：无需公式包。
9. 生成初稿：`completed`。
10. 重新读取项目，确认 package 存在。
11. 生成 filing readiness。
12. official compile：`completed`, blocked items: none。
13. official export 首次 409，提示需 post-draft review。
14. post-draft review：`completed`, `export_allowed=true`。
15. 正式稿 docx/md 导出成功。

## 导出文件

- 内部工作稿 docx: `docs/qa/evidence/patentagent-e2e-draft-internal.docx`
- 内部工作稿 md: `docs/qa/evidence/patentagent-e2e-draft-internal.md`
- 技术交底 md: `docs/qa/evidence/patentagent-e2e-disclosure.md`
- 正式编译报告: `docs/qa/evidence/patentagent-e2e-official-compile-report.md`
- Post-draft review 报告: `docs/qa/evidence/patentagent-e2e-post-draft-review-report.md`
- 正式提交稿 docx: `docs/qa/evidence/patentagent-e2e-draft-official.docx`
- 正式提交稿 md: `docs/qa/evidence/patentagent-e2e-draft-official.md`
- API 结果 JSON: `docs/qa/evidence/patentagent-api-e2e-result.json`
- 正式导出结果 JSON: `docs/qa/evidence/patentagent-post-review-export-result.json`

内容校验：

- 内部 docx 含权利要求：通过。
- 内部 docx 含具体实施方式：通过。
- 正式 docx 含权利要求：通过。
- 正式 docx 含具体实施方式：通过。
- 正式 docx 内部标记污染：未发现。
- 内部工作稿包含会审策略、生成日志和绘图提示词：符合“内部工作稿”定位。

## 问题清单

| ID | 优先级 | 问题 | 证据 | 影响 |
| --- | --- | --- | --- | --- |
| PA-E2E-001 | P0 | 打包后的 Tauri app 黑屏，无法进入 UI | `/tmp/patentagent-e2e-screen-2.png`; DMG app `Contents/Resources` 无 `index.html/assets` | 真实桌面客户端不可用，阻断端到端 UI 测试 |
| PA-E2E-002 | P1 | 项目信息缺少结构化字段 | `ProjectCreate` 仅有 `name/draft_text/patent_type` | 申请人、发明人、技术领域等只能塞进自由文本，无法保存/校验/导出 |
| PA-E2E-003 | P2 | official compile clean 后 official export 仍 409，但 UI/API 缺少明确下一步状态 | 409: `Post-draft multi-agent review is required...` | 用户可能误以为正式编译完成即可导出 |
| PA-E2E-004 | P2 | 纯中文文件名的 ASCII fallback 为 `-.docx` / `-.md` | Content-Disposition: `filename="-.docx"; filename*=UTF-8''...` | 部分客户端下载名不可读 |
| PA-E2E-005 | P3 | 前端依赖和体积风险 | npm install: 3 vulnerabilities; Vite chunk 557 kB | 发布工程风险，非主流程阻塞 |

环境/限制：

- 真实 DeepSeek API key 未配置在 QA 数据目录，Tauri health 显示 `llm_configured=false`。本次生成质量不代表真实模型质量。
- Computer Use 在 macOS 锁屏后无法继续操作；未绕过登录。
- Playwright headless Chrome 在锁屏环境被系统 SIGKILL，未能补充前端截图。

## 生成质量评价

评价对象：Fake LLM 生成结果，仅用于流程质量参考，不代表真实模型表现。

| 维度 | 分数 | 说明 |
| --- | ---: | --- |
| 章节完整性 | 82/100 | 摘要、权利要求、说明书、附图说明齐全 |
| 权利要求可读性 | 76/100 | 独权步骤闭环清晰，从权覆盖证据链和一致性校验 |
| 专利稳定性 | 68/100 | 技术特征仍偏概括，缺少数据结构、处理规则和边界条件 |
| 说明书支撑 | 72/100 | 支撑基本对应，但实施例细节不足 |
| 正式稿洁净度 | 90/100 | 正式稿未发现会审/日志/提示词污染 |
| 检索与证据可信度 | 45/100 | 测试未接入真实公开检索，创造性支撑不足 |

综合：72/100。适合作为流程 smoke draft，不适合作为真实提交稿。

主要改进建议：

- 补充证据链字段结构、检索评分规则、引用一致性校验算法细节。
- 将“专利语料库”限定为具体索引、片段、章节元数据和匹配规则。
- 对权利要求1的每个步骤补充输入输出数据对象。
- 正式申请前必须做公开专利检索和代理师复核。

## Hermes 同步

- 已完成：`t_f33a3fe6` PR-4A v3、`t_9165260e` PR-11B。
- 已评论：`t_5d22c454` PR-12 v3 存在集成缺口，集成分支已用 `b0299f3` 修复。
- 新建：`t_7cacda4e`, `t_2cd4aef4`, `t_39af97b4`, `t_a3c29562`, `t_bfa3a9cd`。
