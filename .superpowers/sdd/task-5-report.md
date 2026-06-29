Source identity at start:
- Worktree: /Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29
- Branch: codex/ui-refactor-2026-06-29
- Short SHA: 9628838f
- Dirty status: clean

What changed:
- Added first-pass `编辑`, `问题`, and `版本` tab implementations for the document repair workspace.
- Added section-level draft editing for `标题`, `摘要`, `权利要求书`, `说明书`, and `附图说明`, with `保存当前初稿` calling `onSaveDraftPackage`.
- Added the required persistent invalidation copy: `保存后旧正式稿、旧成稿会审和旧导出状态将失效，需要重新编译正式稿并重新成稿会审。`
- Added a filterable issue inbox sourced from review blocking issues, contamination hits, rewrite suggestions, chair tasks/actions, compile blockers, and quality checks.
- Added a compact version chain: `内部初稿 -> 质量检查 -> 正式稿 -> 成稿会审 -> 导出`, with full hashes only under `<details>`.
- Kept `标注修复` as a placeholder that can return to overview.
- Fixed SDD review finding where equivalent parent rerenders could reset unsaved edit-tab draft fields before save.

Tests/build commands and results:
- `cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx features/documentRepair/selectors.test.ts`: passed, 2 files / 13 tests.
- `cd frontend && npm run build`: passed.
- `cd frontend && npm test`: passed, 32 files / 223 tests.
- `git diff --check`: passed.

Files changed:
- `frontend/src/features/documentRepair/DocumentEditTab.tsx`
- `frontend/src/features/documentRepair/DocumentIssuesTab.tsx`
- `frontend/src/features/documentRepair/DocumentVersionsTab.tsx`
- `frontend/src/features/documentRepair/selectors.ts`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- `frontend/src/styles.css`
- `.superpowers/sdd/task-5-report.md`

Self-review notes:
- No raw JSON, logs, run IDs, `generation_logs`, or `official_safe_patches` are rendered by the new tabs.
- Issue states are derived conservatively as `open` or `pending_revalidation`.
- Full hashes are available only inside collapsed version `<details>` sections; default visible labels use short hashes.
- The issue filter intentionally avoids a persistent `建议` label outside rows so `只看阻断` hides suggestion rows cleanly.
- Edit-tab local draft state now resets only when incoming draft field values change, not merely because selector output object identity changes.
- `标注修复` remains a placeholder; Task 6 still owns embedding the annotated repair editor.

Concerns, if any:
- None.

Review fix:
- Reviewer finding addressed: version-chain default labels could still expose the full hash when the source hash length was 12 characters or fewer.
- Changed `shortHash` so every non-empty hash is elided before inline display, including short-but-complete hash strings.
- Added a regression test covering a 12-character full hash and asserting it is not present in the default version-chain labels.

Review fix tests/build commands and results:
- `cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx features/documentRepair/selectors.test.ts`: passed, 2 files / 14 tests.
- `cd frontend && npm run build`: passed.
- `cd frontend && npm test`: passed, 32 files / 224 tests.
- `git diff --check`: passed.

Review follow-up fix:
- Source identity verified before edits:
  - Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
  - Branch: `codex/ui-refactor-2026-06-29`
  - Short SHA: `a15c2d17`
  - Dirty status: clean
- Tightened `shortHash()` so inline version labels always elide non-empty hashes, including very short values like `abc`.
- Updated the workspace regression coverage to assert the visible `.document-short-hash` labels do not contain the full short hash before the `<details>` disclosure is opened.

Review follow-up tests/build commands and results:
- `cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx features/documentRepair/selectors.test.ts`: passed, 2 files / 14 tests.
- `cd frontend && npm run build`: passed.
- `git diff --check`: passed.
