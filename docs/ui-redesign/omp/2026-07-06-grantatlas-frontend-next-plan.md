---
status: proposed
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/omp-grantatlas-frontend-next
  short_sha: 5efe5e46
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
related:
  - docs/ui-redesign/omp/2026-07-06-grantatlas-frontend-next-spec.md
---

# GrantAtlas Export Navigation Implementation Plan

This plan breaks down the export workspace navigation integration into reviewable slices.

## Slice 1: Icon Registry Update
- **Target File**: `frontend/src/lib/icons.ts`
- **Work**: Add `FileSearch`, `FolderOpen`, and `ArrowRight` to the re-exports from `lucide-react` to keep the registry centralized.
- **Verification**: Ensure no export conflicts and check type correctness.

## Slice 2: ExportView Callback Integration
- **Target File**: `frontend/src/views/exportView.tsx`
- **Work**:
  - Add `onNavigateDocuments` to the props definition of `ExportView`.
  - Inside the "正式提交稿" locked gate `InfoCard`, render an action button linking to `onNavigateDocuments("annotated")` if the gate is locked.
  - Inside the contamination warning `callout` block, render a secondary button: "前往文稿与修复 / 标注修复" calling `onNavigateDocuments("annotated")` to guide the user back to cleanup.
- **Verification**: Run `npm run build` from `frontend` to verify type compliance.

## Slice 3: ExportWorkspace Wiring
- **Target File**: `frontend/src/features/export/ExportWorkspace.tsx`
- **Work**: Pass `onNavigateDocuments` to `ExportView` in the render block.
- **Verification**: Ensure props type check compiles.

## Slice 4: Unit Test Coverage
- **Target File**: `frontend/src/views/exportView.test.tsx`
- **Work**:
  - Add tests validating that the navigation buttons/links are rendered within the contamination callout when contamination matches are present.
  - Add tests validating that the locked gate warning card contains the action link/button invoking `onNavigateDocuments`.
- **Verification**: Run `cd frontend && npm test -- views/exportView.test.tsx`.

---

# Implemented Slice (This Session)
We will implement **Slice 1, 2, 3, and 4** in this session as a single cohesive unit: **"Export Navigation Integration"**.
- This implementation removes the friction between showing a gate blocker/contamination warning and resolving it.
- Keeps code modifications minimal, focused, and reviewable.
