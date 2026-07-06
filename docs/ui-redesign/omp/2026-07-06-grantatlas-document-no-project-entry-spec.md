---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: e48cc707
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas Document No-Project Entry Guidance Spec

This specification describes the requirements for handling the no-project entry-intent redirection inside the `DocumentRepairWorkspace` component.

## 1. Current UI Problem

In the current React frontend:
- When a user is guided/routed to the `文稿与修复` workspace with a requested tab of `标注修复` (`requestedTab === "annotated"`), but no project is selected (`projectState.selectedProject === null` or loading has failed), the workspace still switches to the `标注修复` tab.
- This results in rendering an empty, broken, or misleading repair workspace layout (e.g. displaying "暂无可修复会审" or "请先选择项目" on a blank surface).
- Since `标注修复` completely relies on project review sessions and draft data, showing this tab is misleading when there is no active project context.
- There is no clear visual guidance or actionable recovery path instructing the user that they must select a project first, nor any quick-access navigation to go to the `项目` workspace.

## 2. Desired User Outcome

- **Automated Fallback**: If a user attempts to enter the `标注修复` (or other repair-oriented) tab via external navigation (`requestedTab === "annotated"`) but no project is currently selected, the system should select/stay on the `总览` (overview) tab or default back to it. This keeps them on a stable, non-empty workspace.
- **Guidance Band**: Provide a concise, clear guidance band at the top of the workspace (near the header) indicating that a project must be selected first (e.g., "标注修复需要选择项目后才能展示会审问题与修复正文。").
- **Clear Navigation Path**:
  - The guidance band should offer a prominent, task-state oriented action: a primary button/link "选择项目" to navigate to the `项目` list view via `onNavigate("projects")`.
  - A secondary action to dismiss the guidance or stay on the current tab layout.
- **Stale State Avoidance**: The guidance band must automatically clear/hide when the user manually switches tabs or clicks the close/dismiss button.
- **Design Alignment**: Clean, solid background styling matching the workbench aesthetics. No raw database hashes, run IDs, or logs exposed in the copy. All copy remains in Chinese.

## 3. Scope

- **DocumentRepairWorkspace Component**:
  - Intercept the `requestedTab === "annotated"` condition when `projectState.selectedProject === null`.
  - Prefer keeping/resetting the active tab to `overview` instead of rendering `annotated`.
  - Activate a specific no-project guidance band type (e.g., `guidanceType === "no-project"`).
  - Render a clear dismissible alert band featuring:
    - Text: `标注修复需要选择项目后才能展示会审问题与修复正文。`
    - Main action: A button to navigate to `项目` (`onNavigate("projects")`).
    - Dismiss/Secondary action: A button/icon to close or dismiss the alert.
- **Unit Tests**:
  - Cover the fallback behavior: `activeTab` stays/defaults to `overview` when no project is selected even if `requestedTab === "annotated"`.
  - Assert the guidance band is displayed with the correct warning text.
  - Verify that clicking "选择项目" triggers `onNavigate("projects")`.
  - Verify that switching tabs or dismissing the guidance hides the alert.

## 4. Non-Goals

- Do not modify backend API paths or schemas.
- Do not introduce any third-party UI libraries (e.g., Tailwind, new component suites).
- Do not restyle global shell headers, sidebars, or default navigation.

## 5. Verification

- Run unit tests:
  ```bash
  cd frontend && npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx
  ```
- Build the frontend project to verify type-safety:
  ```bash
  cd frontend && npm run build
  ```
