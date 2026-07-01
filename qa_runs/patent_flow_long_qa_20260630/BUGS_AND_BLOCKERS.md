# Bugs And Blockers

## Blockers

### BLOCKER-001: Current source worktree has unresolved merge/index conflicts in core API, UI, and tests

- 阻塞位置：Full long-flow QA against current source; release-grade backend, frontend, and Tauri evidence.
- 阻塞原因：`git diff --name-only --diff-filter=U` reports unmerged files in core backend API (`backend/app/main.py`), deliberation providers, frontend app/style files, README, and tests. AGENTS.md requires source identity clarity before testing/packaging; current source cannot be treated as a stable build target.
- 已尝试的命令或路径：
  - `git status --short --branch`
  - `git diff --name-only --diff-filter=U`
  - `rg -n "<<<<<<<|=======|>>>>>>>" ...` against known conflicted files
- 实际输出：
  - Unmerged files: `README.md`, `backend/app/deliberation/orchestrator.py`, `backend/app/deliberation/providers.py`, `backend/app/main.py`, `frontend/src/App.tsx`, `frontend/src/GuidedPatentFlowView.test.ts`, `frontend/src/flow/panels/InventionPointConfirmation.tsx`, `frontend/src/styles.css`, `tests/test_deliberation_api.py`, `tests/test_tauri_desktop_skeleton.py`.
  - No conflict markers were found in the checked files, but the index remains unmerged.
- 需要人工提供的信息或环境：A resolved worktree or explicit approval to resolve conflicts is required before release-grade full QA, browser screenshots, Tauri build evidence, or DMG evidence can be trusted. This QA run will not resolve conflicts because the goal forbids business-code changes.
- 可继续测试的替代路径：Run deterministic API TestClient journeys and targeted commands if imports work, recording all results as partial evidence from a dirty/unmerged worktree.
- 当前状态：stale/resolved on 2026-06-30 rebaseline at SHA `f566fc09`; `git diff --name-only --diff-filter=U` returned no files. See `CURRENT_STATE_REBASELINE.md`.

### BLOCKER-002: One-command `scripts/v1_smoke.sh` fails when stale generated sidecar directory exists

- 阻塞位置：Full one-command smoke gate at `ensure_tauri_resource_placeholders`.
- 阻塞原因：`scripts/v1_smoke.sh` expects `build/backend/patentagent-backend` to be absent, a file placeholder, or an empty legacy directory. Current local workspace has a non-empty generated PyInstaller sidecar directory at that path.
- 已尝试的命令或路径：
  - `PATENTAGENT_SKIP_INSTALL=1 PATENTAGENT_V1_1_REPORT_DIR=qa_runs/patent_flow_long_qa_20260630/artifacts/v1-smoke-report bash scripts/v1_smoke.sh`
  - `ls -la build/backend/patentagent-backend`
  - `sed -n '40,95p' scripts/v1_smoke.sh`
  - `sed -n '1,220p' src-tauri/tauri.conf.json`
- 实际输出：
  - The smoke script completed pytest, v1 API smoke, frontend tests, and frontend build, then failed with: `Tauri sidecar placeholder path is a non-empty directory: build/backend/patentagent-backend` and `Remove that generated build directory before running v1 smoke or packaging.`
  - The directory contains `_internal/` and executable `patentagent-backend`.
- 需要人工提供的信息或环境：Permission to clean/remove generated build artifacts, or a clean workspace where `build/backend/patentagent-backend` is absent. This QA run did not remove it because it is an existing generated artifact outside the requested QA files.
- 可继续测试的替代路径：Individual gates passed: `python3 -m pytest -q`, `scripts/v1_api_smoke.py`, `npm --prefix frontend test -- --run`, `npm --prefix frontend run build`, `cargo check`, and `cargo test`.
- 当前状态：fixed on 2026-06-30. `scripts/v1_smoke.sh` now accepts an existing generated sidecar directory and stages a directory-shaped placeholder for clean worktrees. Verification command `PYTHON=/usr/local/bin/python3 PATENTAGENT_SKIP_INSTALL=1 PATENTAGENT_SKIP_TAURI_SMOKE=1 PATENTAGENT_V1_1_REPEAT_COUNT=1 ... bash scripts/v1_smoke.sh` completed successfully and logged `Using existing Tauri sidecar resource directory`.

## Bugs

### BUG-001: Golden quality gate exits successfully while all golden patent cases are disabled/skipped

- 严重级别：P2
- 类型：测试缺口
- 用户画像：QA/release owner
- 流程阶段：质量门禁 / 发布前自动化
- 环境：Branch `codex/grantatlas-readme-branding`, SHA `449e451f`, dirty/unmerged worktree
- 前置条件：Current repo checkout with `tests/golden_patent_cases/*/case.json`
- 复现步骤：
  1. Run `python3 scripts/golden_quality_gate.py --report-path qa_runs/patent_flow_long_qa_20260630/artifacts/golden/golden-quality-gate.json`.
  2. Inspect command output or report.
