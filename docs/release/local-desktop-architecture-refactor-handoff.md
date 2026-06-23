# Local Desktop Architecture Refactor Handoff

## Source

- Branch: `codex/refactor-architecture-integration-qa`
- Short SHA at worker handoff: `fa6ecbe`
- Final pre-review merge SHA: `d8f373d`
- Current PR branch tip is the authoritative reviewed SHA after follow-up
  commits.
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/t_cd5e347c`
- Dirty status at worker handoff: clean
- Codex reviewer follow-up: added `tests/test_tauri_build_prereqs.py`,
  performed desktop running-app QA, and updated this handoff on top of
  `fa6ecbe`.
- Review follow-up after PR creation: addressed Claude review feedback by
  removing small dead-code smells, documenting Tauri backend URL memoization,
  moving SQLAlchemy/Alembic to optional `dev`/`migration` extras, and excluding
  the unwired migration scaffold from the PyInstaller sidecar.

## PRs Reviewed

- PR-0: Planning baseline — spec and plan merged from
  `codex/architecture-refactor-plan` at 895f5c76
- PR-1: Backend Router Foundation — merged into PR-4 via d0b626e6 / cherry-picked into PR-5 via 83871a3d
- PR-2: Backend Projects and Corpus Domains — merged into PR-5 at 6905694b
- PR-3: Frontend API and Query Foundation — merged into PR-4 at 17e654e7 / 7be7a3e0
- PR-4: Frontend App Decomposition — branch `codex/refactor-frontend-app-decomposition` at 74944c77
- PR-5: Storage Repository and Migration Foundation — branch `codex/refactor-storage-repository-migrations` at 51d7da83

Merged both PR-4 (74944c77) and PR-5 (51d7da83) into integration branch. Clean merge, no conflicts.
Codex reviewer also merged PR-0 planning docs into the final result so the
architecture spec and implementation plan are present in the deliverable branch.

## Commands

- `python3 -m pytest tests/test_api_router_foundation.py tests/test_projects_api_router.py tests/test_corpus_api_router.py tests/test_project_repository.py -q`
  - Result: **53 passed** in 4.96s

- `npm --prefix frontend test -- features/system/queries.test.ts app/routes.test.tsx GuidedPatentFlowView.test.ts PostDraftRepairEditor.test.tsx`
  - Result: **4 files, 15 tests passed** in 1.22s

- `npm --prefix frontend run build`
  - Result: **passed** (1900 modules transformed, built in 1.38s)

- `python3 -m pytest tests/test_tauri_desktop_skeleton.py -q`
  - Result: **11 passed** in 0.05s

- `python3 -m pytest tests/test_tauri_desktop_skeleton.py tests/test_tauri_build_prereqs.py -q`
  - Result after Claude review follow-up: **17 passed** in 0.03s

- `python3 -m pytest tests/test_corpus_api_router.py tests/test_tauri_build_prereqs.py tests/test_db_session.py -q`
  - Result after Claude review follow-up: **18 passed** in 1.81s.

- Broader backend regression: `python3 -m pytest tests/test_db_session.py tests/test_project_repository.py tests/test_corpus_api_router.py tests/test_api_router_foundation.py tests/test_patent_points.py tests/test_disclosure.py tests/test_deep_research.py tests/test_grantability.py tests/test_claim_defense.py tests/test_draft_completion_api.py -q`
  - Result: **133 passed, 1 skipped** in 7.33s

- `npm --prefix frontend run build` (frontend production build)
  - Result: **passed**

- Desktop running-app QA after Codex reviewer follow-up:
  - Backend: `PATENTAGENT_BACKEND_DATA_DIR=/tmp/patentagent-pr6-backend-data python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
  - Frontend: `npm --prefix frontend run dev -- --host 127.0.0.1 --port 5178`
  - Playwright desktop viewport: `1440x1100`
  - Console: no errors, no warnings; only the React DevTools info message.

## UI Evidence

- No Tauri packaging, `src-tauri/`, or package script changes touched in PR-4 or PR-5. DMG packaging is not required.
- Mobile viewport evidence is intentionally out of scope. Patent drafting is
  a desktop/Tauri workflow, and the user explicitly de-scoped mobile
  maintenance for this refactor.
- Frontend src files verified: `AppRoot.tsx`, `ShellLayout.tsx`, `routes.tsx`, `ProjectWorkspace.tsx`, `CorpusWorkspace.tsx`, `QualityWorkspace.tsx`, `PostDraftWorkspace.tsx` all present and wired.
- `PostDraftRepairEditor.test.tsx` passes, confirming repair editor UI surface is intact.
- `GuidedPatentFlowView.test.ts` passes, confirming guided patent flow UI surface is intact.
- Frontend build output written to `frontend/dist/` — production bundle verified.
- Desktop running-app screenshots captured from this integration worktree:
  - `output/playwright/pr6-start-desktop-1440x1100.png`
  - `output/playwright/pr6-projects-desktop-1440x1100.png`
  - `output/playwright/pr6-settings-desktop-1440x1100.png`
  - `output/playwright/pr6-expert-desktop-1440x1100.png`

## Architecture Check

- `backend/app/main.py`: 3286 lines (was ~3665, reduced by ~379 lines)
- `frontend/src/App.tsx`: 1808 lines (was ~2022, reduced by ~214 lines)
- Routers registered in `main.py`: system, desktop_config, corpus, projects
- Feature workspaces: projects, corpus, quality, post-draft, settings, system
- Generated API types: `frontend/src/generated/api/schema.d.ts` (5465 lines)
- Query client: `frontend/src/lib/queryClient.ts` wired in `frontend/src/main.tsx`
- Typed API client: `frontend/src/lib/apiClient.ts` with Tauri bridge
- SQLAlchemy/Alembic migration scaffold: present for future local SQLite
  migration work, but optional-only and excluded from the current PyInstaller
  sidecar until production storage is wired to the ORM path.

## Merge Recommendation

- Verdict: **Ready for review**
- Blockers: none
- Residual risks:
  - PR-4 HEAD used was 74944c77 (actual branch tip), not the superseded 9da2a7d2 referenced in an earlier task comment.
  - Post-draft repair editor was covered by component tests in this pass; no fixture project with repairable review data was available for a live editor-entry flow.
