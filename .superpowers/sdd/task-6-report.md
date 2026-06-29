Task 6 report: Writing-Flow Gates

Source identity
- Branch: `codex/automation-test-plan`
- Short SHA at start: `a280981a`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty at start: yes; only the pre-existing out-of-scope files listed in the task dispatch were already dirty

What changed
- Added backend grantability gating on `ProjectKnowledgeState` in `backend/app/grantability.py`.
- Passed project knowledge state from the grantability API endpoint in `backend/app/main.py`.
- Added backend tests for missing and not-ready project corpus states in `tests/test_grantability.py`.
- Passed project knowledge into the quality workspace and grantability view.
- Added pre-generation grantability gate copy in the frontend quality UI.
- Updated `frontend/src/app/routes.test.tsx` to satisfy the expanded `QualityWorkspaceState` type used by the frontend build.

Behavior summary
- Missing project corpus now adds a low-evidence flag and forces fail-closed output.
- Not-ready or stale project corpus states now prevent high-confidence authorization conclusions.
- Corpus quality flags for synthetic-only, empty, insufficient, and document counts below 2 now add low-evidence flags and fail closed.
- The grantability narrative now explicitly says the result is evidence-insufficient when fail-closed conditions apply.
- The grantability UI now tells the user before generation whether the project corpus is ready enough to support authorization analysis.

Verification
- `python3 -m pytest tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing tests/test_api.py::test_grantability_report_api_generates_persists_and_exports -q`
- `npm --prefix frontend run build`

Files changed
- `backend/app/grantability.py`
- `backend/app/main.py`
- `tests/test_grantability.py`
- `frontend/src/features/quality/QualityWorkspace.tsx`
- `frontend/src/App.tsx`
- `frontend/src/views/qualityViews.tsx`
- `frontend/src/app/routes.test.tsx`
