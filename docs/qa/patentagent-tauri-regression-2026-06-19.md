# PatentAgent Tauri Regression - 2026-06-19

分支：`codex/patentagent-e2e-qa-integration`
测试对象：新构建 debug DMG
DMG：`/private/tmp/patents-agent-e2e-integration/src-tauri/target/debug/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg`

## 结论

- 集成分支已 push 到 `origin/codex/patentagent-e2e-qa-integration`。
- 新 Tauri debug DMG 构建成功。
- 旧 P0 “打包后黑屏/缺前端资源”在自动 Tauri renderer smoke 中已解决：`tauri://localhost` 页面 `readyState=complete`，存在 app shell/sidebar/topbar。
- 旧 P1 “结构化项目信息无法独立保存/编辑”在 live packaged backend 回归中已解决：9 个 metadata 字段可创建、GET/list 回显、PUT 局部更新、空字符串清空。
- 基础模型配置在默认 app data dir 下可用：`llm_configured=true`，model `deepseek-v4-pro`。
- 实用新型轻量路径的真实 AI 生成与内部稿导出通过。
- 发明专利完整路径的真实多智能体会审、核心公式包、AI 生成与内部稿导出通过。

## 证据

### Build

命令：`cargo tauri build --debug`

结果：

- `npm --prefix frontend run build` 通过。
- Rust/Tauri debug build 通过。
- 生成 DMG：`src-tauri/target/debug/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg`
- Notarization 跳过：debug 构建无 Apple notarization credentials，符合当前测试范围。

### Tauri DMG Smoke

命令：`python3 scripts/tauri_dmg_smoke.py --keep-artifacts src-tauri/target/debug/bundle/dmg/PatentAgent_1.1.0_aarch64.dmg`

Smoke artifacts：`/private/tmp/patents-tauri-dmg-smoke-babjdu2_`

关键结果：

- `bundle_metadata_ok=true`
- `bundled_backend_ok=true`
- `codesign_strict_ok=true`
- `health.ok=true`
- `health.llm_configured=true`
- `health.model=deepseek-v4-pro`
- `renderer_dom_smoke.ok=true`
- `renderer_dom_smoke.url=tauri://localhost`
- `renderer_dom_smoke.readyState=complete`
- `renderer_dom_smoke.hasAppShell=true`
- `renderer_dom_smoke.hasSidebar=true`
- `renderer_dom_smoke.hasTopbar=true`
- `app_alive_after_quit=false`
- `backend_alive_after_quit=false`

`spctl.status=rejected-not-notarized` 仍存在，属于 debug/未 notarized 构建的预期限制，不视为本轮回归 bug。

### Live Packaged Backend Regression

测试实例：从新 DMG app 直接启动，默认 app data dir，端口 `63620`。
Health：

```json
{
  "ok": true,
  "llm_configured": true,
  "model": "deepseek-v4-pro",
  "embedding_model": "local-hash-128",
  "version": "1.1.0"
}
```

结果：

- 创建虚构项目 `Tauri回归-多模态检索专利草案生成` 成功。
- `applicant`, `inventors`, `technical_field`, `background`, `pain_point`, `technical_solution`, `innovation`, `embodiments`, `beneficial_effects` 创建后立即回显。
- GET/list 均保留 metadata。
- PUT 局部更新保留未传字段。
- PUT `{"applicant": ""}` 可清空已保存字段，验证 reviewer fix 生效。
- 未生成 draft package 时 legacy export 返回 409。
- official export readiness 返回 `reason=draft_required`，`required_actions` 包含 `generate_draft`。
- 测试项目已删除。

### Live AI Generate Smoke

测试路径：实用新型轻量版，默认 app data dir，端口 `63620`。
测试项目：`Tauri生成Smoke-模块化检索终端`，虚构数据，测试后已删除。

结果：

```json
{
  "ok": true,
  "elapsed_seconds": 64.19,
  "generated_title": "一种Tauri生成Smoke-模块化检索终端结构",
  "claims_chars": 646,
  "description_chars": 4013,
  "abstract_chars": 312,
  "export_md_bytes": 21623,
  "export_docx_bytes": 44275
}
```

### Live Invention Patent Full Path

测试路径：发明专利，默认 app data dir，端口 `64601`。
测试项目：`Tauri发明专利Smoke-多模态检索草案生成方法`，虚构数据，测试后已删除。
导出文件：`docs/qa/artifacts/tauri-invention-patent-draft.docx`

结果：

