# Patent Agent 长程流程测试报告

## 1. 测试环境

- 项目路径：`/Users/leo/Projects/patents_agent`
- Git 分支：`codex/grantatlas-readme-branding`
- HEAD：`f566fc09`
- 工作树状态：dirty。开始和结束时均存在既有修改：`.github/workflows/ci.yml`、`backend/app/api/projects.py`、`backend/app/services/project_service.py`、`scripts/golden_quality_gate.py`、`scripts/v1_smoke.sh`、`tests/test_golden_release_gate.py`、`tests/test_projects_api_router.py`、`tests/test_tauri_desktop_skeleton.py`，以及既有/本次 QA 产物。
- 关键工具：Python 3.12.2、Node v22.22.3、npm 10.9.8、cargo 1.93.1、`npx` 可用。
- 后端启动方式：
  - 发现已有 `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` 和 Vite `5174` 进程，先用于真实浏览器路径。
  - 进程中断后，重新启动受控服务：`/usr/local/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`，`npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174`。
- 后端健康状态：`GET /api/health` 返回 `ok=true`、`llm_configured=true`、`data_dir=data`、模型 `deepseek-v4-pro`。未记录或输出任何 API key。
- 浏览器测试入口：`http://127.0.0.1:5174/`；过程中发现另有旧 Vite 服务 `5175` 使用 `qa_runs/.../vite.browser-smoke.config.ts`。
- 本次新增证据：
  - `qa_runs/patent_flow_long_qa_20260630/current-artifacts/agent-journeys/*.json`
  - `qa_runs/patent_flow_long_qa_20260630/current-artifacts/v1-api-smoke/v1_1_quality_report.json`
  - `qa_runs/patent_flow_long_qa_20260630/current-artifacts/golden-quality-gate-strict.json`
  - `output/playwright/goal-patent-flow-recovery-20260630.png`

测试命令结果：

- `/usr/local/bin/python3 tests/agent_journey_runner.py --journey all --output-dir qa_runs/patent_flow_long_qa_20260630/current-artifacts/agent-journeys`：通过，3 条 API journey 均 passed。
- `/usr/local/bin/python3 scripts/v1_api_smoke.py --repeat-count 1 --report-dir qa_runs/patent_flow_long_qa_20260630/current-artifacts/v1-api-smoke`：通过，5 个 workflow 完成，0 失败。
- `/usr/local/bin/python3 scripts/golden_quality_gate.py --strict --report-path qa_runs/patent_flow_long_qa_20260630/current-artifacts/golden-quality-gate-strict.json`：按预期失败，`enabled_count=0`，`no_release_gate_cases_enabled`。
- `/usr/local/bin/python3 -m pytest -q`：通过，`880 passed in 83.95s`。
- `npm --prefix frontend test -- --run`：通过，39 个文件 / 260 个测试。
- `npm --prefix frontend run build`：通过。
- `cargo test --manifest-path src-tauri/Cargo.toml`：通过，5 个 Rust 单测。
- `/usr/local/bin/python3 -m pytest tests/test_projects_api_router.py tests/test_golden_release_gate.py tests/test_tauri_desktop_skeleton.py -q`：通过，41 个测试。

## 2. 测试范围

已覆盖：

- API 级完整主流程：从想法创建发明专利、实用新型结构方案、导入已有稿件三条路径。
- API 级质量链路：初稿生成、质量检查、正式稿编译、成稿会审、official export。
- API 级恢复/一致性：source draft 修改后，质量检查、正式稿编译、成稿会审变为 stale，official export 被阻断。
- v1 deterministic smoke：software、sensing inspection、mechanical device、algorithmic、external draft 五类样例。
- 真实浏览器 UI：工作台入口、创建简单发明项目、启动发明点提炼、观察运行状态和中断恢复。
- 工程门禁：Python 测试、前端测试、前端 build、Tauri Rust test。

未覆盖或弱覆盖：

- 未完成真实浏览器端从输入到正式导出的完整一条链路，因为 live run 中途遇到服务进程消失、浏览器落到旧 `5175` QA 服务、项目被未知客户端删除/不可继续。
- 未验证 installed `/Applications/PatentAgent.app`、DMG 或 Tauri 窗口端到端；本轮目标是流程 QA 报告，不做 DMG 交付。
- 未验证 DOCX/PDF 文件打开后的视觉排版。
- 未用真实 CNIPA 检索；CNIPA helper 未配置，Google Patents fallback 出现本机 SSL 证书错误。
- 未运行真实多 CLI agent 会审，只覆盖 deterministic/fake 或 live LLM 后端的部分流程。

