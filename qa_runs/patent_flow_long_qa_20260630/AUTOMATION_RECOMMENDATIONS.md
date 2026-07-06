# Automation Recommendations

## P0

### 1. Full API happy path from project to official export

- 测试名称：`test_patent_flow_happy_path_official_export`
- 测试层级：integration
- 建议文件位置：extend `tests/test_flow_driver.py` or `tests/agent_journey_runner.py`
- mock 策略：FastAPI `TestClient`, temp data dir, `FakeLLMClient` with deterministic claims/description/review outputs.
- 输入数据：`qa_runs/patent_flow_long_qa_20260630/test_data/simple_invention.md`
- 断言点：project created, draft generated, quality/compile/review gates current, official export 200, official export lacks internal markers.
- 能防止什么回归：core patent drafting flow blocked, export incorrectly locked/unlocked, official contamination.
- 实现复杂度：中
- 优先级：P0

### 2. Hash drift blocks stale official export

- 测试名称：`test_edit_after_review_stales_all_export_gates`
- 测试层级：integration
- 建议文件位置：`tests/test_flow_driver.py`
- mock 策略：reuse `FlowDriver` and fake LLM.
- 输入数据：generated export-ready project, then manual `PUT /draft-package`.
- 断言点：export readiness false; quality/official/post-review gates stale; `official-export.md` returns 409.
- 能防止什么回归：用户修改后旧正式稿错误放行。
- 实现复杂度：低
- 优先级：P0

### 3. Prompt injection material does not affect system behavior

- 测试名称：`test_prompt_injection_material_is_treated_as_evidence_only`
- 测试层级：integration/golden quality
- 建议文件位置：new `tests/test_prompt_injection_materials.py` or extend `tests/test_golden_patent_cases.py`
- mock 策略：Fake LLM records prompts and returns deterministic draft; assertions inspect prompt boundaries and official export.
- 输入数据：`test_data/boundary_prompt_injection.md`
- 断言点：injection text may appear only as quoted material context; generated system behavior ignores it; official export contains no injected instruction phrases.
- 能防止什么回归：材料污染 prompt/system policy or official draft.
- 实现复杂度：中
- 优先级：P0

### 4. Official export content equals current official package

- 测试名称：`test_official_export_matches_current_official_package_hash`
- 测试层级：integration
- 建议文件位置：`tests/test_official_compile.py` or `tests/test_content_disposition.py`
- mock 策略：Fake LLM export-ready project; compare endpoint text/docx extracted text to current official package.
- 输入数据：simple and medium generated packages.
- 断言点：exported title/abstract/claims/description match official package; no stale package after source edit.
- 能防止什么回归：导出内容和页面/API 数据源不一致。
- 实现复杂度：中
- 优先级：P0

## P1

### 5. Overlong material filename is validated before filesystem write

- 测试名称：`test_material_upload_rejects_overlong_filename_without_500`
- 测试层级：integration
- 建议文件位置：`tests/test_projects_api_router.py` or `tests/test_disclosure.py`
- mock 策略：FastAPI `TestClient`, temp data dir, upload a Markdown file with a filename longer than the filesystem limit.
- 输入数据：synthetic Markdown bytes and a 260-character basename.
- 断言点：response status is 400/422, not 500; response detail tells user to rename the file; no material record is created.
- 能防止什么回归：超长文件名导致 opaque 500 and failed recovery guidance.
- 实现复杂度：低
- 优先级：P1

### 6. Golden quality gate has at least one enabled calibrated release case

- 测试名称：`test_golden_quality_gate_fails_release_mode_when_no_cases_enabled`
- 测试层级：unit/script
- 建议文件位置：`tests/test_golden_release_gate.py`
- mock 策略：Use temp golden case metadata or monkeypatch case loader to simulate zero enabled cases.
- 输入数据：one all-disabled case set and one calibrated enabled case set.
- 断言点：release-mode gate fails or emits a non-ignorable warning when `enabled_count=0`; enabled calibrated case enforces deterministic checks.
- 能防止什么回归：quality gate gives false confidence while skipping all patent-quality cases.
- 实现复杂度：中
- 优先级：P1

### 7. Multi-file upload partial success

- 测试名称：`test_batch_material_upload_partial_success_keeps_successful_materials`
- 测试层级：frontend/integration
- 建议文件位置：`frontend/src/materialUploadBatch.test.ts` plus backend integration test if API supports batch.
- mock 策略：Mock upload API returns mixed 200/415/422 results; backend TestClient for individual upload behavior.
- 输入数据：valid markdown, empty txt, unsupported xyz, corrupt docx.
- 断言点：successful material visible; failed materials show exact reason; next step remains available when enough material exists.
- 能防止什么回归：部分成功被整体失败吞掉。
- 实现复杂度：中
- 优先级：P1

### 8. Empty/incomplete material guides user instead of fabricating invention

- 测试名称：`test_incomplete_disclosure_blocks_or_guides_generation`
- 测试层级：integration/e2e
- 建议文件位置：`tests/test_disclosure.py`, `frontend/src/GuidedMaterialStatus.test.tsx`
- mock 策略：Fake LLM returns low-information extraction; component test checks guidance text and disabled state.
- 输入数据：`test_data/incomplete_disclosure.md`
- 断言点：missing technical problem/solution/effects surfaced; user sees next required info; no official export-ready status.
- 能防止什么回归：输入不足时假成功。
- 实现复杂度：中
- 优先级：P1

