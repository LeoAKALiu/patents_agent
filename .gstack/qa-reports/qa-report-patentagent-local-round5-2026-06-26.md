# PatentAgent QA Report - Round 5

日期：2026-06-26

测试模式：按 `docs/qa/ai-scenario-testing-pipeline.md` 继续执行报告-only QA，重点补测空白输入、超长文本、文件上传取消、不支持扩展名上传和长 Markdown 补充材料。

源码身份：

- 分支：fix/code-review-hardening
- 短 SHA：045b042
- worktree：/Users/leo/Projects/patents_agent
- 工作树：dirty，包含 QA 文档、BUGS.md 和本地 QA 记录

测试对象：

- 前端：http://127.0.0.1:5174/
- 后端：http://127.0.0.1:8000/
- 后端数据目录：`.gstack/qa-reports/runtime-data-round5`
- 后端 health：`ok=true`, `llm_configured=true`, `model=deepseek-v4-pro`, `embedding_model=local-hash-128`
- 浏览器：本地 Chromium/Playwright，桌面 1440x1100，移动端 390x1100

## Summary

本轮健康分：69/100

新增问题：

- P2：1

累计问题：

- P1：3
- P2：5
- P3：1

新增 Top 1：

1. `BUG-009`：不支持扩展名上传失败后仍计入补充材料数量，并在前置材料详情中和有效材料同列展示。

## Commands Run

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round5 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
curl http://127.0.0.1:8000/api/health
Playwright: blank/space-only project name
Playwright: long project name + long invention idea
Playwright: setInputFiles([]) cancellation
Playwright: upload unsupported-round5.xyz
Playwright: upload long-round5.md
GET /api/projects/{project_id}/materials
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-GUIDED-001 | 空白/空格项目名 | 通过；创建按钮保持 disabled |
| TC-LONG-TEXT-001 | 超长项目名和超长技术想法 | 部分通过；桌面无横向滚动，移动端仍受 `BUG-006` 状态恢复问题影响 |
| TC-UPLOAD-001 | 文件选择取消 | 通过；空选择不触发材料写入，不显示错误 |
| TC-UPLOAD-002 | 不支持扩展名 + 有效 Markdown | 失败；failed 文件计入材料数量并列入前置材料详情 |

## Positive Evidence

- 空项目名和只有空格的项目名均不能提交，`创建并继续` 保持 disabled。
- 桌面超长技术想法在 Deep Research 提示词 textarea 内滚动，页面没有横向滚动。
- 上传取消/空选择后，页面内容和材料列表保持不变。
- 有效 `long-round5.md` 上传后 API 中 `status="processed"`，文本内容完整落库。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round5-blank-spaces-name-form.png`
- `.gstack/qa-reports/screenshots/round5-long-text-after-create.png`
- `.gstack/qa-reports/screenshots/round5-long-text-mobile-after-create.png`
- `.gstack/qa-reports/screenshots/round5-upload-before.png`
- `.gstack/qa-reports/screenshots/round5-upload-cancel-empty-files.png`
- `.gstack/qa-reports/screenshots/round5-upload-unsupported-xyz.png`
- `.gstack/qa-reports/screenshots/round5-upload-long-md.png`
- `.gstack/qa-reports/screenshots/round5-material-detail-material-list.png`

State evidence:

- `.gstack/qa-reports/round5-long-text-form-state.json`
- `.gstack/qa-reports/round5-upload-state.json`
- `.gstack/qa-reports/round5-material-detail-state.json`
- `.gstack/qa-reports/round5-material-detail-material-list-state.json`

## Findings

### ISSUE-009 / BUG-009: Failed Unsupported Upload Counts As Supplemental Material

Severity：Medium / P2

Repro:

1. Create a project and enter the invention-point step.
2. Upload `unsupported-round5.xyz`.
3. Upload valid `long-round5.md`.
4. Open the pre-material detail view.

Actual：The `.xyz` upload is stored with `status="failed"`, but the guided flow says `当前已有 1 份材料`. After uploading a valid Markdown file, the flow says `当前已有 2 份材料`. The detail page lists both `long-round5.md` and `unsupported-round5.xyz` under supplemental materials.

Expected：Failed uploads should not count as usable supplemental materials, and the detail page should visually separate failed uploads from processed materials.

Evidence：

- `.gstack/qa-reports/screenshots/round5-upload-unsupported-xyz.png`
- `.gstack/qa-reports/screenshots/round5-upload-long-md.png`
- `.gstack/qa-reports/screenshots/round5-material-detail-material-list.png`
- `.gstack/qa-reports/round5-upload-state.json`

## Console Health

No browser console errors were observed in this round. The new finding is a state/counting and UX issue.

## Notes

- I did not repair any code.
- The mobile long-text reload behavior appears to be covered by existing `BUG-006`; no duplicate bug was opened.
- The unsupported file was intentionally uploaded through automation to verify backend and UI failure handling; normal file pickers advertise accepted extensions.
