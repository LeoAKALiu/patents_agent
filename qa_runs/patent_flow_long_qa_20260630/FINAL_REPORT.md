# patent_agent 长程 QA Final Report

## 1. 本轮 QA 摘要

本轮在当前工作树执行了 patent drafting 长程 QA。核心 API 层 deterministic happy paths 通过：发明想法、实用新型结构、已有稿件润色三条路径都能通过 fake LLM + FastAPI TestClient 走到质量门禁、正式稿编译、成稿会审和 official export。主要自动化门禁也通过：pytest、frontend Vitest、frontend build、v1 API smoke、Tauri cargo check/test。

Debug follow-up rebaseline at SHA `f566fc09` confirmed the earlier 10-file unmerged index blocker is stale/resolved. Before Task 2/3/4 edits, the current tree had no unmerged files and only untracked QA/output artifacts. The remaining issues under active fix are the one-command smoke sidecar policy, the overlong material filename 500, and the disabled golden release gate.

Task 2/3/4 follow-up results: overlong material filename upload now returns a controlled 422; strict golden release mode now fails when zero cases are enabled; `v1_smoke.sh` no longer blocks on an existing generated sidecar directory. The strict golden gate still cannot pass until at least one golden patent case is calibrated and enabled.

Browser follow-up at SHA `f566fc09` added current-source React evidence for workbench, document repair, annotated repair editor, and export lock state. Installed app, Tauri runtime, and DMG evidence are still not covered.

## 2. 已理解的 patent_agent 专利撰写主流程

```text
工作台三入口
  -> 新建/选择项目
  -> 输入想法、元数据、材料或已有稿件
  -> 材料解析 / 外部稿解析确认
  -> 发明点提炼与确认
  -> 多智能体会审
  -> 核心公式判断与生成
  -> 初稿生成：标题、摘要、权利要求、说明书、附图说明
  -> 质量检查：filing readiness、claim defense、draft completion
  -> 正式稿编译：清除内部痕迹并生成 hash
  -> 成稿会审：post-draft review 和 export decision
  -> 可选 repair-session / repair patches
  -> 导出 official MD/DOCX 和内部侧车报告
```

## 3. 已执行命令和结果

- `python3 tests/agent_journey_runner.py --journey all ...`: passed, 3 API journeys passed.
- `python3 scripts/v1_api_smoke.py --repeat-count 2 ...`: passed.
- `python3 scripts/golden_quality_gate.py ...`: exit 0, but all 5 cases skipped/disabled. Logged `BUG-001`.
- `python3 -m pytest -q`: passed, 878 tests.
- `npm --prefix frontend test -- --run`: passed, 39 files / 260 tests.
- `npm --prefix frontend run build`: passed.
- `cargo check --manifest-path src-tauri/Cargo.toml`: passed.
- `cargo test --manifest-path src-tauri/Cargo.toml`: passed, 5 tests.
- `scripts/v1_smoke.sh`: failed at sidecar placeholder preflight after sub-gates passed. Logged `BLOCKER-002`.
- QA explorations: material upload and incomplete-input scripts ran and wrote artifacts.
- Browser follow-up: isolated QA backend `8001` + Vite `5175`, seeded repairable project, captured current React screenshots and snapshots under `current-artifacts/browser-smoke-current/`.
- Repair follow-up: `/usr/local/bin/python3 -m pytest tests/test_post_draft_repair.py -q` passed 31 tests; `npm --prefix frontend test -- PostDraftRepairEditor DocumentRepairWorkspace --run` passed 28 frontend tests.
- Robustness follow-up: prompt-injection/conflict disclosure tests and QA preflight tests passed; frontend `MaterialSummary`/`IdeaIntakePanel` tests passed; frontend production build passed.

Full details: `COMMAND_RESULTS.md`.

## 4. 已覆盖的用户路径

- Happy path: `invention_from_idea` API journey passed.
- Existing draft polish path: `polish_existing_draft` API journey passed.
- Utility model path: `utility_model_from_structure` API journey passed.
- Incomplete material path: API exploration covered empty/short ideas, incomplete material, export before draft, and no-key generation response.
- Abnormal/recovery path: upload errors, hash drift export blocking, missing draft export blocking, and one-command smoke build-artifact blocker covered.
- Browser UI path: current React workbench, document overview, annotated repair editor, claims-issue selection, and export lock state covered with screenshots.
- Prompt-injection/conflict robustness path: fake-LLM disclosure generation now verifies malicious uploaded text stays in user material context and conflicting rule-model/neural-network material facts remain distinguishable in prompts.
- First-mile guidance path: frontend now warns on very short or marketing-only ideas and duplicate visible material filenames.

