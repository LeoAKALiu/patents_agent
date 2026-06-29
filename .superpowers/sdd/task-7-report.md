## Task 7 Report

### Source identity at start
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- Starting HEAD: `668ee94a`
- Dirty worktree at start: no

### Files changed
- `frontend/src/features/knowledge/KnowledgeWorkspace.tsx`
- `frontend/src/features/export/ExportWorkspace.tsx`
- `frontend/src/features/expert/ExpertToolsWorkspace.tsx`
- `frontend/src/app/AppRoot.tsx`
- `frontend/src/views/exportView.tsx`
- `frontend/src/views/exportView.test.tsx`
- `frontend/src/app/routes.test.tsx`
- `frontend/src/styles.css`

### Behavior implemented
- Split `AppRoot` route rendering so `knowledge`, `export`, and `expert` each render their own top-level workspace wrapper instead of sharing the old expert-workspace branch.
- Added `KnowledgeWorkspace` as a normal workspace with two explicit modes, `语料库建设` and `知识库检索`, composed around the existing `CorpusWorkspace`.
- Added `ExportWorkspace` as a normal workspace around `ExportView`, with clear framing for `正式提交稿`, `内部复核材料`, and `风险说明与追溯`.
- Added locked-export guidance that sends users back toward `文稿与修复 / 总览` or `文稿与修复 / 标注修复` instead of embedding repair actions inside export.
- Reframed `专家工具` as an advanced tool center, with copy explicitly stating it is not the default repair/export path, while preserving the existing chooser and expert sub-workspaces.
- Updated `ExportView` copy so the rendered export surface now uses the exact titles `正式提交稿`, `内部复核材料`, and `风险说明与追溯`.

### Tests and build run
- `cd frontend && npm test -- views/exportView.test.tsx app/routes.test.tsx` — passed
- `cd frontend && npm run build` — passed
- `cd frontend && npm test` — passed
- `git diff --check` — passed

### Self-review notes
- Export does not render repair UI, `人工修正`, or `一键AI修正`.
- Locked export guidance points users back to the document-repair workspace instead of trying to continue repairs inline.
- Knowledge and export are now top-level normal workspaces, not framed as sub-pages of expert tools.
- Expert tools remain available, but are presented as lower-priority advanced tools with explicit copy.

### Concerns
- The locked-export buttons currently navigate back to the `文稿与修复` workspace and label the intended destination (`总览` or `标注修复`), but they do not preselect the inner tab because that tab state is still owned inside `DocumentRepairWorkspace`.

### Fix follow-up
- Concern addressed: locked export guidance now carries an in-app document-tab intent so `总览` and `标注修复` land on the intended inner tab.
- Fix applied:
  - Added optional `requestedTab` and `onRequestedTabHandled` props to `DocumentRepairWorkspace`, with an effect that switches the local tab when a parent intent arrives.
  - Updated `AppRoot` to own a one-shot document-repair tab intent and feed it into `DocumentRepairWorkspace`.
  - Kept normal top-level `文稿与修复` navigation unchanged by clearing the intent immediately after consumption.
  - Added tests covering both the direct tab-intent behavior and the click path from export guidance into the correct document tab.
- Commands and results:
  - `cd frontend && npm test -- views/exportView.test.tsx app/routes.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx` — passed
  - `cd frontend && npm run build` — passed
  - `cd frontend && npm test` — passed
  - `git diff --check` — passed
