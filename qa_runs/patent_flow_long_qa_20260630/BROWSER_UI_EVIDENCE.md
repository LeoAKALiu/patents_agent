# Browser UI Evidence

## Source And Servers

- Date: 2026-06-30
- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- Short SHA: `f566fc09`
- Backend: `http://127.0.0.1:8001`
- Frontend: `http://127.0.0.1:5175`
- Backend module: `qa_runs/patent_flow_long_qa_20260630/browser_evidence_backend.py`
- Vite config: `qa_runs/patent_flow_long_qa_20260630/vite.browser-smoke.config.ts`
- Seed script: `qa_runs/patent_flow_long_qa_20260630/seed_browser_repair_project.py`

The QA servers were isolated from existing local dev servers on `8000` and `5174`. The QA frontend proxied `/api` to the fake-LLM backend on `8001`.

## Seeded Project

- Project ID: `73855542dcb141f19eb29355319b3189`
- Project name: `QA 标注修复证据项目`
- Material status: `processed`
- Official compile status: `completed`
- Post-draft review status: `completed`
- Post-draft export allowed: `false`
- Repair session: `9` issues, sections `abstract`, `claims`, `description`, `drawing_description`, `title`
- Repair session stale: `false`

API payload artifacts:

- `current-artifacts/browser-smoke-current/seed-summary.json`
- `current-artifacts/browser-smoke-current/repair-session.json`
- `current-artifacts/browser-smoke-current/export-readiness.json`
- `current-artifacts/browser-smoke-current/post-draft-reviews.json`
- `current-artifacts/browser-smoke-current/official-compile-runs.json`
- `current-artifacts/browser-smoke-current/project.json`

## Browser Evidence

- `current-artifacts/browser-smoke-current/workbench.png`
  - Shows current project selected, next action `处理成稿会审阻断项`, and `导出锁定`.
- `current-artifacts/browser-smoke-current/documents-overview.png`
  - Shows `文稿与修复` overview, gate chain, issue summary, and recent records.
- `current-artifacts/browser-smoke-current/annotated-repair-initial.png`
  - Shows embedded `标注式修复编辑器` with left issue queue, middle draft sections, and right inspector.
- `current-artifacts/browser-smoke-current/annotated-repair-claims-selected.png`
  - Shows selecting the claims issue updates the active issue, middle section context, and inspector.
- `current-artifacts/browser-smoke-current/export-gate.png`
  - Shows export workspace locked with official export disabled and official/internal/risk areas separated.

DOM/text artifacts:

- `current-artifacts/browser-smoke-current/*.snapshot.yml`
- `current-artifacts/browser-smoke-current/dom-summary.raw.txt`

## Verification Summary

- `GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session` returned non-empty `issues` and non-empty draft `sections`.
- The browser rendered the real React app, not static docs or component-only fixtures.
- The repair editor rendered all three required panes.
- Clicking a different issue updated the active issue and inspector to `权利要求书`.
- The export page visibly blocked official export and separated official/internal/risk output areas.

## Observed Friction

The workbench prioritized post-draft repair as the next action, while the export workspace and export-readiness API prioritized missing quality checks (`next_action=run_quality_checks`). This is recorded as `FRICTION-005` because it can make the next best action feel inconsistent across workspaces.