## 3. 测试输入

### 输入 A：简单技术方案

项目名：`QA简单方案-智能水杯温控-20260630`

技术方案：

> 一种智能水杯温控方法，通过杯底温度传感器实时采集水温，根据目标饮用温度和当前温差调整加热片功率，并在温度达到阈值后切换保温模式，解决传统保温杯无法稳定保持适饮温度的问题。

覆盖方式：

- 真实浏览器 UI 创建项目。
- live 后端启动发明点提炼，项目 ID 曾为 `a851fc0bac944f8cb886384270ea33db`，disclosure run ID 曾为 `357f6f295d7246babb9fa505c75915d7`。
- 中途观察到发明点候选、prior-art search warnings、runtime_state。

### 输入 B：复杂技术方案

样例：`samples/algorithmic_route_planning.md`

核心内容：

- 多约束任务路径规划，涉及任务时间窗、电量安全余量、临时禁行区、返航距离。
- 生成多个候选路径，计算时间窗偏离量、电量安全余量缺口、禁行区冲突因子的惩罚向量。
- 当惩罚向量超过阈值时，回退到最近可执行节点，冻结已完成任务和高优先级任务，重新排列剩余任务序列。
- 输出路径版本、回退原因和任务重排记录。

覆盖方式：

- `scripts/v1_api_smoke.py` 的 `algorithmic` workflow 完整覆盖到正式稿编译、成稿会审和 official export hygiene。
- 同轮还覆盖了 software、sensing inspection、mechanical device、external draft 四类复杂/变体输入。

## 4. 流程观察

1. 按 `AGENTS.md` 要求确认 source identity：当前路径、顶层目录、分支、HEAD 和 dirty 状态均明确。分支和路径符合预期，但工作树不干净。
2. 阅读 README、配置、测试脚本和 QA 产物后，确认默认流程为：工作台入口 -> 创建/导入项目 -> 发明点 -> 会审 -> 公式 -> 初稿 -> 质量检查 -> 正式稿编译 -> 成稿会审 -> 导出。
3. deterministic API journeys 均通过：
   - `invention_from_idea` 生成公式、初稿、质量检查、正式稿、成稿会审并成功 official export。
   - `utility_model_from_structure` 正确跳过公式要求，生成结构化权利要求并成功 official export。
   - `polish_existing_draft` 完成外部稿解析、质量链路和 official export。
4. v1 deterministic smoke 通过 5 个 workflow。每个 workflow 都验证了：正式稿编译前导出被 409 阻断、成稿会审前导出被 409 阻断、成稿会审通过后导出解锁、official export 无内部 marker。
5. 浏览器首次打开工作台时，短时间显示“后端检测中/正在刷新工作台”，随后变为“后端在线 / 模型可用 / 智能体部分可用”。
6. 选择“从技术想法撰写发明专利”后，UI 出现完整 9 步流程导航和表单校验。空表单显示项目名称和一句话想法不能为空；填入输入 A 后 CTA 正常启用。
7. 创建项目成功后，UI 自动选中新项目，并把流程推进到“发明点”。创建后约 5 秒内“提炼发明点”按钮处于 disabled；等待后恢复可点，属于轻微流程摩擦。
8. 点击“提炼发明点”后，后端 disclosure run 开始运行。20 秒时 API 显示 `status=running`、`current_stage=patent_points`；约 68 秒时 API 显示 `current_stage=disclosure_body`、`phase_count=6`。
9. 同一时间 UI 顶栏显示“空闲”，按钮“提炼发明点”重新可点，页面只保留旧提示“前置材料生成已启动：排队中”。用户无法从页面理解当前实际 stage，也容易重复触发。
10. live run prior-art search 阶段出现配置/网络 warnings：CNIPA helper 未配置，Google Patents fallback 因 SSL certificate verify failed 失败。UI 未明显暴露这些 warnings。
11. 在 live run 仍进行期间，原有 backend/frontend 进程均消失。重启受控 backend/frontend 后，浏览器 reload 落到旧 `5175` QA 服务；后端关闭日志显示收到一次未知来源的 `DELETE /api/projects/a851fc0bac944f8cb886384270ea33db` 并返回 200，随后该项目在 `/api/projects` 和 `data/` 中均不可见。页面恢复到无项目选中状态，无法继续该 run。
12. 工程测试门禁整体健康：Python 全量测试、前端测试、前端 build、Tauri Rust tests 均通过。

