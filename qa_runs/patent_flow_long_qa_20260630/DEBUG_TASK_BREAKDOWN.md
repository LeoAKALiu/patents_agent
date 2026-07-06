# Debug Task Breakdown

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- Short SHA at breakdown time: `f566fc09`
- Current unmerged files: none
- Dirty scope: untracked `qa_runs/` and two `output/playwright/*.png` files

## Breakdown Notes

This file turns `DEBUG_PLAN.md` into independently grabbable task cards. It is planning-only: no business code was changed while creating this breakdown.

No issue tracker configuration or triage labels were provided, so these are issue-ready cards rather than published tickets.

## Implementation Status

- Task 1: completed on current checkout; `BLOCKER-001` is stale/resolved at SHA `f566fc09`.
- Task 2: completed; overlong material filename uploads now return 422 and are covered by regression tests.
- Task 3: completed for release false-success behavior; strict mode and CI now fail when zero golden cases are enabled.
- Task 4: completed for sidecar resource preflight; `v1_smoke.sh` accepts existing generated sidecar directories.
- Task 5: completed for current React workbench/document/export browser evidence using isolated QA backend/frontend servers.
- Task 6: completed for repair-session API evidence and annotated repair editor UI evidence.
- Task 7: completed for prompt-boundary and conflicting-disclosure preservation regression coverage.
- Task 8: completed for frontend short/marketing-only idea guidance and duplicate material filename warning.
- Task 9: completed with `scripts/qa_preflight.py` and regression tests.

## Proposed Order

1. Rebaseline current QA state and stale blocker status.
2. Fix the clearest runtime bug: overlong material filename returns 500.
3. Repair release confidence gaps: golden quality gate and one-command smoke policy.
4. Add user-facing evidence: browser/Tauri flow proof and repair editor proof.
5. Add remaining robustness coverage: prompt injection, conflicting disclosures, input guidance, duplicate materials.

---

## Task 1: Rebaseline Current QA State And Close Stale Conflict Blocker

**Blocked by:** None - can start immediately

**User stories covered:**

- QA/release owner can trust which branch/SHA and worktree state a debug run refers to.
- Future UI/Tauri verification is not blocked by stale conflict evidence from an earlier SHA.

**What to build**

Create a current-state QA addendum that reruns the source identity checklist, confirms whether `BLOCKER-001` is stale, and records whether UI/Tauri verification can proceed from current source. This is a docs/QA task only.

**Suggested files**

- Modify: `qa_runs/patent_flow_long_qa_20260630/RUN_LOG.md`
- Modify: `qa_runs/patent_flow_long_qa_20260630/BUGS_AND_BLOCKERS.md`
- Modify: `qa_runs/patent_flow_long_qa_20260630/FINAL_REPORT.md`
- Optional create: `qa_runs/patent_flow_long_qa_20260630/CURRENT_STATE_REBASELINE.md`

**Acceptance criteria**

- [ ] Records fresh output for:
  - `pwd`
  - `git status --short --branch`
  - `git rev-parse --show-toplevel`
  - `git branch --show-current`
  - `git rev-parse --short HEAD`
  - `git diff --name-only --diff-filter=U`
- [ ] States clearly whether `BLOCKER-001` is still active, stale, or replaced by a new current-state blocker.
- [ ] If no unmerged files remain, identifies next eligible UI/Tauri verification command or reason not to run it.
- [ ] Does not edit business source.

**Verification commands**

```bash
git diff --name-only --diff-filter=U
rg -n "<<<<<<<|=======|>>>>>>>" README.md backend/app/main.py frontend/src/App.tsx frontend/src/styles.css tests/test_deliberation_api.py tests/test_tauri_desktop_skeleton.py
```

Expected: no unmerged files; no conflict markers in previously conflicted files.

---

## Task 2: Fix Material Upload Overlong Filename 500

**Blocked by:** Task 1 recommended, but not strictly required

**User stories covered:**

- Boundary-input user receives a recoverable error instead of `Internal Server Error`.
- Enterprise user can keep using the project after a bad upload attempt.

**What to build**

Make `/api/projects/{project_id}/materials` reject overlong filenames before or during filesystem write with a controlled localized 4xx response. Preserve successful upload behavior for valid, duplicate, non-ASCII, empty, unsupported, and corrupt files.

**Suggested files**

