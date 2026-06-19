# Post-Draft Review Repair Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the incremental post-draft repair workbench with independent blocker scrolling, a larger manual draft editor, and safe-patch AI repair affordances.

**Architecture:** Add a narrow draft package update endpoint, expose it through `frontend/src/api.ts`, pass save/current-package props through `App` and `GuidedPatentFlowView`, and render the workbench/editor in `PostDraftReviewPanel`. Keep the first increment textarea-based and preserve all existing draft package metadata.

**Tech Stack:** FastAPI, Pydantic, React 19, Vite, Vitest, pytest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tests/test_post_draft_review.py`
- Create: `frontend/src/PostDraftReviewPanel.test.tsx`

- [ ] Add a backend test that `PUT /api/projects/{id}/draft-package` updates title/claims/description fields, preserves metadata, and changes the current post-draft hash.
- [ ] Add a frontend static render test that `PostDraftReviewPanel` renders a scrollable repair workbench, an `打开大编辑器` entry, and per-issue `人工修正` / `一键AI修正` controls.
- [ ] Run the targeted backend and frontend tests and confirm both fail for the missing endpoint/UI.

### Task 2: Backend Save Endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/api.ts`

- [ ] Add `DraftPackageManualUpdate` with `title`, `abstract`, `claims`, `description`, and `drawing_description`.
- [ ] Add `PUT /api/projects/{project_id}/draft-package` that requires an existing package, merges those five fields into it, saves via `store.update_project_package`, and returns the updated package.
- [ ] Add `updateProjectDraftPackage` to the frontend API module.
- [ ] Run the backend test and confirm it passes.

### Task 3: Workbench And Editor UI

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/GuidedPatentFlow.tsx`
- Modify: `frontend/src/flow/panels/PostDraftReviewPanel.tsx`
- Modify: `frontend/src/styles.css`

- [ ] Wire `currentPackage` and `onSaveDraftPackage` from `App` through `GuidedPatentFlowView` into `PostDraftReviewPanel`.
- [ ] Add a two-column workbench where the left issue list has an independent scroll container and the right side stays stable.
- [ ] Add a large editor dialog with section tabs/fields and a save action that calls `onSaveDraftPackage`.
- [ ] Render `人工修正` buttons that open the editor and `一键AI修正` buttons that call the existing safe-patch callback when available.
- [ ] Run the frontend test and confirm it passes.

### Task 4: Verification

**Files:**
- No new files.

- [ ] Run targeted pytest for post-draft review.
- [ ] Run targeted Vitest for the post-draft review panel.
- [ ] Run the frontend build to catch TypeScript and CSS regressions.
