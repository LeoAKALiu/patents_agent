# patent_agent 长程 QA Run Log

## Source Identity

- Date: 2026-06-30
- Worktree path: `/Users/leo/Projects/patents_agent`
- Git top-level: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- Short SHA: `449e451f`
- Dirty state: dirty, with unresolved merge/index conflicts
- Unmerged files:
  - `README.md`
  - `backend/app/deliberation/orchestrator.py`
  - `backend/app/deliberation/providers.py`
  - `backend/app/main.py`
  - `frontend/src/App.tsx`
  - `frontend/src/GuidedPatentFlowView.test.ts`
  - `frontend/src/flow/panels/InventionPointConfirmation.tsx`
  - `frontend/src/styles.css`
  - `tests/test_deliberation_api.py`
  - `tests/test_tauri_desktop_skeleton.py`
- Test target: current source worktree, API TestClient when possible
- LLM mode preference: fake/cassette/deterministic only; no live provider required for this QA run
- Data directory preference: temp directories for automated API journeys; no production customer data

## Current Product Patent Drafting Flow

Text flow based on `README.md`, `docs/project-design-overview.md`, `docs/superpowers/specs/2026-06-02-guided-patent-flow-design.md`, and current source files under `frontend/src/` and `backend/app/`:

```text
Workbench start choice
  -> Create/select project
  -> Add idea, metadata, and optional materials
  -> Parse materials / external draft
  -> Generate or confirm invention point
  -> Multi-agent deliberation for invention projects
  -> Formula requirement check and formula run when required
  -> Generate draft package: title, abstract, claims, description, drawings
  -> Quality gates: filing readiness, claim defense, draft completion
  -> Official compile: clean official-only package and hash it
  -> Post-draft review: official package review and export decision
  -> Optional annotated repair session and repair patches
  -> Export official MD/DOCX and internal/risk sidecar artifacts
```

Utility model path:

```text
Workbench start choice: utility model
  -> Create project with patent_type=utility_model
  -> Structure-focused draft generation
  -> Skip or reduce invention-only deliberation/formula gates
  -> Same quality, official compile, post-draft review, export gates
```

Existing draft path:

```text
Workbench start choice: existing draft
  -> Create/select project
  -> Paste/upload existing draft
  -> Parse sections through external draft intake
  -> Confirm working draft
  -> Quality, official compile, post-draft review, repair/export
```

## Recognized Test Entrypoints

- Backend deterministic tests: `python3 -m pytest -q`
- Backend targeted tests: `python3 -m pytest tests/<file>.py -q`
- API release smoke: `python3 scripts/v1_api_smoke.py --repeat-count 2 --report-dir <dir>`
- Golden quality gate: `python3 scripts/golden_quality_gate.py --report-path <path>`
- Agent journey runner: `python3 tests/agent_journey_runner.py --journey all --output-dir <dir>`
- Frontend tests: `npm --prefix frontend test -- --run`
- Frontend build/typecheck: `npm --prefix frontend run build`
- Tauri Rust checks: `cargo check --manifest-path src-tauri/Cargo.toml`
- Tauri Rust tests: `cargo test --manifest-path src-tauri/Cargo.toml`
- Full local smoke: `bash scripts/v1_smoke.sh`
- DMG package/smoke, not run in this QA unless explicitly needed: `scripts/package_dmg.sh`

## Recognized Startup Commands

- Backend dev server:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- Frontend dev server:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

- Desktop dev:

```bash
npm --prefix frontend ci
npm exec --yes --package @tauri-apps/cli@^2 -- tauri dev
```

## Recognized Core State Objects

