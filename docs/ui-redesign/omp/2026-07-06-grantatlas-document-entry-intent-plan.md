---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 07da321e
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-document-entry-intent-spec.md
---

# GrantAtlas Document Entry-Intent Plan

This implementation plan outlines the steps to introduce the entry-intent guidance band in `DocumentRepairWorkspace`.

## Slice 1: Local State & Guidance Band UI
- **Target File**: `frontend/src/features/documentRepair/DocumentRepairWorkspace.tsx`
- **Work**:
  - Add state `showGuidance` (boolean).
  - Inside the `useEffect` responding to `requestedTab`, set `showGuidance` to `true` if `requestedTab` matches a handled tab (like `"annotated"`).
  - Clear `showGuidance` if the user manually switches tabs (using `setActiveTab` inside `onClick` of the tab buttons).
  - Add a styled guidance band block under the headers with concise Chinese copy explaining that the user has been routed from export/workbench to resolve issues.
  - Provide a button to "返回总览" (calls `setActiveTab("overview")`) or to dismiss the guidance band.
- **Verification**: Ensure visually aligned structure and classNames.

## Slice 2: Scoped Styles
- **Target File**: `frontend/src/styles.css`
- **Work**:
  - Add minimal scoped CSS styles for the guidance band (`document-guidance-band`, its icons, text, and action buttons) to ensure proper styling, borders, and margins.
- **Verification**: Clean alignment, no layout shifting.

## Slice 3: Unit Testing
- **Target File**: `frontend/src/features/documentRepair/DocumentRepairWorkspace.test.tsx`
- **Work**:
  - Add test: "renders guidance band when requestedTab is provided".
  - Add test: "dismisses guidance band when user clicks dismiss button".
  - Add test: "clears guidance band when user manually switches tabs".
- **Verification**: Run `npm test -- features/documentRepair/DocumentRepairWorkspace.test.tsx`.

---

# Implemented Slice (This Session)
We will implement **Slice 1, 2, and 3** in this session as a single cohesive unit: **"Document Entry Intent Guidance"**.
- This slice covers all requirements described in the spec.
- No other slices are required.
