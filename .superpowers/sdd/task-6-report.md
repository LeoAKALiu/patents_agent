Task 6 report: Writing-Flow Gates

Source identity
- Branch: `codex/automation-test-plan`
- Short SHA at start: `05388c1b`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty at start: yes; only the pre-existing out-of-scope files listed in the task dispatch were already dirty

What changed
- Corrected the grantability gate to look for the real project-corpus flag, `synthetic_evidence`, instead of the stale `synthetic_only` name.
- Added regression coverage proving a `ready` project knowledge state with `document_count >= 2` still fail-closes when `quality_flags=["synthetic_evidence"]`.
- Hardened the grantability API regression so it seeds a distinctive `ProjectKnowledgeState` and proves the endpoint passes that state through to grantability generation.
- Tightened the quality view copy so “语料库已就绪” only appears when the corpus is truly analysis-ready: `status === "ready"`, at least 2 documents, and no blocking quality flags.

Behavior summary
- A synthetic-only corpus now fail-closes even if the knowledge state says `ready` and has 2 or more documents.
- The grantability report API now proves that stored project-knowledge state can drive low-evidence grantability output.
- The grantability UI no longer treats every `ready` status as analysis-ready; blocking flags and low document counts keep the copy in an evidence-gated state.

Verification
- `python3 -m pytest tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing tests/test_grantability.py tests/test_api.py::test_grantability_report_api_generates_persists_and_exports -q`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test -- qualityViews`

Files changed
- `backend/app/grantability.py`
- `tests/test_grantability.py`
- `tests/test_api.py`
- `frontend/src/views/qualityViews.tsx`
- `frontend/src/views/qualityViews.test.tsx`
