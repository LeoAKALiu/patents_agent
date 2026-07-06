---
status: implemented
owner: product/frontend
created: 2026-07-06
source_identity:
  branch: codex/agy-grantatlas-all-surfaces-redesign
  short_sha: af9aecb9
  worktree: /Users/leo/Projects/patents_agent_omp_frontend_next
  dirty_at_capture: false
---

# GrantAtlas All-Surfaces Redesign Spec

## Problem

The previous frontend redesign work improved selected workbench and recovery paths, but the rest of the primary navigation still felt like older, unrelated screens. Users could move from `工作台` into `项目`, `文稿与修复`, `知识库`, `专家工具`, `导出`, or `设置` and lose the same task-state framing.

## Goal

Create a production React first slice that makes every primary navigation destination share a coherent, task-focused surface treatment. This is not a marketing hero or full visual rewrite. It is an operational shell layer that gives each main surface a concise title, task-state description, and compact status chips before the existing dense workflow content.

## Covered Surfaces

- `工作台`: patent workflow command center.
- `项目`: project list, selection, load failure, and lifecycle state.
- `文稿与修复`: draft, repair, version, and export blocker context.
- `知识库`: corpus building and retrieval state.
- `专家工具`: quality, grantability, post-draft, and evidence tools.
- `导出`: formal-file readiness and traceability state.
- `设置`: theme, model, and agent readiness state.

## Requirements

- The treatment must render from production React under `frontend/src/`.
- Each primary surface must expose a deterministic DOM hook for tests and visual smoke.
- Copy must stay concise, Chinese, and task-state oriented.
- Do not expose raw API paths, logs, IDs, hashes, or stack traces in the new shared surface.
- Preserve existing route behavior, including export-to-document navigation and document repair requested-tab handling.
- Preserve the project load failure recovery work from PR #134.
- Keep the layout dense and professional, with no decorative gradient blobs/orbs or marketing-style hero composition.
- Use existing design tokens and avoid horizontal overflow on desktop and mobile.

## Non-Goals

- This slice does not deeply redesign every nested expert tool, form, or table.
- This slice does not change backend behavior, Tauri packaging, or project data flow.
- This slice does not create a DMG or release artifact.
