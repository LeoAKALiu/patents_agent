# PatentAgent QA Report

日期：2026-06-26

测试模式：按 `docs/qa/ai-scenario-testing-pipeline.md` 和 `docs/qa/test-case-matrix.md` 执行的报告-only QA。

源码身份：

- 分支：fix/code-review-hardening
- 短 SHA：045b042
- worktree：/Users/leo/Projects/patents_agent
- 工作树：dirty，仅包含 QA 文档和 BUGS.md/报告记录

测试对象：

- 前端：http://127.0.0.1:5174/
- 后端：http://127.0.0.1:8000/
- 后端数据目录：`.gstack/qa-reports/runtime-data`
- 后端 health：`ok=true`, `llm_configured=true`, `model=deepseek-v4-pro`, `embedding_model=local-hash-128`
- 浏览器：本地 Chromium/Playwright，桌面 1440x1100，移动 390x1100

## Summary

健康分：82/100

发现问题：

- P1：1
- P2：2
- P3：0

Top 3：

1. `BUG-001`：第三入口外部稿件导入在选择已有项目后丢失导入模式。
2. `BUG-002`：空 Markdown 可作为 `processed` 补充材料落库。
3. `BUG-003`：伪 DOCX 上传返回 500，并向用户暴露 `Internal Server Error`。

## Commands Run

```bash
python3 -m pytest tests/test_official_compile.py tests/test_post_draft_review.py tests/test_external_drafts.py tests/test_external_drafts_api.py tests/test_post_draft_repair.py -q
npm --prefix frontend test -- PostDraftRepairEditor.test.tsx --run
DATA_DIR=.gstack/qa-reports/runtime-data python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

自动化结果：

- 后端相关测试：100 passed, 53 warnings
- 前端修复编辑器测试：8 passed

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-GUIDED-001 | 新手从一句技术想法创建发明专利 | 通过；空表单禁用创建，正常填写后创建成功 |
| TC-DOUBLE-CLICK-001 | 创建按钮重复点击 | 通过；双击后项目数仍为 1 |
| TC-INTAKE-001 | 空 Markdown 上传 | 失败；空 Markdown 作为补充材料 processed 落库 |
| TC-INTAKE-002 | 伪 DOCX 上传 | 失败；返回 500 |
| 设置页扫描 | 密钥状态、保存/测试按钮 | 未发现阻断问题 |
| 项目页扫描 | 项目列表、选择/删除入口 | 未发现新增问题，未执行删除 |

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/home-desktop.png`
- `.gstack/qa-reports/screenshots/home-mobile.png`
- `.gstack/qa-reports/screenshots/scn001-after-select-invention.png`
- `.gstack/qa-reports/screenshots/issue-double-click-before-create.png`
- `.gstack/qa-reports/screenshots/issue-double-click-after-create.png`
- `.gstack/qa-reports/screenshots/scn004-external-entry.png`
- `.gstack/qa-reports/screenshots/scn004-external-with-project-before-empty-upload.png`
- `.gstack/qa-reports/screenshots/issue-empty-md-with-project-result.png`
- `.gstack/qa-reports/screenshots/issue-fake-docx-material-result.png`
- `.gstack/qa-reports/screenshots/scan-settings-desktop.png`
- `.gstack/qa-reports/screenshots/scan-projects-desktop.png`

## Console Health

No console errors on homepage, project creation, settings, or projects page scans.

One console error during invalid DOCX upload:

```text
Failed to load resource: the server responded with a status of 500 (Internal Server Error)
```

## Findings

### ISSUE-001 / BUG-001: External Draft Import Loses Mode After Selecting Project

Severity：High / P1

Repro:

1. Open the app.
2. Click `导入已有稿件进行润色提升`.
3. Select existing project `QA 重复点击项目` from the top project selector.

Actual：The UI leaves external-draft intake and returns to the regular invention flow.

Expected：The external-draft intake mode should remain active with the selected project bound as the target.

Evidence：

- `.gstack/qa-reports/screenshots/scn004-external-entry.png`
- `.gstack/qa-reports/screenshots/scn004-external-with-project-before-empty-upload.png`

### ISSUE-002 / BUG-002: Empty Markdown Upload Is Accepted As Processed Material

Severity：Medium / P2

Repro:

1. Select project `QA 重复点击项目`.
2. Upload `.gstack/qa-reports/test-files/empty.md` via the supplemental materials upload.
3. Query project materials.

Actual：The UI shows `已上传材料:empty.md`; API returns `status:"processed"` with empty `text`.

Expected：The upload should fail closed with a clear empty-file error and should not be persisted as processed material.

Evidence：

- `.gstack/qa-reports/screenshots/issue-empty-md-with-project-result.png`
- `GET /api/projects/3f3cef1465dc42aca1ee09c5d851019c/materials`

### ISSUE-003 / BUG-003: Invalid DOCX Upload Returns 500

Severity：Medium / P2

Repro:

1. Select project `QA 重复点击项目`.
2. Upload `.gstack/qa-reports/test-files/fake.docx`.

Actual：API returns 500; UI displays raw `Internal Server Error`; backend logs `zipfile.BadZipFile: File is not a zip file`.

Expected：The upload should fail with a user-readable file-format error and a non-500 status.

Evidence：

- `.gstack/qa-reports/screenshots/issue-fake-docx-material-result.png`
- Backend log from QA server session

## Notes

- I did not trigger live LLM generation beyond project creation and upload flows.
- I did not run destructive project delete flows.
- `gstack browse` could not retain a browser session under this sandbox, so Playwright was used for browser evidence.