- Modify: `backend/app/api/projects.py`
- Modify or reuse: `backend/app/services/project_service.py`
- Test: `tests/test_projects_api_router.py`
- QA artifact reference: `qa_runs/patent_flow_long_qa_20260630/artifacts/material-upload-exploration.json`

**Acceptance criteria**

- [ ] Uploading a filename longer than the filesystem component limit returns 400 or 422, never 500.
- [ ] Error detail tells the user to shorten/rename the file.
- [ ] No `ProjectMaterial` row is created for the failed upload.
- [ ] No partial stored file remains in the project material directory.
- [ ] Existing cases still behave as recorded:
  - valid Markdown: 200 processed
  - empty TXT: 422
  - unsupported `.xyz`: 415
  - corrupt DOCX: 422
  - non-ASCII Markdown filename: 200 processed

**Verification commands**

```bash
python3 qa_runs/patent_flow_long_qa_20260630/explore_material_uploads.py
python3 -m pytest tests/test_projects_api_router.py -q
python3 -m pytest -q
```

Expected: exploration no longer reports a 500 for the long filename; targeted and full backend tests pass.

---

## Task 3: Make Golden Quality Gate Honest When No Cases Are Enabled

**Blocked by:** Task 1 recommended; policy decision required before implementation

**User stories covered:**

- QA/release owner can distinguish "quality checks passed" from "all quality cases skipped."
- Release pipeline cannot silently treat zero enabled golden cases as meaningful patent quality coverage.

**What to build**

Define and implement release-mode behavior for `scripts/golden_quality_gate.py` when `enabled_count == 0`. The likely behavior is: calibration/report mode may exit 0, but release/strict mode must fail or emit a non-ignorable result that CI/release gates can enforce.

**Suggested files**

- Modify: `scripts/golden_quality_gate.py`
- Test: `tests/test_golden_release_gate.py`
- Possibly modify CI after policy: `.github/workflows/ci.yml`
- Reference data: `tests/golden_patent_cases/*/case.json`

**Acceptance criteria**

- [ ] The gate exposes an explicit release/strict behavior for zero enabled cases.
- [ ] A test proves zero enabled cases is not mistaken for release quality coverage.
- [ ] Existing calibration queue reporting remains available for pending human review cases.
- [ ] The generated JSON/Markdown report clearly states enabled/skipped/pending counts.
- [ ] CI/release command choice is documented.

**Verification commands**

```bash
python3 scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate.json
python3 -m pytest tests/test_golden_release_gate.py -q
```

Expected depends on chosen policy, but release-mode zero-enabled behavior must be enforced by test.

---

## Task 4: Decide And Implement v1 Smoke Sidecar Artifact Policy

**Blocked by:** Task 1 recommended; policy decision required before implementation

**User stories covered:**

- Release owner can run a single smoke command without being surprised by stale generated artifacts.
- Developer gets a deterministic cleanup/retry path when local sidecar output already exists.

**What to build**

Classify `build/backend/patentagent-backend` non-empty directory behavior as either an expected clean-worktree precondition or a script robustness bug. Then update `scripts/v1_smoke.sh`, tests, and/or docs to enforce the chosen behavior.

**Suggested files**

- Modify: `scripts/v1_smoke.sh`
- Test: `tests/test_v1_smoke_script.py`
- Reference: `scripts/build_backend_sidecar.sh`
- Reference: `src-tauri/tauri.conf.json`
- Optional docs update: `qa_runs/patent_flow_long_qa_20260630/BUGS_AND_BLOCKERS.md`

**Acceptance criteria**

- [ ] Existing non-empty `build/backend/patentagent-backend` directory behavior is explicitly documented.
- [ ] If tolerated, `v1_smoke.sh` does not fail merely because a valid generated sidecar directory exists.
- [ ] If rejected, failure message includes exact cleanup command and is tested.
- [ ] `cargo check` and `cargo test` still run successfully in the supported path.
- [ ] Full one-command smoke succeeds in a supported environment or fails only for documented external reasons.

**Verification commands**

```bash
ls -la build/backend/patentagent-backend
PATENTAGENT_SKIP_INSTALL=1 bash scripts/v1_smoke.sh
python3 -m pytest tests/test_v1_smoke_script.py -q
```

Expected: behavior matches policy and is covered by tests.

---

## Task 5: Produce Current Browser Guided-Flow Evidence

**Blocked by:** Task 1

**User stories covered:**

- First-time inventor can see the workbench path and next action.
- Patent attorney can see quality/export status without relying only on API reports.
- QA/release owner has screenshot-backed evidence tied to current SHA.

