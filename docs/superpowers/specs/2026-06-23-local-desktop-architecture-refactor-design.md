# Local Desktop Architecture Refactor Design

## Source Identity

This spec was written from:

- Worktree: `/private/tmp/patents-agent-architecture-refactor-plan`
- Source root: `/private/tmp/patents-agent-architecture-refactor-plan`
- Branch: `codex/architecture-refactor-plan`
- Short SHA: `f3948e4b`
- Baseline tree: clean at spec start
- Parent checkout observed before isolation: `/Users/leo/Projects/patents_agent`, branch `fix/code-review-hardening`, short SHA `f3948e4b`, dirty

The parent checkout is not the implementation source for this spec. Worker tasks must use dedicated branches/worktrees and must not include unrelated dirty files from `/Users/leo/Projects/patents_agent`.

## Background

PatentAgent is a single-user macOS desktop product delivered through Tauri v2. React renders the desktop UI and talks to a local FastAPI sidecar. The product is not being redesigned as a multiplayer online SaaS.

Current source already matches the broad stack direction:

- Frontend: React 19, TypeScript, Vite, Tailwind 4, Radix UI, lucide-react, Vitest.
- Backend: FastAPI, Pydantic v2, SQLite-backed local storage, document parsing/export libraries, OpenAI-compatible LLM clients.
- Desktop: Tauri v2 with a Python/FastAPI sidecar and renderer bridge.

The main refactor pressure is not framework age. It is code boundary size and state/API coupling:

- `frontend/src/App.tsx`: 2022 lines, many feature states and orchestration handlers.
- `frontend/src/api.ts`: 1600 lines of manually maintained API types and request helpers.
- `backend/app/main.py`: 3665 lines and about 100 route decorators.
- `backend/app/storage.py`: 2038 lines of persistence responsibilities.
- `backend/app/schemas.py`: 1285 lines of shared models.

## Goals

- Keep the local desktop product shape: Tauri renderer plus local FastAPI sidecar.
- Make backend routing, services, storage, and schema ownership understandable by domain.
- Make frontend workflows smaller, testable, and less dependent on one global `App.tsx` state object.
- Introduce generated API types from FastAPI OpenAPI so frontend/backend contracts stop drifting.
- Introduce TanStack Query for server state and cache invalidation instead of hand-rolled refetch state.
- Introduce a light route/workspace structure for React screens without turning the app into a web SaaS.
- Add SQLAlchemy 2 and Alembic as the migration path for local SQLite while keeping existing data compatible.
- Preserve current release gates, desktop smoke expectations, export safety gates, and annotated repair editor regressions.
- Split implementation into reviewable PRs that can be assigned to Hermes workers with disjoint file ownership where practical.

## Non-Goals

- No multiplayer, accounts, cloud tenancy, websocket collaboration, or server-hosted SaaS deployment.
- No Electron migration.
- No Rust rewrite of patent-domain logic.
- No SwiftUI rewrite for the current refactor train.
- No wholesale database rewrite in one PR.
- No visual redesign beyond layout fixes needed to preserve behavior after frontend decomposition.
- No relaxation of official draft compile, post-draft review, export readiness, DMG, or DOM smoke gates.

## Recommended Architecture

### Frontend

Keep React 19, TypeScript, Vite, Tailwind 4, Radix UI, lucide-react, Vitest, and Playwright.

Add:

- `@tanstack/react-query` for server state.
- `@tanstack/react-router` for explicit desktop app routes and view boundaries.
- `openapi-typescript` plus `openapi-fetch` for generated API types and typed request helpers.
- `react-hook-form` and `zod` for forms that currently mix view state and validation.

Do not introduce a large global client store by default. Use local component state for UI-only state, TanStack Query for server state, and small feature hooks for workflow orchestration. If a guided workflow becomes difficult to reason about after extraction, use an explicit reducer first; add XState only for a bounded state machine with named transitions and tests.

### Backend

Keep FastAPI and Pydantic v2.

Add:

- `backend/app/api/` routers grouped by domain.
- `backend/app/services/` for business operations that combine storage, LLMs, runtime state, and exporters.
- `backend/app/repositories/` for persistence interfaces and concrete SQLite implementations.
- SQLAlchemy 2 and Alembic for new and migrated SQLite tables.

`backend/app/main.py` should become composition code: build settings, store/index/LLM state, register routers, and expose startup diagnostics. Route handlers should move into domain routers and call services with explicit dependencies.

### API Contract

FastAPI OpenAPI is the source of truth.