## 5. Bug 列表

### BUG-001：live 浏览器流程中断后落入旧 QA 服务且项目被未知客户端删除

- 严重程度：High
- 类型：流程阻断 / 工程稳定性
- 复现步骤：
  1. 使用已有 dev backend/frontend 打开 `http://127.0.0.1:5174/`。
  2. 选择“从技术想法撰写发明专利”。
  3. 创建项目 `QA简单方案-智能水杯温控-20260630`，项目 ID 曾为 `a851fc0bac944f8cb886384270ea33db`。
  4. 点击“提炼发明点”，disclosure run ID 曾为 `357f6f295d7246babb9fa505c75915d7`。
  5. 确认 API 显示 run `status=running`，随后原有 backend/frontend 进程消失。
  6. 重启 backend/frontend；浏览器 reload 后页面 URL 变为 `5175`，而本轮受控 Vite 是 `5174`。
  7. 停止受控后端时查看日志，发现 `DELETE /api/projects/a851fc0bac944f8cb886384270ea33db` 返回 200，之后查询项目为 404/缺失。
- 实际表现：中断恢复期间浏览器连接到旧 QA Vite 服务；受控 backend 收到未知来源项目删除请求；之后 `/api/projects` 中没有该项目，`data/` 下也找不到项目名、项目 ID 或 run ID，无法重试或继续。
- 预期表现：长流程中断后应固定回到同一个 backend/source identity；任何项目删除都应来自明确用户动作并有确认；正在运行的 disclosure run 不应因 reload/多 dev server 混淆被静默删除。
- 影响：真实用户可能在长生成过程中丢失已输入的技术交底和运行进度；QA 也可能误判当前浏览器连接的并不是正在测试的 source/config。
- 初步判断：核心风险不是单纯 SQLite 不持久化，而是多 Vite/dev backend 并存时的 source/config 混淆和未知删除动作。`5175` 使用 `qa_runs/patent_flow_long_qa_20260630/vite.browser-smoke.config.ts` 且代理到 `8001`，与本轮受控 `5174 -> 8000` 不一致。还需追踪未知 DELETE 的来源。
- 建议修复：在 UI 顶栏暴露 backend base URL、data_dir 和 source identity；项目删除增加二次确认和审计日志；长 run 页面应拒绝跨 backend 恢复；测试脚本结束时清理或显式标记旧 dev server；后端记录 DELETE 请求来源、referer、user-agent 和触发组件。

### BUG-002：live run 正在运行时 UI 显示“空闲”且 CTA 重新可点

- 严重程度：High
- 类型：交互体验 / 可恢复性
- 复现步骤：
  1. 创建输入 A 项目。
  2. 点击“提炼发明点”。
  3. 在 run 仍为 `running` 时观察 UI 和 `/api/projects/{id}/disclosures`。
- 实际表现：API 显示 `status=running`、`current_stage=disclosure_body`、`elapsed_ms=68061`，但 UI 顶栏显示“空闲”，下一步按钮“提炼发明点”可再次点击，旧提示停留在“前置材料生成已启动：排队中”。
- 预期表现：UI 应显示当前 stage、耗时、warning 数、可取消/重试状态；同类操作应在 run 完成/失败前禁用或明确提示已有运行。
- 影响：用户会误以为任务已结束或未启动，可能重复触发发明点提炼，造成状态污染、费用浪费或多个 run 竞争。
- 初步判断：frontend 的全局 busy/active run 判断没有从 disclosure run 的 `runtime_state` 或 `status=running` 正确派生；也可能只在提交请求期间设置 busy，未绑定后台 run 生命周期。
- 建议修复：统一用后端 run 状态驱动 operation console；对 `status=running` 的 disclosure/deliberation/formula/post-review run 建立 activeRun selector；同阶段 running 时主 CTA 改为“查看进度/取消/稍后刷新”。

### BUG-003：prior-art 检索失败只进入 API warnings，UI 未明确提示

- 严重程度：Medium
- 类型：配置问题 / 交互体验
- 复现步骤：
  1. 启动输入 A 的“提炼发明点”。
  2. 查询 `/api/projects/{id}/disclosures`。
  3. 查看 `prior_art_search` 阶段 warnings。
