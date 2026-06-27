# PatentAgent QA Report - Round 3

日期：2026-06-26

测试模式：按 `docs/qa/ai-scenario-testing-pipeline.md` 继续执行报告-only QA，重点补测移动端显示、刷新/返回/关闭窗口类状态恢复、设置页错误输入和网络异常。

源码身份：

- 分支：fix/code-review-hardening
- 短 SHA：045b042
- worktree：/Users/leo/Projects/patents_agent
- 工作树：dirty，包含 QA 文档、BUGS.md 和本地 QA 记录

测试对象：

- 前端：http://127.0.0.1:5174/
- 后端：http://127.0.0.1:8000/
- 后端数据目录：`.gstack/qa-reports/runtime-data-round3`
- 后端 health：`ok=true`, `llm_configured=true`, `model=deepseek-v4-pro`, `embedding_model=local-hash-128`
- 浏览器：本地 Chromium/Playwright，桌面 1440x1100，移动端 390x1100

## Summary

本轮健康分：73/100

新增问题：

- P2：1
- P3：1

累计问题：

- P1：3
- P2：3
- P3：1

新增 Top 2：

1. `BUG-006`：创建项目进入第 2 步后刷新，当前项目和 guided flow 步骤状态丢失。
2. `BUG-007`：设置页连通测试失败时暴露原始 `APIConnectionError`，缺少可操作中文错误说明。

## Commands Run

```bash
DATA_DIR=.gstack/qa-reports/runtime-data-round3 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/projects
Playwright: desktop/mobile baseline screenshots
Playwright: create project -> refresh -> inspect UI state
Playwright: settings invalid URL -> bad endpoint -> test connectivity -> clear key
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-RESPONSIVE-001 | 首页桌面/移动端显示 | 通过；未发现横向滚动或明显遮挡 |
| TC-REFRESH-001 | 创建项目后刷新 | 失败；刷新后当前项目和步骤状态丢失 |
| TC-LONG-DATA-001 | 超长项目名 | 部分通过；未产生页面横向滚动，但刷新后同样丢失工作上下文 |
| TC-SETTINGS-001 | 非法 Base URL | 通过；`not-a-url` 被浏览器 URL 校验拦截 |
| TC-NETWORK-001 | 不可达 LLM Base URL | 部分通过；连通测试失败，但错误文案暴露内部异常类名 |

## Positive Evidence

- 首页桌面和移动端 baseline 没有控制台错误。
- 超长项目名没有造成 `document.documentElement.scrollWidth > innerWidth` 的横向滚动。
- 设置页 `Base URL=not-a-url` 被浏览器原生 URL 校验拦截，未提交保存。
- 设置页假 API Key 测试结束后，`清除密钥` 可用并能回到 `尚未配置 API Key` 状态。

## Screenshot Evidence

- `.gstack/qa-reports/screenshots/round3-home-desktop.png`
- `.gstack/qa-reports/screenshots/round3-home-mobile.png`
- `.gstack/qa-reports/screenshots/round3-reload-short-before.png`
- `.gstack/qa-reports/screenshots/round3-reload-short-after.png`
- `.gstack/qa-reports/screenshots/round3-settings-invalid-url-save.png`
- `.gstack/qa-reports/screenshots/round3-settings-bad-endpoint-after-test.png`
- `.gstack/qa-reports/screenshots/round3-settings-after-clear-key.png`

State evidence:

- `.gstack/qa-reports/round3-baseline-ui.json`
- `.gstack/qa-reports/round3-long-name-state.json`
- `.gstack/qa-reports/round3-reload-short-state.json`
- `.gstack/qa-reports/round3-settings-invalid-state.json`

## Findings

### ISSUE-006 / BUG-006: Reload Loses Current Project And Guided Flow Step

Severity：Medium / P2

Repro:

1. Create project `QA Reload Short` from `从技术想法撰写发明专利`.
2. Confirm the UI has advanced to step 2 `确认发明点与护城河`.
3. Refresh the browser.

Actual：Page returns to the three-entry start screen. The sidebar says `当前项目 未选择`, while the top selector still contains the created projects.

Expected：Current project and guided flow step should restore, or the app should show a clear re-selection prompt without contradictory state.

Evidence：

- `.gstack/qa-reports/screenshots/round3-reload-short-before.png`
- `.gstack/qa-reports/screenshots/round3-reload-short-after.png`
- `.gstack/qa-reports/round3-reload-short-state.json`

### ISSUE-007 / BUG-007: Connectivity Failure Shows Raw SDK Error

Severity：Low / P3

Repro:

1. Open `设置 · LLM 服务`.
2. Set Base URL to `http://127.0.0.1:9`.
3. Enter fake API key `qa-fake-key-do-not-use`.
4. Save, then click `测试连通`.

Actual：The page shows `APIConnectionError: Connection error.`.

Expected：The page should show a user-facing Chinese error with next steps, such as checking Base URL, network/proxy, or credentials.

Evidence：

- `.gstack/qa-reports/screenshots/round3-settings-bad-endpoint-after-test.png`
- `.gstack/qa-reports/round3-settings-invalid-state.json`

## Console Health

No browser console errors were observed in this round. The new issues are state-restoration and user-facing error-message problems.

## Notes

- I did not repair any code.
- I used fake settings credentials only; the key was cleared at the end of the settings test.
- Browser back from a freshly loaded SPA page returned to `about:blank` in this automation session, so it was not counted as a product bug.