The frontend should generate types into `frontend/src/generated/api/` using a deterministic command. The generated folder is checked in only if the project chooses that policy in the PR plan; otherwise the command must run during frontend build/test. The first train should check in the generator config and generated types so worker PRs have stable diffs.

Manual wrappers in `frontend/src/api.ts` should become thin compatibility exports while screens migrate. New screens and migrated vertical slices should use generated types and feature query hooks.

### Desktop Boundary

Tauri stays responsible for:

- launching and supervising the local backend sidecar;
- exposing the backend base URL to the renderer;
- desktop config bridge commands;
- file/folder open/save affordances;
- startup logging and packaged DOM smoke.

Tauri should not absorb patent drafting, review, export, or LLM orchestration logic.

### Data Boundary

Keep SQLite as the local durable store. Introduce SQLAlchemy/Alembic gradually:

1. Add an Alembic environment that targets the local desktop data directory.
2. Wrap existing SQLite operations behind repositories before migrating tables.
3. Migrate one low-risk table family first, such as projects and project metadata.
4. Keep backward-compatible read paths until existing user data is migrated by a tested upgrade step.

## Alternative Approaches Considered

### Full Rewrite With Next.js And A Web Backend

This would improve web deployment ergonomics but works against the current desktop product. It adds routing, deployment, auth, hosting, and state complexity that the user explicitly does not want.

### Native SwiftUI Shell With Python Sidecar

This can improve macOS feel, but it is a large UI rewrite. The current React/Tauri surface already has release gates, tests, and packaging scripts. SwiftUI is better reserved for a future native-client decision, not this architecture cleanup.

### Keep Current Stack Without New Libraries

This avoids dependency churn but leaves the main pain intact: manual API contracts and a very large `App.tsx` state surface. Adding TanStack Query and OpenAPI-generated types is a small, targeted dependency increase that directly reduces recurring maintenance cost.

## Target Boundaries

### Backend Domains

The first refactor train should create these router/service boundaries:

- `system`: health, agent doctor, desktop config health.
- `desktop_config`: read/update/clear/test local LLM config.
- `corpus`: corpus documents, jobs, versions, search, stats.
- `projects`: create/list/get/update/delete projects, materials, patent points.
- `drafts`: generation, draft package updates, external draft intake.
- `quality`: filing readiness, grantability, claim defense, completion, score improvement.
- `post_draft`: post-draft review, repair session, safe patches, repair patches.
- `exports`: official compile, export readiness, docx/markdown/diagram downloads.

The first train does not need to move all endpoints at once. It must establish the pattern, migrate at least two low-risk domains, and document the remaining migration map.

### Frontend Domains

The first refactor train should create these view/query boundaries:

- `frontend/src/app/`: route tree, query client provider, shell integration.
- `frontend/src/features/projects/`: project list, selected project, materials, patent points queries.
- `frontend/src/features/corpus/`: corpus queries and job mutations.
- `frontend/src/features/quality/`: readiness, grantability, claim defense, completion queries.
- `frontend/src/features/postDraft/`: post-draft review and repair editor queries.
- `frontend/src/features/settings/`: desktop config forms and health checks.

`frontend/src/App.tsx` should shrink by moving orchestration into feature components/hooks, not by hiding the same global state in a new file.

## Data Flow

1. Tauri starts the FastAPI sidecar and exposes `get_backend_base_url`.
2. The React app initializes a query client and typed API client.
3. Feature routes call query hooks that use generated OpenAPI types.
4. Mutations invalidate only the affected query keys.
5. Backend routers validate request/response models and call services.
6. Services call repositories and deterministic helpers.
7. Long-running operations continue to return persisted run objects with clear status.
8. Exports remain gated by official compile, matching draft hash, and post-draft review state.

## Error Handling

- Backend services raise domain errors that route handlers translate to `HTTPException` with stable status codes.
- Frontend query hooks expose server errors to existing `RiskBanner`, `OperationConsole`, and toast surfaces.
- Mutations that can stale official drafts must explicitly invalidate official compile and post-draft review queries.
- Desktop config writes keep the existing origin checks and Tauri bridge protections.
- API generation must fail CI if OpenAPI generation changes unexpectedly without committed output.

## Testing Strategy

Backend:

- Keep existing pytest coverage green.
- Add router tests for every migrated domain.
- Add service unit tests around dependency-injected store/LLM/provider objects.
- Add migration tests for SQLAlchemy/Alembic introduction before migrating user data.

Frontend:

- Keep existing Vitest coverage green.
- Add query hook tests with mocked fetch/Tauri base URL resolution.
- Add route smoke tests for the new route tree.
- Add interaction tests for at least one migrated vertical slice.
- Keep Playwright/DOM smoke for desktop UI surfaces touched by decomposition.

