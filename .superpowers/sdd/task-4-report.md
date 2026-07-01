# Task 4 Report: Corpus Quality Gates For CNIPA Official Evidence

- Source branch: `codex/cnipa-official-export-design`
- Source short SHA: `733b626e`
- Worktree path: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Dirty worktree at start: yes (`.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, `task-3-report.md`)

## Scope Implemented

- Added CNIPA official export corpus coverage checks in `backend/app/services/project_knowledge_service.py`.
- Preserved existing ready-state behavior for non-CNIPA patent sources while fail-closing partial CNIPA official exports.
- Added grantability low-evidence fail-closed copy for `cnipa_export_*` quality flags in `backend/app/grantability.py`.
- Added regression tests for:
  - CNIPA official exports with claims + fulltext becoming `ready`
  - metadata-only CNIPA exports becoming `needs_supplemental_search`
  - grantability fail-closed behavior for partial CNIPA export knowledge state

## TDD Notes

1. Added the two corpus tests from the task brief first.
2. Ran:

   `python3 -m pytest tests/test_project_knowledge.py::test_cnipa_official_export_builds_ready_corpus_with_claims_and_fulltext tests/test_project_knowledge.py::test_cnipa_metadata_only_corpus_needs_supplemental_search -q`

3. Observed the expected red failure: metadata-only CNIPA export incorrectly produced `ready`.
4. Implemented the corpus quality gate and grantability copy.
5. Added the grantability regression test.
6. Ran the full required suite and fixed one regression where non-CNIPA patent sources were incorrectly losing claim coverage.

## Verification

- Focused regression:
  - `python3 -m pytest tests/test_project_knowledge.py::test_cnipa_official_export_builds_ready_corpus_with_claims_and_fulltext tests/test_project_knowledge.py::test_cnipa_metadata_only_corpus_needs_supplemental_search tests/test_grantability.py::test_grantability_fails_closed_for_partial_cnipa_export_state -q`
  - Result: `3 passed`

- Required suite:
  - `python3 -m pytest tests/test_project_knowledge.py tests/test_grantability.py -q`
  - Result: `75 passed`

## Self Review

- Confirmed CNIPA-specific quality flags survive the later knowledge-state rewrite and are not overwritten by the generic ready-state branch.
- Confirmed `needs_supplemental_search` is driven by `cnipa_export_*` flags without changing synthetic/non-patent handling.
- Confirmed existing real-patent candidate tests still pass by treating non-CNIPA patent sources as fully covered unless explicitly gated by this task.

## Files Changed

- `backend/app/services/project_knowledge_service.py`
- `backend/app/grantability.py`
- `tests/test_project_knowledge.py`
- `tests/test_grantability.py`

## Review Fix Addendum

- Follow-up source branch: `codex/cnipa-official-export-design`
- Follow-up source short SHA: `100ee995`
- Worktree path: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Dirty worktree at start: yes (`.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, `task-3-report.md`, `task-4-report.md`)

### Fixes Applied

- Tightened `_candidate_has_fulltext()` so CNIPA official export candidates no longer count `abstract` or `claims` as fulltext coverage.
- Added explicit fulltext metadata detection for CNIPA rows that really do carry imported fulltext payload markers.
- Updated CNIPA quality-flag classification so:
  - metadata-only rows get `cnipa_export_metadata_only`
  - claims-without-description/fulltext rows get `cnipa_export_partial_fulltext`
- Preserved CNIPA `cnipa_export_*` flags in mixed corpora instead of overwriting them with only `non_patent_source`.

### Regression Tests Added

- `test_cnipa_claims_without_description_needs_partial_fulltext_search`
- `test_create_project_corpus_preserves_non_patent_and_cnipa_quality_flags_in_mixed_corpus`

### Verification

- Required suite:
  - `python3 -m pytest tests/test_project_knowledge.py tests/test_grantability.py -q`

## Review Fix Addendum 3

- Follow-up source branch: `codex/cnipa-official-export-design`
- Follow-up source short SHA: `3973ff08`
- Worktree path: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Dirty worktree at start: yes (`.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, `task-3-report.md`)

### Fixes Applied

- Added CNIPA-specific `quality_report.failures` entries so stored corpus artifacts explain `cnipa_export_metadata_only`, `cnipa_export_partial_fulltext`, and `cnipa_export_missing_claims` without relying only on state flags.
- Narrowed the grantability CNIPA fail-closed gate to the three blocking coverage flags so `cnipa_export_parse_warnings` alone no longer triggers the low-evidence CNIPA warning.
- Added regression coverage for both the stored corpus failure payloads and the non-blocking parse-warning grantability path.

### Verification

- Required suite:
  - `python3 -m pytest tests/test_project_knowledge.py tests/test_grantability.py -q`
  - Result: `79 passed`
  - Result: `78 passed`
  - Result: `78 passed`
  - Result: `77 passed`

## Review Fix Addendum 2

- Follow-up source branch: `codex/cnipa-official-export-design`
- Follow-up source short SHA: `f7af104e`
- Worktree path: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Dirty worktree at start: yes (`.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, `task-3-report.md`, `task-4-report.md`)

### Fixes Applied

- Stopped treating CNIPA `fulltext_path` and `fulltext_file` attachment metadata as extracted fulltext evidence.
- Added a regression test proving claims plus attachment-only metadata still fail closed as `cnipa_export_partial_fulltext` instead of `ready`.

### Verification

- Required suite:
  - `python3 -m pytest tests/test_project_knowledge.py tests/test_grantability.py -q`
