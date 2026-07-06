# 2026-07-06 UI PR-4 Evidence

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent_omp_ui`
- Branch: `codex/omp-ui-hardening`
- Short SHA at PR-4 start: `3d2ffd66`
- Dev server: `http://127.0.0.1:5174/`
- Evidence mode: current-source Vite dev server, not packaged DMG

## Automated Checks

Targeted UI regression tests:

```bash
cd frontend && npm test -- app/routes.test.tsx features/workbench/WorkbenchWorkspace.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx PostDraftRepairEditor.test.tsx flow/panels/QualityPanel.test.tsx
```

Result:

```text
5 test files passed
60 tests passed
```

Production frontend build:

```bash
cd frontend && npm run build
```

Result:

```text
tsc -b && vite build succeeded
```

## Screenshot Evidence

All screenshots were captured from the current-source Vite dev server.

- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-workbench-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-workbench-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-document-repair-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-annotated-repair-empty-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-quality-tool-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-expert-tools-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-3d2ffd66-export-desktop.png`

## Observations

- All seven sidebar destinations were visible in the browser snapshot: `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, `设置`.
- Topbar chip order matched the contract: project selector, export status, run status, backend status, refresh.
- The sidebar footer stayed compact with model, agent, and backend rows.
- Workbench no-project state rendered start paths, state coverage, process progress, risk/run summary, and work queue without a blank screen.
- Document repair rendered the five tabs and the approved gate vocabulary in the no-draft state.
- Export kept formal submission, internal review material, and risk trace surfaces separate.
- Expert tools exposed the quality group and a submitted-maturity route without making expert tools the default flow.

## Limits

- Backend health returned a 500/offline state during screenshot capture, so project list and live project data were unavailable.
- The annotated repair screenshot is the no-project/empty state. The real repair-session data-flow gate is covered by `PostDraftRepairEditor.test.tsx` and `DocumentRepairWorkspace.test.tsx`, but a live project with non-empty repair-session payload was not available in this run.
- No DMG or installed app was inspected for this PR-4 evidence.

