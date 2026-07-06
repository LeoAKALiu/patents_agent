# PR #132 Review Fix Evidence

Date: 2026-07-06

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent_omp_ui`
- Branch: `codex/omp-ui-hardening`
- Base PR: #132, base `codex/omp-ui-baseline`, head `codex/omp-ui-hardening`
- Starting HEAD for this review-fix pass: `ec71015d`
- Dirty tree: intentional review-fix changes only

## Fixes Covered

- P0 backend CI dependency gate: bounded FastAPI to `>=0.115.0,<0.139.0` and Starlette to `<1.0.0` so CI does not resolve a Starlette 1.x lifecycle API break.
- P0 inherited frontend regression: completed disclosure runs now preserve package patent-point candidates after backend list refresh, and the routed UI test asserts the current expert-tool flow.
- P1 quality workflow gate: completion patch mutations now respect `!actionGate.allowed` for both bulk accept and individual patch accept controls.
- P1 annotated repair real-data gate: verified the production React surface against a live seeded backend with a non-empty repair-session payload.
- P3 whitespace gate: removed the trailing blank line from the prior evidence file.

## Annotated Repair Real-Data Gate

Seeded backend:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5174`
- Project: `c61a77d85ad14af2aeceb49a6ff255b6`
- Post-draft review run: `e72a9a51a9f445f7a97f91a478a4e3dc`

API check:

```bash
curl -fsS \
  http://127.0.0.1:8000/api/projects/c61a77d85ad14af2aeceb49a6ff255b6/post-draft-reviews/e72a9a51a9f445f7a97f91a478a4e3dc/repair-session \
  | python -m json.tool
```

Observed payload:

- `stale: false`
- `issues`: 9 non-empty issues
- `sections`: non-empty `title`, `abstract`, `claims`, `description`, and `drawing_description`
- `draft_package_hash` equals `current_draft_hash`

UI verification:

- Selected project `标注修复真实数据门禁` in the production React dev app.
- Opened `文稿与修复` -> `标注修复`.
- Confirmed the embedded annotated repair editor renders all three panes:
  - left issue queue: `9 项`
  - middle draft sections: title, abstract, claims, description, drawing description
  - right issue detail panel: selected issue summary, anchor context, manual/AI repair actions
- Clicked `严重 权利要求1含内部引导语 好的，根据`.
- Confirmed the selected issue changed to active, the inspector changed to `权利要求书`, and the anchor context highlighted `好的，根据`.

Screenshot:

- `docs/ui-redesign/evidence/screenshots/2026-07-06-pr132-review-fixes-repair-real-data.png`

## Verification

```bash
python -m venv /tmp/patents-agent-ci-deps-check
/tmp/patents-agent-ci-deps-check/bin/python -m pip install -q -e ".[dev]"
/tmp/patents-agent-ci-deps-check/bin/python - <<'PY'
import fastapi, starlette
print(fastapi.__version__)
print(starlette.__version__)
print(hasattr(fastapi.FastAPI, "add_event_handler"))
PY
```

Confirmed fresh dependency resolution uses `fastapi-0.138.2` with `starlette-0.52.1`, preserving `FastAPI.add_event_handler`.

```bash
/tmp/patents-agent-ci-deps-check/bin/python -m pytest -q
```

Result: passed, 891 tests in 230.66 seconds.

```bash
cd frontend && npm test -- AppProjectSelectionFlow.test.tsx flow/panels/QualityPanel.test.tsx -- --run
cd frontend && npm test -- --run
cd frontend && npm run build
python -m pytest -q
git diff --check
```

Results:

- Focused frontend tests: passed, 2 files / 9 tests
- Full frontend tests: passed, 41 files / 293 tests
- Frontend build: passed
- Backend pytest: passed, 891 tests
- Fresh venv backend pytest: passed, 891 tests
- Diff whitespace check: passed

No DMG or installed app artifact was built or inspected for this review-fix pass.