**What to build**

Run a current-source browser smoke against React/Vite and FastAPI using deterministic or temporary data. Capture screenshots/page text for workbench, project selection, export gate status, and at least one blocked/empty state.

**Suggested files**

- Create artifacts under: `qa_runs/patent_flow_long_qa_20260630/artifacts/browser-smoke-current/`
- Optional script: `qa_runs/patent_flow_long_qa_20260630/browser_guided_flow_smoke.py` or Playwright script under the QA run directory
- Modify docs: `qa_runs/patent_flow_long_qa_20260630/RUN_LOG.md`
- Modify docs: `qa_runs/patent_flow_long_qa_20260630/FINAL_REPORT.md`

**Acceptance criteria**

- [ ] Records current branch/SHA and dev server URLs.
- [ ] Screenshots show real React UI, not docs or static artifacts.
- [ ] Workbench start path is visible.
- [ ] Current project selection/status is visible.
- [ ] Export gate state is visible and matches API state.
- [ ] Any failed/blocked UI state has a user-actionable message.

**Verification commands**

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

Then run the chosen Playwright/browser script. Expected: screenshots and page text saved under the QA artifact directory.

---

## Task 6: Prove Annotated Repair Editor Data Flow

**Blocked by:** Task 1, Task 5 recommended

**User stories covered:**

- Patent attorney can open a repairable post-draft review and see issues, draft sections, and the inspector.
- QA can reject DOM-only proof and verify the actual repair-session API payload.

**What to build**

Create deterministic data for a repairable post-draft review, verify `repair-session` returns non-empty issues and draft sections, then capture UI evidence that issue selection updates the highlighted section and inspector.

**Suggested files**

- Existing tests: `tests/test_post_draft_repair.py`
- Existing frontend tests: `frontend/src/PostDraftRepairEditor.test.tsx`
- Artifact directory: `qa_runs/patent_flow_long_qa_20260630/artifacts/repair-editor-current/`
- Optional QA script in run directory

**Acceptance criteria**

- [ ] API evidence includes `GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session`.
- [ ] API payload has non-empty `issues`.
- [ ] API payload has non-empty draft `sections`.
- [ ] UI screenshot shows issue rail, middle draft sections, and right inspector.
- [ ] Clicking an issue updates selected/highlighted section and inspector content.
- [ ] Long issue list scrolls inside its pane if applicable.

**Verification commands**

```bash
python3 -m pytest tests/test_post_draft_repair.py -q
npm --prefix frontend test -- PostDraftRepairEditor --run
```

Expected: targeted tests pass and artifact evidence exists.

---

## Task 7: Add Prompt Injection And Conflicting Disclosure Coverage

**Blocked by:** Task 1

**User stories covered:**

- Boundary/malicious input user cannot inject instructions through materials.
- Enterprise R&D user with contradictory materials gets a confirmation path rather than silent context corruption.

**What to build**

Add deterministic tests around uploaded material containing prompt injection and conflicting disclosure materials. The tests should prove material content remains bounded as evidence and that contradictory technical facts are preserved or surfaced instead of silently merged.

**Suggested files**

- Test data: `qa_runs/patent_flow_long_qa_20260630/test_data/boundary_prompt_injection.md`
- Test data: `qa_runs/patent_flow_long_qa_20260630/test_data/conflict_rules_model.md`
- Test data: `qa_runs/patent_flow_long_qa_20260630/test_data/conflict_neural_model.md`
- Candidate test: `tests/test_prompt_injection_materials.py`
- Candidate test: `tests/test_conflict_disclosure.py`

**Acceptance criteria**

- [ ] Prompt injection phrases in uploaded material do not appear as instructions in official export.
- [ ] Fake LLM prompt boundary assertions prove malicious text is treated as quoted/material context.
- [ ] Conflict A/B test verifies both rule-model and neural-model facts remain distinguishable.
- [ ] If product currently lacks conflict confirmation, the test documents the gap without inventing a false pass.

**Verification commands**

```bash
python3 -m pytest tests/test_prompt_injection_materials.py tests/test_conflict_disclosure.py -q
```

Expected: tests either pass after product support or fail first as documented regression targets.

**Current result**

- Implemented in `tests/test_disclosure.py`.
- Verified prompt-injection text stays in fake-LLM user prompts as material context and does not enter system prompts.
- Verified conflicting rule-model and neural-network facts remain distinguishable in scan, patent-point, and body prompts.
- Product still lacks explicit user confirmation for conflicting technical facts; keep automation recommendation `test_conflicting_materials_require_user_confirmation` open.

