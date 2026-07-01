# Patent Flow E2E Audit Findings

Source identity:
- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/patent-flow-e2e-audit`
- Branch: `codex/patent-flow-e2e-audit`
- Base SHA: `e5036fc3`
- Dirty tree: yes, intentionally contains fixes plus QA artifacts from this audit.

## Repro Strategy

I used a clean isolated worktree, deterministic API smoke tests, then a browser-driven run against the real React app and a local fake backend. The browser path starts from a blank app state, creates a project from one technical idea, generates disclosure materials, confirms the invention point, runs deliberation, formula extraction, draft generation, quality checks, official compile, post-draft review, then downloads official Markdown and DOCX exports.

The reusable browser script is:

`qa_runs/patent_flow_goal_20260701/artifacts/browser-ui-created-flow/run_full_happy_path.js`

## Blockers Found

1. Created-project selection race
   - Symptom: after creating a project, an older `refreshAll()` result could clear or overwrite the newly selected project.
   - Fix: guard `refreshAll()` by the selection active at refresh start and do not overwrite current project state with stale selections.
   - Regression: `frontend/src/AppProjectSelectionFlow.test.tsx`.

2. Guided workbench collapsed after project creation
   - Symptom: after choosing "from idea" and creating a project, the detailed guided flow disappeared, so candidate cards/actions were unreachable.
   - Fix: keep the detailed guided workbench whenever `startChoice` is active, even after a project is selected.
   - Regression: `frontend/src/AppProjectSelectionFlow.test.tsx`.

3. Synchronous disclosure completion could be lost
   - Symptom: fake/fast disclosure runs returned `completed`, but list refresh could still be stale; UI showed no invention candidates.
   - Fix: upsert terminal disclosure runs locally and preserve locally observed terminal runs across stale fetched lists.
   - Regression: `frontend/src/AppProjectSelectionFlow.test.tsx`.

4. Browser QA backend was not a true first-mile harness
   - Symptom: disclosure/formula stages were missing, and deliberation tried to call real local agent CLIs.
   - Fix: add deterministic fake LLM responses and a `FakeAgentRuntime`.
   - Regression: `tests/test_browser_evidence_backend.py`.

5. Happy-path fake draft generated dirty claims
   - Symptom: official compile and post-draft review reached a blocked path because fake `claims` contained "好的，根据..." and "注：内部备注".
   - Fix: make the happy-path fake backend generate clean claims and passing post-draft review payloads.
   - Regression: `tests/test_browser_evidence_backend.py`.

6. Official warning missed "内部备注" residual text
   - Symptom: a formal compile run could complete even when official claims still contained "注：内部备注"; hard-blocking this at compile time broke post-draft repair sessions that intentionally diagnose and repair such residual text.
   - Fix: keep backend compile pass-through for the repair gate and add "内部备注" to frontend official contamination scanning.
   - Regression: `tests/test_official_compile.py`, `tests/test_post_draft_repair.py`, and `frontend/src/lib/officialContamination.test.ts`.

7. Browser waiting strategy was too brittle
   - Symptom: fixed sleeps falsely reported failures while the app was still refreshing or had moved to different copy.
   - Fix: use step/readiness text and API export readiness as the source of completion.
   - Evidence: `run_full_happy_path.js`.

## Suggested PR Boundaries

PR 1: Frontend first-mile guided flow recovery
- `frontend/src/App.tsx`
- `frontend/src/AppProjectSelectionFlow.test.tsx`
- `frontend/src/app/AppRoot.tsx`

PR 2: Deterministic browser E2E harness
- `qa_runs/patent_flow_long_qa_20260630/browser_evidence_backend.py`
- `tests/test_browser_evidence_backend.py`
- `qa_runs/patent_flow_goal_20260701/artifacts/browser-ui-created-flow/run_full_happy_path.js`

PR 3: Official compile residual internal-note gate
- `backend/app/official_compile.py`
- `tests/test_official_compile.py`
- `frontend/src/lib/officialContamination.ts`
- `frontend/src/lib/officialContamination.test.ts`

## Passing Evidence

Browser full happy path:
- Project: `ab9e37ef14d74f9c96dc05c6a7f6f32d`
- Result: `exportReady: true`, `nextAction: export_ready`
- Screenshot: `qa_runs/patent_flow_goal_20260701/artifacts/browser-ui-created-flow/full-happy-export-ready.png`

Downloaded official exports:
- Markdown: `qa_runs/patent_flow_goal_20260701/artifacts/browser-ui-created-flow/full-happy-official.md`
  - Size: 870 bytes
  - SHA256: `f5838ecf4a37edc511b3f03a681077a551bb9de42303543b64f240e0a3476e4b`
- DOCX: `qa_runs/patent_flow_goal_20260701/artifacts/browser-ui-created-flow/full-happy-official.docx`
  - Size: 37173 bytes
  - SHA256: `d85e334da03b236598f77dfe1d5b409f65d274b609f8f2d78f07f4bfe4a9f94c`

Validation commands:
- `python3 -m pytest tests/test_official_compile.py tests/test_browser_evidence_backend.py -q` -> 90 passed.
- `npm --prefix frontend test -- AppProjectSelectionFlow routes officialContamination --run` -> 19 passed.
- `npm --prefix frontend test -- --run` -> 274 passed.
- `npm --prefix frontend run build` -> passed.
- `python3 scripts/qa_preflight.py --json` -> clean.