- `ProjectRecord`: project identity, idea/draft text, patent type, applicant/inventor/technical field metadata, current draft package.
- `ProjectMaterial`: uploaded material file, parsed text, status, warnings.
- `ExternalDraftSource` and `ExternalDraftIntakeRun`: existing draft source and parsed/confirmed working draft.
- `DisclosureRun` and `PatentPointCandidate`: invention point extraction, evidence state, prior-art differences, moat/support gaps.
- `DeliberationRun` and `PatentStrategyBrief`: multi-agent strategy and logs.
- `FormulaNeedAssessment` and `FormulaRun`: formula gate and formula package.
- `DraftPackage`: title, abstract, claims, description, drawing description, mermaid, image prompt, review findings.
- `FilingReadinessReport`, `ClaimDefenseWorksheet`, `DraftCompletionRun`: quality gates tied to source draft hash/package hash.
- `OfficialCompileRun` and `OfficialDraftPackage`: cleaned official package, contamination removal, source and official hashes.
- `PostDraftReviewRun`: official review, blocking issues, export decision, safe patches.
- `PostDraftRepairSession` and `DraftRepairPatch`: annotated repair issue list, section anchors, patch application.
- Export readiness gates: quality, official compile, post-draft review, and hash freshness.

## Top 10 Current Risks

1. Current worktree has unresolved conflicts in backend, frontend, README, and tests; full-flow evidence cannot be treated as release evidence until resolved.
2. `backend/app/main.py` is both a conflicted file and the central long-flow API module, so import/runtime failures may block all API journeys.
3. `frontend/src/App.tsx` and `frontend/src/styles.css` are conflicted, so any UI test or screenshot from the dev server may be unreliable.
4. `tests/test_deliberation_api.py` and `tests/test_tauri_desktop_skeleton.py` are conflicted, so full pytest and Tauri test gates may fail before reaching product behavior.
5. Material upload accepts supported extensions and parses content, but current scanned code shows no explicit max-size, duplicate-name, or MIME/extension mismatch handling.
6. Multi-agent deliberation and post-draft review rely on provider availability outside fake/TestClient runs; live-provider UX remains high risk without installed provider validation.
7. Official export depends on multiple hash gates; stale quality/compile/review state must be tested after user edits, refresh, and two-tab conflicts.
8. Repair editor correctness requires API-level `repair-session` data, not DOM-only evidence; blank middle/inspector panes are a known regression class.
9. Existing docs contain version/context drift (`README.md` says current release `v1.0.0`, package metadata is `1.1.0`), increasing environment confusion.
10. Full browser/Tauri user-flow proof may be blocked by current conflicts even if headless deterministic API journeys can run.

## Round 1 - Repository Understanding And QA Setup

- Goal: identify current source identity, flow, commands, test entrypoints, and initial blockers before running tests.
- Actions:
  - Ran AGENTS.md source identity checklist.
  - Read `QA_GOAL.md`.
  - Read `README.md`, `docs/project-design-overview.md`, `docs/qa/ai-scenario-testing-pipeline.md`, `docs/superpowers/specs/2026-06-02-guided-patent-flow-design.md`, and `docs/superpowers/specs/2026-06-28-agent-automation-testing-architecture-design.md`.
  - Scanned `pyproject.toml`, root `package.json`, `frontend/package.json`, `.github/workflows/ci.yml`, `scripts/v1_smoke.sh`, `scripts/v1_api_smoke.py`, `tests/agent_journey_runner.py`, and `tests/flow_driver.py`.
  - Scanned core backend/frontend files for routes, material upload, LLM config, and guided flow state.
- Observations:
  - Current source is dirty and unmerged.
  - There is an existing deterministic journey runner for three high-value API paths using fake LLM and temp data.
  - Backend and frontend test commands are identifiable from CI and README.
  - Full UI verification should wait until conflicts are resolved; API TestClient journeys may still provide useful partial evidence if imports work.
- Findings:
  - `BLOCKER-001` opened for unresolved merge/index conflicts in core source and test files.
  - `FRICTION-001` opened for source/version/documentation ambiguity.
- Next plan:
  - Create QA matrix, test data, command log, blockers/friction ledger, and automation recommendations.
  - Run safe environment/version probes.
  - Attempt deterministic API journey runner first because it is closest to the requested three path coverage and does not require live LLM.

## Round 2 - Deterministic User Journeys And Regression Gates