### 9. LLM timeout/malformed/rate-limit recovery

- 测试名称：`test_generation_runtime_failures_show_retryable_actionable_errors`
- 测试层级：integration/frontend
- 建议文件位置：`tests/test_runtime_controls.py`, `frontend/src/flow/runtimeWidgets.test.tsx`
- mock 策略：LLM/provider fake raises timeout, rate-limit-like runtime error, invalid JSON; no live provider.
- 输入数据：simple project.
- 断言点：status failed; failure detail redacted/actionable; retry endpoint available; draft unchanged.
- 能防止什么回归：loading 卡死、错误不可恢复、失败污染草稿。
- 实现复杂度：中
- 优先级：P1

### 10. Repeated submit does not duplicate irreversible tasks

- 测试名称：`test_duplicate_generate_and_review_submission_is_blocked_or_idempotent`
- 测试层级：integration/e2e
- 建议文件位置：`tests/test_runtime_controls.py`, `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`
- mock 策略：Slow fake runtime/provider; concurrent TestClient calls or UI double-click.
- 输入数据：export-eligible project before generation/review.
- 断言点：one active run max; second action disabled or returns 409; no duplicate exportable artifacts.
- 能防止什么回归：重复点击导致重复生成、状态错乱。
- 实现复杂度：高
- 优先级：P1

### 11. Repair session returns usable annotated editor data

- 测试名称：`test_repair_session_has_issues_sections_and_active_selection`
- 测试层级：integration/frontend
- 建议文件位置：`tests/test_post_draft_repair.py`, `frontend/src/PostDraftRepairEditor.test.tsx`
- mock 策略：Fake post-draft review returns blocking issues with anchors.
- 输入数据：reviewable draft package.
- 断言点：repair-session returns non-empty `issues` and non-empty draft `sections`; issue click updates highlighted section and inspector.
- 能防止什么回归：标注式修复编辑器空白或右栏不更新。
- 实现复杂度：中
- 优先级：P1

## P2

### 12. Claim numbering and dependent references

- 测试名称：`test_claim_numbering_and_references_are_valid`
- 测试层级：unit/integration
- 建议文件位置：`tests/golden_patent_evaluator.py`, `tests/test_golden_patent_cases.py`
- mock 策略：Pure parser/oracle; no LLM needed for evaluator.
- 输入数据：generated claims from golden cases.
- 断言点：numbers continuous; dependent claims reference existing earlier claim; multi-dependencies conform to product rules.
- 能防止什么回归：权利要求结构低级错误。
- 实现复杂度：低
- 优先级：P2

### 13. Specification section completeness

- 测试名称：`test_specification_required_sections_present`
- 测试层级：unit/integration
- 建议文件位置：`tests/golden_patent_evaluator.py`
- mock 策略：Pure text parser/oracle.
- 输入数据：generated descriptions from golden cases.
- 断言点：技术领域、背景技术、发明内容、附图说明、具体实施方式 present where expected.
- 能防止什么回归：说明书章节缺失。
- 实现复杂度：低
- 优先级：P2

### 14. Missing drawings do not create fake numbered drawings

- 测试名称：`test_no_drawing_input_does_not_fabricate_figure_numbers`
- 测试层级：integration
- 建议文件位置：`tests/test_generator.py` or `tests/test_official_compile.py`
- mock 策略：Fake LLM response for no-drawing case; official compile oracle.
- 输入数据：text-only simple invention with no figure disclosure.
- 断言点：drawing description is empty/generic with warning or user-editable placeholder; no unsupported `图1` in official export.
- 能防止什么回归：无附图时凭空生成虚假附图。
- 实现复杂度：中
- 优先级：P2

### 15. Conflict disclosure confirmation

- 测试名称：`test_conflicting_materials_require_user_confirmation`
- 测试层级：exploratory/integration
- 建议文件位置：new `tests/test_conflict_disclosure.py`
- mock 策略：Fake LLM returns conflict candidates; rule/oracle checks both alternatives preserved.
- 输入数据：`test_data/conflict_rules_model.md` and `test_data/conflict_neural_model.md`
- 断言点：system does not silently merge contradiction; user sees conflict and must confirm.
- 能防止什么回归：前后矛盾材料导致上下文错误。
- 实现复杂度：高
- 优先级：P2
- 当前覆盖：已新增 `tests/test_disclosure.py::test_disclosure_generation_preserves_conflicting_material_facts_in_prompts`，覆盖两份冲突材料不会被静默丢弃；仍缺少“必须用户确认权威路径”的产品级测试。

## P3

### 16. QA preflight fails on unmerged files and version drift

- 测试名称：`test_qa_preflight_source_identity_clean_enough`
- 测试层级：script/unit
- 建议文件位置：new `scripts/qa_preflight.py` and `tests/test_qa_preflight.py`
- mock 策略：temporary git fixture or subprocess abstraction.
- 输入数据：simulated clean tree, dirty tree, unmerged files, version mismatch.
- 断言点：unmerged files fail; dirty files are reported; versions are listed.
- 能防止什么回归：从错误分支、脏冲突或错误版本开始 QA/打包。
- 实现复杂度：低
- 优先级：P3
- 当前覆盖：已新增 `scripts/qa_preflight.py` 和 `tests/test_qa_preflight.py`；当前策略为 unmerged files 失败，dirty/version drift 报告但不失败。
