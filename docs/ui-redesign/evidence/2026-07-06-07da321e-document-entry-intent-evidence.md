---
status: verified
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 07da321e
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_start: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-entry-intent-spec.md
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-entry-intent-plan.md
---

# Document Entry Intent Evidence

## Implemented Slice

OMP started the document entry-intent guidance slice. Codex completed review fixes after the OMP run hit a Google Cloud Code quota limit.

The implemented behavior:

- `文稿与修复` shows a concise guidance band when routed into `标注修复` from export/workbench intent.
- The guidance band can return to `总览`, stay on `标注修复`, or be dismissed.
- Manual tab changes clear the guidance so it does not become stale.
- A locked export state can show a document-repair guidance band, but it does not override an active external navigation intent.

## Verification

Commands run from `/Users/leo/Projects/patents_agent_omp_frontend_next/frontend`:

```bash
npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx app/routes.test.tsx
npm test
npm run build
```

Results:

- Targeted Vitest: 2 files passed, 35 tests passed.
- Full frontend Vitest: 41 files passed, 318 tests passed.
- Frontend build: passed.

## Browser Smoke

Current-source dev server:

```bash
npm run dev -- --port 5176
```

Playwright opened `http://127.0.0.1:5176/`, navigated from `导出` to `文稿与修复 / 标注修复`, and checked desktop and mobile viewports.

- Desktop viewport: `1440x1000`, document heading visible, guidance band visible, `标注修复` tab selected, no horizontal overflow.
- Mobile viewport: `390x844`, document heading visible, guidance band visible, `标注修复` tab selected, no horizontal overflow.
- Backend API calls returned 500 because this smoke intentionally started only the frontend dev server, not the backend. The UI still rendered the target flow.

Screenshots:

- `docs/ui-redesign/evidence/screenshots/2026-07-06-07da321e-document-entry-intent-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-07da321e-document-entry-intent-mobile.png`
