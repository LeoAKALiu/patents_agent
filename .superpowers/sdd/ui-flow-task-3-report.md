# Task 3 Report: Hide Long Draft Preview While Export Is Locked

## Source identity

- Branch: `codex/grantatlas-readme-branding`
- Short SHA at start: `89a342a4`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at start: yes; unrelated existing modifications were present and left untouched

## What changed

- Updated `frontend/src/views/exportView.tsx` so the risk/explanatory section only renders `PackagePreview` when `officialAllowed` is true.
- Replaced the locked-state long draft preview with explicit warning copy:
  - `导出解锁前隐藏申请文本预览`
  - `先完成上方门禁后再复核正式提交稿内容；内部稿仍可在文稿工作区查看和编辑。`
- Added the required regression test in `frontend/src/views/exportView.test.tsx` covering the locked state with oversized claims/description content and asserting the long preview text is absent.

## TDD evidence

### RED

Command:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx -t "hides the long package preview"
```

Observed result:

- FAIL
- Failure reason matched the brief: the new locked-state guidance text was missing because `PackagePreview` was still rendered in the locked state.

### GREEN

Implementation:

- Applied the minimal conditional render in `frontend/src/views/exportView.tsx` from the task brief.

Verification command:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx src/features/export/ExportWorkspace.test.tsx
```

Observed result:

- PASS
- `2` test files passed
- `8` tests passed

## Tests and output

### Focused RED command

```text
FAIL src/views/exportView.test.tsx > ExportView quality gate copy > hides the long package preview while official export is locked
TestingLibraryElementError: Unable to find an element with the text: 导出解锁前隐藏申请文本预览.
```

### Focused GREEN suite

```text
Test Files  2 passed (2)
Tests       8 passed (8)
```

## Files changed

- `frontend/src/views/exportView.tsx`
- `frontend/src/views/exportView.test.tsx`

## Self-review

- Scope stayed within the two owned production/test files.
- The behavior matches the brief exactly: locked export shows explicit guidance first and does not expose long draft preview text.
- The existing unlocked path is preserved by leaving `PackagePreview` behind the existing `officialAllowed` gate.
- No unrelated files were staged or modified for this task beyond this report file.

## Concerns

- None for this task's scoped behavior.

---

## Reviewer follow-up fix

### Finding addressed

- The initial preview hide/show logic followed locally recomputed `officialAllowed`, which could diverge from backend export readiness.

### What changed

- Updated `frontend/src/views/exportView.tsx` so preview visibility now uses backend readiness when `exportReadiness` is present:
  - show preview when `exportReadiness.export_allowed === true`
  - or when `exportReadiness.next_action === "export_ready"`
  - otherwise hide preview and keep the locked callout copy
- Preserved the earlier fallback behavior when `exportReadiness` is absent by falling back to local `officialAllowed`.

### Added regressions

- Added a mismatch regression where local inputs would make `officialAllowed` true, but backend readiness still reports `next_action: "run_quality_checks"` and `export_allowed: false`; preview remains hidden.
- Added a companion unlocked regression where backend readiness reports export ready; preview renders even without the local `officialAllowed` prerequisites.

### TDD evidence for follow-up fix

#### RED

Command:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx -t "hides the long package preview"
```

Observed result before the fix:

- FAIL
- The mismatch regression failed because the preview still rendered from local `officialAllowed` even though backend readiness kept export locked.

#### GREEN

Commands:

```bash
npm --prefix frontend test -- --run src/views/exportView.test.tsx -t "hides the long package preview"
npm --prefix frontend test -- --run src/views/exportView.test.tsx src/features/export/ExportWorkspace.test.tsx
```

Observed result after the fix:

- PASS for the focused `-t "hides the long package preview"` run
- PASS for the focused export suite
- `2` test files passed
- `10` tests passed

### Self-review for follow-up fix

- The change is intentionally narrow and only affects preview visibility in the risk/traceability section.
- Export buttons and existing status logic still use their prior gates; this avoids broadening behavior beyond the reviewer’s requested fix.
- The locked callout copy from Task 3 remains unchanged.