---

## Task 8: Improve Empty/Short Idea And Duplicate Material Guidance

**Blocked by:** Task 1; Task 2 recommended for shared upload behavior

**User stories covered:**

- First-time inventor gets actionable guidance when the idea lacks technical substance.
- Careless user can understand duplicate material uploads.

**What to build**

Decide whether guidance belongs in API warning metadata, frontend derived validation, or both. Then add tests and UI/API behavior so empty/short marketing-only ideas and duplicate materials do not look like fully ready patent drafting inputs.

**Suggested files**

- Inspect/modify if approved: `frontend/src/flow/panels/IdeaIntakePanel.tsx`
- Inspect/modify if approved: `frontend/src/flow/panels/MaterialSummary.tsx`
- Inspect/modify if approved: `backend/app/api/projects.py`
- Inspect/modify if approved: `backend/app/services/project_service.py`
- Test candidates:
  - `frontend/src/GuidedMaterialStatus.test.tsx`
  - `frontend/src/flow/panels/MaterialSummary.test.tsx`
  - `tests/test_projects_api_router.py`

**Acceptance criteria**

- [ ] Empty idea either blocks start or clearly saves as incomplete draft with missing-info guidance.
- [ ] Very short marketing-only idea shows guidance for technical problem, solution, effects, and embodiment.
- [ ] Duplicate filename/content upload is surfaced with visible disambiguation or warning.
- [ ] Existing successful upload behavior remains unchanged.
- [ ] UX copy is understandable for non-patent users and precise enough for patent professionals.

**Verification commands**

```bash
npm --prefix frontend test -- GuidedMaterialStatus MaterialSummary --run
python3 -m pytest tests/test_projects_api_router.py -q
```

Expected: targeted frontend/backend tests pass with chosen behavior.

**Current result**

- Implemented frontend-derived guidance in `frontend/src/flow/panels/IdeaIntakePanel.tsx`.
- Implemented duplicate filename warning in `frontend/src/flow/panels/MaterialSummary.tsx`.
- Added `frontend/src/flow/panels/IdeaIntakePanel.test.tsx` and extended `frontend/src/flow/panels/MaterialSummary.test.tsx`.
- API behavior remains permissive for saving incomplete ideas; the UI now surfaces missing technical substance before creation.

---

## Task 9: Add QA Preflight For Source Identity And Version Drift

**Blocked by:** None - can start immediately

**User stories covered:**

- QA/release owner cannot accidentally run release evidence from a wrong branch, unmerged index, or stale version docs.
- Future debug and packaging runs begin with objective source identity.

**What to build**

Create a lightweight QA preflight command that records source identity and fails on unmerged files. Optionally report version drift across `pyproject.toml`, `frontend/package.json`, `src-tauri/tauri.conf.json`, and README release text without failing until policy is agreed.

**Suggested files**

- Create: `scripts/qa_preflight.py`
- Test: `tests/test_qa_preflight.py`
- Optional docs: `docs/qa/ai-scenario-testing-pipeline.md`

**Acceptance criteria**

- [ ] Prints worktree path, top-level, branch, short SHA, and dirty summary.
- [ ] Fails when `git diff --name-only --diff-filter=U` is non-empty.
- [ ] Reports version values from Python, frontend, and Tauri metadata.
- [ ] Does not require live provider credentials.
- [ ] Test covers clean, dirty, and unmerged simulated states.

**Verification commands**

```bash
python3 scripts/qa_preflight.py
python3 -m pytest tests/test_qa_preflight.py -q
```

Expected: current source reports no unmerged files; tests pass.

**Current result**

- Implemented `scripts/qa_preflight.py`.
- Added `tests/test_qa_preflight.py`.
- Current run reports branch `codex/grantatlas-readme-branding`, SHA `f566fc09`, dirty entries, no unmerged files, and version metadata `1.1.0` across Python, frontend, and Tauri.

---

## Approval Questions

Before publishing these to an issue tracker or dispatching implementation agents:

1. Does this granularity look right, or should Task 5/6 UI evidence be merged?
2. Should `BUG-001` be fixed by adding strict release mode, or by calibrating/enabling at least one golden case first?
3. Should `BLOCKER-002` tolerate existing generated sidecar directories, or intentionally require a clean build directory?
