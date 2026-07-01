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

Controller test hardening:
- Added selector-level coverage for both a very short hash (`abc`) and a 12-character full hash (`abc123def456`) in the version chain data model.
- Re-ran `cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx features/documentRepair/selectors.test.ts`: passed, 2 files / 15 tests.
- Re-ran `cd frontend && npm run build`: passed.
- Re-ran `cd frontend && npm test`: passed, 32 files / 225 tests.
- Re-ran `git diff --check`: passed.

Task 5 implementation report:
- Source identity verified before edits:
  - Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
  - Branch: `codex/cnipa-official-export-design`
  - Short SHA: `53da62cf`
  - Dirty status: dirty from pre-existing `.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, and `task-3-report.md`
- Added CNIPA official export frontend API types and wrappers in `frontend/src/api.ts` for patent source capabilities, CNIPA query packs, import ledgers, and export-upload POSTs.
- Added API coverage in `frontend/src/api.test.ts` for:
  - `GET /api/patent-sources`
  - `GET /api/projects/{project_id}/knowledge/cnipa-query-pack`
  - `GET /api/projects/{project_id}/knowledge/import-ledgers?plan_id=...`
  - `POST /api/projects/{project_id}/knowledge/cnipa-export-imports`
- Updated `frontend/src/views/projectKnowledgeView.tsx` to:
  - expose a CNIPA official export import panel whenever a knowledge plan exists
  - show query-pack strategies
  - show the latest import ledger summary
  - relabel candidate sources with user-facing names, including `CNIPA 官方导出`
  - rewrite helper-config warnings so ordinary UI points users to the official export path rather than `CNIPA_EPUB_SEARCH_SCRIPT`
  - surface new CNIPA quality flags as official-export evidence issues, while keeping parse warnings informational rather than a hard gate
- Threaded CNIPA query-pack/import-ledger state and the upload handler through:
  - `frontend/src/App.tsx`
  - `frontend/src/features/corpus/CorpusWorkspace.tsx`
- Added view/workspace regression coverage in:
  - `frontend/src/projectKnowledgeView.test.tsx`
  - `frontend/src/features/corpus/CorpusWorkspace.test.tsx`

Verification:
- `npm --prefix frontend install`: passed
- `npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx`: passed, 3 files / 18 tests
- `npm --prefix frontend run build`: passed

Files changed for Task 5:
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/features/corpus/CorpusWorkspace.tsx`
- `frontend/src/views/projectKnowledgeView.tsx`
- `frontend/src/api.test.ts`
- `frontend/src/projectKnowledgeView.test.tsx`
- `frontend/src/features/corpus/CorpusWorkspace.test.tsx`
- `.superpowers/sdd/task-5-report.md`

Concerns:
- None.

Task 5 reviewer fix 2 report:
- Source identity verified before edits:
  - Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
  - Branch: `codex/cnipa-official-export-design`
  - Short SHA: `5d96e539`
  - Dirty status: dirty from pre-existing `.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, and `task-3-report.md`
- Tightened the CNIPA official-export picker UI to advertise only the supported formats for this phase: `.csv`, `.xlsx`, and `.zip`.
- Changed per-strategy CNIPA copy actions to copy only the clicked strategy's queries, and updated the button label to `复制该策略检索式`.
- Refactored `loadProjectKnowledge()` so the main project knowledge overview loads first and remains visible if CNIPA query-pack or import-ledger fetches fail; supplemental failures now reset only CNIPA supplemental state.
- Added regression coverage for:
  - restricted file-picker accepted formats
  - per-strategy CNIPA copy behavior
  - source-level guard on the isolated supplemental-failure loading flow

Reviewer fix 2 verification:
- `npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx src/AppRefreshEffect.test.ts`: passed, 4 files / 27 tests
- `npm --prefix frontend run build`: passed

Concerns:
- None.

Task 5 reviewer fix report:
- Source identity verified before edits:
  - Worktree: `/Users/leo/Projects/patents_agent/.worktrees/cnipa-official-export-design`
  - Branch: `codex/cnipa-official-export-design`
  - Short SHA: `2a66ce95`
  - Dirty status: dirty from pre-existing `.superpowers/sdd/progress.md`, `task-1-report.md`, `task-2-report.md`, and `task-3-report.md`
- Updated `frontend/src/views/projectKnowledgeView.tsx` to add a `复制 CNIPA 检索式` action that uses `navigator.clipboard.writeText(...)` when available and falls back to manual-copy guidance while still rendering the query text inline.
- Expanded CNIPA import ledger diagnostics in the same view to show import time, row count, parsed count, derived skipped/duplicate-ish count, warnings, and row-level failures with file name, row number, code, and message.
- Added focused frontend regression coverage in `frontend/src/projectKnowledgeView.test.tsx` for:
  - CNIPA query-pack copy action success and fallback paths
  - import ledger warning/failure diagnostics
  - official-export quality flag guidance copy

Reviewer fix verification:
- `npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx`: passed, 3 files / 21 tests
- `npm --prefix frontend run build`: passed

Concerns:
- None.
