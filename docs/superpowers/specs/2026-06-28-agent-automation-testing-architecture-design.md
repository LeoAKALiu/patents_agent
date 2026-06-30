# Agent 自动化测试架构设计

## Source Identity

| 项目 | 当前值 |
| --- | --- |
| Worktree | `/Users/leo/Projects/patents_agent` |
| Git top-level | `/Users/leo/Projects/patents_agent` |
| Branch | `codex/automation-test-plan` |
| Short SHA | `3f6258ac` |
| Worktree 状态 | Dirty |

当前 dirty 内容包括已有自动化测试相关改动和未跟踪文件：`backend/app/services/llm_factory.py`、`backend/app/llm_cassette.py`、`tests/flow_driver.py`、`tests/test_flow_driver.py`、`tests/test_llm_cassette.py`、`frontend/src/GuidedPatentFlow.tsx`、`frontend/src/guidedFlow.ts`、`frontend/src/guidedFlow.test.ts`、`frontend/src/GuidedPatentFlow.progress.test.tsx`、`docs/project-design-overview.md`、`docs/qa/automation-test-plan-execution-2026-06-27.md`、`output/` 等。本文档只描述架构设计，不把这些未提交改动视为已发布能力。

## Goal

把 PatentAgent 的 agent 自动化测试从“运行测试并修复失败”升级为可重复的专利撰写流水线审查器。测试系统必须先固定源码和运行对象身份，再复现用户旅程断点，保存证据，分类根因，小步修复，并用确定性门禁和专利质量 oracle 验证正式稿不会被错误放行。

## Non-Goals

- 不在本设计中实现完整 Playwright/Tauri E2E 框架。
- 不把 live LLM 评测作为 release blocker。
- 不用 LLM-as-judge 替代确定性规则、fake LLM golden 或 hash/export 门禁。
- 不改变现有产品流程、专利生成逻辑、导出格式或 DMG 打包规则。
- 不把 `docs/superpowers/`、截图、OpenDesign 导出或静态 prototype 当作生产 UI 证据。

## Design Principles

1. **身份先于测试**：每次测试报告必须记录 worktree、branch、SHA、dirty 状态、运行对象、LLM 模式和数据目录。
2. **确定性优先**：release blocker 默认使用 fake LLM、replay cassette、临时数据目录和 golden fixture。
3. **旅程不是 HTTP 200**：journey 检查必须断言按钮解锁、状态保留、错误修复建议、hash 失效和导出锁定。
4. **专利质量独立评测**：质量 oracle 独立于生成器，检测区别特征、创造性支撑、说明书支撑、正式稿清洁度和证据诚实性。
5. **故障注入常态化**：测试必须覆盖缺 key、坏 JSON、超时、取消重试、hash drift、空/超大/乱码文件和 provider 中途失败。
6. **修复闭环可审计**：agent 输出必须包含 bug、根因、改动、窄验证、宽验证和剩余风险。

## Architecture Overview

自动化测试分为一个前置身份门禁和三层执行体系：

```text
Source Identity Gate
  -> Layer 1: Deterministic Regression Gates
  -> Layer 2: User Journey Breakpoint Inspection
  -> Layer 3: Patent Quality Oracle
  -> Agent Repair Protocol
```

### Source Identity Gate

每次自动测试、修复、打包或 handoff 前，agent 必须运行并记录：

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

报告中必须包含：

- `worktree_path`
- `git_top_level`
- `branch`
- `short_sha`
- `dirty_status`
- `dirty_files_summary`
- `test_target`: `dev_server`、`tauri_dev`、`packaged_dmg`、`installed_app` 或 `api_testclient`
- `llm_mode`: `fake`、`cassette_replay`、`cassette_record` 或 `live_provider`
- `data_dir`: 临时目录、默认 `data/`、Tauri app data 目录或 installed app 日志中的目录
- `artifact_identity`: DMG/app 路径、大小、SHA256、挂载卷或 dev server URL

如果测试对象和当前源码不一致，例如用户截图来自 `/Applications/PatentAgent.app`，agent 必须同时核对 installed app、`backend-startup.log`、后端 health 和当前源码 dev server，不能从当前源码直接推断 installed app 行为。

## Layer 1: Deterministic Regression Gates

基础确定性门禁固定为：

```bash
python3 -m pytest -q
python3 scripts/v1_api_smoke.py --repeat-count 2
npm --prefix frontend test -- --run
npm --prefix frontend run build
bash scripts/v1_smoke.sh
```

职责划分：