- 实际结果：Command exits 0 with `"passed": true`, but reports `enabled_count=0`, `skipped_count=5`, `pending_calibration_count=5`, and every case status is `skipped` with reason `release_gate_disabled`.
- 预期结果：A release-quality golden gate should either have enabled release-blocking cases or clearly fail/warn when all cases are disabled so it cannot be mistaken for quality coverage.
- 是否稳定复现：Yes, reproduced once in this run.
- 影响范围：Patent text quality invariants such as claim feature coverage, spec support coverage, official cleanliness, and evidence honesty are not enforced by this gate in the current state.
- 可能根因：Golden cases are present but still pending human calibration and not enabled as release gates.
- 涉及文件/模块：`scripts/golden_quality_gate.py`, `tests/golden_patent_cases/*/case.json`
- 日志/命令输出摘要：`passed=true`, `case_count=5`, `enabled_count=0`, `skipped_count=5`, `release_gate_disabled`.
- 截图或输出路径，如有：`qa_runs/patent_flow_long_qa_20260630/artifacts/golden/golden-quality-gate.json`
- 推荐修复策略：Calibrate at least one golden case with approved official output fixtures and enable it as release-blocking, or make the script exit non-zero/emit strong warning when enabled_count is zero in release mode.
- 推荐回归测试：Add a unit test for `golden_quality_gate` behavior when all cases are disabled and when at least one calibrated case is enabled.
- 当前状态：fixed for release false-success path. `scripts/golden_quality_gate.py --strict` now exits non-zero with `no_release_gate_cases_enabled` when all golden cases are disabled, and CI invokes strict mode. Golden cases still need human calibration/enabling before the strict release gate can pass.

### BUG-002: Material upload with an overlong filename returns 500 instead of actionable validation error

- 严重级别：P2
- 类型：错误处理 / 文件异常
- 用户画像：用户 D：粗心/误操作用户；用户 E：边界/恶意输入用户
- 流程阶段：输入技术交底材料
- 环境：FastAPI TestClient, temp data dir, branch `codex/grantatlas-readme-branding`, SHA `449e451f`
- 前置条件：An existing project created through `POST /api/projects`.
- 复现步骤：
  1. Run `python3 qa_runs/patent_flow_long_qa_20260630/explore_material_uploads.py`.
  2. Inspect case with filename length 260 plus `.md`.
  3. Or upload a Markdown material to `/api/projects/{project_id}/materials` with a filename long enough to exceed filesystem filename limits after UUID prefixing.
- 实际结果：Upload returns status 500 with detail `Internal Server Error`.
- 预期结果：Upload should return a controlled 4xx response, such as 400/422, with an actionable message that the filename is too long and should be renamed.
- 是否稳定复现：Yes in TestClient exploration.
- 影响范围：Boundary file uploads can produce opaque server errors and may look like backend instability. The failed file is not persisted in material list, but the user receives no useful recovery instruction.
- 可能根因：`backend/app/api/projects.py` builds `stored_path = upload_dir / f"{uuid}-{safe_name}"` and opens it directly; filesystem `OSError: File name too long` is not caught and mapped to user-facing HTTPException.
- 涉及文件/模块：`backend/app/api/projects.py`, `backend/app/services/project_service.py`, `backend/app/disclosure/material_parser.py`
- 日志/命令输出摘要：`material-upload-exploration.json` case: status_code `500`, detail `Internal Server Error`, filename summarized as `aaaaaaaa...aaaaaaaa.md`.
- 截图或输出路径，如有：`qa_runs/patent_flow_long_qa_20260630/artifacts/material-upload-exploration.json`
- 推荐修复策略：Validate/sanitize upload filename length before writing; catch `OSError` around file write; return localized 4xx error. Keep stored filenames bounded while preserving original filename in metadata.
- 推荐回归测试：Add backend integration test that uploads a >255 character filename and asserts non-500 response and no material record.
- 当前状态：fixed. Uploading an overlong project material filename now returns 422 with `材料文件名过长，请缩短文件名后重新上传。`, creates no material record, and leaves no stored upload file.

## High-Risk Unconfirmed Issues

- HR-001: Material upload appears to lack explicit max-file-size and MIME/extension mismatch handling in the scanned upload path (`backend/app/api/projects.py`, `backend/app/services/project_service.py`, `backend/app/disclosure/material_parser.py`). Needs execution with boundary files before it can be logged as a bug.
- HR-002: Documentation version/context drift exists in the current unmerged README (`当前发布版本：v1.0.0`) versus package metadata (`pyproject.toml` and `frontend/package.json` version `1.1.0`). Because README is itself unmerged, this is recorded as ambiguity rather than a confirmed product doc bug.