## 5. 发现的 P0/P1/P2/P3 bug

- P0: none confirmed.
- P1: none confirmed as product bugs.
- P2:
  - `BUG-001`: fixed for strict/release mode; current strict gate now fails as intended because no cases are enabled.
  - `BUG-002`: fixed; overlong filenames return 422 with actionable guidance.
- P3: none separately logged.

## 6. 发现的 blocker

- `BLOCKER-001`: stale/resolved on rebaseline at SHA `f566fc09`.
- `BLOCKER-002`: fixed for sidecar resource preflight; full Tauri rebuild was not run in the follow-up smoke variant.

## 7. 发现的流程卡点 friction

- `FRICTION-001`: source and product identity ambiguous before QA starts. Mitigated with `scripts/qa_preflight.py`.
- `FRICTION-002`: material upload boundary behavior not obvious without code/trial-and-error.
- `FRICTION-003`: empty and very short marketing-only ideas can create projects without immediate guidance. Mitigated in frontend only; API remains permissive.
- `FRICTION-004`: duplicate material filename uploads accepted without visible disambiguation. Mitigated in frontend material summary for duplicate file names.
- `FRICTION-005`: workbench and export workspace can disagree on next recovery priority when quality checks are missing and a repairable post-draft review exists.

## 8. 高风险但未确认的问题

- Broader browser guided-flow UX beyond workbench/document/repair/export evidence remains unverified.
- Installed app and DMG behavior not verified.
- Prompt-injection material is now covered at fake-LLM prompt-boundary level, but live-provider behavior and official export contamination with a real model remain unverified.
- Conflict disclosure A/B facts are now preserved in generator prompts, but the product still does not force user confirmation of the authoritative technical path.
- MIME/extension mismatch and very large file upload limits remain unverified.

## 9. 建议优先补充的自动化测试

Priority recommendations are in `AUTOMATION_RECOMMENDATIONS.md`. Top items:

1. Full API happy path to official export.
2. Hash drift blocks stale official export.
3. Prompt injection material does not affect system behavior.
4. Official export content equals current official package.
5. Overlong material filename returns controlled non-500 error.
6. Golden quality gate fails release mode when no cases are enabled.
7. Conflict disclosures require user confirmation before final drafting.

## 10. 是否建议当前版本进入下一阶段

不建议合入/发布：core API, command gates, and current React repair evidence are healthier after Task 1-6, but strict golden release gate correctly fails until calibrated cases are enabled, and Tauri runtime / installed app / DMG evidence is still missing.

## 11. 仍未覆盖的风险

- Browser coverage outside workbench/document/repair/export evidence.
- Tauri app runtime with sidecar startup and real `/api/health`.
- Installed app vs current source comparison.
- DMG packaging and exact-artifact smoke.
- Live provider unavailable/rate-limit/timeout UX beyond deterministic fake flows.
- DOCX/PDF exported file open/render verification.

## 12. 本轮创建或修改的 QA 文件列表

- `QA_GOAL.md`
- `RUN_LOG.md`
- `TEST_MATRIX.md`
- `BUGS_AND_BLOCKERS.md`
- `FLOW_FRICTION.md`
- `AUTOMATION_RECOMMENDATIONS.md`
- `COMMAND_RESULTS.md`
- `FINAL_REPORT.md`
- `explore_material_uploads.py`
- `explore_incomplete_flow.py`
- `test_data/*.md`
- `test_data/boundary_prompt_injection.xyz`
- `artifacts/agent-journeys/*.json`
- `artifacts/v1-api-smoke/*`
- `artifacts/v1-smoke-report/*`
- `artifacts/golden/golden-quality-gate.json`
- `artifacts/material-upload-exploration.json`
- `artifacts/incomplete-flow-exploration.json`
- `BROWSER_UI_EVIDENCE.md`
- `browser_evidence_backend.py`
- `seed_browser_repair_project.py`
- `vite.browser-smoke.config.ts`
- `current-artifacts/browser-smoke-current/*`
- `CURRENT_STATE_REBASELINE.md`
- `DEBUG_PLAN.md`
- `DEBUG_TASK_BREAKDOWN.md`
- `scripts/qa_preflight.py`
- `tests/test_qa_preflight.py`
- `frontend/src/flow/panels/IdeaIntakePanel.test.tsx`
