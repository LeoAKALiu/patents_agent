---
status: passed
captured_at: 2026-07-06
source_identity:
  branch: codex/agy-grantatlas-all-surfaces-redesign
  base_short_sha: af9aecb9
  initial_implementation_short_sha: c3736e82
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  base: origin/main
implementation_agent: agy Gemini 3.5 Flash Medium started, Codex completed and verified
---

# All-Surfaces Redesign Evidence

## Production Scope

Production React source changed under `frontend/src/`:

- `frontend/src/ui/PrimarySurface.tsx`
- `frontend/src/app/AppRoot.tsx`
- `frontend/src/styles.css`
- `frontend/src/runtimeDisplay.ts`

Test coverage changed under `frontend/src/`:

- `frontend/src/app/routes.test.tsx`
- `frontend/src/runtimeDisplay.test.ts`
- `frontend/src/SettingsPanel.test.tsx`

Design/spec artifacts:

- `docs/ui-redesign/agy/2026-07-06-grantatlas-all-surfaces-redesign-spec.md`
- `docs/ui-redesign/agy/2026-07-06-grantatlas-all-surfaces-redesign-plan.md`

## Acceptance Checks

- All seven primary destinations render the shared `PrimarySurface` chrome:
  `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, `设置`.
- Each destination has a stable `data-testid="primary-surface-{id}"`.
- Route-specific copy and status chips are task-state oriented and avoid raw hashes/API paths.
- Existing nested workspaces remain mounted inside their existing flows.
- Health-check failures are demoted on all primary surfaces.
- Generic app 5xx errors keep raw details in diagnostics but do not expose raw API paths as primary UI copy.
- The topbar no longer renders duplicate page headings; the shared primary surface is the route title source.
- Desktop and mobile browser smoke found no horizontal overflow.

## Commands

```bash
cd frontend && npm test -- app/routes.test.tsx SettingsPanel.test.tsx runtimeDisplay.test.ts
cd frontend && npm test -- app/routes.test.tsx features/workbench/WorkbenchWorkspace.test.tsx features/documentRepair/DocumentRepairWorkspace.test.tsx features/export/ExportWorkspace.test.tsx projectViews.test.tsx SettingsPanel.test.tsx runtimeDisplay.test.ts
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

## Browser Smoke

Dev server:

```bash
cd frontend && npm run dev -- --port 5179
```

Browser smoke used Chromium against `http://127.0.0.1:5179/` with backend offline. It clicked each real sidebar navigation item on desktop `1440x980` and mobile `390x844`, waited for the matching `primary-surface-*` hook, asserted no horizontal overflow, asserted the topbar had zero heading elements, and asserted visible body text did not include `/api/health`, `/api/desktop-config`, or `/api/evidence-sources`.

## Screenshots

- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-workbench-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-projects-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-documents-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-knowledge-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-expert-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-export-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-settings-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-workbench-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-projects-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-documents-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-knowledge-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-expert-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-export-mobile.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-af9aecb9-all-surfaces-settings-mobile.png`