- Goal: execute the highest-value automated paths available without live provider credentials.
- Actions:
  - Ran environment probes for Python, Node, npm, cargo, and Python test dependency imports.
  - Ran `python3 tests/agent_journey_runner.py --journey all --output-dir qa_runs/patent_flow_long_qa_20260630/artifacts/agent-journeys`.
  - Ran `python3 scripts/v1_api_smoke.py --repeat-count 2 --report-dir qa_runs/patent_flow_long_qa_20260630/artifacts/v1-api-smoke`.
  - Ran `python3 scripts/golden_quality_gate.py --report-path qa_runs/patent_flow_long_qa_20260630/artifacts/golden/golden-quality-gate.json`.
  - Ran `python3 -m pytest -q`.
  - Ran `npm --prefix frontend test -- --run`.
  - Ran `npm --prefix frontend run build`.
  - Ran `cargo check --manifest-path src-tauri/Cargo.toml`.
  - Ran `cargo test --manifest-path src-tauri/Cargo.toml`.
  - Ran one-command smoke: `PATENTAGENT_SKIP_INSTALL=1 PATENTAGENT_V1_1_REPORT_DIR=qa_runs/patent_flow_long_qa_20260630/artifacts/v1-smoke-report bash scripts/v1_smoke.sh`.
- Observations:
  - Three API journeys passed: `invention_from_idea`, `utility_model_from_structure`, and `polish_existing_draft`.
  - Each journey reported current quality, official compile, and post-draft review gates and a successful official export check.
  - `v1_api_smoke.py` passed for 5 workflow categories repeated twice.
  - `python3 -m pytest -q` passed: 878 tests.
  - Frontend Vitest passed: 39 files, 260 tests.
  - Frontend build passed.
  - Tauri `cargo check` and `cargo test` passed.
  - `scripts/v1_smoke.sh` failed only after the same pytest/API/frontend/build stages passed, at its Tauri sidecar placeholder preflight.
- Findings:
  - `BUG-001`: golden quality gate exits success while all 5 golden patent cases are skipped/disabled.
  - `BLOCKER-002`: one-command v1 smoke blocked by non-empty generated `build/backend/patentagent-backend` directory.
- Next plan:
  - Explore material upload and incomplete-input paths with TestClient scripts and synthetic QA data.
  - Update matrix execution status and final risk judgment.
- Stop-condition status:
  - Main flow identified: yes.
  - Test matrix generated: yes.
  - Three complete/near-complete user paths attempted: yes, API layer passed.
  - Major commands executed: mostly yes; one-command smoke has environment/build-artifact blocker.

## Round 3 - Boundary, Incomplete Input, And Recovery Exploration

- Goal: cover incomplete materials, file anomalies, and recovery/error message behavior beyond happy-path journeys.
- Actions:
  - Added `qa_runs/patent_flow_long_qa_20260630/explore_material_uploads.py`.
  - Ran material upload exploration with valid Markdown, duplicate filename, empty TXT, unsupported `.xyz`, corrupt DOCX, prompt-injection Markdown, and overlong filename.
  - Added `qa_runs/patent_flow_long_qa_20260630/explore_incomplete_flow.py`.
  - Ran incomplete flow exploration with empty idea, short marketing-only idea, incomplete Markdown disclosure, export readiness before draft, generation before usable setup, and official export before draft.
- Observations:
  - Valid Markdown uploads are processed.
  - Empty TXT returns 422 with clear localized message.
  - Unsupported `.xyz` returns 415 with supported-format guidance.
  - Corrupt DOCX returns 422 with clear localized message.
  - Prompt-injection Markdown uploads as normal material; downstream generation contamination was not executed in this round.
  - Duplicate filename/content uploads both succeed and appear as separate material records with identical visible name.
  - Overlong filename upload returns 500 Internal Server Error.
  - Empty and short marketing-only project ideas are accepted by the API; incomplete disclosure upload is processed without warning.
  - Export before draft is blocked with `Generate a draft before export.`
  - Generation in the no-key environment returns 503 with `LLM is not configured. Set DEEPSEEK_API_KEY before generating drafts.`
