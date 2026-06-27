# QA Report: PatentAgent Local Round 18

Status: DONE_WITH_CONCERNS

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Long Chinese supplemental material display in the real browser UI:

- Create a normal invention project from the first guided-flow entry.
- Upload `.gstack/qa-reports/fixtures/round18-long-chinese-material.md`.
- Open `专家工具` -> `前置材料`.
- Capture desktop and mobile screenshots, scroll the material detail surface, and check horizontal overflow.

## Environment

- Frontend: `http://127.0.0.1:5174/`
- Backend: `DATA_DIR=.gstack/qa-reports/runtime-data-round18 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round18","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Browser: local Chromium/Playwright, desktop 1440x1100 and mobile 390x1100 viewports
- Fixture: `.gstack/qa-reports/fixtures/round18-long-chinese-material.md` (`137762` bytes, `46417` characters shown after upload)

## Commands / Probes

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
DATA_DIR=.gstack/qa-reports/runtime-data-round18 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
node .gstack/qa-reports/round18_long_material_detail_probe.js
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-LONGTEXT-002 | 超长中文 Markdown 补充材料在前置材料详情中的显示 | 失败；打开和滚动正常，但补充材料文件行显示为 `round18-long-chinese-material.mdmd / 46417 字` |

## Findings

### New BUG-015: Supplemental material file row concatenates filename extension and type label

Severity: P3

The material upload succeeded and the `前置材料` page opened without browser errors. In the `补充材料` section, however, the uploaded file row rendered:

`round18-long-chinese-material.mdmd / 46417 字`

The original file extension `.md` and the material type label `md` are concatenated without a separator or badge treatment. This is a low-severity readability issue, but it can make the user think the uploaded filename is malformed.

## Positive Evidence

- `POST /api/projects/a70ecc14ada64cc3a87628942b6976c3/materials` returned HTTP 200.
- `GET /materials` refreshed successfully after upload.
- The material detail surface opened on desktop and mobile.
- No page errors, request failures, or console errors were recorded.
- Document/body width stayed within the viewport on both desktop and mobile. The recorded desktop overflow flag came only from an intended truncated sidebar project-name span (`overflow-x: hidden`), not from page-level horizontal overflow.

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round18/01-load-app.png`
- `.gstack/qa-reports/screenshots/round18/02-filled-project-form.png`
- `.gstack/qa-reports/screenshots/round18/03-project-created.png`
- `.gstack/qa-reports/screenshots/round18/04-after-upload.png`
- `.gstack/qa-reports/screenshots/round18/05-material-detail-desktop-top.png`
- `.gstack/qa-reports/screenshots/round18/06-material-detail-desktop-scrolled.png`
- `.gstack/qa-reports/screenshots/round18/07-material-detail-mobile.png`
- `.gstack/qa-reports/screenshots/round18/08-material-detail-mobile-scrolled.png`

State evidence:

- `.gstack/qa-reports/round18-long-material-detail-state.json`

## Baseline Update

- New bug ID opened: `BUG-015`.
- Added matrix case: `TC-LONGTEXT-002`.
- Baseline UX category score changed from `38` to `35`.
- Baseline health score remains `62` after rounding.
- Current cumulative issues: `P1=3`, `P2=8`, `P3=4`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- The local QA probe was added only to collect browser evidence and does not affect product behavior.