| Gate | 责任 |
| --- | --- |
| `python3 -m pytest -q` | 后端规则、存储、API、质量门禁、正式稿、成稿会审 |
| `scripts/v1_api_smoke.py --repeat-count 2` | fake LLM 下端到端 golden pipeline |
| `npm --prefix frontend test -- --run` | 前端状态机、组件逻辑、UI gate 行为 |
| `npm --prefix frontend run build` | TypeScript、Vite build 和静态资源完整性 |
| `bash scripts/v1_smoke.sh` | 发布级单命令总门禁 |

失败处理规则：

1. 先最小复现，记录命令、失败日志、相关 fixture、API payload 或截图。
2. 分类为 UI 断点、API contract、状态机、质量规则、导出门禁、provider 兼容、数据目录或打包问题。
3. 只改相关模块，不绕过门禁，不用测试放宽掩盖产品错误。
4. 先运行最小相关测试，再运行对应宽门禁。
5. 报告明确说明没有运行的门禁和原因。

## Layer 2: User Journey Breakpoint Inspection

Journey runner 面向真实用户入口，而不是单个 API。每条 journey 都输出结构化 JSON 报告，并可附加截图、API payload 和事件日志路径。

### Required Journeys

| Journey ID | 入口 | 关键断点 |
| --- | --- | --- |
| `invention_from_idea` | 从技术想法撰写发明专利 | 创建项目 -> 发明点 -> 会审 -> 公式 -> 初稿 -> 质检 -> 正式稿 -> 成稿会审 -> 导出 |
| `utility_model_from_structure` | 从结构方案撰写实用新型 | 创建项目 -> 结构化方案 -> 轻量初稿 -> 质量检查 -> 导出 |
| `polish_existing_draft` | 导入已有稿件润色 | 上传/粘贴 -> 章节解析 -> 确认工作稿 -> 质量检查 -> 正式稿清理 -> 导出 |

### Breakpoint Assertions

每个断点至少断言：

- 下一步按钮是否解锁，且禁用时有明确修复建议。
- 取消、重试、返回和刷新是否保留项目、run、draft 和错误上下文。
- 长任务是否显示阶段、耗时、失败原因和可执行下一步。
- 当前 draft 改变后，旧质量检查、正式稿编译、成稿会审和导出是否被 hash 锁定。
- 正式提交稿、内部策略稿和风险侧车报告是否分离。
- 内部策略、prompt、会审日志、未验证效果和支撑缺口不会进入正式提交稿。
- 专家工具跳步访问时，系统是否展示缺失前置条件，而不是静默失败。

### Runner Modes

| Mode | 运行对象 | 用途 |
| --- | --- | --- |
| `api` | FastAPI `TestClient` + 临时数据目录 | 最快的确定性 journey 和 failure injection |
| `browser` | dev server + Playwright DOM | 证明用户不会卡在真实 React UI |
| `tauri_dom` | Tauri dev 或 packaged app DOM smoke | 证明桌面壳、sidecar health、API base URL 和 UI 可用 |
| `manual` | installed app 或签名 DMG | 只用于文件选择器、权限弹窗、真实 app data 和发布前抽检 |

### Journey Report Schema

每次 journey 输出一个 JSON 文件，默认路径：

```text
output/agent-journeys/<timestamp>-<journey_id>.json
```

报告字段：

```json
{
  "schema_version": 1,
  "source_identity": {
    "worktree_path": "/Users/leo/Projects/patents_agent",
    "git_top_level": "/Users/leo/Projects/patents_agent",
    "branch": "codex/automation-test-plan",
    "short_sha": "3f6258ac",
    "dirty_status": "dirty",
    "dirty_files_summary": ["frontend/src/guidedFlow.ts", "tests/flow_driver.py"]
  },
  "execution": {
    "journey_id": "invention_from_idea",
    "mode": "api",
    "test_target": "api_testclient",
    "llm_mode": "fake",
    "data_dir": "/tmp/patentagent-journey-abc123",
    "started_at": "2026-06-28T00:00:00+08:00",
    "finished_at": "2026-06-28T00:00:20+08:00",
    "status": "failed"
  },
  "steps": [
    {
      "id": "official_compile_hash_gate",
      "status": "passed",
      "input_summary": "edited draft after official compile",
      "expected": "official export blocked",
      "actual": "HTTP 409 export-readiness blocked",
      "evidence": ["payloads/export-readiness.json"]
    }
  ],
  "quality": {
    "case_id": "urban-health-agent-claim-support",
    "status": "passed",
    "rule_failures": []
  },
  "failures": [
    {
      "classification": "export_gate",
      "severity": "P1",
      "user_visible_message": "正式稿已过期，请重新生成正式稿并完成成稿会审。",
      "suggested_fix": "invalidate post-draft review when source draft hash changes"
    }
  ],
  "artifacts": {
    "screenshots": [],
    "api_payloads": ["payloads/export-readiness.json"],
    "logs": ["logs/backend.log"]
  }
}
```