- Findings:
  - `BUG-002`: overlong material filename returns 500 instead of controlled 4xx.
  - `FRICTION-003`: empty/short ideas can create projects without immediate missing-disclosure guidance.
  - `FRICTION-004`: duplicate material filenames are accepted without visible disambiguation.
- Next plan:
  - Finalize matrix statuses, automation recommendations, and release risk judgment.
  - Do not start browser/Tauri UI proof in this dirty/unmerged worktree; record as remaining risk.
- Stop-condition status:
  - Happy path: covered at API layer.
  - Incomplete material path: covered at API/upload/gate layer.
  - Abnormal/recovery path: covered for file errors, no-key generation, official export before draft, and hash drift in journey runner.

## Round 4 - Debug Task 1 Rebaseline And Task 2/3/4 Implementation Start

- Goal: execute `DEBUG_TASK_BREAKDOWN.md` Task 1, then start Task 2/3/4 fixes.
- Actions:
  - Re-ran AGENTS.md source identity checklist.
  - Created `CURRENT_STATE_REBASELINE.md`.
  - Confirmed `git diff --name-only --diff-filter=U` is empty at SHA `f566fc09`.
  - Fixed `BUG-002`, `BUG-001`, and `BLOCKER-002` with targeted regression tests.
  - Ran targeted pytest for project uploads, golden release gate, and Tauri smoke script policy.
  - Re-ran material upload exploration.
  - Ran a controlled `v1_smoke.sh` variant with Tauri checks skipped but Tauri resource preflight enabled.
- Observations:
  - `BLOCKER-001` is stale/resolved for the current checkout; the previous unresolved index state was tied to earlier SHA `449e451f`.
  - Current dirty state before implementation was untracked QA artifacts plus two Playwright output screenshots.
  - UI/Tauri current-source evidence can proceed after targeted command verification.
  - Targeted tests passed: `41 passed`.
  - Full backend pytest inside the smoke variant passed: `880 passed`.
  - Frontend Vitest and frontend build inside the smoke variant passed.
  - Material upload exploration now reports overlong filename as 422 with `材料文件名过长，请缩短文件名后重新上传。`
  - `golden_quality_gate.py --strict` now exits 1 with `no_release_gate_cases_enabled`, which is the intended release-mode behavior until at least one golden case is calibrated and enabled.
  - `v1_smoke.sh` no longer fails on an existing non-empty PyInstaller sidecar directory; it logs `Using existing Tauri sidecar resource directory`.
- Findings:
  - No current merge/index conflict blocker remains.
  - `BUG-002` fixed.
  - `BUG-001` false-success path fixed in strict/release mode; golden case calibration remains required.
  - `BLOCKER-002` fixed for the sidecar resource preflight path.
- Next plan:
  - Continue with browser/Tauri current-source evidence tasks if requested.
  - Calibrate and enable at least one golden patent case before treating strict release gate as passable.

## Round 5 - Browser Guided Flow And Annotated Repair Evidence

- Goal: complete `DEBUG_TASK_BREAKDOWN.md` Task 5 and Task 6 evidence for current React UI and repair-session data flow.
- Actions:
  - Read Playwright skill instructions and used the CLI wrapper.
  - Confirmed existing user dev servers were already listening on `8000` and `5174`; did not kill them.
  - Started isolated QA backend on `8001` using `browser_evidence_backend.py` with fake LLM responses.
  - Started isolated QA Vite server on `5175` using `vite.browser-smoke.config.ts` proxying `/api` to `8001`.
  - Ran `seed_browser_repair_project.py` to create a deterministic project, upload material, generate a draft, compile official draft, run post-draft review, and fetch repair-session/export-readiness payloads.
  - Used Playwright CLI to open the real React app, select the seeded project through persisted app state, and capture screenshots/snapshots for workbench, document overview, annotated repair, issue selection, and export gate.
  - Ran targeted repair tests: backend `tests/test_post_draft_repair.py`, frontend `PostDraftRepairEditor` and `DocumentRepairWorkspace`.
