# PatentAgent QA Report - Round 2

日期：2026-06-26

测试模式：按 `docs/qa/ai-scenario-testing-pipeline.md` 继续执行报告-only QA，重点补测 `TC-EXPORT-001`、`TC-EXPORT-002`、`TC-REPAIR-001`、`TC-REPAIR-002`。

源码身份：

- 分支：fix/code-review-hardening
- 短 SHA：045b042
- worktree：/Users/leo/Projects/patents_agent
- 工作树：dirty，仅包含 QA 文档、BUGS.md 和本地 QA 记录

测试对象：

- 前端：http://127.0.0.1:5174/
- 后端：http://127.0.0.1:8000/
- 后端数据目录：`.gstack/qa-reports/runtime-data-round2`
- 后端 health：`ok=true`, `llm_configured=true`, `model=deepseek-v4-pro`, `embedding_model=local-hash-128`
- 浏览器：本地 Chromium/Playwright，桌面 1440x1100

## Summary

本轮健康分：76/100

新增问题：

- P1：2

累计问题：

- P1：3
- P2：2
- P3：0

新增 Top 2：

1. `BUG-004`：正式稿编译显示已清理，但正式稿仍包含全部污染词。
2. `BUG-005`：成稿会审超时失败，修复编辑器按钮 disabled，无法进入真实 repair-session 数据流。

## Commands Run

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round2 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
curl http://127.0.0.1:8000/openapi.json
POST /api/projects
POST /api/projects/{project_id}/external-drafts
POST /api/projects/{project_id}/external-drafts/{source_id}/intake-runs
POST /api/projects/{project_id}/external-draft-intake-runs/{run_id}/confirm
POST /api/projects/{project_id}/filing-readiness
POST /api/projects/{project_id}/claim-defense-worksheets
POST /api/projects/{project_id}/completion-runs
POST /api/projects/{project_id}/official-compile-runs
POST /api/projects/{project_id}/post-draft-reviews
GET /api/projects/{project_id}/post-draft-reviews/{run_id}/repair-session
GET /api/projects/{project_id}/export-readiness
GET /api/projects/{project_id}/official-export.md
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-EXPORT-001 | 编译 + 会审 + 导出门禁 | 部分通过；未会审时官方导出被 409 正确阻止 |
| TC-EXPORT-002 | 正式稿编译清理与 hash gate | 失败；正式稿编译没有清理污染词但 UI 显示已清理 |
| TC-REPAIR-001 | repair-session issues + sections + editor | 失败；sections 非空但 issues 为空，按钮 disabled |
| TC-REPAIR-002 | 长问题列表滚动 | 未达到前置条件；无 issues 可测试 |

## Positive Evidence

- 有内部工作稿但未正式编译时，`GET /official-export.md` 返回 409。
- 正式稿编译后但未通过成稿会审时，`GET /official-export.md` 返回 409。
- UI 中第 9 步 `导出` 仍为未解锁状态，导出 gate 没有被绕过。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round2-after-quality-project-state.png`
- `.gstack/qa-reports/screenshots/round2-after-quality-正式稿编译.png`
- `.gstack/qa-reports/screenshots/round2-after-quality-成稿会审.png`
- `.gstack/qa-reports/screenshots/round2-after-quality-导出.png`

API evidence:

- `.gstack/qa-reports/round2-api-state.json`

## Findings

### ISSUE-004 / BUG-004: Official Compile Claims Cleanup But Leaves Pollutants

Severity：High / P1

Repro:

1. Create a project from external draft intake with known pollutants.
2. Run quality checks.
3. Run official compile.
4. Inspect official package and UI compile report.

Actual：Official package still contains `好的，根据`, `待验证`, `主席修订`, `需在提交前补充`, `颠覆`, and `方法方法`; UI says official draft is clean and `已清理内部痕迹 0 项`.

Expected：Official compile should clean or block these pollutants before showing success.

Evidence：

- `.gstack/qa-reports/screenshots/round2-after-quality-正式稿编译.png`
- `.gstack/qa-reports/round2-api-state.json`

### ISSUE-005 / BUG-005: Post-Draft Review Times Out And Blocks Repair Editor

Severity：High / P1

Repro:

1. With official compile completed, run post-draft review with `providers:["deterministic"]`, `stage_timeout_ms:30000`, `run_timeout_ms:60000`.
2. Wait for completion.
3. Inspect UI and repair-session.

Actual：Review failed after `181823ms`; no role/chair result, no blocking issues, no contamination hits. Repair session returns sections but no issues, and UI disables `打开标注式修复编辑器`.

Expected：Review should honor timeout boundaries and produce usable issues for polluted drafts, or fail promptly with a clear retry path.

Evidence：

- `.gstack/qa-reports/screenshots/round2-after-quality-成稿会审.png`
- `.gstack/qa-reports/screenshots/round2-after-quality-导出.png`
- `.gstack/qa-reports/round2-api-state.json`

## Console Health

No browser console errors were observed in the round-2 Playwright scans. The failures are product/API state issues, not front-end JavaScript crashes.

## Notes

- I did not repair any code.
- I did not force a fake completed review into storage; repair editor validation remains blocked by the real failed review state.
- The official export gate behaved correctly in this test: it remained closed before post-draft review passed.
