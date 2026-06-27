# QA Report: PatentAgent Local Round 32

## Metadata

- Date: 2026-06-27
- Source branch: `fix/code-review-hardening`
- Source SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Worktree status: dirty; existing `README.md` modification plus QA artifacts and `BUGS.md`
- Target URL: `http://127.0.0.1:5174/`
- Backend: `http://127.0.0.1:8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round32","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Data dir: `.gstack/qa-reports/runtime-data-round32`
- Browser: local Chromium via Playwright
- Viewports: 1440x1100 desktop, 390x1100 mobile

## Scope

Round32 focused on the remaining long-text/export-preview risk:

- Seed a project with an external draft containing long Chinese paragraphs and a 670-character no-break technical token.
- Run filing readiness and official compile through the running black-box API.
- Open the seeded project in the real React UI.
- Inspect `专家工具 -> 提交成熟度` and `专家工具 -> 导出文件`.
- Compare app-internal export preview with direct Markdown report preview.

## Commands Run

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round32 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
node .gstack/qa-reports/round32_long_report_preview_probe.js
```

The probe also used the running OpenAPI surface to prepare data:

```text
POST /api/projects
POST /api/projects/{project_id}/external-drafts
POST /api/projects/{project_id}/external-drafts/{source_id}/intake-runs
POST /api/projects/{project_id}/external-draft-intake-runs/{run_id}/confirm
POST /api/projects/{project_id}/filing-readiness
POST /api/projects/{project_id}/official-compile-runs
GET /api/projects/{project_id}/official-compile-runs/{run_id}/report.md
GET /api/projects/{project_id}/filing-readiness/{report_id}/export.md
```

## Scenario Results

| Case | Result |
|---|---|
| `TC-LONGTEXT-003` | Failed: BUG-019 opened |
| App project selection | Passed; seeded project selected in topbar |
| Expert tools navigation | Passed; no action failures |
| Filing-readiness tool card | Passed; opened without page/request failure |
| Export-files tool card | Failed; app-internal package preview clips long no-break claim text |
| Direct official compile `report.md` | Passed; mobile and desktop previews use wrapping and no horizontal overflow |

## New BUG-019: Export file package preview clips long no-break claim text inside the app

Severity: P2

Repro summary:

1. Create and confirm an external draft containing long Chinese text plus `ROUND32_NO_BREAK_TECH_...`.
2. Run filing readiness and official compile.
3. Open `专家工具 -> 导出文件`.
4. Inspect `包内容预览` on desktop and mobile.

Actual:

- The app-internal preview contains a `pre` for claims with `whiteSpace:"pre"` and width about `10532px`.
- Parent `.workspace` has `overflow-x:hidden`; page-level `documentScrollWidth` does not exceed the viewport.
- The user gets no reachable horizontal scroll for the clipped preview content.

Expected:

The preview should wrap, clip with a visible affordance, or scroll inside the preview pane so users can inspect complete claims before export.

Evidence:

- `.gstack/qa-reports/screenshots/round32/05-export-files-tool.png`
- `.gstack/qa-reports/screenshots/round32/06-export-files-mobile.png`
- `.gstack/qa-reports/round32-long-report-preview-state.json`

Counter-evidence narrowing the scope:

- `.gstack/qa-reports/screenshots/round32/07-official-compile-report-md-mobile.png`
- `.gstack/qa-reports/screenshots/round32/08-official-compile-report-md-desktop.png`
- Direct Markdown report previews did not show horizontal overflow.

## Console And Network

- Page errors: 0
- Request failures: 0
- Action failures: 0
- Console resource errors: 1

The single console resource error was observed while navigating raw backend Markdown preview pages and was not tied to an app UI failure in this round.

## Baseline Update

- Added `BUG-019`.
- Severity totals now: `P1=3`, `P2=10`, `P3=6`.
- Visual score changed from `84` to `76`.
- Health score changed from `60` to `59`.

## Artifacts

- Probe: `.gstack/qa-reports/round32_long_report_preview_probe.js`
- State: `.gstack/qa-reports/round32-long-report-preview-state.json`
- Screenshots:
  - `.gstack/qa-reports/screenshots/round32/01-app-loaded.png`
  - `.gstack/qa-reports/screenshots/round32/02-project-selected.png`
  - `.gstack/qa-reports/screenshots/round32/03-expert-tools.png`
  - `.gstack/qa-reports/screenshots/round32/04-filing-readiness-tool.png`
  - `.gstack/qa-reports/screenshots/round32/05-export-files-tool.png`
  - `.gstack/qa-reports/screenshots/round32/06-export-files-mobile.png`
  - `.gstack/qa-reports/screenshots/round32/07-official-compile-report-md-mobile.png`
  - `.gstack/qa-reports/screenshots/round32/08-official-compile-report-md-desktop.png`
  - `.gstack/qa-reports/screenshots/round32/09-filing-readiness-export-md-desktop.png`