- Observations:
  - Workbench loaded the seeded project and displayed `处理成稿会审阻断项`, `导出锁定`, 2 blocking items, and 5 risk items.
  - Document overview displayed the gate chain and issue summary.
  - Repair-session API returned 9 issues, 5 sections, and `stale=false`.
  - Embedded annotated repair editor displayed the left issue queue, middle draft sections, and right inspector.
  - Clicking the claims issue updated the active issue and inspector from `标题` to `权利要求书`.
  - Export workspace showed official export locked and separated official submission, internal review materials, and risk trace sections.
- Findings:
  - `FRICTION-005` opened for next-action priority inconsistency: workbench points to post-draft repair while export readiness/export page points first to missing quality checks.
- Artifact directory:
  - `current-artifacts/browser-smoke-current/`
- Next plan:
  - Stop the isolated QA dev servers and browser session.
  - Continue with Tasks 7-9 if requested: prompt-injection/conflict coverage, input guidance, and QA preflight.

## Round 6 - Prompt/Conflict Coverage, Input Guidance, And QA Preflight

- Goal: complete `DEBUG_TASK_BREAKDOWN.md` Tasks 7, 8, and 9.
- Actions:
  - Re-ran AGENTS.md source identity checklist on branch `codex/grantatlas-readme-branding`, SHA `f566fc09`; no unmerged files were reported.
  - Added disclosure generator regression tests for prompt-injection material boundaries and conflicting material preservation.
  - Added frontend guidance for very short or marketing-only idea input in `IdeaIntakePanel`.
  - Added duplicate material filename warning in `MaterialSummary`.
  - Added `scripts/qa_preflight.py` to print worktree identity, branch, short SHA, dirty summary, unmerged files, and Python/frontend/Tauri version metadata.
  - Added `tests/test_qa_preflight.py`.
  - Ran targeted Python tests, targeted frontend tests, `qa_preflight.py --json`, a wider related Python test set, and frontend production build.
- Observations:
  - Prompt-injection text remains in LLM user prompts as uploaded material context and does not enter system prompts in the fake-LLM pipeline.
  - Conflicting rule-model and neural-network material facts are both preserved in scan, patent-point, and disclosure-body prompts.
  - The UI now warns before project creation when the idea is too short or reads as pure business/marketing value.
  - The material summary now warns when the same visible file name appears more than once.
  - `qa_preflight.py --json` exits 0 in the current dirty-but-not-conflicted worktree and reports all release metadata versions as `1.1.0`.
- Findings:
  - No new P0/P1 bug was found in this round.
  - Conflict confirmation remains a product gap beyond the new prompt-preservation coverage; the system still does not require the user to choose the authoritative model path.
  - API-level empty/short idea handling remains permissive; this round adds frontend guidance, not API blocking.
- Verification:
  - `/usr/local/bin/python3 -m pytest tests/test_disclosure.py::test_disclosure_generation_keeps_prompt_injection_material_as_user_context_only tests/test_disclosure.py::test_disclosure_generation_preserves_conflicting_material_facts_in_prompts tests/test_qa_preflight.py -q` -> `5 passed`.
  - `npm --prefix frontend test -- MaterialSummary IdeaIntakePanel --run` -> 2 files, 3 tests passed.
  - `/usr/local/bin/python3 scripts/qa_preflight.py --json` -> exit 0; dirty tree reported; no unmerged files.
  - `/usr/local/bin/python3 -m pytest tests/test_disclosure.py tests/test_qa_preflight.py tests/test_projects_api_router.py tests/test_golden_release_gate.py tests/test_tauri_desktop_skeleton.py -q` -> `60 passed`.
  - `npm --prefix frontend run build` -> TypeScript and Vite build passed.
- Stop-condition status:
  - Tasks 1-9 are now complete for the current follow-up scope.
  - Remaining high-value work is product behavior, not QA infrastructure: explicit conflict confirmation and unified next-action precedence.
