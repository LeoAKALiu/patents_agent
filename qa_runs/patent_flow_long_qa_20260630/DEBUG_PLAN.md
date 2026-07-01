# Debug Plan Based On Long QA Documents

## Source Identity

- Date: 2026-06-30
- Worktree: `/Users/leo/Projects/patents_agent`
- Git top-level: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- Current short SHA: `f566fc09`
- Current unmerged files: none from `git diff --name-only --diff-filter=U`
- Dirty scope observed now: untracked `qa_runs/` and two `output/playwright/*.png` files
- Active `.planning/debug/*.md` sessions: none found

Note: the original QA report recorded `BLOCKER-001` against SHA `449e451f` with unresolved index conflicts. Current source state no longer shows unmerged files, so the first debug step is to reclassify that blocker against current evidence rather than assuming it still applies.

## Debug Objective

Convert the QA findings into a sequenced, evidence-first debug plan. This plan does not modify business code. Each item below is a candidate debug session with symptoms, evidence, current hypothesis, diagnostics, and exit criteria.

## Priority Order

1. `BUG-002`: material upload with overlong filename returns 500.
2. `BUG-001`: golden quality gate exits success while all golden cases are disabled/skipped.
3. `BLOCKER-002`: one-command `scripts/v1_smoke.sh` fails on non-empty generated sidecar directory.
4. `BLOCKER-001`: stale source-conflict blocker needs current-state revalidation.
5. UI/Tauri evidence gap: browser/Tauri guided flow and repair editor not yet proven.
6. Input guidance frictions: empty/short ideas and duplicate filenames.

## Session A - BUG-002 Overlong Material Filename 500

### Symptom

Uploading a Markdown material with an overlong filename returns HTTP 500 `Internal Server Error`.

### Evidence

- Artifact: `qa_runs/patent_flow_long_qa_20260630/artifacts/material-upload-exploration.json`
- Case: 260-character basename plus `.md`
- Actual: `status_code=500`, `detail="Internal Server Error"`
- Expected: controlled 4xx with a user-actionable filename/rename message

### Likely Data Flow

```text
POST /api/projects/{project_id}/materials
  -> backend/app/api/projects.py:105 upload_project_material()
  -> safe_name = Path(file.filename).name
  -> stored_path = upload_dir / f"{uuid}-{safe_name}"
  -> stored_path.open("wb")
  -> OSError / filesystem filename limit
  -> uncaught exception
  -> 500
```

Relevant code:

- `backend/app/api/projects.py:105-117`
- `backend/app/services/project_service.py:56-90`
- `backend/app/disclosure/material_parser.py`

### Primary Hypothesis

The filename length is only basename-sanitized, not length-bounded. The write happens before any `ValueError` mapping, so filesystem `OSError` is not caught and becomes a 500.

### Diagnostic Steps

1. Reproduce with a minimal TestClient command using `raise_server_exceptions=True` to capture the exact Python exception and stack.
2. Confirm whether the effective filename limit failure is from the full basename segment or the complete path.
3. Check whether the failed write leaves any partial file on disk.
4. Check whether the failed upload creates a `ProjectMaterial` row. Current artifact suggests it does not.
5. Confirm expected behavior for normal long-but-valid names, non-ASCII names, and duplicate names.

### Regression Test To Add Later

`tests/test_projects_api_router.py::test_material_upload_rejects_overlong_filename_without_500`

Assertions:

- Response is 400 or 422, never 500.
- Response detail tells the user to rename/shorten the file.
- Material list does not include a failed record.
- No partial stored file remains.

### Fix Strategy Later

Do not implement until approved. Candidate fix:

- Bound the stored filename component before writing.
- Preserve original filename in metadata.
- Catch `OSError` during file write and map to localized 4xx.

### Exit Criteria

- Reproduction command captures root cause stack.
- Failing regression test exists.
- Proposed fix location is confirmed.
- After a future fix: targeted test, material upload exploration, and `python3 -m pytest tests/test_projects_api_router.py -q` pass.

## Session B - BUG-001 Golden Quality Gate Empty Pass

### Symptom

`python3 scripts/golden_quality_gate.py --report-path ...` exits 0 and reports `"passed": true` while all five golden cases are skipped.

### Evidence

- Artifact: `qa_runs/patent_flow_long_qa_20260630/artifacts/golden/golden-quality-gate.json`
- Summary: `case_count=5`, `enabled_count=0`, `skipped_count=5`, `pending_calibration_count=5`
- Every case reason: `release_gate_disabled`
- Current case files all include `"release_gate_enabled": false`

Relevant code/files:

- `scripts/golden_quality_gate.py`
- `tests/golden_patent_cases/*/case.json`
- `tests/golden_patent_outputs/*.md` currently absent for the cases reported in the artifact

### Primary Hypothesis

The script treats "no enabled calibrated cases" as non-failing because disabled cases are intended to be queued for calibration. That is acceptable for calibration reporting, but weak as a release gate if CI or QA interprets exit 0 as quality coverage.

### Diagnostic Steps

1. Read `scripts/golden_quality_gate.py` around enabled/skipped/passed aggregation.
2. Confirm whether the script has a release mode, strict mode, or CI mode.
3. Check `.github/workflows/ci.yml` usage to decide whether current behavior can create false green CI.
4. Inspect one case JSON to identify required human calibration fields and fixture expectations.
5. Decide product policy:
   - calibration report mode may exit 0 with enabled_count=0;
   - release gate mode should fail or emit non-ignorable warning when enabled_count=0.

### Regression Test To Add Later

`tests/test_golden_release_gate.py::test_gate_fails_release_mode_when_no_cases_enabled`

Assertions:

- In release/strict mode, zero enabled cases is not treated as a quality pass.
- In calibration/report mode, zero enabled cases may exit 0 but clearly reports "no release coverage".

### Fix Strategy Later

Do not implement until policy is agreed. Candidate options:

- Add `--strict-release` and use it in CI/release smoke.
- Or make default gate fail when `case_count > 0 and enabled_count == 0`.
- Or calibrate and enable at least one golden case before relying on the gate.

### Exit Criteria

- Root cause classified as script policy vs missing calibrated fixtures.
- Recommended release behavior documented.
- Future fix has a test covering all-disabled cases.

## Session C - BLOCKER-002 v1 Smoke Sidecar Directory

### Symptom

`scripts/v1_smoke.sh` fails at `ensure_tauri_resource_placeholders` when `build/backend/patentagent-backend` is a non-empty generated PyInstaller one-folder output.

### Evidence

- Command in `COMMAND_RESULTS.md` exited 1.
- `build/backend/patentagent-backend` currently exists as a directory with `_internal/` and executable `patentagent-backend`.
- `scripts/v1_smoke.sh:75-96` attempts to remove the path if it is a directory, but fails on non-empty directories and tells the user to remove it.
- `src-tauri/tauri.conf.json` maps `../build/backend/patentagent-backend` to resource `patentagent-backend`.
- Individual `cargo check` and `cargo test` already passed.

### Primary Hypothesis

The smoke script is designed for a clean tree or an empty legacy placeholder, not a workspace that already has a valid one-folder PyInstaller sidecar directory. This may be an intentional environment precondition, but it blocks one-command smoke in normal iterative local packaging workflows.

### Diagnostic Steps

1. Confirm whether `build/backend/patentagent-backend` is ignored/generated and safe to remove locally.
2. Rerun `scripts/v1_smoke.sh` in a clean workspace or after moving the generated directory aside, only if allowed.
3. Compare `scripts/build_backend_sidecar.sh` output mode with the Tauri resource expectation.
4. Decide whether one-command smoke should:
   - fail fast and require clean build dir;
   - tolerate existing valid one-folder sidecar;
   - clean/regenerate the sidecar itself.
5. Check package script behavior before changing smoke behavior.

### Regression Test To Add Later

`tests/test_v1_smoke_script.py::test_v1_smoke_handles_existing_sidecar_directory_policy`

Assertions depend on policy:

- If existing directory should fail: message must be actionable and documented.
- If existing directory should pass: script must not require `rmdir` on non-empty directory.

### Fix Strategy Later

Do not implement until policy is chosen. Candidate options:

- Make `v1_smoke.sh` run `scripts/build_backend_sidecar.sh` before placeholder handling and skip placeholder creation when a valid executable exists.
- Or keep strict clean-tree behavior and add a preflight docs/update that marks generated sidecar directory as a known environment cleanup step.

### Exit Criteria

- Current failure classified as expected environment precondition or script robustness bug.
- One-command smoke path has a documented cleanup/retry path.
- Future verification: `scripts/v1_smoke.sh` exits 0 in the chosen supported environment.

## Session D - BLOCKER-001 Source Conflict Revalidation

### Symptom

The QA docs recorded unresolved conflicts at SHA `449e451f`, but current source at SHA `f566fc09` reports no unmerged files.

### Evidence

- Current `git diff --name-only --diff-filter=U`: empty.
- Current `git status --short --branch`: only untracked `qa_runs/` and two output screenshots.
- Old QA docs still state 10 unmerged files.

### Primary Hypothesis

The blocker was valid at the time of QA execution but stale now because the worktree was updated between runs.