- 实际表现：API warnings 包含多条 `CNIPA EPUB helper is not configured`，以及 Google Patents fallback 的 `SSL: CERTIFICATE_VERIFY_FAILED`。UI 页面未明显提示检索降级、失败来源或用户可操作修复。
- 预期表现：用户应在发明点/知识库区域看到“现有技术检索已降级/失败”的提示，以及 CNIPA helper、证书、网络配置的修复方向。
- 影响：用户可能误以为系统已完成现有技术检索，从而高估授权判断可靠性。
- 初步判断：warnings 已在 API payload 中存在，但未映射到工作台运行提示或发明点确认面板。
- 建议修复：将 disclosure run warnings 汇总到 UI 风险与运行面板；对 provider 配置缺失和 SSL 错误提供明确文案；报告中标记该 run 的 prior-art evidence coverage 为不足。

### BUG-004：严格 golden release gate 仍无任何启用样例

- 严重程度：Medium
- 类型：工程稳定性 / 文本质量门禁
- 复现步骤：
  1. 运行 `/usr/local/bin/python3 scripts/golden_quality_gate.py --strict --report-path qa_runs/patent_flow_long_qa_20260630/current-artifacts/golden-quality-gate-strict.json`。
  2. 检查报告。
- 实际表现：命令以非 0 退出；`case_count=5`、`enabled_count=0`、`skipped_count=5`、`gate_failures[0].reason=no_release_gate_cases_enabled`。
- 预期表现：发布前至少有一个经过人工校准并启用的 golden patent case，或明确将该 gate 标记为不可发布状态。
- 影响：自动化可以证明流程跑通，但不能证明生成的专利文本达到人工批准的 release 质量基线。
- 初步判断：脚本的 strict 行为是正确的；阻断点是 golden cases 仍处于 `pending_human_review`，缺少 approved official output fixtures。
- 建议修复：优先校准并启用一个发明专利样例和一个实用新型样例；把 strict gate 保持在 CI/release gate 中。

### BUG-005：发明点提炼会把缺失实施细节扩展成具体方案，未充分标记为待确认

- 严重程度：Medium
- 类型：文本质量
- 复现步骤：
  1. 使用输入 A 只提供“温度传感器、温差、加热片功率、保温阈值”的简单方案。
  2. 启动发明点提炼。
  3. 查看 disclosure run 的 `patent_points` 阶段候选。
- 实际表现：候选 p1 增加了姿态传感器推断液位、环境温度传感器、多阈值、增量式 PID、前馈自学习校正、安全阈值等输入中没有明确提供的技术特征。虽然 `evidence_status=model_generated`，但这些内容以完整技术方案形式出现。
- 预期表现：模型补充的实施细节应显式标记为“建议补充/待确认/未验证”，并要求用户确认后才进入权利要求主线。
- 影响：后续权利要求可能写入用户未交底、未验证的特征，造成真实性和权属风险。
- 初步判断：发明点提炼 prompt 倾向于补足实施细节，但 UI 没有把“模型生成 vs 交底事实”分层呈现。
- 建议修复：在候选发明点中拆分“交底原文支持特征”和“模型建议补充特征”；默认只把交底支持特征带入独权，补充特征需要用户勾选确认。

## 6. 卡点列表

- 当前工作树 dirty，且包含与本轮目标无关的既有修改。QA 报告可以完成，但 release-grade 结论必须说明 dirty source。
- 真实浏览器路径依赖共享 `data/`，已有大量历史项目；新项目和旧项目混在同一个下拉框中，测试和真实用户都容易选错。
- 本机同时存在 `5174` 和旧 `5175` Vite 服务，且 `5175` 使用 QA 自定义 config。多 dev server 会混淆“当前 app 来自哪个 source/config”。
- 创建项目后下一步 CTA 短时间 disabled，缺少“正在加载项目状态”的明确说明。
- CNIPA helper 未配置，Google Patents SSL 失败，现有技术检索可信度不足。
- live run 的进度、warnings、partial artifacts 没有清楚展示在工作台，用户只能通过 API 才能判断发生了什么。
- strict golden gate 已正确失败，但还没有校准样例，因此不能作为文本质量通过证据。
- 未验证 installed app/DMG；如果用户反馈来自安装包，仍需按 `AGENTS.md` 做 installed app vs current source 对照。

## 7. 专利产物质量评估

### 权利要求书

deterministic API journeys 能生成有编号层级的权利要求，实用新型样例能围绕“底座、支撑臂、限位件”等结构特征组织，发明样例能覆盖核心处理流程。v1 smoke 的 official export hygiene 均通过，未发现内部 marker 泄露。

