---
status: verified
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: a85b69bf
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_start: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-project-load-recovery-spec.md
  - docs/ui-redesign/omp/2026-07-06-grantatlas-project-load-recovery-plan.md
---

# Project Load Recovery Evidence

## Implemented Slice

AGY with Gemini 3.5 Flash (Medium) produced the project-load recovery spec and plan, then implemented the production React update in `frontend/src/views/projectViews.tsx`. Codex completed the tests and verification.

The implemented behavior:

- `ProjectSelect` keeps stale project options selectable when project loading fails.
- The failed select state renders `项目列表加载失败。恢复后端连接后，使用右上角刷新重试。`.
- The helper text is associated with the select through `aria-describedby`.
- `ProjectsOverview` failed empty states clarify that the user is seeing a load failure, not a true empty project list, and point to the top-right refresh path.

## Verification

Commands run from `/Users/leo/Projects/patents_agent_omp_frontend_next/frontend`:

```bash
npm test -- projectViews.test.tsx
npm run build
npm test
```

Results:

- Targeted Vitest: 1 file passed, 5 tests passed.
- Frontend build: passed.
- Full frontend Vitest: 41 files passed, 323 tests passed.

## Browser Smoke

Current-source dev server:

```bash
npm run dev -- --port 5178
```

Playwright opened `http://127.0.0.1:5178/` with only the frontend dev server running, so project loading intentionally entered the failed/offline recovery state.

- Desktop viewport: `1440x980`, select helper visible, select `aria-describedby` points to the helper, no horizontal overflow.
- Mobile viewport: `390x844`, select helper visible and wrapped cleanly, select `aria-describedby` points to the helper, no horizontal overflow.

Screenshots:

- `docs/ui-redesign/evidence/screenshots/2026-07-06-a85b69bf-project-load-recovery-desktop.png`
- `docs/ui-redesign/evidence/screenshots/2026-07-06-a85b69bf-project-load-recovery-mobile.png`