```json
{
  "ok": true,
  "model": "deepseek-v4-pro",
  "direct_generate_blocked_without_deliberation": true,
  "deliberation": {
    "status": "completed",
    "providers": ["codex", "deepseek", "claude"],
    "run_mode": "full",
    "failure_count": 0
  },
  "formula_required": true,
  "formula_run": {
    "status": "completed",
    "quality_severity": "normal",
    "providers": ["codex", "deepseek", "claude"]
  },
  "draft_generated": true,
  "generated_title": "一种Tauri发明专利Smoke-多模态检索草案生成方法方法",
  "claims_chars": 2427,
  "description_chars": 5914,
  "abstract_chars": 324,
  "export_md_bytes": 38005,
  "export_docx_bytes": 46412,
  "final_elapsed_seconds": 201.84
}
```

说明：

- 发明专利直接 `/generate` 在无会审时返回 409，确认 strict deliberation gate 生效。
- 多智能体会审以 full 模式调用 `codex/deepseek/claude`，状态 completed。
- 会审后生成仍要求核心公式包；公式包运行 completed，质量 `normal`。
- 携带 `formula_run_id` 后生成内部工作稿并导出 MD/DOCX 成功。
- DOCX 原始导出保存在 app data `exports/835138c1708143598ff06a7c60887b53-internal.docx`，已复制到 QA artifacts；抽查 DOCX XML 包含标题、`多模态`、`权利要求` 与内部工作稿边界提示。

## Previous Issues

| 问题 | 状态 | 证据 |
| --- | --- | --- |
| P0 打包 app 黑屏/缺前端资源 | 已解决 | renderer DOM smoke 非空，`hasAppShell/hasSidebar/hasTopbar=true` |
| P1 项目信息缺结构化字段 | 已解决 | live packaged backend 创建/读取/更新/清空 9 个 metadata 字段通过 |
| P2 正式稿导出门禁文案/状态不清 | 已改善 | API readiness 可机器读取 `draft_required` 等 reason；前端测试覆盖 216 passed |
| P2 CJK 下载名 fallback | 已合入并回归 | `tests/test_content_disposition.py` 与 API/export 组合回归通过 |
| P3 前端依赖/包体告警 | 已合入并回归 | Vite build main chunk 483.22 kB，无 500 kB warning |

## New Findings

### QA-REG-001: Computer Use cannot attach to temporary Tauri windows in this environment

严重程度：P3 / 测试工具阻塞
影响：无法完成逐点击 UI 录屏式测试；改用 Tauri renderer DOM smoke + live packaged backend/API + build/test 组合验证。
观察：

- `mcp__computer_use.get_app_state` 对 `/private/tmp/.../PatentAgent.app` 和临时 QA bundle 均返回 `cgWindowNotFound`。
- `list_apps` 能看到 app running。
- 修改 bundle id 的临时 QA 副本可启动后端，但 System Events 显示没有窗口对象；该临时副本不作为产品缺陷证据。
- 未改动 DMG 的 `tauri_dmg_smoke.py` 可以在 Tauri webview 内验证真实 renderer DOM 非空，因此 P0 黑屏回归以 smoke 结果为准。

建议：

- 后续若要做逐点击桌面 UI 自动化，优先给测试包使用唯一 bundle id 的正式 QA 构建配置，而不是临时改 plist。
- 或扩展 `scripts/tauri_dmg_smoke.py`，加入更多 DOM-level UI contract checks，例如 metadata section、export gate CTA、项目创建表单字段存在性。

### QA-REG-002: Isolated `PATENTAGENT_BACKEND_DATA_DIR` does not inherit model credentials

严重程度：P3 / 环境说明
影响：使用隔离数据目录启动 app 时 `llm_configured=false`，不适合验证“已配置基础模型”的 AI 路径。
证据：`/private/tmp/patentagent-tauri-regression-data` 实例 health 返回 `llm_configured=false`，默认 app data dir 实例返回 `llm_configured=true`。
建议：如果需要既隔离数据又继承模型配置，应提供单独的 QA config import/export 或测试专用 env 注入方式。

### QA-REG-003: Invention-patent generated title duplicated terminal noun

严重程度：P3 / 生成质量
影响：不阻塞生成和导出，但正式初稿标题需要人工修正，降低首稿可信度。
证据：发明专利完整路径生成标题为 `一种Tauri发明专利Smoke-多模态检索草案生成方法方法`。
建议：在标题生成 prompt 和后处理层增加重复尾词规范化，例如去除 `方法方法`、`系统系统`、`装置装置` 等重复结尾。
