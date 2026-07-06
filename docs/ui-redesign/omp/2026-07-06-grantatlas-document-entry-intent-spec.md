---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 07da321e
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas Document Entry-Intent Guidance Spec

This specification describes a next-step frontend improvement to enhance the landing experience in `DocumentRepairWorkspace` when a user navigates there via export/workbench guidance.

## 1. Current UI Problem

In the current production React frontend source:
- When a user is guided to the `文稿与修复` section from the `导出` workspace (or other workbench routes) because the export is locked or contamination/issues need resolution, they land on the requested tab (e.g. `标注修复`).
- While this tab switch happens automatically, the interface does not show any contextual indicator or message explaining why the user was routed here, or what they need to do to proceed.
- Without a clear guidance alert/band explaining the intent, the user may feel disoriented or wonder how to navigate back to `总览` or `导出` once they resolve the issues.
- We must not expose raw internal run IDs, full git hashes, internal logs, or keys to the user; the copy must be clear, concise, and task-state oriented in Chinese.

## 2. Desired User Outcome

- When the user lands on the document workspace via an external guidance action (indicated by `requestedTab`), they should see a clear and concise guidance band near the header.
- This guidance band will:
  - Explain that the user was redirected here to resolve issues blocking export or draft preparation.
  - Present clear actions: a main link/button to return to `总览` (or go to `导出` / `总览` as appropriate) and a way to dismiss the band.
  - Automatically clear itself if the user manually clicks/switches to another tab, so it does not persist as stale noise.
- The visual presentation must use clean, professional styling matching the workbench design principles (no heavy glass elements, solid backgrounds, simple icon integrations).

## 3. Scope

- **DocumentRepairWorkspace Component**:
  - Introduce local state to track whether guidance is active (e.g., `showGuidance`).
  - Set `showGuidance` to true when `requestedTab` is processed, and clear it when the user switches tabs manually or explicitly clicks "dismiss" (关闭/我知道了) or clicks "返回总览".
  - Render a clear, dismissible guidance band below the header containing the Chinese context-oriented copy and actions.
- **Unit Tests**:
  - Verify that the guidance band is displayed when `requestedTab` is passed.
  - Verify that switching tabs or clicking dismiss hides the band.
  - Verify that no raw run IDs or hashes are rendered.

## 4. Non-Goals

- Do not change any backend API, database schemas, or Tauri build scripts.
- Do not introduce new UI libraries.
- Do not restyle the sidebar, sidebar menus, or topbar layout.

## 5. Verification

- Run unit tests:
  ```bash
  cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx
  ```
- Build the frontend project to verify type-safety:
  ```bash
  cd frontend && npm run build
  ```