## Layer 3: Patent Quality Oracle

质量 oracle 使用独立 golden patent cases，覆盖发明、实用新型、已有稿件润色、低证据方案和内部痕迹污染。release blocker 以确定性规则和 fake LLM golden 为主，live LLM 只用于诊断和人工复核。

### Golden Case Schema

每个 case 存放在 `tests/golden_patent_cases/<case_id>/case.json`，字段为：

```json
{
  "case_id": "urban-health-agent-claim-support",
  "application_type": "invention",
  "input_kind": "idea",
  "technical_idea": "一种城市体检智能体任务编排与可信复核方法。",
  "existing_draft": "",
  "key_innovations": ["任务 DAG", "证据链绑定", "可信复核节点"],
  "prior_art_summary": "现有系统仅汇总指标，缺少任务链路和证据复核。",
  "required_distinguishing_features": ["任务 DAG", "证据链绑定"],
  "forbidden_official_content": ["内部策略", "会审日志", "需实验", "模型生成但未验证"],
  "expected_quality_thresholds": {
    "claim_feature_coverage": 0.9,
    "spec_support_coverage": 0.85,
    "official_cleanliness": 1.0,
    "evidence_honesty": 1.0
  }
}
```

### Evaluation Dimensions

| 维度 | 自动检查方式 | Release blocker |
| --- | --- | --- |
| 新颖性差异 | 独权和关键从权必须包含 `required_distinguishing_features` | 是 |
| 创造性支撑 | 说明书包含技术问题、技术手段、技术效果的对应段落 | 是 |
| 权利要求防线 | 独权不过窄，从权有层级兜底；规则检查 claim 数量和特征分布 | 是 |
| 说明书支撑 | 每个核心 claim feature 在实施例、附图说明或公式说明中有支撑 | 是 |
| 正式稿清洁度 | 正式稿无 Markdown、prompt、会审日志、内部策略、待办标记、调试信息 | 是 |
| 证据诚实性 | `需实验`、`模型生成`、`可行未验证` 不被写成已验证事实 | 是 |
| 导出门禁 | 编译、成稿会审和 current hash 必须匹配 | 是 |
| 语言流畅度 | LLM-as-judge 或人工复核诊断 | 否 |

### Oracle Output

质量 oracle 输出：

- `case_id`
- `application_type`
- `draft_hash`
- `official_package_hash`
- `rule_results`
- `threshold_results`
- `blocking_failures`
- `diagnostic_notes`
- `official_contamination_hits`
- `unsupported_claim_features`
- `unverified_evidence_promotions`

任何 release-blocking 失败都必须能从输出定位到具体 claim、说明书段落、正式稿片段或 hash gate。

## Failure Injection Matrix

故障注入不只跑 happy path。每个故障注入项必须输出步骤、输入摘要、失败点、用户可见提示和建议修复。

| Fault ID | 注入方式 | 期望行为 | 主要分类 |
| --- | --- | --- | --- |
| `missing_api_key` | 无 API key 启动生成类功能 | fail closed，UI 给设置入口和可读提示 | provider_config |
| `malformed_llm_json` | fake LLM 返回坏 JSON | 后端修复成功或明确失败，不能写入伪成功 run | provider_contract |
| `long_task_timeout` | runtime 超时 | 状态变为 failed/canceled，保留重试入口 | runtime |
| `cancel_retry` | 中途取消后重试 | 取消不破坏上下文，重试创建新 run | runtime_state |
| `hash_drift_after_quality` | 质检后修改 draft | 正式稿和导出锁定 | quality_gate |
| `hash_drift_after_compile` | 正式稿编译后修改 draft | 成稿会审和导出锁定 | export_gate |
| `empty_upload` | 上传空文件 | 明确拒绝并保留项目上下文 | file_input |
| `oversized_upload` | 上传超大文件 | 明确失败或后台任务化，UI 不冻结 | file_input |
| `garbled_upload` | 上传乱码文件 | 解析失败提示可执行修复 | parser |
| `provider_mid_failure` | 会审 provider 中途失败 | run 标记失败，阶段日志可见，可重试 | provider_runtime |
| `expert_tool_deep_link` | 跳步访问专家工具 | 显示缺前置条件，不产生空白页 | ui_gate |
| `empty_corpus_grantability` | 空语料库跑授权前景 | 明确说明证据不足，不伪造现有技术 | patent_quality |
| `official_contamination` | 正式稿混入内部会审痕迹 | 编译或成稿会审阻断导出 | official_cleanliness |

