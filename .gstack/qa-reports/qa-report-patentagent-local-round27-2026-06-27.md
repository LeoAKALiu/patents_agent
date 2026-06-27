# QA Report: PatentAgent Local Round 27

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` contains ignored local QA evidence.

## Scope

Formal draft, post-draft review, and annotated repair editor regression tests:

- Official compile behavior and stale compile/review invalidation.
- Post-draft review behavior used by the formal draft gate.
- Repair-session backend behavior.
- Frontend repair editor rendering and interaction regression coverage.

## Environment

- Command environment: local repo checkout, no browser server required for this regression round.
- Python command: `python3 -m pytest tests/test_official_compile.py tests/test_post_draft_review.py tests/test_post_draft_repair.py -q`
- Frontend command: `npm --prefix frontend test -- PostDraftRepairEditor.test.tsx --run`

## Commands / Probes

```bash
python3 -m pytest tests/test_official_compile.py tests/test_post_draft_review.py tests/test_post_draft_repair.py -q
npm --prefix frontend test -- PostDraftRepairEditor.test.tsx --run
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-EXPORT-002 | 修改初稿后尝试复用旧导出结果 | 通过；正式稿和成稿会审相关回归测试全绿 |
| TC-REPAIR-001 | 打开标注式修复编辑器并点击多个问题 | 通过；后端 repair-session 和前端编辑器测试全绿 |

## Findings

No new product bug opened in Round27.

The Python regression suite passed:

```text
71 passed, 43 warnings in 4.16s
```

The frontend repair editor test passed:

```text
Test Files  1 passed (1)
Tests       8 passed (8)
Duration    1.39s
```

Warnings were Chroma `DeprecationWarning` messages from collection configuration and did not fail the run.

## Positive Evidence

- `tests/test_official_compile.py` passed.
- `tests/test_post_draft_review.py` passed.
- `tests/test_post_draft_repair.py` passed.
- `frontend` Vitest `PostDraftRepairEditor.test.tsx` passed.
- Exit code: `0` for both commands.
- No new bug ID opened.

## State Evidence

- `.gstack/qa-reports/round27-official-review-repair-tests-state.json`

## Baseline Update

- New bug ID opened: none.
- Baseline health score unchanged: `61`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=5`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- This was an automated regression round, not a browser/Tauri visual evidence round; it complements earlier browser and API evidence around post-draft review and repair editor risk.
