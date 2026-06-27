# QA Report: PatentAgent Local Round 30

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Supplemental-material unreadable-file upload handling:

- Create a normal invention project from the first guided-flow entry.
- Prepare a local Markdown fixture and remove read permissions before upload selection.
- Attempt to upload the unreadable file through the real browser file chooser path.
- Verify material count, request/console failures, and user-visible error message.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round30 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round30","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Project: `Round30 无读权限材料 1782498889106`
- Fixture: `.gstack/qa-reports/fixtures/round30-unreadable-material.md`, mode `000` during upload attempt

## Commands / Probes

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round30 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
node .gstack/qa-reports/round30_unreadable_file_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-UPLOAD-003 | 选择无读权限 Markdown 作为补充材料 | 失败；材料未污染，但错误提示暴露 API 路径和 `Failed to fetch` |

## Findings

### New BUG-017: Unreadable supplemental file upload shows raw API failure instead of a file-permission message

Severity: P2

The unreadable file was selected by the browser file input, but the upload request failed with `net::ERR_ACCESS_DENIED`. The app displayed:

```text
POST /api/projects/bc8d5199b9b24120b2f6ec227419baed/materials 请求失败:Failed to fetch
```

This is not actionable for a user. The UI should say the file cannot be read and ask the user to check permissions or choose another file. The positive part is that no material record was created.

## Positive Evidence

- `materialCountBefore: 0`
- `materialCountAfter: 0`
- `noMaterialCountIncrease: true`
- No page errors were recorded.
- Page-level horizontal overflow was false.

## Failure Evidence

- Browser request failure: `POST /api/projects/.../materials`, `net::ERR_ACCESS_DENIED`.
- Browser console error: `Failed to load resource: net::ERR_ACCESS_DENIED`.
- User-visible error includes raw API path and `Failed to fetch`.
- File input still displays `round30-unreadable-material.md` after the failed attempt.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round30/01-load-app.png`
- `.gstack/qa-reports/screenshots/round30/02-filled-project-form.png`
- `.gstack/qa-reports/screenshots/round30/03-project-created.png`
- `.gstack/qa-reports/screenshots/round30/04-after-unreadable-selection-attempt.png`

State evidence:

- `.gstack/qa-reports/round30-unreadable-file-state.json`

## Baseline Update

- New bug ID opened: `BUG-017`.
- Added matrix case: `TC-UPLOAD-003`.
- Baseline UX category score changed from `32` to `24`.
- Baseline health score changed from `61` to `60`.
- Current cumulative issues: `P1=3`, `P2=9`, `P3=5`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The unreadable fixture was restored to readable permissions after the probe so the workspace is not left with an inaccessible file.