风险是 v1 quality trend 分数偏低：多个 workflow `overall=26/27`，external draft 为 `37`；`support_strength` 多为 0。虽然当前 gate 阈值通过，但这不等于文本已达到真实提交质量。

### 说明书

API 路径能产出技术领域、背景技术、发明内容、附图说明、具体实施方式等结构，说明书能支撑 deterministic fake LLM 的核心权利要求。复杂样例中 embodiment_density 约 `0.7-0.857`，说明实施例密度基本存在。

主要风险是 live LLM 对简单输入自动补充大量未交底细节，可能导致说明书支持的是“模型扩写方案”而不是用户真实方案。

### 摘要

API 路径均能生成摘要，official compile 后可导出。未发现 deterministic official export 中包含 prompt、Mermaid、generation logs 等内部文本。

### 附图说明 / 流程图

deterministic 路径包含 drawing description、Mermaid 或 diagram 产物，并在 official export hygiene 中检查内部标记不泄露。未进行真实图像/PDF/DOCX 渲染检查。

### 一致性

API journey 的 hash gate 设计有效：修改 source draft 后，quality、official compile、post-draft review 均变 stale，official export 被阻断。这是当前最强的完整性证据。

## 8. 可恢复性和长程稳定性

正向证据：

- API journey 中明确验证了 hash drift 后导出被阻断，说明版本链路对“源稿变化”有保护。
- API deterministic flows 使用临时数据目录，三条 journey 都能稳定跑完。
- v1 smoke 五类 workflow 均完成，无 execution failures。

负向证据：

- live browser run 中，后端 run 仍在 running 时 UI 显示空闲，恢复提示不可信。
- 原有 dev backend/frontend 中断后，浏览器 reload 落到 `5175` 旧 QA 服务；受控 backend 随后出现未知 `DELETE /api/projects/{id}`，导致新建项目和 disclosure run 无法继续。
- 浏览器 reload 后没有恢复到中断项目，且在 `5175` 旧服务上显示无项目选中，暴露多服务/多配置下的上下文混乱风险。
- prior-art provider warnings 没有作为用户可理解的恢复/修复动作呈现。

结论：API 层可恢复性比 UI/live runtime 可恢复性强；真实用户长流程还不够可靠。

## 9. 优先级建议

P0：

- 暂无已完全隔离根因的 P0。若 BUG-001 的未知 DELETE 或跨服务恢复混淆在受控服务中稳定复现，应升为 P0，发布前必须修复。

P1：

- 修复 live run 状态与 UI operation console 不一致问题，避免 running 时显示空闲和重复触发。
- 为项目创建、disclosure run 创建增加强持久化和恢复验证；启动时扫描 stale running runs 并展示“可恢复/可重试”。
- 清理 dev server/source identity 机制，避免 5174/5175 多服务导致测试或用户连接到不同配置。

P2：

- 校准并启用至少一个 golden patent case，使 strict golden gate 能成为真实文本质量证据。
- 将 prior-art provider warnings 显示到 UI，并给出 CNIPA helper、证书、网络配置修复建议。
- 对模型补充技术特征建立“用户确认”门禁，降低未交底特征进入权利要求的风险。
- 增加浏览器 E2E 覆盖：创建项目 -> 发明点 -> 确认 -> 生成初稿 -> 质量检查 -> 编译 -> 会审 -> 导出。

## 10. 后续建议

- 用受控 `PATENTAGENT_BACKEND_DATA_DIR` 创建隔离数据目录，复现 BUG-001，确认未知 DELETE 来源以及是否存在多服务/多 backend 恢复混淆。
- 增加 Playwright/Vitest 集成测试，断言后台 run `running` 时 UI 显示当前 stage，且同阶段 CTA 不可重复提交。
- 给 disclosure runs 增加 `stale/running_at_startup/failed_after_restart` 状态转换和用户可见恢复按钮。
- 对 live LLM 产物增加“交底事实 vs 模型建议”结构化检查，防止未确认扩写进入正式权利要求。
- 继续补 installed app/Tauri evidence：按 `AGENTS.md` 对比 `/Applications/PatentAgent.app`、当前 source dev server、同一数据目录。
- 对 DOCX/MD official export 做实际打开或文本抽检，验证文件名、章节顺序、中文专利格式和内部痕迹清理。

简短结论：当前 patent_agent 的 API 主流程已经能稳定完成专利撰写链路，但真实浏览器长流程的运行状态、恢复能力和文本质量门禁仍不适合真实用户连续完成专利撰写流程。
