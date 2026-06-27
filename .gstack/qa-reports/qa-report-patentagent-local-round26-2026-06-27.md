# QA Report: PatentAgent Local Round 26

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

External draft / intake regression tests:

- Empty Markdown / empty document handling for external draft intake.
- Invalid or fake DOCX handling.
- External draft API behavior for abnormal files.
- Regression coverage tied to `TC-INTAKE-001` and `TC-INTAKE-002`.

## Environment

- Command environment: local repo checkout, no browser server required for this integration round.
- Python command: `python3 -m pytest tests/test_external_drafts.py tests/test_external_drafts_api.py -q`

## Commands / Probes

```bash
python3 -m pytest tests/test_external_drafts.py tests/test_external_drafts_api.py -q
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-INTAKE-001 | 外部稿件入口上传空 Markdown / 空文档 | 通过；相关外部稿件和 API 回归测试全绿 |
| TC-INTAKE-002 | 外部稿件入口上传伪装成 DOCX 的非 DOCX 文件 | 通过；相关异常 DOCX 回归测试全绿 |

## Findings

No new product bug opened in Round26.

The external draft regression suite passed:

```text
29 passed, 11 warnings in 1.99s
```

Warnings were Chroma `DeprecationWarning` messages from collection configuration and did not fail the run.

## Positive Evidence

- `tests/test_external_drafts.py` passed.
- `tests/test_external_drafts_api.py` passed.
- Exit code: `0`.
- No new bug ID opened.

## State Evidence

- `.gstack/qa-reports/round26-external-drafts-pytest-state.json`

## Baseline Update

- New bug ID opened: none.
- Baseline health score unchanged: `61`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=5`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- This was an integration regression round, not a browser UI round; it complements prior browser and API evidence for abnormal file handling.
