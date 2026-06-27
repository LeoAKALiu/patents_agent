# PatentAgent QA Report - Round33 Long Editor/Report Overflow

## Metadata

- Date: 2026-06-27
- Source branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree: yes; includes pre-existing `README.md`, QA docs, `BUGS.md`, and local QA evidence
- Target: `http://127.0.0.1:5174/`
- Backend: `http://127.0.0.1:8000`
- Backend health: `{"ok":true,"llm_configured":true,"data_dir":".gstack/qa-reports/runtime-data-round33","model":"deepseek-v4-pro","embedding_model":"local-hash-128"}`
- Runtime data dir: `.gstack/qa-reports/runtime-data-round33`
- Browser: local Chromium via Playwright
- Viewports: desktop 1440x1100, mobile 390x1100

## Scope

Round33 covered the remaining long-text scenario for generated report and editor surfaces:

- Seeded project `Round33 长编辑报告 1782500346609`.
- Confirmed an external draft containing long Chinese paragraphs and a 679-character continuous token.
- Generated `授权前景`, `权利要求防线`, and `初稿完善` artifacts.
- Opened real UI surfaces for `授权前景`, `权利要求防线`, `初稿完善`, and `分步撰写`.
- Compared app-internal `分步撰写` application text preview against direct `completion-runs/{run_id}/report.md`.

This run did not inspect or modify product source code.

## Result Summary

| Case | Result | Evidence |
|---|---|---|
| `TC-LONGTEXT-004` | Fail: `BUG-020` | `.gstack/qa-reports/round33-long-editor-report-state.json` |
| Report generation APIs | Pass | grantability `7228947324f14cb5b282f6b028e59f9f`; claim defense `c5a9d68f987c4633ae3f41e3c1bed61e`; completion `359c9c596be0486784dece5d18754ed9` |
| UI actions | Pass | 0 action failures |
| Browser/runtime errors | Pass with note | 0 page errors; 0 request failures; 1 raw backend `/favicon.ico` 404 while viewing Markdown directly |
| Visible editable text control in `分步撰写` | Not found | `editorFilled:false`; `textControlsObserved:0` |
| Direct Markdown report preview | Pass | mobile Markdown `pre` width 374px, `whiteSpace:"pre-wrap"`, no page overflow |

## New Finding

### BUG-020 - Step-writing application text preview clips long no-break claim text inside the app

Severity: P2
Category: Visual
Status: 已复现

`分步撰写` 的申请文本预览被连续长 token 撑到约 12819px 宽，进而把专家工具内容列撑宽。父级 `.workspace` 使用 `overflow-x:hidden`，页面本身没有横向滚动，用户无法访问被裁切的右侧内容。

Desktop evidence:

- `.workspace`: `clientWidth:1181`, `scrollWidth:12909`, `overflowX:"hidden"`.
- App-internal content column extends to about 12869px.
- Long token is visible in app content.

Mobile evidence:

- `.workspace`: `clientWidth:390`, `scrollWidth:12893`, `overflowX:"hidden"`.
- Tool card/button rows extend to about 12835px.
- Page-level `documentScrollWidth` remains 390, so the overflow is silently clipped.

Direct Markdown control:

- `completion-runs/{run_id}/report.md` at 390px viewport has `documentScrollWidth:390`, `bodyScrollWidth:374`.
- Browser-rendered `pre` uses `whiteSpace:"pre-wrap"` and remains readable.

This localizes the failure to the app-internal `分步撰写` preview/tool layout, not to the generated Markdown content itself.

## Console And Network

- Action failures: 0
- Page errors: 0
- Request failures: 0
- Console resource errors: 1
- Note: the single console error was a `/favicon.ico` 404 from directly opening backend Markdown preview and was not recorded as a product UI issue.

## Baseline Update

- Added `BUG-020`.
- Current issue totals: `P1=3`, `P2=11`, `P3=6`.
- Visual score changed from 76 to 68.
- Health score changed from 59 to 58.

## Artifacts

- Probe: `.gstack/qa-reports/round33_long_editor_report_probe.js`
- State: `.gstack/qa-reports/round33-long-editor-report-state.json`
- Screenshots:
  - `.gstack/qa-reports/screenshots/round33/01-app-loaded.png`
  - `.gstack/qa-reports/screenshots/round33/02-project-selected.png`
  - `.gstack/qa-reports/screenshots/round33/03-expert-tools.png`
  - `.gstack/qa-reports/screenshots/round33/04-grantability-report.png`
  - `.gstack/qa-reports/screenshots/round33/05-claim-defense-report.png`
  - `.gstack/qa-reports/screenshots/round33/06-completion-report.png`
  - `.gstack/qa-reports/screenshots/round33/07-step-writing-editor-empty.png`
  - `.gstack/qa-reports/screenshots/round33/08-step-writing-editor-long-text.png`
  - `.gstack/qa-reports/screenshots/round33/09-step-writing-editor-mobile.png`
  - `.gstack/qa-reports/screenshots/round33/10-completion-report-md-mobile.png`
  - `.gstack/qa-reports/screenshots/round33/11-grantability-export-md-mobile.png`
