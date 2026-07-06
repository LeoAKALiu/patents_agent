---
status: implemented
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/agy-grantatlas-all-surfaces-redesign
  base_short_sha: af9aecb9
  initial_implementation_short_sha: c3736e82
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas All-Surfaces Redesign Plan

## Slice 1: Shared Primary Surface

Add a reusable `PrimarySurface` component under `frontend/src/ui/`.

Acceptance:

- Renders a stable `data-testid="primary-surface-{id}"`.
- Provides eyebrow, title, description, status chips, optional actions, and dense body layout.
- Uses existing tokens and does not introduce marketing hero decoration.

## Slice 2: Wrap All Primary Routes

Update `frontend/src/app/AppRoot.tsx` so every primary navigation destination renders inside `PrimarySurface`.

Acceptance:

- `工作台`, `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, and `设置` each receive route-specific copy and status chips.
- User-facing copy avoids hashes, API paths, logs, and internal IDs.
- Existing nested workspaces keep their current behavior.

## Slice 3: Styling

Add token-based styles in `frontend/src/styles.css`.

Acceptance:

- Header is compact, professional, and responsive.
- Chips wrap instead of forcing horizontal overflow.
- Mobile layout stacks cleanly.

## Slice 4: Tests

Update route tests to prove the shared surface renders for all seven primary destinations.

Acceptance:

- `frontend/src/app/routes.test.tsx` covers each `primary-surface-*` hook.
- Existing export-to-document navigation tests remain intact.
- Existing topbar, health demotion, and route rendering tests continue to pass.

## Verification

Run:

```bash
cd frontend && npm test -- app/routes.test.tsx
cd frontend && npm run build
```

For final handoff, Codex should also run the full frontend suite and a browser smoke across desktop/mobile if the implementation remains in scope.
