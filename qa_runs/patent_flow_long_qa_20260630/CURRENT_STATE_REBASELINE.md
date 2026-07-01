# Current State Rebaseline

## Source Identity

- Date: 2026-06-30
- Worktree: `/Users/leo/Projects/patents_agent`
- Git top-level: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- Short SHA: `f566fc09`
- Dirty state: dirty, with untracked QA/output artifacts only before Task 2/3/4 edits
- Unmerged files: none

## Commands

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git diff --name-only --diff-filter=U
```

Observed output:

```text
/Users/leo/Projects/patents_agent
## codex/grantatlas-readme-branding...origin/codex/grantatlas-readme-branding
?? output/playwright/grantatlas-brand-sidebar.png
?? output/playwright/patentagent-logo-sidebar.png
?? qa_runs/
/Users/leo/Projects/patents_agent
codex/grantatlas-readme-branding
f566fc09
```

`git diff --name-only --diff-filter=U` returned no files.

## Blocker Status

- `BLOCKER-001` is stale/resolved for the current checkout. The earlier unresolved merge/index conflicts were tied to SHA `449e451f`; current SHA `f566fc09` has no unmerged files.
- UI/Tauri verification is no longer blocked by merge/index conflicts, but still needs current browser/Tauri evidence under the QA artifact directory before release-grade UI claims.
- The remaining active release blocker before this debug pass was `BLOCKER-002`, the one-command smoke sidecar directory policy.

## Next Eligible Verification

- Current-source browser smoke can proceed with:
  - `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
  - `npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174`
- Current-source command verification should prioritize:
  - `python3 -m pytest tests/test_projects_api_router.py tests/test_golden_release_gate.py tests/test_tauri_desktop_skeleton.py -q`
  - `python3 qa_runs/patent_flow_long_qa_20260630/explore_material_uploads.py`
  - `PATENTAGENT_SKIP_INSTALL=1 PATENTAGENT_SKIP_TAURI_SMOKE=1 PATENTAGENT_V1_1_REPEAT_COUNT=1 bash scripts/v1_smoke.sh`
