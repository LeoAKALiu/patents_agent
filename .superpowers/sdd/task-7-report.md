# Merged Task 7 Reports

This file records reports from two independent SDD plans that both used the same task report path. The merge preserves both original reports.

## Project Evidence Corpus / PR #123 branch

# Task 7 Report: End-To-End Verification And Documentation Update

## Source Identity

- Branch: `codex/automation-test-plan`
- Base SHA before Task 7: `c7cddd0e`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty at start: yes
- Pre-existing out-of-scope dirty files left untouched:
  - `backend/app/official_compile.py`
  - `docs/qa/automation-test-plan-execution-2026-06-27.md`
  - `tests/adversarial_flow_harness.py`
  - `tests/test_adversarial_flow_explorer.py`
  - `tests/test_official_compile.py`
  - `.superpowers/sdd/task-3-report.md`
  - `.superpowers/sdd/task-4-report.md`

## Documentation Changes

- Updated `docs/project-design-overview.md` to match the actual knowledge API surface:
  - `GET /api/projects/{project_id}/knowledge/candidates`
  - `PATCH /api/projects/{project_id}/knowledge/candidates/{candidate_id}`
  - `POST /api/projects/{project_id}/knowledge/candidates/bulk-decision`
- Revised the Knowledge expert-tools row and search-plan run description so they now describe the deterministic fake-provider-first implementation, while keeping the future official/public-provider shape and the advanced local import fallback visible.
- Left `docs/superpowers/specs/2026-06-29-project-evidence-corpus-design.md` unchanged because it already matches the implemented behavior.

## Verification Commands

### 1. Targeted backend

Command:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_api.py::test_project_creation_initializes_project_knowledge tests/test_api.py::test_project_knowledge_run_candidates_and_build_version tests/test_grantability.py::test_grantability_low_evidence_when_project_corpus_missing -q
```

Result:

- `13 passed in 1.18s`

### 2. Targeted frontend

Command:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx src/views/qualityViews.test.tsx
```

Result:

- `Test Files 4 passed`
- `Tests 13 passed`

### 3. Broad backend gate

Command:

```bash
python3 -m pytest tests/test_project_knowledge.py tests/test_api.py tests/test_grantability.py -q
```

Result:

- `65 passed in 2.04s`

### 4. Broad frontend gate

Command:

```bash
npm --prefix frontend test -- --run
```

Result:

- `Test Files 31 passed`
- `Tests 195 passed`

### 5. Frontend build

Command:

```bash
npm --prefix frontend run build
```

Result:

- build passed
- output bundles emitted under `frontend/dist/`

## Manual Smoke

Feasible and completed with local dev servers:

- Backend: `uvicorn backend.app.main:app --reload --port 8000`
- Frontend: `npm --prefix frontend run dev -- --host 127.0.0.1 --port 4173`

Smoke steps performed:

1. Created a fresh project through `POST /api/projects`:
   - name: `Task7 Manual Smoke 1782733532117`
   - id: `d6269aff4d9d4da883bf53b94d5b5f5e`
2. Opened the dev app at `http://127.0.0.1:4173/` and selected that project.
3. Opened `专家工具`.
4. Verified the default Knowledge surface renders `项目现有技术库`, not the old manual-import-first flow.
5. Verified Knowledge status shows `检索计划待确认`.
6. Verified the Knowledge panel note says the project has not completed search and that grantability remains evidence-gated.
7. Opened `授权前景`.
8. Verified the grantability note references live corpus state, including:
   - status `search_plan_pending`
   - included document count `0`
   - quality flag `needs_search`
   - fail-closed copy that only evidence-insufficient or gated conclusions are allowed

Manual smoke summary:

- Knowledge build tab defaults to project evidence corpus workflow: yes
- Grantability note references project corpus state: yes

## Broad-Failure Handling

- No broad-gate failure occurred.
- No narrow-gate rerun was required after broad-gate failure.

## Files Changed For Task 7

- `docs/project-design-overview.md`
- `.superpowers/sdd/task-7-report.md`

## Residual Gaps

- No production spec text change was needed because the design spec already matched the implemented fake-provider-first and fail-closed behavior.
- Manual smoke validated the default Knowledge and Grantability surfaces, but did not walk the full candidate decision plus corpus build flow entirely through UI clicks because automated backend/frontend coverage already exercises that chain end to end.

## Addendum: Branch-Level Review Blocker Fix

- Follow-up fix on branch `codex/automation-test-plan` from head `7ee9362c`.
- Wired project knowledge staleness to real project mutations and patent-point create/update/delete mutations.
- Regeneration path for `POST /api/projects/{project_id}/knowledge/search-intent` now creates a fresh intent and plan from the current project snapshot plus selected patent points.
- UI copy now refers to deterministic candidate search instead of implying a live official-source provider, and stale / needs-supplemental-search states now regenerate a fresh plan.
- Verification rerun for this addendum:
  - `python3 -m pytest tests/test_project_knowledge.py tests/test_api.py::test_project_creation_initializes_project_knowledge tests/test_api.py::test_project_knowledge_run_candidates_and_build_version -q`
  - `python3 -m pytest tests/test_api.py tests/test_project_knowledge.py tests/test_grantability.py -q`
  - `npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx src/features/corpus/CorpusWorkspace.test.tsx src/views/qualityViews.test.tsx`
  - `npm --prefix frontend run build`

---

## UI Refactor / origin/main

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

### Review fix-up
- Findings addressed:
  1. `正式提交稿` actions were grouped under `内部复核材料`.
  2. Tests did not exercise the real `ExportWorkspace` locked-guidance wrapper.
- Fix applied:
  - Moved official export links (`正式提交稿 DOCX` / `正式提交稿 MD`) and native official save actions back into the `正式提交稿` section.
  - Kept `内部复核材料` limited to internal package exports from `exportUrl` (`docx`, `md`, `mmd`, `prompt`).
  - Kept `风险说明与追溯` responsible for sidecar/risk export and preview/trace content.
  - Added section-aware `ExportView` tests that verify official and internal actions live in the correct groups.
  - Added a real `ExportWorkspace` wrapper test that covers overview cards, locked guidance, absence of repair UI, and navigation callbacks.
- Commands and results:
  - `cd frontend && npm test -- views/exportView.test.tsx features/export/ExportWorkspace.test.tsx app/routes.test.tsx` — passed
  - `cd frontend && npm run build` — passed
  - `cd frontend && npm test` — passed
  - `git diff --check` — passed
