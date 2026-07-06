---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: e48cc707
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-no-project-entry-spec.md
---

# GrantAtlas Document No-Project Entry Guidance Implementation Plan

This plan details the step-by-step changes required to implement the no-project document workspace entry fallback and guidance.

## Slice 1: Fallback Logic & Guidance State Updates
- **Target File**: `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- **Changes**:
  - In `useEffect` that processes `requestedTab`:
    - Check if `projectState.selectedProject` is `null`.
    - If `requestedTab === "annotated"` AND `projectState.selectedProject === null`:
      - Do not set the active tab to `annotated`. Instead, set it to `"overview"`.
      - Set `showGuidance` to `true`.
      - Set `guidanceType` to a new type `"no-project"`.
      - Do NOT trigger normal active tab updates to `"annotated"`.
      - Invoke `onRequestedTabHandled?.()`.
  - In the rendering block for `showGuidance`:
    - Add a conditional check for `guidanceType === "no-project"`.
    - Render the warning copy: `"标注修复需要选择项目后才能展示会审问题与修复正文。"`
    - Render a primary button `"选择项目"` that calls `onNavigate("projects")` and clears the guidance.
    - Render a secondary button `"留在当前页"` or simply allow closing/dismissing. Let's offer `"留在当前页"` / `"取消"` which simply dismisses the guidance. Let's offer a simple secondary button `"我知道了"` or `"留在总览"` to clear guidance and stay in `overview`. Let's use `"留在总览"` and close `X` button.
- **Acceptance Criteria**:
  - If requestedTab is `"annotated"` but no project is selected, the page defaults/stays on `overview` (总览) tab.
  - The guidance band is displayed with the correct warning text.

## Slice 2: Scoped Styles Verification
- **Target File**: `frontend/src/styles.css` (Optional or minimal additions if required)
- **Changes**:
  - If any custom or scoped class is needed, define it here. However, `document-guidance-band` and its buttons (e.g. `document-guidance-btn-primary`, `document-guidance-btn-secondary`, `document-guidance-close`) are already defined and styled nicely. We should leverage existing CSS rules to maintain styling consistency.
- **Acceptance Criteria**:
  - Visual layout is clean, centered, and matches the rest of the workspace guidance bands without any layout shifting.

## Slice 3: Targeted Unit Tests
- **Target File**: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- **Changes**:
  - Add tests:
    - `"does not switch to annotated tab and displays no-project guidance when requestedTab is annotated but no project is selected"`
    - `"navigates to projects workspace when clicking the primary action button in no-project guidance"`
    - `"dismisses no-project guidance on close or tab change"`
- **Acceptance Criteria**:
  - Run Vitest and ensure all tests pass.

---

# Implemented Slice (This Session)

We will implement all slices (**Slice 1, 2, and 3**) in this session to deliver the complete, high-quality "No-Project Entry Intent Guidance" feature.
- Implemented Slice Name: **"Document No-Project Entry Intent Guidance"**
- Changed Files:
  - `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
  - `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- Build Verification: `npm run build`
- Test Verification: `npm test` with targeted suite path.
