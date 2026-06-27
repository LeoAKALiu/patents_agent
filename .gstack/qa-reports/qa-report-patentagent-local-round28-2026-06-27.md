# QA Report: PatentAgent Local Round 28

Status: DONE

Date: 2026-06-27

## Source Identity

- Branch: `fix/code-review-hardening`
- Short SHA: `045b042`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at test time: `M README.md`, `?? BUGS.md`, `?? docs/qa/`; `.gstack/qa-reports` and `.artifacts` contain ignored local QA evidence.

## Scope

V1 smoke regression for the formal draft/export gate:

- Full backend pytest suite.
- V1 API smoke with repeat count 2.
- Deterministic quality gate and official compile path.
- Frontend Vitest suite.
- Frontend production build.
- Tauri `cargo check` and `cargo test`.

## Environment

- Command environment: local repo checkout.
- Smoke command: `bash scripts/v1_smoke.sh`
- Quality report artifacts:
  - `.artifacts/v1.1.0-quality/v1_1_quality_report.json`
  - `.artifacts/v1.1.0-quality/v1_1_quality_report.md`

## Commands / Probes

```bash
bash scripts/v1_smoke.sh
```

## Scenarios Covered

| 用例ID | 场景 | 结果 |
|---|---|---|
| TC-EXPORT-001 | 运行质量检查、正式稿编译、成稿会审后导出 | 通过；v1 smoke 完整成功退出 |

## Findings

No new product bug opened in Round28.

The v1 smoke completed successfully:

```text
420 passed, 147 warnings in 18.24s
v1.1 deterministic quality gate passed
v1 API smoke passed
Frontend Vitest: 14 test files passed, 130 tests passed
Vite build passed
cargo check passed
cargo test: 5 passed
v1 smoke completed successfully
```

Warnings were Chroma `DeprecationWarning` messages and Node `DEP0205` deprecation warnings; they did not fail the smoke.

## Positive Evidence

- Full backend pytest suite passed.
- `scripts/v1_api_smoke.py --repeat-count 2` passed.
- V1 quality report was generated under `.artifacts/v1.1.0-quality/`.
- Frontend Vitest suite passed.
- Frontend production build passed.
- Tauri `cargo check` passed.
- Tauri `cargo test` passed.
- Exit code: `0`.
- No new bug ID opened.

## State Evidence

- `.gstack/qa-reports/round28-v1-smoke-state.json`
- `.artifacts/v1.1.0-quality/v1_1_quality_report.json`
- `.artifacts/v1.1.0-quality/v1_1_quality_report.md`

## Baseline Update

- New bug ID opened: none.
- Baseline health score unchanged: `61`.
- Current cumulative issues unchanged: `P1=3`, `P2=8`, `P3=5`.

## Notes

- I did not repair any code.
- Product source was not inspected for implementation details during this QA round.
- This was an automated smoke round, not a packaged DMG or installed-app smoke.
