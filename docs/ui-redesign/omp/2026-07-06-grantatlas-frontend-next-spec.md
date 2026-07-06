---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 5efe5e46
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas Export Navigation Improvement Spec

This specification describes a next-step frontend improvement to streamline the user experience when export gates are locked or when contamination warning alerts are displayed in the export workspace.

## 1. Current UI Problem

In the current production React frontend source:
- In `frontend/src/views/exportView.tsx`, if the export is locked (due to incomplete quality checks, missing official compile runs, or blocked review gates), or if the official compile run contains contamination matches (internal review traces/memos), the user is presented with static alerts explaining the blockers.
- However, there is no direct call-to-action or link button inside the warning callouts or lock status cards to help users navigate back to the relevant document workbench tab (e.g., the annotated repair tab or edit tab) to resolve those blockers.
- To resolve the problems, the user must manually navigate to the sidebar "文稿与修复" and switch tabs. This creates navigation friction, especially since the export workspace already knows the specific gates that are blocking progress.

## 2. Desired User Outcome

- When the export is locked, the locked status card (`InfoCard` under "正式提交稿") should display a clear, context-aware secondary action button (e.g., "前往文稿与修复 / 标注修复" or "去处理问题") when an actionable state exists.
- When contamination matches (internal markers) are detected in the official compile run, the warning callout should display a direct button guiding the user to the document workspace to execute cleanups and trigger revalidation.
- Clicking these buttons should seamlessly switch the sidebar view to `documents` and focus the `annotated` (or appropriate) tab, reducing cognitive overhead and clicks.

## 3. Scope

- **Icon Registry**: Re-export `FileSearch`, `FolderOpen`, and `ArrowRight` (or similar navigation icons) in the central registry `frontend/src/lib/icons.ts` if not already present.
- **ExportView component**:
  - Accept an optional `onNavigateDocuments?: (target: "overview" | "annotated") => void` prop.
  - Inside the "正式提交稿" lock `InfoCard` and the "检测到正式稿仍包含 X 处内部痕迹" `callout-warn` banner, render navigation buttons calling `onNavigateDocuments("annotated")` or `onNavigateDocuments("overview")` when provided.
- **ExportWorkspace wiring**:
  - Pass the existing `onNavigateDocuments` handler down to `ExportView`.
- **Unit Tests**:
  - Add test assertions in `frontend/src/views/exportView.test.tsx` to verify the presence of navigation actions and ensure they invoke the callback.

## 4. Non-Goals

- Do not modify the backend APIs, database models, or Tauri packaging configurations.
- Do not restyle the sidebar, sidebar menus, or global shells.
- Do not introduce new UI libraries (e.g., Radix, shadcn packages) not already present in the codebase.

## 5. Verification

- Run focused Vitest unit tests:
  ```bash
  cd frontend && npm test -- views/exportView.test.tsx
  ```
- Build the frontend project to verify type-safety:
  ```bash
  cd frontend && npm run build
  ```
- Confirm the new navigation actions render correctly and trigger callbacks without warnings.
