# QA Report: PatentAgent Local Round 20

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Supplemental-material upload cancellation:

- Create a normal invention project from the first guided-flow entry.
- Reach the invention-point confirmation step.
- Click `选择并上传多份报告/补充材料`.
- Cancel the file chooser by providing an empty file selection.
- Verify no upload API call, no material count increase, no success text, and no browser errors.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round20 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round20","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, 1440x1100 viewport
- Project: `Round20 上传取消项目 1782495773512`

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round20 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round20_upload_cancel_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-UPLOAD-001 | 在发明点确认页取消补充材料文件选择 | 通过；未触发上传，不增加材料计数，也没有错误提示 |

## Findings

No new product bug opened in Round20.

After the file chooser was cancelled, the UI remained on the invention-point confirmation page with the file input text still showing `未选择任何文件`. The material API still returned zero materials, and no `POST /materials` request was observed.

## Positive Evidence

- `materialCountBefore: 0`
- `materialCountAfterCancel: 0`
- `materialPostCountBefore: 0`
- `materialPostCountAfter: 0`
- `noMaterialPostAfterCancel: true`
- `noMaterialCountIncrease: true`
- `noUploadedMaterialText: true`
- No page errors, request failures, or console errors were recorded.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round20/01-load-app.png`
- `.gstack/qa-reports/screenshots/round20/02-filled-project-form.png`
- `.gstack/qa-reports/screenshots/round20/03-project-created.png`
- `.gstack/qa-reports/screenshots/round20/04-after-filechooser-cancel.png`

State evidence:

- `.gstack/qa-reports/round20-upload-cancel-state.json`

## Baseline Update

- New bug ID opened: none.
- `TC-UPLOAD-001` now has a concrete Round20 probe command.
- Baseline health score unchanged: `62`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- Playwright simulated user cancellation by resolving the file chooser with an empty file list.