### Diagnostic Steps

1. Rerun the full AGENTS source identity checklist and record current values.
2. Update or append a "current-state revalidation" note in QA docs if desired.
3. Confirm no conflict markers remain with `rg -n "<<<<<<<|=======|>>>>>>>"` over previously conflicted files.
4. Decide whether release-grade UI evidence can now proceed after current-state checks.

### Exit Criteria

- `BLOCKER-001` is either closed/stale in current context or replaced by a current dirty-tree blocker.
- Follow-up UI/Tauri smoke uses current SHA, not stale SHA `449e451f`.

## Session E - UI/Tauri Evidence Gap

### Symptom

API and unit/build gates passed, but there is no current browser/Tauri proof for the guided patent flow, repair editor, installed app, or DMG artifact.

### Evidence

- `FINAL_REPORT.md` lists UI/Tauri/DMG as remaining risk.
- API journeys are TestClient/fake LLM only.
- Frontend tests/build passed, but no dev server screenshot or Tauri DOM smoke was captured in this debug round.

### Primary Hypothesis

The product flow is likely healthy at API/state-machine level, but user-facing continuity is unproven. The main risk is integration mismatch between React state, API payloads, and desktop sidecar runtime.

### Diagnostic Steps

1. Start backend and frontend dev servers from current source.
2. Use deterministic seed/temp data where possible.
3. Run browser smoke for:
   - workbench start path,
   - current project selection,
   - export gate status,
   - document repair workspace empty and repairable states.
4. For annotated repair editor, verify the real API flow first:
   - `GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session`
   - non-empty `issues`
   - non-empty draft `sections`
5. Only after browser proof, run Tauri dev or packaged-app DOM smoke.

### Exit Criteria

- Screenshot/artifact paths exist for desktop and mobile-ish viewport.
- UI proof is tied to current branch/SHA.
- No evidence relies on stale `/Volumes/PatentAgent` or old installed app.

## Session F - Input Guidance And Duplicate Material Frictions

### Symptoms

- Empty and extremely short ideas can create projects.
- Incomplete disclosure uploads as processed without warning.
- Duplicate material filenames appear as separate rows with identical visible names.

### Evidence

- `artifacts/incomplete-flow-exploration.json`
- `artifacts/material-upload-exploration.json`
- `FLOW_FRICTION.md` entries `FRICTION-003` and `FRICTION-004`

### Primary Hypothesis

The API intentionally allows draft project creation with low-information input, but the workflow needs stronger UI-level guidance and maybe server-side warning metadata. Duplicate material behavior may be acceptable technically but confusing without UI disambiguation.

### Diagnostic Steps

1. Inspect `frontend/src/flow/panels/IdeaIntakePanel.tsx` and material list rendering.
2. Determine whether UI already warns on short text even though API does not.
3. Add component-level scenarios later if missing:
   - empty idea,
   - short marketing text,
   - duplicate file names,
   - incomplete material warning.
4. Decide whether server should add warnings or UI should derive them.

### Exit Criteria

- Product decision recorded: permissive project save vs validation block.
- User guidance location identified.
- Future tests cover chosen behavior.

## Suggested Debug Execution Sequence

1. Revalidate current source identity and close/reclassify stale `BLOCKER-001`.
2. Open a focused debug session for `BUG-002`, because it is the clearest product bug with a narrow reproduction and likely narrow fix.
3. Open a policy/debug session for `BUG-001`, because it affects release confidence more than user runtime.
4. Resolve or document `BLOCKER-002` before relying on `scripts/v1_smoke.sh` as a single release gate.
5. Run current-source browser UI smoke only after source identity is clean enough and no stale blocker remains.
6. Treat input-guidance frictions as product UX follow-ups unless they block a release criterion.

## Commands To Start With

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git diff --name-only --diff-filter=U
```

For `BUG-002`:

```bash
python3 qa_runs/patent_flow_long_qa_20260630/explore_material_uploads.py
python3 -m pytest tests/test_projects_api_router.py -q
```

For `BUG-001`:

```bash
python3 scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate.json
python3 -m pytest tests/test_golden_release_gate.py -q
```

For `BLOCKER-002`:

```bash
ls -la build/backend/patentagent-backend
PATENTAGENT_SKIP_INSTALL=1 bash scripts/v1_smoke.sh
```

## Do Not Do Yet

- Do not modify business code while only using this as a plan.
- Do not remove `build/backend/patentagent-backend` without explicit approval, because it is an existing generated artifact.
- Do not treat old QA source-conflict evidence as current without rerunning source identity checks.
- Do not claim UI/Tauri readiness from API TestClient reports alone.
