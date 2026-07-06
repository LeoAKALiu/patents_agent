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

# GrantAtlas Project Selection Load Recovery Plan

This implementation plan decomposes the requirements from the Load Recovery Specification into independently reviewable slices.

## Slice 1: Enhance `ProjectSelect` Loading Failure Guidance (Accessibility + Helper Text)
Implement the core UI changes to the standalone `ProjectSelect` component when project list loading fails.

### Files
- `frontend/src/views/projectViews.tsx`
- `frontend/src/projectViews.test.tsx`

### Implementation Details
- In `ProjectSelect`:
  - Check if `loadStatus === "failed"`.
  - Add a unique ID to the helper container: `id="project-select-error-helper"`.
  - Associate the `<select>` element with the helper text using `aria-describedby="project-select-error-helper"`.
  - Display the helper text: `"项目列表加载失败。恢复后端连接后，使用右上角刷新重试。"` in a soft, warning-tinted or muted sub-label layout near/below the dropdown selector.
- In `projectViews.test.tsx`:
  - Add a test suite `"ProjectSelect load recovery status"`.
  - Assert that when `loadStatus === "failed"`, the helper text is rendered and its ID matches the `aria-describedby` attribute of the select control.

### Acceptance Checks
- Check visually/DOM structure that the select has `aria-describedby` pointing to the text element.
- Assert select dropdown remains interactive and lists any existing stale projects.


## Slice 2: Strengthen `ProjectsOverview` Failed Empty-State Copy
Strengthen the empty state text inside `ProjectsOverview` to prevent any confusion when project list loading fails and no projects are visible.

### Files
- `frontend/src/views/projectViews.tsx`
- `frontend/src/projectViews.test.tsx`

### Implementation Details
- In `ProjectsOverview`:
  - Locate the empty state render block (when `visibleProjects.length === 0`).
  - Strengthen the message when `loadStatus === "failed"` so that it says: `"项目列表加载失败。请恢复后端连接后使用右上角刷新重试，这并非空项目列表。"` or matches the spec's directive to emphasize this is a loading issue, not an empty workspace, pointing directly to the refresh recovery path.
- In `projectViews.test.tsx`:
  - Add a test asserting that when `loadStatus === "failed"` and `projects` list is empty, `ProjectsOverview` displays the strengthened warning explaining it's not a blank workspace.

### Acceptance Checks
- Run the targeted unit tests to verify both messages.
- Run `npm run build` to verify standard type-checking.
