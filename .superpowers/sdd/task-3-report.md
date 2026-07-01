# Task 3 Report: Project Knowledge Import API And Ledger Storage

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Branch: `codex/cnipa-official-export-design`
- Starting HEAD: `a93dabbb`
- Commit created: `abd29605`
- Dirty at start: yes, existing `.superpowers/sdd/progress.md`, `.superpowers/sdd/task-1-report.md`, and `.superpowers/sdd/task-2-report.md`

## Scope Completed

- Added `ProjectKnowledgeImportLedger` and `CnipaExportImportResponse` schemas in `backend/app/schemas.py`
- Added SQLite persistence for project knowledge import ledgers in `backend/app/storage.py`
- Added `import_cnipa_official_export(...)` in `backend/app/services/project_knowledge_service.py`
- Added project knowledge CNIPA upload/list endpoints in `backend/app/api/project_knowledge.py`
- Added service and API coverage in `tests/test_project_knowledge.py` and `tests/test_api.py`

## TDD Evidence

### RED

Command:

```bash
python3 -m pytest tests/test_project_knowledge.py::test_import_cnipa_official_export_adds_real_candidates_and_ledger -q
```

Observed failure:

```text
ImportError: cannot import name 'import_cnipa_official_export'
```

### GREEN

Focused service command:

```bash
python3 -m pytest tests/test_project_knowledge.py::test_import_cnipa_official_export_adds_real_candidates_and_ledger -q
```

Result:

```text
1 passed in 0.48s
```

Focused API command:

```bash
python3 -m pytest tests/test_api.py::test_project_knowledge_cnipa_export_upload_returns_overview -q
```

Result:

```text
1 passed in 0.82s
```

Final task verification:

```bash
python3 -m pytest tests/test_api.py tests/test_project_knowledge.py tests/test_cnipa_export_importer.py tests/test_patent_sources.py -q
```

Result:

```text
67 passed in 3.09s
```

## Implementation Notes

- Reused `CNIPA_OFFICIAL_EXPORT_SOURCE`, `CnipaExportImportContext`, and `parse_cnipa_official_export_file(...)` from the current worktree as required.
- Preserved Task 2 import metadata and carried truthful ZIP attachment names into persisted import ledgers via `attachments`.
- Stored retained candidate IDs based on the actual post-import candidate set for the active plan.
- Kept the new API limited to Task 3 upload/query behavior; no Task 4 gating or Task 5 frontend work was added.

## Self-Review

- Verified the service path updates project knowledge state to `candidates_pending` on successful imports.
- Verified ledger persistence contains the CNIPA source ID, parsed row count, retained candidate IDs, and attachment metadata.
- Verified the upload endpoint stores the uploaded file under the app data dir and returns both `overview` and newest `ledger`.

## Concerns

- None within Task 3 scope.

## Review Fix Addendum

- Date: 2026-07-01
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Branch: `codex/cnipa-official-export-design`
- HEAD: `abd29605`
- Dirty at start: yes; pre-existing `.superpowers` report/progress edits were present in this worktree

### Reviewer Findings Addressed

- Cleaned up persisted CNIPA upload files on `POST /api/projects/{project_id}/knowledge/cnipa-export-imports` when import validation/activation fails before any ledger is created. The API now unlinks the randomized stored upload on the `400` and `409` failure paths.
- Preserved the user-facing original upload basename in `ProjectKnowledgeImportLedger.source_file_name` by threading `source_file_name` through `import_cnipa_official_export(...)`, while keeping parser/service reads pointed at the randomized stored path on disk.
- Added focused regression coverage for:
  - ledger original filename preservation
  - stored upload cleanup after failed import request
  - ZIP attachment filenames remaining visible in import ledger/API responses

### Verification

Required task suite:

```bash
python3 -m pytest tests/test_api.py tests/test_project_knowledge.py tests/test_cnipa_export_importer.py tests/test_patent_sources.py -q
```

Result:

```text
70 passed in 3.40s
```

## Re-review Fix 2 Addendum

- Date: 2026-07-01
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
- Branch: `codex/cnipa-official-export-design`
- Starting HEAD: `dd72b23b`
- Dirty at start: yes; existing `.superpowers/sdd/progress.md`, `.superpowers/sdd/task-1-report.md`, `.superpowers/sdd/task-2-report.md`, and `.superpowers/sdd/task-3-report.md` edits were already present

### Reviewer Finding Addressed

- Updated `backend/app/api/project_knowledge.py` so any unexpected exception raised after the upload is written also unlinks the randomized stored file before returning `400 Failed to import CNIPA export.`

### Regression Coverage

- Added an API test in `tests/test_api.py` that monkeypatches `import_cnipa_official_export(...)` to raise an unexpected runtime error and asserts the stored upload directory is empty after the failed request.

### Verification

Required task suite:

```bash
python3 -m pytest tests/test_api.py tests/test_project_knowledge.py tests/test_cnipa_export_importer.py tests/test_patent_sources.py -q
```

Result:

```text
71 passed in 4.12s
```
