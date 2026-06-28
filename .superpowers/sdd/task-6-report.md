# Task 6 Report: Record Revision Ledger Events And Expose API

## What I implemented

- Added `GET /api/projects/{project_id}/revision-ledger` in `backend/app/main.py`.
- Added revision-ledger event recording in the Task 6 mutation flows:
  - post-draft single repair patch apply
  - post-draft safe patch apply
  - official compile cleanup apply
  - completion patch accept
  - completion patch accept-all
- Used Task 5's existing `create_revision_record(...)` and store create/list methods without reworking storage/schema.
- Added frontend API surface in `frontend/src/api.ts`:
  - `RevisionLedgerRecord` interface
  - `listRevisionLedger(projectId)`
- Added API coverage in `tests/test_revision_ledger_api.py` for:
  - empty ledger listing
  - single-issue repair patch recording a `post_draft_repair` ledger event

## TDD evidence

### RED

Command:

```bash
pytest tests/test_revision_ledger_api.py -v
```

Summary:

- 2 tests collected
- both failed
- failure cause: `GET /api/projects/{project_id}/revision-ledger` returned `404 Not Found`

### GREEN

Command:

```bash
pytest tests/test_revision_ledger_api.py -v
```

Summary:

- 2 tests collected
- 2 passed

## Test commands and results

1. `pytest tests/test_revision_ledger_api.py -v`
   - PASS (`2 passed`)
2. `pytest tests/test_revision_ledger.py tests/test_revision_ledger_api.py tests/test_post_draft_review.py -v`
   - PASS (`27 passed`)
3. `npm --prefix frontend run build`
   - PASS (`vite build` completed successfully)

## Files changed

- `backend/app/main.py`
- `frontend/src/api.ts`
- `tests/test_revision_ledger_api.py`

## Self-review findings

- Confirmed the new API returns serialized `RevisionLedgerRecord` rows from the existing store.
- Confirmed ledger writes occur only after successful package mutation; no-op mutations do not create ledger rows.
- Confirmed repair patch ledger entries use before/after draft package snapshots and preserve affected section names.
- Confirmed safe patch and official cleanup entries detect changed sections from package diffs.
- Confirmed completion patch entries mark claim-targeted mutations as `protection_scope_changed=True`.
- Confirmed unrelated dirty files were left untouched and not included in staging scope.

## Concerns

- `accept-all` completion patch application now attempts sequential package mutation for each accepted proposed patch and records ledger events only for patches that actually change the draft. The requested test suite passed, but there is not yet dedicated completion-ledger coverage in this task.

## Review Fix Follow-up

### Findings addressed

- Critical: restored a stale-run guard in `accept_all_completion_patches` before any patch statuses or package mutations occur.
- Important: added regression coverage for:
  - sequential `completion_patch` ledger recording on fresh `accept-all`
  - stale `accept-all` conflict with no ledger writes
  - post-draft safe patch ledger recording
  - official cleanup ledger recording

### Follow-up TDD evidence

#### RED

Command:

```bash
pytest tests/test_revision_ledger_api.py -v
```

Summary:

- 6 tests collected
- 5 passed, 1 failed
- failing case: `test_revision_ledger_accept_all_completion_patches_rejects_stale_run`
- failure detail: stale `accept-all` returned `200 OK` instead of `409 Conflict`

#### GREEN

Command:

```bash
pytest tests/test_revision_ledger_api.py -v
```

Summary:

- 6 tests collected
- 6 passed

### Additional test results

1. `pytest tests/test_revision_ledger.py tests/test_revision_ledger_api.py tests/test_post_draft_review.py -v`
   - PASS (`31 passed`)
2. `npm --prefix frontend run build`
   - Not rerun; frontend source was unchanged in this fix pass.

### Follow-up self-review

- Confirmed stale `accept-all` now exits before mutating completion patch statuses, the draft package, or ledger rows.
- Confirmed fresh `accept-all` still applies proposed patches sequentially against the evolving package and records one ledger row per actual mutation.
- Confirmed completion patch ledger rows preserve section mapping:
  - `claim` -> `claims` with `protection_scope_changed=True`
  - `description` -> `description`
- Confirmed the new safe-patch and official-cleanup tests use real route flows and ledger API reads rather than direct store inspection alone.

### Updated concerns

- The original concern about missing completion-ledger coverage is now resolved.
