---
status: verified
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 5efe5e46
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_start: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-frontend-next-spec.md
  - docs/ui-redesign/omp/2026-07-06-grantatlas-frontend-next-plan.md
---

# Export Navigation Evidence

## Implemented Slice

OMP implemented the export navigation integration slice: locked export guidance and formal-draft contamination warnings now expose direct actions back to `文稿与修复` / `标注修复`.

## Verification

Commands run from `/Users/leo/Projects/patents_agent_omp_frontend_next/frontend`:

```bash
npm test -- views/exportView.test.tsx features/export/ExportWorkspace.test.tsx app/routes.test.tsx
npm test
npm run build
```

Results:

- Targeted Vitest: 3 files passed, 29 tests passed.
- Full frontend Vitest: 41 files passed, 314 tests passed.
- Frontend build: passed.

## Browser Smoke

Current-source dev server:

```bash
npm run dev -- --port 5175
```

Playwright opened `http://127.0.0.1:5175/`, navigated to `导出`, and checked desktop and mobile viewports.

- Desktop viewport: `1440x1000`, export heading visible, no horizontal overflow.
- Mobile viewport: `390x844`, export heading visible, no horizontal overflow.
- Backend API calls returned 500 because this smoke intentionally started only the frontend dev server, not the backend. The UI still rendered the export workspace.

Screenshots:

- `docs/ui-redesign/evidence/screenshots/2026-07-06-5efe5e46-export-navigation-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-5efe5e46-export-navigation-mobile.png`
