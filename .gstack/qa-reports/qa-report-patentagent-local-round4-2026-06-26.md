# PatentAgent QA Report - Round 4

日期：2026-06-26

测试模式：按 `docs/qa/ai-scenario-testing-pipeline.md` 继续执行报告-only QA，重点补测项目列表空状态、超多项目、筛选、项目切换、移动端项目页和删除取消流程。

源码身份：

- 分支：fix/code-review-hardening
- 短 SHA：045b042
- worktree：/Users/leo/Projects/patents_agent
- 工作树：dirty，包含 QA 文档、BUGS.md 和本地 QA 记录

测试对象：

- 前端：http://127.0.0.1:5174/
- 后端：http://127.0.0.1:8000/
- 后端数据目录：`.gstack/qa-reports/runtime-data-round4`
- 后端 health：`ok=true`, `llm_configured=true`, `model=deepseek-v4-pro`, `embedding_model=local-hash-128`
- 浏览器：本地 Chromium/Playwright，桌面 1440x1100，移动端 390x1100

## Summary

本轮健康分：71/100

新增问题：

- P2：1

累计问题：

- P1：3
- P2：4
- P3：1

新增 Top 1：

1. `BUG-008`：移动端项目列表筛选 chip 和操作按钮超出视口，点击选择后列表内容横向偏移。

## Commands Run

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round4 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/projects
POST /api/projects x30
Playwright: project list empty desktop/mobile
Playwright: project list many-item desktop/mobile
Playwright: project filters and top selector project switching
Playwright: mobile project-list button bounding boxes
Playwright: desktop delete confirmation dismissed
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-PROJECTS-EMPTY-001 | 空项目列表 | 通过；桌面/移动端无横向滚动，空状态文案可理解 |
| TC-PROJECTS-MANY-001 | 30 个项目桌面列表 | 通过；桌面列表、实用新型筛选、顶部项目切换可用 |
| TC-PROJECTS-MOBILE-001 | 30 个项目移动端列表 | 失败；操作按钮和筛选 chip 超出 390px 视口 |
| TC-PROJECTS-DELETE-001 | 删除确认取消 | 通过；确认框可取消，项目数保持 30 |

## Positive Evidence

- 空项目列表桌面和移动端均无控制台错误，无横向滚动。
- 桌面 30 项目列表显示统计 `全部项目 30`、`仅有想法 30`、`实用新型 7`，表格行数为 30。
- 桌面筛选 `实用新型` 后表格行数为 7。
- 顶部选择 `QA Round4 项目 12` 后，当前项目摘要和项目列表当前行均更新。
- 桌面删除确认弹窗可取消，取消后 API 项目数仍为 30。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round4-projects-empty-desktop.png`
- `.gstack/qa-reports/screenshots/round4-projects-empty-mobile.png`
- `.gstack/qa-reports/screenshots/round4-projects-many-desktop.png`
- `.gstack/qa-reports/screenshots/round4-projects-filter-utility-desktop.png`
- `.gstack/qa-reports/screenshots/round4-project-switch-top-select-desktop.png`
- `.gstack/qa-reports/screenshots/round4-projects-many-mobile.png`
- `.gstack/qa-reports/screenshots/round4-projects-mobile-button-bounds-before.png`
- `.gstack/qa-reports/screenshots/round4-projects-mobile-after-select.png`
- `.gstack/qa-reports/screenshots/round4-project-delete-dismiss-desktop.png`

State evidence:

- `.gstack/qa-reports/round4-projects-empty-state.json`
- `.gstack/qa-reports/round4-projects-many-state.json`
- `.gstack/qa-reports/round4-projects-mobile-buttons-state.json`
- `.gstack/qa-reports/round4-project-delete-state.json`

## Findings

### ISSUE-008 / BUG-008: Mobile Project List Action Buttons Exceed Viewport

Severity：Medium / P2

Repro:

1. Seed 30 projects in the isolated round-4 data directory.
2. Open the project list at mobile viewport 390x1100.
3. Inspect the project filter chips and first project card action buttons.
4. Tap `选择项目` on the first card.

Actual：The `实用新型 7` chip and project action buttons extend beyond the viewport. The first visible `选择项目` button has `width=724.484375` and `right=786.484375`; after tapping it, the chip row and cards shift horizontally, clipping left-side content.

Expected：Mobile chips and action buttons should stay inside the card/viewport, and selecting a project should not introduce horizontal offset.

Evidence：

- `.gstack/qa-reports/screenshots/round4-projects-mobile-button-bounds-before.png`
- `.gstack/qa-reports/screenshots/round4-projects-mobile-after-select.png`
- `.gstack/qa-reports/round4-projects-mobile-buttons-state.json`

## Console Health

No browser console errors were observed in this round. The new finding is a responsive layout issue.

## Notes

- I did not repair any code.
- The failed `utility` enum during data seeding was a QA setup mistake, not counted as a product bug; the runtime API correctly accepted `utility_model`.
- Delete confirmation was dismissed only; no isolated projects were deleted.