## Agent Repair Protocol

Codex、Claude 或 Hermes worker 修复必须遵循同一闭环：

```text
1. Identify
   记录 source identity、测试对象、数据目录、LLM 模式和入口。

2. Reproduce
   跑最小 journey、golden case 或 fault injection，保存失败日志、截图、API payload 和 hash。

3. Classify
   分类为 UI 断点、API contract、状态机、质量规则、导出门禁、provider 兼容、数据目录或打包问题。

4. Patch
   只改相关模块；不绕过质量门禁；不把内部稿内容放进正式稿。

5. Verify Narrow
   跑最小相关测试或 journey。

6. Verify Broad
   跑 `bash scripts/v1_smoke.sh` 或本次风险对应的发布门禁。

7. Report
   输出 bug、根因、改动、测试证据、剩余风险。
```

Agent 不得：

- 未复现就修。
- 只跑 happy path。
- 用 live LLM 通过结果替代 fake/golden 确定性证据。
- 修改测试来绕过产品门禁。
- 用旧 DMG、旧分支或旧数据目录作为通过证据。
- 把 dirty build 描述成纯 `HEAD`。

## Implementation Phases

### Phase 1: `agent-journey-runner`

目标：把三条用户入口变成可重复执行的 journey checklist，并输出 JSON 报告。

验收：

- 支持 `api` mode，使用临时数据目录和 fake LLM。
- 覆盖 `invention_from_idea`、`utility_model_from_structure`、`polish_existing_draft`。
- 每条 journey 输出 source identity、steps、gates、hashes、artifacts 和 failures。
- 至少覆盖 hash drift 后正式导出锁定。
- 对应 pytest 可单独运行。

### Phase 2: `golden-patent-quality-suite`

目标：建立 5 到 10 个 golden patent cases，验证授权导向、证据诚实性和正式稿清洁度。

验收：

- 覆盖发明、实用新型、已有稿件润色、低证据方案和内部痕迹污染。
- 每个 case 包含区别特征、现有技术摘要、禁止进入正式稿内容和质量阈值。
- 确定性规则能定位 claim feature、说明书支撑和正式稿污染片段。
- live LLM judge 只输出诊断，不影响 release blocker。

### Phase 3: `failure-injection-matrix`

目标：系统性测试缺 key、LLM 坏响应、hash drift、取消重试、导出锁定和异常文件。

验收：

- 每个 fault 输出结构化事件日志。
- UI/API 都能看到用户可执行修复建议。
- provider、runtime、parser、export gate 分类清晰。
- P0/P1 fault 进入 `v1_smoke.sh` 或 release gate。

### Phase 4: `agent-repair-protocol`

目标：把修复闭环固定为 Codex/Claude/Hermes 可执行 prompt 和验收格式。

验收：

- 新增 agent repair prompt/template。
- Handoff 必须包含 source identity、复现证据、分类、改动、窄验证、宽验证和剩余风险。
- Worker 任务必须写明目标 branch、worktree、文件范围、命令、截图或 browser verification 要求、merge blocker。
- Review agent 必须检查 diff、运行声明的检查，并验证集成 app。

## Report And Artifact Conventions

默认输出目录：

```text
output/agent-journeys/
output/patent-quality/
output/failure-injection/
```

每个报告目录包含：

- `report.json`
- `source-identity.txt`
- `api-payloads/`
- `logs/`
- `screenshots/`，仅 UI/Tauri mode 必需
- `README.md`，简述本次运行命令和结果

报告不得提交真实 API key、用户隐私数据、完整 live provider 响应或不可公开专利材料。需要保留调试上下文时，使用摘要、hash、fixture ID 或脱敏片段。

## Acceptance Criteria

设计实施后，agent 自动化测试被视为可用必须满足：

- 任一测试报告都能追溯到明确 source identity 和运行对象。
- 三条主 journey 至少能在 `api` mode 下重复运行，并能在失败时输出定位证据。
- 正式导出必须受正式稿编译、成稿会审和 hash 匹配共同控制。
- 质量 oracle 能阻断内部策略污染、未验证证据事实化、区别特征缺失和说明书支撑缺失。
- 故障注入覆盖 P0/P1 级质量门禁、导出门禁和 provider/runtime 失败。
- Agent 修复报告不再只有“跑了测试”，而是包含复现、分类、根因、补丁、窄验证、宽验证和剩余风险。
