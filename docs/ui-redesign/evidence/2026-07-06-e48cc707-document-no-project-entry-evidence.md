---
status: verified
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: e48cc707
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_start: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-no-project-entry-spec.md
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-no-project-entry-plan.md
---

# Document No-Project Entry Evidence

## Implemented Slice

AGY with Gemini 3.5 Flash implemented the no-project entry guidance slice for `文稿与修复`.

The implemented behavior:

- If external navigation requests `标注修复` while no project is selected, the workspace stays on `总览`.
- A concise guidance band explains that `标注修复` needs a selected project before it can show review issues and draft sections.
- The primary action `选择项目` routes to the `项目` workspace.
- The guidance can be dismissed or cleared by manual tab changes.

## Verification

Commands run from `/Users/leo/Projects/patents_agent_omp_frontend_next/frontend`:

```bash
npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx app/routes.test.tsx
npm test
npm run build
```

Results:

- Targeted Vitest: 2 files passed, 38 tests passed.
- Full frontend Vitest: 41 files passed, 321 tests passed.
- Frontend build: passed.

## Browser Smoke

Current-source dev server:

```bash
npm run dev -- --port 5177
```

Playwright opened `http://127.0.0.1:5177/`, navigated from `导出` to `文稿与修复 / 标注修复` without a selected project, and checked desktop and mobile viewports.

- Desktop viewport: `1440x1000`, document heading visible, no-project guidance visible, `总览` tab selected, `标注修复` not selected, `选择项目` action visible, no horizontal overflow.
- Mobile viewport: `390x844`, document heading visible, no-project guidance visible, `总览` tab selected, `标注修复` not selected, `选择项目` action visible, no horizontal overflow.
- Backend API calls returned 500 because this smoke intentionally started only the frontend dev server, not the backend. The UI still rendered the target recovery state.

Screenshots:

- `docs/ui-redesign/evidence/screenshots/2026-07-06-e48cc707-document-no-project-entry-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-e48cc707-document-no-project-entry-mobile.png`
