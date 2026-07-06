---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: a85b69bf
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas Project Selection Load Recovery Spec

This specification describes the requirements for improving the project selection load recovery state in GrantAtlas when backend loading fails or is disconnected.

## 1. Current UI Problem

In the current React frontend implementation:
- If loading the project list fails (i.e., `loadStatus === "failed"`):
  - The `ProjectSelect` control dropdown displays "项目加载失败" as its fallback/empty option when no projects are loaded. However, there is no explanation of the recovery path or that this represents a backend connection issue.
  - The `ProjectsOverview` component has a basic callout banner explaining the failure, but the empty state text inside `ProjectsOverview` when no projects match the active filter simply says: "项目列表加载失败。请恢复后端连接后刷新。"
  - This is confusing because users may mistake the backend loading failure for an empty workspace with zero projects. It is also not clear that they should recover by connecting/reconnecting and then clicking the topbar refresh trigger.
  - Screen readers or keyboard users have no immediate accessibility association linking the selection failure or helper guidance to the `ProjectSelect` component.

## 2. Desired User Outcome

- **Usable Stale State**: If the system contains stale projects (e.g. cached locally or loaded previously before connection loss), keep the `ProjectSelect` selector and the table/cards in `ProjectsOverview` fully usable, allowing users to select and view existing items.
- **Actionable Recovery Guidance**:
  - In `ProjectSelect`, when `loadStatus === "failed"`, display a concise helper copy near/below the control: "项目列表加载失败。恢复后端连接后，使用右上角刷新重试。"
  - This helper must be accessible (e.g., via `aria-describedby` associated with the select element).
  - In `ProjectsOverview`, when `loadStatus === "failed"`, make sure the empty state clearly emphasizes that this is a loading failure and not a empty workspace (e.g., "请检查后端连接后刷新，这不是空项目列表。"), pointing specifically to the topbar refresh recovery path.
- **Chinese & Task-State Focus**: Keep all messages in Chinese. Do not expose internal technical jargon, raw logs, HTTP status codes, stack traces, API endpoints, or database IDs/hashes. Focus on task state ("恢复后端连接", "右上角刷新重试").

## 3. Scope

- **ProjectSelect (in `projectViews.tsx`)**:
  - Receive `loadStatus` parameter.
  - Render helper text `"项目列表加载失败。恢复后端连接后，使用右上角刷新重试。"` when `loadStatus === "failed"`.
  - Link helper text using `aria-describedby` to the `<select>` element.
- **ProjectsOverview (in `projectViews.tsx`)**:
  - Update the empty-state fallback copy inside the list table/card view when `visibleProjects.length === 0` and `loadStatus === "failed"`.
  - Strengthen the message so that it is visually clear, reassuring the user that their workspace is not empty, and pointing to the topbar refresh button.
- **Tests**:
  - Verify that the helper text in `ProjectSelect` is rendered when `loadStatus === "failed"` and properly associated via accessibility properties.
  - Verify that `ProjectsOverview` displays the strengthened empty-state error text when loading fails with no projects.

## 4. Non-Goals

- Do not modify global shell components, headers, or topbar layout.
- Do not add new global reload handlers or API interceptors.
- Do not expose raw logs or debug stack traces.
- Do not translate the interface to English or change other unrelated copy.

## 5. Verification

- Run unit tests:
  ```bash
  cd frontend && npm test -- projectViews.test.tsx
  ```
- Build the frontend project to verify type safety:
  ```bash
  cd frontend && npm run build
  ```