Packaging:

- PRs that touch Tauri or package scripts must follow `docs/release/dmg-ui-regression-guard.md`, `docs/release/v1.1.0-tauri-release-gate.md`, and `docs/release/v1.1.0-tauri-packaging.md`.
- PRs that only move React/Python source do not need DMG handoff, but final integration must run the release gate selected in the plan.

## PR Train

The implementation should be split into these PRs:

| PR | Owner | Branch | Purpose | Merge Dependency |
|---|---|---|---|---|
| PR-0 | Codex | `codex/architecture-refactor-plan` | Spec, implementation plan, Hermes board/cards | none |
| PR-1 | `deepseekworker` | `codex/refactor-backend-router-foundation` | Add backend router/service foundation and migrate system + desktop config endpoints | PR-0 |
| PR-2 | `deepseekworker` | `codex/refactor-backend-projects-corpus` | Migrate projects/materials/patent-points and corpus endpoints into routers/services | PR-1 |
| PR-3 | `qwenworker` | `codex/refactor-frontend-api-query-foundation` | Add generated API types, typed client, query client, and migrate health/settings/project list reads | PR-1 |
| PR-4 | `qwenworker` | `codex/refactor-frontend-app-decomposition` | Split `App.tsx` into app shell, routes, feature hooks, and selected project orchestration | PR-3 |
| PR-5 | `deepseekworker` | `codex/refactor-storage-repository-migrations` | Add repository seams, SQLAlchemy/Alembic scaffold, and migrate one low-risk table family with compatibility tests | PR-2 |
| PR-6 | `kimiworker` + `codexreviewer` | `codex/refactor-architecture-integration-qa` | Patent workflow QA, desktop smoke, docs update, final merge-readiness review | PR-4 and PR-5 |

PR-3 can start after PR-1 because it depends on a stable OpenAPI composition pattern. PR-4 waits for PR-3. PR-5 can proceed after PR-2. PR-6 waits for all implementation PRs.

## Hermes Dispatch Requirements

Every Hermes worker card must include:

- Source branch and base SHA.
- Required worktree mode and branch.
- Exact files or modules in scope.
- Files/modules explicitly out of scope.
- Commands to run.
- UI screenshot/browser requirements when touching React surfaces.
- Merge blocker conditions.
- Reminder that workers must read `AGENTS.md`, must not revert unrelated changes, and must not commit secrets, auth stores, `.env`, generated DMGs, or unrelated dirty files.

Before real dispatch, run:

```bash
hermes kanban dispatch --dry-run --max 1
```

Use real bounded dispatch only after PR-0 is committed and the board contains reviewed cards.

## Merge Policy

- Codex owns PR-0 and final review.
- Worker PRs must be reviewed before merge, even when tests pass.
- Merge order is PR-0, PR-1, PR-2 and PR-3 as allowed by dependencies, PR-4, PR-5, PR-6.
- No PR may relax official export gates, post-draft repair safety checks, desktop config origin checks, or packaged app smoke checks.
- No PR may claim UI completion from specs, screenshots, or OpenDesign exports. UI evidence must come from `frontend/src/` and a running app.
- No PR may use stale `/Volumes/PatentAgent` as packaged UI evidence.

## Acceptance Criteria

- `backend/app/main.py` is reduced to app composition and route registration for migrated domains.
- Migrated backend domains have routers, services, tests, and no behavioral regressions.
- `frontend/src/App.tsx` is reduced by moving feature orchestration into route/feature modules.
- At least one vertical frontend slice uses generated OpenAPI types and TanStack Query.
- Existing API functions remain compatible until all call sites migrate.
- SQLAlchemy/Alembic scaffold exists with a tested compatibility path for one migrated local SQLite table family.
- `python3 -m pytest` passes for affected backend tests.
- `npm --prefix frontend test -- <affected tests>` passes for affected frontend tests.
- `npm --prefix frontend run build` passes before integration merge.
- Final integration runs the relevant desktop smoke gate and records evidence.

## Spec Self-Review

- Placeholder scan: no placeholder requirements remain.
- Consistency check: frontend, backend, desktop, and data sections all preserve local single-user desktop delivery.
- Scope check: implementation is split into seven PRs, with the first train establishing patterns and migrating representative domains rather than attempting a risky one-shot rewrite.
- Ambiguity check: multiplayer/SaaS work, Electron migration, SwiftUI rewrite, Rust domain rewrite, and gate relaxation are explicit non-goals.
