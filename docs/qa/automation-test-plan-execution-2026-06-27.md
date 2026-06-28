# PatentAgent 自动化测试计划执行报告

日期：2026-06-27

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/automation-test-plan`
- Short SHA: `3f6258ac`
- Dirty tree: yes
- Pre-existing unrelated dirty files observed: `docs/project-design-overview.md`, frontend guided-flow/progress files
- Test artifact generated during verification: `output/playwright/guided-progress-next-button.png`

## Plan Source

- `/Users/leo/Downloads/PatentAgent-自动化测试计划.md`
- Version: `v0.1`
- Important caveat from plan: draft, must align with real `guidedFlow.ts`, `schemas.py`, and `main.py` before execution.

## Work Completed

1. Aligned the plan with current backend/frontend implementation surfaces.
2. Added Phase 0 cassette support for the LLM adapter:
   - `PATENTAGENT_LLM_MODE=live|record|replay`
   - `PATENTAGENT_LLM_CASSETTE_DIR`
   - `PATENTAGENT_LLM_CASSETTE_SUITE`
   - `PATENTAGENT_LLM_CASSETTE_CASE`
   - Replay mode fails closed on missing entries and can run without a real API key.
3. Added a headless API `FlowDriver` test helper for plan-level pipeline tests.
4. Added an end-to-end driver regression proving:
   - external draft intake creates a working draft
   - official export is blocked until official compile + post-draft review pass
   - source draft edits invalidate previous compile/review hashes
   - official export blocks after invalidation

## Verification Run

- Focused backend plan suites:
  `python -m pytest tests/test_llm_cassette.py tests/test_flow_driver.py tests/test_post_draft_review.py tests/test_draft_completion_api.py tests/test_official_compile.py tests/test_export.py tests/test_evidence_binding.py tests/test_llm_cache.py tests/test_external_drafts_api.py tests/test_runtime_controls.py -q`
  Result: 93 passed, 59 warnings.

- Focused frontend gate suites:
  `npm test -- --run src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx src/PostDraftReviewPanel.test.tsx src/PostDraftRepairEditor.test.tsx src/store/projectData.test.ts`
  Result: 5 files passed, 78 tests passed.

- Full backend suite:
  `python -m pytest -q`
  Result: 512 passed, 203 warnings.

- Full frontend suite:
  `npm test`
  Result: 27 files passed, 181 tests passed.

## Plan Coverage Status

- Phase 0.1 cassette mode: implemented and tested for record/replay/live behavior.
- Phase 0.2 Headless FlowDriver: implemented as a test helper over real FastAPI endpoints.
- Phase 0.3 structured run logs: existing runtime state/log tests passed; no new schema migration added.
- INV-2 hash consistency: executed through existing export tests and new FlowDriver invalidation test.
- INV-3 official/internal isolation: existing official compile/export tests passed.
- INV-5 export gate completeness: existing post-draft/export gate tests plus FlowDriver test passed.
- INV-1, INV-4, INV-6: partially covered by existing tests; not yet exhaustive against every target step/long-running run.
- Phase 2 adversarial E2E explorer: not executed; requires a larger action generator and trace budget.
- Phase 3 patent quality judge/golden set: not executed; blocked on golden data, judge-family selection, and patent-agent calibration.
- Phase 4 CI/release gate: not changed in this pass.

## Remaining Gaps

1. Generate/curate real cassette fixtures under `tests/cassettes/<suite>/<case>.json` before requiring replay mode for broad deterministic CI.
2. Expand FlowDriver tests into the full INV-1..6 matrix.
3. Add the adversarial explorer/triage harness for 20+ traces per run.
4. Human-calibrate the queued golden/red-team patent-quality cases, approve fixture contents, record fixture SHA256 values, and only then enable selected judge/release regression gates.

## Continuation: 2026-06-28

Source identity:

- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/automation-test-plan`
- Short SHA at continuation start: `7bc7a450`
- Short SHA at latest continuation checkpoint: `d01715bf`
- Dirty tree: yes

Additional progress:

1. Added a static replay fixture at `tests/cassettes/generation/utility_model.json`.
   - It drives the real `/api/projects/{project_id}/generate` API path.
   - It runs with `PATENTAGENT_LLM_MODE=replay` and no `DEEPSEEK_API_KEY`.
   - It covers the utility-model generation stages: `claims`, `description`, `drawings`, `diagram`, `abstract`, and `image_prompt`.
2. Fixed cassette record mode for concurrent generation stages.
   - The draft generator records `description`, `drawings`, and `diagram` concurrently.
   - Cassette writes now use a per-cassette lock so record mode does not corrupt JSON or race on the temporary file.
3. Expanded `FlowDriver` invariant coverage.
   - Official export blocks with no draft.
   - Official export blocks with no current official compile.
   - Official export blocks with no post-draft review.
   - A later blocking post-draft review invalidates a prior passing review for the same compile.
   - Internal export remains available when official export is blocked by stale hashes.
4. Promoted `quality_done` into a hard official-export gate.
   - `/api/projects/{project_id}/official-export.md` and `.docx` now require current quality artifacts in addition to current official compile and current passing post-draft review.
   - The hash-bound quality artifacts are current `filing-readiness` and completed current `completion-runs`.
   - `claim-defense-worksheets` remain part of the quality bundle through completion-run inputs, but the current schema does not store a worksheet draft hash, so the hard freshness check is limited to the two hash-bound artifacts.
   - `/api/projects/{project_id}/export-readiness` now reports `quality_required`, `quality_done`, `missing_quality_checks`, and `next_action=run_quality_checks`.
5. Synchronized the frontend export guard with the backend gate.
   - `ExportReadiness.next_action` includes `run_quality_checks`.
   - The post-draft export surface and native export handler require `currentQualityChecked` before enabling official DOCX/Markdown export.
6. Expanded INV-1 cannot-skip-step coverage.
   - `FlowDriver` now verifies the readiness `next_action` chain from no draft through quality, official compile, post-draft review, and export-ready.
   - Direct API calls also assert draft generation, quality checks, official compile, and post-draft review cannot be skipped.
   - Partial quality bundles are covered: filing-only and completion-only states both fail official export with explicit missing quality checks.
7. Expanded INV-4 runtime control coverage.
   - Post-draft review queued-run cancellation is covered.
   - Repeated cancellation is idempotent and does not duplicate failure details.
   - Retry from a cancelled post-draft review links `retry_of` and reuses the current official compile.
8. Expanded INV-6 evidence-honesty coverage at the official export surface.
   - A project with materials, prior-art hits, research ledger entries, and verified patent points runs quality checks and official export.
   - The official Markdown export is asserted not to leak evidence ids, publication numbers, URLs, material file names, research ledger fields, or patent-point metadata.
9. Added a baseline adversarial flow explorer.
   - `tests/test_adversarial_flow_explorer.py` runs 20 deterministic random traces.
   - The action space includes out-of-order intake, partial quality checks, repeated quality checks, official compile, passing/blocking post-draft reviews, source edits, readiness reads, and official export attempts.
   - After every action it asserts `/export-readiness` and `/official-export.md` agree, successful official export implies current quality/compile/review gates, and internal export remains available for any project with a package.
10. Expanded the adversarial explorer into a replayable trace harness.
    - `tests/adversarial_flow_harness.py` records action names, action payloads, seed, and final gate state.
    - Trace artifacts can be written as JSON and replayed against a fresh temp data directory.
    - Explicit action sequences are supported so failing traces can be reduced and replayed without depending only on a PRNG seed.
    - The action space now includes lightweight `disclosure` and `formula` actions backed by deterministic fake LLM responses and a static prior-art provider.
    - Failure triage now supports greedy action-sequence shrinking and writes both a minimized replay trace and a summary JSON with original/minimized action counts and replay hints.
11. Seeded the golden/red-team patent-quality fixture set.
    - Added five cases under `tests/golden_patent_cases/<case_id>/case.json`.
    - Categories cover invention, utility model, existing draft cleanup, low-evidence effect honesty, and internal-pollution red-team.
    - Each case includes distinguishing features, prior-art summary, forbidden official content, quality thresholds, deterministic release-blocker checks, non-blocking LLM judge metadata, and human calibration status.
    - All cases are currently `pending_human_review` and `release_gate_enabled=false`; this keeps them out of release blocking until human calibration is actually completed.
12. Added a deterministic golden case evaluator.
    - `tests/golden_patent_evaluator.py` computes `claim_feature_coverage`, `spec_support_coverage`, `official_cleanliness`, and `evidence_honesty`.
    - Golden fixture tests verify supported official text meets thresholds.
    - Red-team low-evidence text containing forbidden verified-effect claims fails cleanliness and evidence-honesty checks.
    - The evaluator is deterministic and does not use live LLM judging.
13. Expanded the adversarial explorer with runtime-control actions.
    - Added `deliberation_queued_cancel` to create a queued deliberation run through the real store and cancel it through the public cancel endpoint.
    - Added `post_review_cancel_retry` to prepare a current draft/quality/official compile, create a queued post-draft review, cancel it through the public endpoint, and retry it through the public retry endpoint.
    - The replay payload records deterministic run IDs and retry linkage so minimized traces can reproduce queued-cancel/runtime-control failures.
14. Expanded generated-draft official text honesty coverage.
    - Added a `/generate` -> official compile regression where the generated draft leaks `evidence_id`, `research_ledger`, and a Google Patents URL into official fields.
    - Official compile now classifies evidence metadata fields as internal contamination and blocks the run before any official export can rely on the polluted package.
    - The existing hand-seeded evidence-boundary export test still covers that external evidence store metadata is not introduced into official text.
15. Added `draft_package_hash` freshness to claim-defense worksheets.
    - `ClaimDefenseWorksheet` now carries the same current-source hash used by filing readiness, official compile, post-draft review, and draft completion.
    - `/export-readiness` and official export now require all three quality-bundle artifacts for the current draft: filing readiness, claim-defense worksheet, and draft completion.
    - The frontend guided-flow quality gate now also rejects stale worksheets instead of only checking that some worksheet exists.
16. Expanded running post-draft review cancellation-race coverage.
    - Added a runtime-control regression where the claims reviewer completes, then the specification reviewer simultaneously requests cancellation and raises a provider exception.
    - Post-draft review progress now persists completed role results as partial artifacts before later stages finish.
    - Runtime LLM checkpoints now re-check cancellation when a provider raises, so cancellation wins over incidental provider errors and the interrupted run preserves retryable partial work.
17. Wired deterministic golden patent evaluation into CI/release gating.
    - Added `scripts/golden_quality_gate.py` as a release-gate entrypoint around the deterministic golden evaluator.
    - Disabled or uncalibrated cases are reported as skipped unless explicitly enabled, preserving the human-calibration requirement.
    - Enabled but uncalibrated cases fail closed with `enabled_without_human_calibration`.
    - Calibrated enabled cases require an official text fixture and must pass deterministic thresholds before the gate passes.
    - GitHub Actions now runs the golden patent deterministic release gate after the existing v1.1 deterministic quality gate and writes `.artifacts/golden-quality-gate.json`.
18. Expanded formula runtime cancellation-race coverage.
    - Added a running formula regression where `core_formula` observes a cancel request and then the provider raises `Connection error`.
    - Formula execution now treats persisted cancellation as the winning terminal state in the generic exception branch, returning `interrupted` with `reason=cancelled` instead of leaking the provider exception as a failed run.
    - The adversarial flow harness now includes a replayable `formula_cancel_exception` action, which forces formula-required project text, records the interrupted run payload, and asserts provider errors do not leak into the final cancellation result.
19. Expanded deliberation provider exception/cancellation-race coverage.
    - Added a running deliberation regression where the opening provider marks the run cancelled and then raises a provider exception.
    - Deliberation execution now treats persisted cancellation as the winning terminal state in the generic exception branch, returning `interrupted` with `reason=cancelled` instead of writing provider/runtime attribute errors into the terminal run.
    - The adversarial flow harness now includes a replayable `deliberation_cancel_exception` action that drives the real deliberation executor with a controlled failing provider runner and records whether provider errors leaked into the final cancellation result.
20. Expanded generated-draft inline evidence-key honesty coverage.
    - Added a `/generate` -> official compile regression where the generated draft leaks evidence key/value metadata inside otherwise normal official sentences, including `source_id=...`, `source_label=...`, and `material_id=...`.
    - Official compile now treats residual evidence metadata keys such as `source_id`, `source_label`, `material_id`, `source_url`, `evidence_status`, `verification_status`, and `internal_only` as blockers even when they are embedded inline instead of appearing as standalone JSON-like fields.
    - The blocked compile continues to prevent official export, preserving the official/internal evidence boundary for generated drafts.
21. Added adversarial generated-draft evidence-honesty action coverage.
    - The adversarial harness now includes a replayable `generated_evidence_honesty` action.
    - The action creates an isolated utility-model project, injects a generated draft with inline evidence metadata, verifies official compile blocks it, verifies official export remains blocked, and then restores the main trace project and LLM.
    - The isolation keeps random traces and `force_ready` traces stable while still exercising the generated-draft/evidence-honesty boundary through real API calls.
22. Distinguished stale quality artifacts from missing quality checks.
    - `/export-readiness` now reports `stale_quality_checks` and per-check `quality_check_states` alongside `missing_quality_checks`.
    - A source draft edit after a complete quality/compile/review loop now reports filing readiness, claim-defense worksheet, and draft completion as `stale` rather than `missing`.
    - Official export now surfaces stale quality artifacts in the 409 detail before falling through to stale compile/review messaging, improving release-gate ergonomics after cleanup or source edits.
    - The frontend `ExportReadiness` type now exposes the new stale-quality fields for UI follow-up.
23. Tightened mixed stale/missing quality-bundle state classification.
    - Added a FlowDriver regression where filing readiness and claim-defense worksheet exist only for an old draft, while draft completion only has a failed old run.
    - `/export-readiness` now reports filing readiness and claim-defense worksheet as `stale`, but reports draft completion as `missing` because failed completion runs are not usable quality artifacts.
    - Official export 409 details now include both `missing quality checks` and `stale quality checks` for mixed quality-bundle states.
24. Expanded Chinese generated-draft evidence-metadata honesty coverage.
    - Added an official compile regression for Chinese evidence metadata aliases in official fields, including `证据编号`, `材料编号`, `来源标签`, and `引用来源`.
    - Official compile now blocks those Chinese metadata labels as official-text contamination, while residual scanning continues to report multiple metadata keys from the same generated sentence instead of collapsing them into one removal.
    - The adversarial harness now includes a replayable `generated_chinese_evidence_honesty` action that creates an isolated generated utility-model project, verifies the compile is blocked, verifies official export remains blocked, and restores the main force-ready trace project.
25. Expanded generated-draft URL leakage honesty coverage.
    - Added an official compile regression for official fields that embed Markdown links and bare `https://...` URLs inside otherwise normal claim/description text.
    - Official compile now blocks residual `http://` and `https://` content as official-text contamination without auto-deleting the whole claim or description line.
    - The adversarial harness now includes a replayable `generated_url_evidence_honesty` action that creates an isolated generated utility-model project, injects Markdown-link and bare-URL leakage, verifies official compile blocks it, verifies official export remains blocked, and restores the main force-ready trace project.
26. Expanded generated-draft bracketed citation honesty coverage.
    - Added an official compile regression for bracketed evidence/source citations embedded in otherwise normal claim and description text, including `[evidence:EV-...]` and `【来源：...】`.
    - Official compile now blocks bracketed evidence citations through residual official-text scanning without auto-deleting the surrounding claim or description sentence.
    - The adversarial harness now includes a replayable `generated_bracketed_citation_honesty` action that creates an isolated generated utility-model project, injects bracketed evidence citation leakage, verifies official compile blocks it, verifies official export remains blocked, and restores the main force-ready trace project.
27. Expanded generated-draft nested JSON wrapper honesty coverage.
    - Added an official compile regression for non-empty official JSON field wrappers such as `{"claims": "..."}` and nested `{"description": {...}}` content inside official draft fields.
    - Official compile now blocks non-empty `title`, `abstract`, `claims`, `description`, and `drawing_description` field wrappers as JSON/format contamination instead of letting wrapper syntax enter the official package.
    - The adversarial harness now includes a replayable `generated_json_wrapper_honesty` action that creates an isolated generated utility-model project, injects non-empty official JSON wrappers, verifies official compile blocks it, verifies official export remains blocked, and restores the main force-ready trace project.
28. Expanded adversarial failure triage summary detail.
    - Failure triage summaries now include the original final `FlowState` snapshot, including gate states and `export_allowed`.
    - Summaries now include `failure_tags` such as `export_blocked`, `quality_stale`, `official_compile_stale`, and `post_draft_review_stale` so the failure class is visible without opening the trace.
    - Summaries now include full minimized action entries with payloads plus removed action names, making replay and root-cause inspection easier than action names alone.
29. Added replay command and action category counts to adversarial triage.
    - Failure triage summaries now include a copyable `PYTHONPATH=tests python` replay command for the minimized trace artifact.
    - Summaries now include original, minimized, and removed action category counts, grouping steps into setup, quality gate, official gate, export probe, mutation, runtime-control, and honesty-probe buckets.
    - The richer category counts make shrink results easier to inspect when a reproducer removes nonessential reads/exports or quality preparation.
30. Added per-action gate deltas to adversarial traces and triage.
    - Trace artifacts now include `action_gate_deltas` for each action, recording before/after gate states and export eligibility.
    - Failure triage summaries now copy those deltas and split them into minimized and removed action delta groups.
    - The edit-after-ready regression now surfaces the exact transition where quality, official compile, and post-draft review gates move from `current` to `stale` and official export flips from allowed to blocked.
31. Aligned direct official export with export-readiness quality priority.
    - Added a FlowDriver regression for legacy/current drafts that have no quality bundle and no official compile.
    - Direct `/official-export.md` now reports missing quality checks before reporting missing official compile, matching `/export-readiness` and preventing users from being sent to compile before the stricter three-artifact quality bundle exists.
    - Existing compile/review invalidation tests now explicitly create current quality artifacts before asserting compile/review gate failures, keeping those tests focused on the intended gate.

Additional verification:

- `python -m pytest tests/test_llm_cassette.py -q`
  Result: 7 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result: 4 passed, 5 warnings.
- `python -m pytest tests/test_llm_cassette.py tests/test_flow_driver.py -q`
  Result: 11 passed, 6 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_filing_readiness.py tests/test_post_draft_review.py tests/test_external_drafts_api.py tests/test_api.py tests/test_draft_completion_api.py tests/test_content_disposition.py -q`
  Result: 103 passed, 69 warnings.
- `npm run build`
  Result: passed.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after INV-1 expansion: 6 passed, 7 warnings.
- `python -m pytest tests/test_runtime_controls.py -q`
  Result after INV-4 expansion: 9 passed, 10 warnings.
- `python -m pytest tests/test_evidence_binding.py -q`
  Result after INV-6 expansion: 6 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_llm_cassette.py -q`
  Result: 28 passed, 18 warnings.
- `git diff --check`
  Result: passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result: 1 passed, 21 warnings. This single test executes 20 traces.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_llm_cassette.py -q`
  Result: 29 passed, 38 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after replay/disclosure/formula expansion: 3 passed, 24 warnings.
- `python -m pytest tests/test_golden_patent_cases.py -q`
  Result: 3 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_llm_cassette.py -q`
  Result: 34 passed, 41 warnings.
- `git diff --check`
  Result: passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after triage shrinking: 4 passed, 41 warnings.
- `python -m pytest tests/test_golden_patent_cases.py -q`
  Result after deterministic evaluator: 5 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_llm_cassette.py -q`
  Result after triage shrinking and deterministic evaluator: 39 passed, 60 warnings.
- `git diff --check`
  Result: passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_runtime_control_actions -q`
  Result after runtime-control action expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after runtime-control action expansion: 5 passed, 42 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_llm_cassette.py -q`
  Result after runtime-control action expansion: 40 passed, 61 warnings.
- `git diff --check`
  Result after runtime-control action expansion: passed.
- `python -m pytest tests/test_evidence_binding.py::test_generated_draft_with_evidence_metadata_is_blocked_by_official_compile -q`
  Result after generated-draft honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_official_compile.py -q`
  Result after generated-draft honesty expansion: 30 passed, 14 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_llm_cassette.py -q`
  Result after generated-draft honesty expansion: 64 passed, 73 warnings.
- `git diff --check`
  Result after generated-draft honesty expansion: passed.
- `python -m pytest tests/test_claim_defense.py::test_claim_defense_api_persists_multiple_versions tests/test_flow_driver.py::test_flow_driver_export_gate_requires_complete_quality_bundle -q`
  Result after claim-defense worksheet hash expansion: 2 passed, 3 warnings.
- `npm test -- --run src/guidedFlow.test.ts`
  Result after frontend worksheet freshness expansion: 53 passed.
- `python -m pytest tests/test_claim_defense.py tests/test_flow_driver.py tests/test_filing_readiness.py tests/test_official_compile.py tests/test_post_draft_review.py tests/test_draft_completion_api.py tests/test_external_drafts_api.py tests/test_evidence_binding.py -q`
  Result after claim-defense worksheet hash expansion: 104 passed, 64 warnings.
- `npm test -- --run src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx`
  Result after claim-defense worksheet hash expansion: 55 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after claim-defense worksheet hash expansion: 75 passed, 77 warnings.
- `npm run build`
  Result after claim-defense worksheet hash expansion: passed.
- `git diff --check`
  Result after claim-defense worksheet hash expansion: passed.
- `python -m pytest tests/test_runtime_controls.py::test_post_draft_review_cancel_preserves_partial_role_result_and_wins_provider_exception -q`
  Result after running post-draft cancellation-race expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_runtime_controls.py tests/test_post_draft_review.py -q`
  Result after running post-draft cancellation-race expansion: 32 passed, 33 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after running post-draft cancellation-race expansion: 76 passed, 78 warnings.
- `git diff --check`
  Result after running post-draft cancellation-race expansion: passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after deterministic golden release-gate wiring: 4 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate.json`
  Result after deterministic golden release-gate wiring: passed; 5 cases skipped, 0 enabled, 0 failed.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after deterministic golden release-gate wiring: 9 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after deterministic golden release-gate wiring: 80 passed, 78 warnings.
- `git diff --check`
  Result after deterministic golden release-gate wiring: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after deterministic golden release-gate wiring: no new root artifacts found.
- `python -m pytest tests/test_runtime_controls.py::test_formula_cancel_request_wins_provider_exception_race -q`
  Result after formula cancellation-race expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_runtime_control_actions -q`
  Result after formula cancellation-race adversarial action: 1 passed, 2 warnings.
- `python -m pytest tests/test_runtime_controls.py -q`
  Result after formula cancellation-race expansion: 11 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after formula cancellation-race adversarial action: 5 passed, 42 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after formula cancellation-race expansion: 81 passed, 79 warnings.
- `git diff --check`
  Result after formula cancellation-race expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after formula cancellation-race expansion: no new root artifacts found.
- `python -m pytest tests/test_runtime_controls.py::test_deliberation_cancel_request_wins_provider_exception_race -q`
  Result after deliberation cancellation-race expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_runtime_control_actions -q`
  Result after deliberation cancellation-race adversarial action: 1 passed, 2 warnings.
- `python -m pytest tests/test_runtime_controls.py -q`
  Result after deliberation cancellation-race expansion: 12 passed, 13 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after deliberation cancellation-race adversarial action: 5 passed, 42 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after deliberation cancellation-race expansion: 82 passed, 80 warnings.
- `git diff --check`
  Result after deliberation cancellation-race expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after deliberation cancellation-race expansion: no new root artifacts found.
- `python -m pytest tests/test_evidence_binding.py::test_generated_draft_with_inline_evidence_keys_is_blocked_by_official_compile -q`
  Result after inline evidence-key honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_evidence_binding.py::test_generated_draft_with_evidence_metadata_is_blocked_by_official_compile tests/test_evidence_binding.py::test_generated_draft_with_inline_evidence_keys_is_blocked_by_official_compile -q`
  Result after inline evidence-key honesty expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_official_compile.py -q`
  Result after inline evidence-key honesty expansion: 31 passed, 15 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after inline evidence-key honesty expansion: 83 passed, 81 warnings.
- `git diff --check`
  Result after inline evidence-key honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after inline evidence-key honesty expansion: no new root artifacts found.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_isolated_generated_evidence_honesty_action -q`
  Result after generated evidence-honesty adversarial action: 1 passed, 2 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after generated evidence-honesty adversarial action: 6 passed, 43 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after generated evidence-honesty adversarial action: 84 passed, 82 warnings.
- `git diff --check`
  Result after generated evidence-honesty adversarial action: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after generated evidence-honesty adversarial action: no new root artifacts found.
- `python -m pytest tests/test_flow_driver.py::test_export_readiness_distinguishes_stale_quality_bundle_from_missing_checks -q`
  Result after stale-quality readiness expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after stale-quality readiness expansion: 9 passed, 10 warnings.
- `npm run build`
  Result after stale-quality readiness expansion: passed.
- `python -m pytest tests/test_official_compile.py::test_blocked_compile_cleanup_rechecks_quality_and_unlocks_export_loop -q`
  Result after stale-quality readiness expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_official_compile.py -q`
  Result after stale-quality readiness expansion: 32 passed, 21 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after stale-quality readiness expansion: 85 passed, 83 warnings.
- `git diff --check`
  Result after stale-quality readiness expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after stale-quality readiness expansion: no new root artifacts found.
- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_mixed_stale_and_missing_quality_checks -q`
  Result after mixed stale/missing quality-bundle expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after mixed stale/missing quality-bundle expansion: 10 passed, 11 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_official_compile.py -q`
  Result after mixed stale/missing quality-bundle expansion: 33 passed, 22 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after mixed stale/missing quality-bundle expansion: 86 passed, 84 warnings.
- `git diff --check`
  Result after mixed stale/missing quality-bundle expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after mixed stale/missing quality-bundle expansion: no new root artifacts found.
- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_chinese_evidence_metadata_aliases_and_markdown_links -q`
  Result after Chinese evidence-metadata honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_isolated_generated_evidence_honesty_action tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_chinese_generated_evidence_honesty_action -q`
  Result after Chinese evidence-metadata honesty expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after Chinese evidence-metadata honesty expansion: 24 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after Chinese generated evidence-honesty adversarial action: 7 passed, 44 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after Chinese evidence-metadata honesty expansion: 88 passed, 85 warnings.
- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_inline_url_and_markdown_link_leakage -q`
  Result after generated URL leakage honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_url_evidence_honesty_action -q`
  Result after generated URL leakage honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after generated URL leakage honesty expansion: 25 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after generated URL leakage honesty expansion: 8 passed, 45 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after generated URL leakage honesty expansion: 90 passed, 86 warnings.
- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_bracketed_evidence_citation_leakage -q`
  Result after generated bracketed citation honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_bracketed_citation_honesty_action -q`
  Result after generated bracketed citation honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after generated bracketed citation honesty expansion: 26 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after generated bracketed citation honesty expansion: 9 passed, 46 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after generated bracketed citation honesty expansion: 92 passed, 87 warnings.
- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_non_empty_official_json_field_wrappers -q`
  Result after generated JSON wrapper honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_json_wrapper_honesty_action -q`
  Result after generated JSON wrapper honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after generated JSON wrapper honesty expansion: 27 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after generated JSON wrapper honesty expansion: 10 passed, 47 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after generated JSON wrapper honesty expansion: 94 passed, 88 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_failure_triage_writes_minimized_replay_summary -q`
  Result after richer adversarial failure triage summary expansion: 1 passed, 18 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after richer adversarial failure triage summary expansion: 10 passed, 47 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after richer adversarial failure triage summary expansion: 94 passed, 88 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_failure_triage_writes_minimized_replay_summary -q`
  Result after replay command/action category triage expansion: 1 passed, 18 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after replay command/action category triage expansion: 10 passed, 47 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after replay command/action category triage expansion: 10 passed, 11 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after replay command/action category triage expansion: 94 passed, 88 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_failure_triage_writes_minimized_replay_summary -q`
  Result after per-action gate delta triage expansion: 1 passed, 18 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after per-action gate delta triage expansion: 10 passed, 47 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after per-action gate delta triage expansion: 10 passed, 11 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after per-action gate delta triage expansion: 94 passed, 88 warnings.
- `python -m pytest tests/test_flow_driver.py::test_official_export_reports_missing_quality_before_missing_compile_for_legacy_drafts -q`
  Result after direct export quality-priority expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py::test_flow_driver_export_gate_blocks_until_compile_and_review -q`
  Result after direct export quality-priority expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py::test_review_for_previous_compile_run_cannot_unlock_latest_compile -q`
  Result after direct export quality-priority expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py::test_official_export_requires_recompile_when_draft_changes -q`
  Result after direct export quality-priority expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after direct export quality-priority expansion: 27 passed, 12 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after direct export quality-priority expansion: 11 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after direct export quality-priority expansion: 95 passed, 89 warnings.

32. Frontend export gate now explains the quality blocker that the backend reports:
    - Added a RED test for the locked export view when quality checks are mixed missing/stale:
      `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
      Initial result: failed because the UI still showed only the generic `正式稿入口已锁定` copy.
    - Added shared frontend quality-check state typing and passed the three-artifact state bundle from `App.tsx` through `PostDraftWorkspace` into `ExportView`.
    - `ExportView` now labels missing/stale blockers as:
      `提交前质量检查`, `权利要求防守工作表`, and `成稿完整度检查`.
    - `currentQualityChecked` now comes from the same three states and treats stale claim-defense worksheets as not current, matching the guided-flow/export-readiness gate semantics.
    - Note: `npm run typecheck` is not defined in `frontend/package.json`; `npm run build` is the available TypeScript build gate and was run instead.

Verification after frontend quality-gate copy expansion:

- `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
  Result after frontend quality-gate copy expansion: 1 passed.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after frontend quality-gate copy expansion: 4 files passed, 58 tests passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after frontend quality-gate copy expansion: 95 passed, 89 warnings.
- `npm run build`
  Result after frontend quality-gate copy expansion: passed.
- `git diff --check`
  Result after frontend quality-gate copy expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after frontend quality-gate copy expansion: no new root artifacts found.

33. Frontend guided flow now fails closed when the current source draft hash is not loaded:
    - Added a RED regression for legacy/loading states where filing readiness, claim-defense worksheet, and completion records exist, but `currentSourceDraftHash` is empty.
      `npm test -- --run src/guidedFlow.test.ts --reporter=dot`
      Initial result: failed because `qualityChecked` was `true` without a comparable current source hash.
    - Updated `guidedFlow.ts` so quality checks require a known current source hash before advancing to official compile/post-review/export.
    - Updated `App.tsx` export-state derivation so quality artifacts are treated as `stale` rather than `current` while the current source hash is unknown.
    - Updated older guided-flow test fixtures that were meant to exercise official-compile/post-review paths to include `currentSourceDraftHash: "draft-hash"` explicitly.

Verification after legacy unknown-hash quality-gate expansion:

- `npm test -- --run src/guidedFlow.test.ts --reporter=dot`
  Result after legacy unknown-hash quality-gate expansion: 1 file passed, 54 tests passed.
- `npm test -- --run src/guidedFlow.test.ts src/views/exportView.test.tsx src/app/routes.test.tsx src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after legacy unknown-hash quality-gate expansion: 4 files passed, 59 tests passed.
- `npm run build`
  Result after legacy unknown-hash quality-gate expansion: passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after legacy unknown-hash quality-gate expansion: 95 passed, 89 warnings.
- `git diff --check`
  Result after legacy unknown-hash quality-gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after legacy unknown-hash quality-gate expansion: no new root artifacts found.

34. Added a source-footer evidence-honesty adversarial variant:
    - Added a RED compiler test for line-level evidence/source footers that do not contain URLs or bracketed citations:
      `Sources: internal-experiment-record.md`, `参考资料：实验记录.md`, and `依据材料：采集日志-001`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_source_footer_honesty`.
      Initial result: failed because the action was not registered.
    - Extended official compile evidence metadata line detection to block `sources`, `references`, `citations`, `materials`, `参考资料`, `参考文献`, `资料来源`, `依据材料`, and `支撑材料` when they appear as metadata-style line prefixes.
    - Added the `generated_source_footer_honesty` action and fixture LLM so generated drafts with source-footer leakage are covered by replayable adversarial traces.

Verification after source-footer honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_source_footer_metadata_lines -q`
  Result after source-footer honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_source_footer_honesty_action -q`
  Result after source-footer honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after source-footer honesty expansion: 28 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after source-footer honesty expansion: 11 passed, 48 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after source-footer honesty expansion: 97 passed, 90 warnings.
- `git diff --check`
  Result after source-footer honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after source-footer honesty expansion: no new root artifacts found.

35. Added a parenthetical evidence-citation adversarial variant:
    - Added a RED compiler test for parenthetical source/evidence metadata that is not a URL, not bracketed with `[]`/`【】`, and not a line-prefix footer:
      `（来源：实验记录.md）` and `(source: lab-note-001)`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_parenthetical_citation_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped parenthetical citation detector for parentheses containing source/evidence/citation/ref/material metadata with `:`, `：`, or `=`.
    - Added the `generated_parenthetical_citation_honesty` action and fixture LLM so generated drafts with parenthetical citation leakage are covered by replayable adversarial traces.

Verification after parenthetical citation honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_parenthetical_evidence_citation_leakage -q`
  Result after parenthetical citation honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_parenthetical_citation_honesty_action -q`
  Result after parenthetical citation honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after parenthetical citation honesty expansion: 29 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after parenthetical citation honesty expansion: 12 passed, 49 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after parenthetical citation honesty expansion: 99 passed, 91 warnings.
- `git diff --check`
  Result after parenthetical citation honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after parenthetical citation honesty expansion: no new root artifacts found.

36. Added human-readable Markdown failure triage for adversarial traces:
    - Added a RED assertion that `write_failure_triage(...)` must emit `trace-{seed}-triage.md` alongside the JSON summary.
      Initial result: failed because only `trace-{seed}-triage.json` existed.
    - The Markdown triage now includes failure message, tags, final gates, minimized actions, changed gate deltas, removed actions, and the replay command in a copyable bash block.
    - The Markdown is generated from the same summary dictionary as the JSON file so JSON and human-readable triage stay in sync.

Verification after Markdown triage UX expansion:

- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_failure_triage_writes_minimized_replay_summary -q`
  Result after Markdown triage UX expansion: 1 passed, 18 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown triage UX expansion: 12 passed, 49 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after Markdown triage UX expansion: 99 passed, 91 warnings.
- `git diff --check`
  Result after Markdown triage UX expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown triage UX expansion: no new root artifacts found.

37. Added an XML/HTML evidence-tag honesty variant:
    - Added a RED compiler test for XML-like evidence/source tags:
      `<source id="CN111111A">...</source>` and `<evidence ref="EV-CITY-001">...</evidence>`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_xml_tag_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped evidence-tag detector for `evidence`, `source`, `citation`, `ref`, `reference`, `references`, `material`, and `materials` tags.
    - Added the `generated_xml_tag_honesty` action and fixture LLM so generated drafts with XML/HTML-style evidence tags are covered by replayable adversarial traces.

Verification after XML evidence-tag honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_xml_evidence_tag_leakage -q`
  Result after XML evidence-tag honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_xml_tag_honesty_action -q`
  Result after XML evidence-tag honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after XML evidence-tag honesty expansion: 30 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after XML evidence-tag honesty expansion: 13 passed, 50 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after XML evidence-tag honesty expansion: 101 passed, 92 warnings.
- `git diff --check`
  Result after XML evidence-tag honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after XML evidence-tag honesty expansion: no new root artifacts found.

38. Added an HTML/Markdown comment evidence-honesty variant:
    - Added a RED compiler test for evidence/source metadata hidden inside comments:
      `<!-- source: lab-note-001 -->` and `<!-- 证据：EV-CITY-001 -->`.
      Initial result: failed because the compile was blocked by another pollution detector but did not surface `html_comment_citation`.
    - Added a RED adversarial harness test for `generated_html_comment_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped HTML comment detector for comment bodies containing source/evidence/citation/ref/material metadata with `:`, `：`, or `=`.
    - Added the `generated_html_comment_honesty` action and fixture LLM so generated drafts with hidden HTML/Markdown comment evidence leakage are covered by replayable adversarial traces.

Verification after HTML comment honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_comment_evidence_leakage -q`
  Result after HTML comment honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_comment_honesty_action -q`
  Result after HTML comment honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after HTML comment honesty expansion: 31 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after HTML comment honesty expansion: 14 passed, 51 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after HTML comment honesty expansion: 103 passed, 93 warnings.
- `git diff --check`
  Result after HTML comment honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML comment honesty expansion: no new root artifacts found.

39. Added a Markdown footnote evidence-honesty variant:
    - Added a RED compiler test for Markdown footnote definitions that carry evidence/source metadata:
      `[^source]: 来源：实验记录.md` and `[^1]: source: lab-note-001`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_markdown_footnote_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped Markdown footnote-definition detector so ordinary prose can still use inline footnote references, while evidence/source/citation/ref/material metadata in the footnote definition blocks official compile.
    - Added the `generated_markdown_footnote_honesty` action and fixture LLM so generated drafts with footnote-based evidence leakage are covered by replayable adversarial traces.

Verification after Markdown footnote honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_footnote_evidence_leakage -q`
  Result after Markdown footnote honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_footnote_honesty_action -q`
  Result after Markdown footnote honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after Markdown footnote honesty expansion: 32 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown footnote honesty expansion: 15 passed, 52 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after Markdown footnote honesty expansion: 105 passed, 94 warnings.
- `git diff --check`
  Result after Markdown footnote honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown footnote honesty expansion: no new root artifacts found.

40. Added an actionable golden-case calibration queue to the deterministic release-gate report:
    - Added a RED release-gate test requiring `run_gate(...)` to report `pending_calibration_count`, `calibration_queue_count`, and a `calibration_queue` entry for each uncalibrated golden case.
      Initial result: failed with `KeyError: 'pending_calibration_count'`.
    - The queue now includes case identity, category, application/input type, calibration status, reviewer/notes, release-gate state, required distinguishing features, forbidden official content, expected thresholds, deterministic checks, LLM diagnostic metadata, and a fixed human-review checklist.
    - Calibrated cases are not included in the pending calibration queue, so the queue specifically represents cases needing human review before any release-gate enablement.
    - The normal pass/fail/skipped release-gate semantics remain unchanged; the queue is additional evidence in the JSON report.
    - Running the gate against the checked-in golden cases now reports `pending_calibration_count=5`, `enabled_count=0`, and `failed_count=0`, keeping the cases non-blocking until human calibration is completed.

Verification after golden calibration queue expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_reports_actionable_calibration_queue -q`
  Result after golden calibration queue expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden calibration queue expansion: 5 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-calibration.json`
  Result after golden calibration queue expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden calibration queue expansion: 10 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden calibration queue expansion: 106 passed, 94 warnings.

41. Added a Markdown reference-definition evidence-honesty variant:
    - Added a RED compiler test for Markdown reference definitions carrying evidence/source metadata:
      `[source]: internal-experiment-record.md` and `[证据]: EV-CITY-001`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_markdown_reference_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped Markdown reference-definition detector for line-start definitions whose label is source/evidence/citation/ref/material metadata.
    - Added the `generated_markdown_reference_honesty` action and fixture LLM so generated drafts with reference-definition evidence leakage are covered by replayable adversarial traces.

Verification after Markdown reference-definition honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_reference_evidence_leakage -q`
  Result after Markdown reference-definition honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_reference_honesty_action -q`
  Result after Markdown reference-definition honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after Markdown reference-definition honesty expansion: 33 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown reference-definition honesty expansion: 16 passed, 53 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after Markdown reference-definition honesty expansion: 11 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after Markdown reference-definition honesty expansion: 108 passed, 95 warnings.
- `git diff --check`
  Result after Markdown reference-definition honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown reference-definition honesty expansion: no new root artifacts found.

42. Added a YAML front matter evidence-honesty variant:
    - Added a RED compiler test for front matter metadata containing `evidence:` and `证据：` keys.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_yaml_front_matter_honesty`.
      Initial result: failed because the action was not registered.
    - Added a small front matter scanner that only inspects text between `---` delimiters and blocks `evidence:` / `证据：` metadata keys inside that block.
    - Added the `generated_yaml_front_matter_honesty` action and fixture LLM so generated drafts with YAML-style evidence metadata are covered by replayable adversarial traces.

Verification after YAML front matter honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_yaml_front_matter_evidence_leakage -q`
  Result after YAML front matter honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_yaml_front_matter_honesty_action -q`
  Result after YAML front matter honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after YAML front matter honesty expansion: 34 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after YAML front matter honesty expansion: 17 passed, 54 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after YAML front matter honesty expansion: 110 passed, 96 warnings.
- `git diff --check`
  Result after YAML front matter honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after YAML front matter honesty expansion: no new root artifacts found.

43. Split failed current quality checks from missing quality checks in export readiness:
    - Added a RED FlowDriver test for the legacy/unstable run edge case where filing readiness and the claim-defense worksheet are current, but the current draft completion run exists with `status=failed`.
      Initial result: failed because export readiness reported `missing_quality_checks=["draft_completion"]`.
    - Backend export readiness now returns `failed_quality_checks=["draft_completion"]` and `quality_check_states.draft_completion="failed"` for a failed current completion run.
    - The official export 409 detail now includes `failed quality checks: draft_completion`, so users are directed to rerun the failed check rather than hunt for a missing artifact.
    - Frontend export gate copy now accepts `failed` quality states and renders `失败：成稿完整度检查` alongside missing and stale rows.

Verification after failed-quality state expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_failed_current_quality_checks -q`
  Result after failed-quality state expansion: 1 passed, 2 warnings.
- `npm test -- --run src/views/exportView.test.tsx`
  Result after failed-quality state expansion: 1 passed.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after failed-quality state expansion: 12 passed, 13 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts`
  Result after failed-quality state expansion: 2 files passed, 55 tests passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after failed-quality state expansion: 111 passed, 97 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts src/app/routes.test.tsx src/GuidedPatentFlow.officialCompile.test.tsx`
  Result after failed-quality state expansion: 4 files passed, 59 tests passed.
- `git diff --check`
  Result after failed-quality state expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after failed-quality state expansion: no new root artifacts found.

44. Split failed/interrupted current post-draft review attempts from missing review runs:
    - Added a RED FlowDriver test for the legacy edge case where the current source draft has passed the quality bundle and official compile, but the matching post-draft review attempt exists with `status=failed`.
      Initial result: failed because export readiness reported `has_review_run=false`.
    - Added a second RED FlowDriver test for an `interrupted` matching post-draft review attempt.
      Initial result: failed because the official export 409 detail still used the generic missing-review message.
    - Backend export readiness now reports the latest matching post-draft review attempt separately from the latest completed matching review, so failed/interrupted attempts return `has_review_run=true`, `review_run_id`, and `review_status`.
    - The official export gate still only unlocks on a completed, export-allowed review for the exact current official package, but the 409 detail now distinguishes failed and interrupted current review attempts from a truly missing review.
    - Frontend `ExportReadiness` typing now includes `review_status` for callers that surface readiness-state details.

Verification after failed/interrupted post-draft review state expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_failed_current_post_draft_review tests/test_flow_driver.py::test_export_readiness_reports_interrupted_current_post_draft_review -q`
  Result after post-draft review state expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after post-draft review state expansion: 14 passed, 15 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts`
  Result after post-draft review state expansion: 2 files passed, 55 tests passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after post-draft review state expansion: 113 passed, 99 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts src/app/routes.test.tsx src/GuidedPatentFlow.officialCompile.test.tsx`
  Result after post-draft review state expansion: 4 files passed, 59 tests passed.
- `git diff --check`
  Result after post-draft review state expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after post-draft review state expansion: no new root artifacts found.

45. Added a Markdown table evidence-honesty variant:
    - Added a RED compiler test for Markdown tables that carry evidence/source metadata rows such as `| source | lab-note-001 |`, `| evidence | EV-CITY-001 |`, and `| 证据 | 实验记录.md |`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_markdown_table_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped Markdown-table detector that only flags table rows with evidence/source/citation/ref/material metadata cells, then blocks official compile with `markdown_table_citation`.
    - Added the `generated_markdown_table_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in tables are covered by replayable adversarial traces.

Verification after Markdown table honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_table_evidence_leakage -q`
  Result after Markdown table honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_table_honesty_action -q`
  Result after Markdown table honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after Markdown table honesty expansion: 35 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown table honesty expansion: 18 passed, 55 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after Markdown table honesty expansion: 115 passed, 100 warnings.
- `git diff --check`
  Result after Markdown table honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown table honesty expansion: no new root artifacts found.

46. Split blocked/failed current official compile attempts from missing compile runs:
    - Added a RED FlowDriver test for the legacy edge case where the current source draft has a quality-current bundle, but the matching official compile attempt exists with `status=blocked`.
      Initial result: failed with `KeyError: 'has_compile_run'` because export readiness treated the blocked attempt as if no compile had ever run.
    - Added a second RED FlowDriver test for a current official compile attempt with `status=failed`.
      Initial result: failed because the official export 409 detail still used the generic missing-compile message.
    - Backend export readiness now reports the latest compile attempt for the current source hash separately from the latest completed usable compile, so blocked/failed attempts return `has_compile_run=true`, `compile_run_id`, `compile_status`, and `compile_blocked_items`.
    - The official export gate still only unlocks on a completed official package for the exact current source draft, but the 409 detail now distinguishes blocked and failed compile attempts from a truly missing compile.
    - Frontend `ExportReadiness` typing now includes the compile-attempt status fields for callers that surface readiness-state details.

Verification after official compile attempt state expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_blocked_current_official_compile_attempt tests/test_flow_driver.py::test_export_readiness_reports_failed_current_official_compile_attempt -q`
  Result after official compile attempt state expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after official compile attempt state expansion: 16 passed, 17 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts`
  Result after official compile attempt state expansion: 2 files passed, 55 tests passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after official compile attempt state expansion: 117 passed, 102 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts src/app/routes.test.tsx src/GuidedPatentFlow.officialCompile.test.tsx`
  Result after official compile attempt state expansion: 4 files passed, 59 tests passed.
- `git diff --check`
  Result after official compile attempt state expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after official compile attempt state expansion: no new root artifacts found.

47. Split completed-but-blocking post-draft reviews from missing review runs:
    - Updated the existing FlowDriver regression where a later blocking post-draft review invalidates an earlier passed review for the same compile.
      Initial result: failed with `KeyError: 'review_gate_status'` because export readiness pointed at the latest review but did not expose whether the completed review passed or blocked export.
    - Backend export readiness now reports `review_gate_status` and `review_blocking_issues` for the latest matching review attempt.
    - A completed review with `export_allowed=false` now returns `review_gate_status="blocked"` when the chair or reviewer findings block export, rather than looking like a missing review.
    - The official export 409 detail now distinguishes a blocked completed post-draft review from a truly missing review, while still only unlocking export on a completed, export-allowed review for the exact current official package.
    - Frontend `ExportReadiness` typing now includes `review_gate_status` and `review_blocking_issues` for callers that surface readiness-state details.

Verification after blocked post-draft review state expansion:

- `python -m pytest tests/test_flow_driver.py::test_flow_driver_later_blocking_review_invalidates_prior_pass -q`
  Result after blocked post-draft review state expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after blocked post-draft review state expansion: 16 passed, 17 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts`
  Result after blocked post-draft review state expansion: 2 files passed, 55 tests passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after blocked post-draft review state expansion: 117 passed, 102 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/guidedFlow.test.ts src/app/routes.test.tsx src/GuidedPatentFlow.officialCompile.test.tsx`
  Result after blocked post-draft review state expansion: 4 files passed, 59 tests passed.
- `git diff --check`
  Result after blocked post-draft review state expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after blocked post-draft review state expansion: no new root artifacts found.

48. Added an HTML attribute evidence-honesty variant:
    - Added a RED compiler test for HTML attributes carrying evidence/source metadata, including `data-source="lab-note-001"` and `evidence-ref="EV-CITY-001"`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_html_attribute_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped HTML-attribute detector that flags evidence/source/citation/ref/material metadata attributes without broadening the existing XML evidence-tag and HTML-comment checks.
    - Added the `generated_html_attribute_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in HTML attributes are covered by replayable adversarial traces.

Verification after HTML attribute honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_attribute_evidence_leakage -q`
  Result after HTML attribute honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_attribute_honesty_action -q`
  Result after HTML attribute honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after HTML attribute honesty expansion: 36 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after HTML attribute honesty expansion: 19 passed, 56 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after HTML attribute honesty expansion: 119 passed, 103 warnings.
- `git diff --check`
  Result after HTML attribute honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML attribute honesty expansion: no new root artifacts found.

49. Added an HTML meta evidence-honesty variant:
    - Added a RED compiler test for HTML `<meta>` metadata carrying evidence/source hints such as `name="source"` and `property="evidence-ref"`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_html_meta_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped `<meta>` detector that requires a metadata key (`name`, `property`, or `itemprop`) to point at evidence/source/citation/ref/material and a non-empty `content`.
    - Added the `generated_html_meta_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in HTML meta tags are covered by replayable adversarial traces.

Verification after HTML meta honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_meta_evidence_leakage -q`
  RED result before implementation: failed because official compile returned `completed` instead of `blocked`.
  Result after HTML meta honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_meta_honesty_action -q`
  RED result before implementation: failed with `ValueError: Unknown adversarial action: generated_html_meta_honesty`.
  Result after HTML meta honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after HTML meta honesty expansion: 37 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after HTML meta honesty expansion: 20 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after HTML meta honesty expansion: 121 passed, 104 warnings.
- `git diff --check`
  Result after HTML meta honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML meta honesty expansion: no new root artifacts found.

50. Split queued/running current post-draft review attempts from missing review runs:
    - Added a RED FlowDriver test for the edge case where the current source draft and official compile are current, but the matching post-draft review attempt is still `queued`.
      Initial result: failed because official export reported the generic missing-review message instead of a queued review attempt.
    - Added a second RED FlowDriver test for a matching `running` post-draft review attempt.
      Initial result: failed because official export reported the generic missing-review message instead of a running review attempt.
    - Backend export readiness already exposed `review_status` and `review_gate_status` for active matching review attempts; official export now mirrors that state in the 409 detail so queued/running attempts are no longer confused with a missing review.
    - Export still remains locked until a completed, export-allowed post-draft review exists for the exact current official package.

Verification after active post-draft review state expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_queued_current_post_draft_review tests/test_flow_driver.py::test_export_readiness_reports_running_current_post_draft_review -q`
  RED result before implementation: 2 failed because official export returned the generic post-draft review required message.
  Result after active post-draft review state expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after active post-draft review state expansion: 19 passed, 20 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after active post-draft review state expansion: 124 passed, 107 warnings.
- `git diff --check`
  Result after active post-draft review state expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after active post-draft review state expansion: no new root artifacts found.

51. Made draft-completion quality state follow the latest current attempt:
    - Added a RED FlowDriver test for the edge case where the current draft has an earlier completed draft-completion report, then a newer draft-completion attempt for the same source hash fails.
      Initial result: failed because export readiness skipped quality checks and moved on to `run_official_compile`.
    - Backend quality readiness now evaluates draft completion from the latest attempt for the current source hash, so a newer failed attempt marks `draft_completion` as `failed` even if an older completed report exists for the same draft.
    - The gate still treats an older completed draft-completion report as stale when no current attempt exists, and it still unlocks only when the latest current attempt completed.

Verification after latest draft-completion attempt expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_uses_latest_current_draft_completion_attempt -q`
  RED result before implementation: failed because readiness returned `run_official_compile` instead of `run_quality_checks`.
  Result after latest draft-completion attempt expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after latest draft-completion attempt expansion: 20 passed, 21 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after latest draft-completion attempt expansion: 125 passed, 108 warnings.
- `git diff --check`
  Result after latest draft-completion attempt expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after latest draft-completion attempt expansion: no new root artifacts found.

52. Made official-compile gate follow the latest current attempt:
    - Added a RED FlowDriver test for the edge case where the current source draft has an earlier completed official compile, then a newer official compile attempt for the same source hash fails.
      Initial result: failed because export readiness skipped the compile gate and moved on to `run_post_draft_review`.
    - Added a second RED FlowDriver test for the same sequence with a newer blocked official compile attempt.
      Initial result: failed for the same reason: the older completed official package was still treated as usable.
    - Backend export readiness and official export now evaluate the latest official compile attempt for the current source hash; the gate only advances to post-draft review when that latest attempt is `completed` and has an official package.
    - Export remains blocked for newer failed/blocked attempts even if an older completed compile exists for the same source draft.

Verification after latest official-compile attempt expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_uses_latest_failed_official_compile_attempt tests/test_flow_driver.py::test_export_readiness_uses_latest_blocked_official_compile_attempt -q`
  RED result before implementation: 2 failed because readiness returned `run_post_draft_review` instead of `run_official_compile`.
  Result after latest official-compile attempt expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after latest official-compile attempt expansion: 22 passed, 23 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after latest official-compile attempt expansion: 127 passed, 110 warnings.
- `git diff --check`
  Result after latest official-compile attempt expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after latest official-compile attempt expansion: no new root artifacts found.

53. Made post-draft review gate follow the latest current attempt:
    - Added a RED FlowDriver test for the edge case where the current official package has an earlier passed post-draft review, then a newer matching post-draft review attempt fails.
      Initial result: failed because export readiness still returned `export_ready`.
    - Added a second RED FlowDriver test for the same sequence with a newer queued post-draft review attempt.
      Initial result: failed for the same reason: the earlier passed review still unlocked official export.
    - Backend export readiness and official export now evaluate the latest matching post-draft review attempt for the current source draft, official compile run, and official package hash.
    - Export only unlocks when that latest matching review attempt is `completed` and `export_allowed=true`; newer failed/queued/running/interrupted attempts supersede older passed reviews.

Verification after latest post-draft review attempt expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_uses_latest_failed_post_draft_review_attempt tests/test_flow_driver.py::test_export_readiness_uses_latest_queued_post_draft_review_attempt -q`
  RED result before implementation: 2 failed because readiness returned `export_ready` instead of `run_post_draft_review`.
  Result after latest post-draft review attempt expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after latest post-draft review attempt expansion: 24 passed, 25 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after latest post-draft review attempt expansion: 129 passed, 112 warnings.
- `git diff --check`
  Result after latest post-draft review attempt expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after latest post-draft review attempt expansion: no new root artifacts found.

54. Added a CSV metadata evidence-honesty variant:
    - Added a RED compiler test for CSV-style evidence/source metadata leakage such as `evidence_id,source_label` and `证据编号,来源标签` followed by data rows.
      Initial result: failed because the compiler did not report `csv_metadata_citation`; the sample was only blocked through broader residual metadata signals.
    - Added a RED adversarial harness test for `generated_csv_metadata_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped CSV metadata detector that requires a CSV-like header row with evidence/source/citation/ref/material fields and a following non-empty data row.
    - Added the `generated_csv_metadata_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in CSV rows are covered by replayable adversarial traces.

Verification after CSV metadata honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_csv_evidence_metadata_leakage -q`
  RED result before implementation: failed because no blocked item used `csv_metadata_citation`.
  Result after CSV metadata honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_csv_metadata_honesty_action -q`
  RED result before implementation: failed with `ValueError: Unknown adversarial action: generated_csv_metadata_honesty`.
  Result after CSV metadata honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after CSV metadata honesty expansion: 38 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after CSV metadata honesty expansion: 21 passed, 58 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after CSV metadata honesty expansion: 131 passed, 113 warnings.
- `git diff --check`
  Result after CSV metadata honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after CSV metadata honesty expansion: no new root artifacts found.

55. Added a TOML front-matter evidence-honesty variant:
    - Added a RED compiler test for TOML-style `+++` front matter carrying evidence metadata such as `evidence = [...]` and `证据 = [...]`.
      Initial result: failed because official compile completed instead of blocking.
    - Added a RED adversarial harness test for `generated_toml_front_matter_honesty`.
      Initial result: failed because the action was not registered.
    - Added a narrowly scoped TOML front-matter detector that scans only `+++` delimited blocks for evidence/source/citation/ref/material keys.
    - Added the `generated_toml_front_matter_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in TOML front matter are covered by replayable adversarial traces.

Verification after TOML front-matter honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_toml_front_matter_evidence_leakage -q`
  RED result before implementation: failed because official compile returned `completed` instead of `blocked`.
  Result after TOML front-matter honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_toml_front_matter_honesty_action -q`
  RED result before implementation: failed with `ValueError: Unknown adversarial action: generated_toml_front_matter_honesty`.
  Result after TOML front-matter honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after TOML front-matter honesty expansion: 39 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after TOML front-matter honesty expansion: 22 passed, 59 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after TOML front-matter honesty expansion: 133 passed, 114 warnings.
- `git diff --check`
  Result after TOML front-matter honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after TOML front-matter honesty expansion: no new root artifacts found.

56. Added an INI section evidence-honesty variant:
    - Added a RED compiler test for INI-style evidence/source metadata leakage such as `[evidence]` and `[证据]` sections with `id = ...` / `编号 = ...` rows.
      Initial result: failed because official compile returned `completed` instead of `blocked`.
    - Added a RED adversarial harness test for `generated_ini_section_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_ini_section_honesty`.
    - Added a narrowly scoped INI section detector that requires an evidence/source/citation/ref/material section header and a metadata key/value row inside that section.
    - Added the `generated_ini_section_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in INI-style sections are covered by replayable adversarial traces.

Verification after INI section honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_ini_section_evidence_leakage -q`
  RED result before implementation: failed because official compile returned `completed` instead of `blocked`.
  Result after INI section honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_ini_section_honesty_action -q`
  RED result before implementation: failed with `ValueError: Unknown adversarial action: generated_ini_section_honesty`.
  Result after INI section honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after INI section honesty expansion: 40 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after INI section honesty expansion: 23 passed, 60 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after INI section honesty expansion: 135 passed, 115 warnings.
- `git diff --check`
  Result after INI section honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after INI section honesty expansion: no new root artifacts found.

57. Added an HTML JSON-LD evidence-honesty variant:
    - Added a RED compiler test for `<script type="application/ld+json">` blocks carrying evidence/source/material metadata in JSON keys.
      Initial result: failed because official compile returned `completed` instead of `blocked`.
    - Added a RED adversarial harness test for `generated_html_json_ld_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_json_ld_honesty`.
    - Added a narrowly scoped HTML JSON-LD detector that scans only `application/ld+json` script blocks for evidence/source/citation/ref/material keys.
    - Added the `generated_html_json_ld_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in JSON-LD script blocks are covered by replayable adversarial traces.

Verification after HTML JSON-LD honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_json_ld_evidence_leakage -q`
  RED result before implementation: failed because official compile returned `completed` instead of `blocked`.
  Result after HTML JSON-LD honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_json_ld_honesty_action -q`
  RED result before implementation: failed with `ValueError: Unknown adversarial action: generated_html_json_ld_honesty`.
  Result after HTML JSON-LD honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py -q`
  Result after HTML JSON-LD honesty expansion: 41 passed, 12 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py -q`
  Result after HTML JSON-LD honesty expansion: 24 passed, 61 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after HTML JSON-LD honesty expansion: 137 passed, 116 warnings.
- `git diff --check`
  Result after HTML JSON-LD honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML JSON-LD honesty expansion: no new root artifacts found.

58. Distinguished completed official compile runs missing official-package artifacts:
    - Added a RED FlowDriver/readiness test for a legacy or corrupted current official compile run with `status=completed` but no `official_package`.
      Initial result: failed because `/export-readiness` did not expose `compile_artifact_state`.
    - Added `compile_artifact_state` to the official compile gate state so UI and automation can distinguish `missing`, `blocked`, `failed`, `missing_official_package`, `missing_official_package_hash`, and `current`.
    - Updated official export's 409 detail to call out an incomplete official compile with a missing official package, instead of presenting it as a generic missing compile.

Verification after incomplete official compile artifact expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_completed_compile_missing_official_package -q`
  RED result before implementation: failed with `KeyError: 'compile_artifact_state'`.
  Result after incomplete official compile artifact expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after incomplete official compile artifact expansion: 25 passed, 26 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after incomplete official compile artifact expansion: 138 passed, 117 warnings.
- `git diff --check`
  Result after incomplete official compile artifact expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after incomplete official compile artifact expansion: no new root artifacts found.

59. Surfaced official-output fixture targets in the golden calibration queue:
    - Added a RED release-gate test requiring each pending calibration queue entry to include the exact official-output fixture path and whether that fixture currently exists.
      Initial result: failed with `KeyError: 'official_text_fixture_path'`.
    - Updated `scripts/golden_quality_gate.py` so queued human-review entries now include `official_text_fixture_path` and `official_text_fixture_exists`.
    - Ran the gate against the checked-in golden set; it reports 5 pending calibration entries, 0 enabled cases, and all five current official-output fixture targets as missing.
      This keeps release gates disabled while giving the human reviewer the concrete fixture files to create or approve.

Verification after golden fixture-target queue expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_reports_actionable_calibration_queue -q`
  RED result before implementation: failed with `KeyError: 'official_text_fixture_path'`.
  Result after golden fixture-target queue expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden fixture-target queue expansion: 5 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-fixtures.json`
  Result after golden fixture-target queue expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed, 5 official fixture targets currently missing.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden fixture-target queue expansion: 10 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden fixture-target queue expansion: 138 passed, 117 warnings.

60. Added a human-readable golden calibration packet:
    - Added a RED release-gate test requiring `run_gate(..., calibration_markdown_path=...)` to write a Markdown packet for human review.
      Initial result: failed with `TypeError: run_gate() got an unexpected keyword argument 'calibration_markdown_path'`.
    - Added `--calibration-markdown-path` to `scripts/golden_quality_gate.py` and rendered Markdown from the same calibration queue used by the JSON report.
    - The Markdown packet lists each pending case, fixture target path, fixture existence state, notes, required distinguishing features, forbidden official content, thresholds, and checklist items.
    - Generated `/tmp/golden-calibration-queue.md` from the checked-in cases; it contains 5 pending cases and shows all five fixture targets currently missing.
      This is a handoff aid for real human calibration, not evidence that calibration is complete.

Verification after golden calibration Markdown packet expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_writes_human_readable_calibration_packet -q`
  RED result before implementation: failed with `TypeError: run_gate() got an unexpected keyword argument 'calibration_markdown_path'`.
  Result after golden calibration Markdown packet expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden calibration Markdown packet expansion: 6 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-markdown.json --calibration-markdown-path /tmp/golden-calibration-queue.md`
  Result after golden calibration Markdown packet expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed, and Markdown packet generated.
- `sed -n '1,90p' /tmp/golden-calibration-queue.md`
  Result after golden calibration Markdown packet expansion: packet starts with `# Golden Patent Calibration Queue`, reports `Pending cases: 5`, and includes fixture paths, fixture existence state, thresholds, and checklist items.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden calibration Markdown packet expansion: 11 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden calibration Markdown packet expansion: 139 passed, 117 warnings.
- `git diff --check`
  Result after golden calibration Markdown packet expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after golden calibration Markdown packet expansion: no new root artifacts found.

61. Fail-closed when enabled calibrated golden cases lack human-review metadata:
    - Added a RED release-gate test for enabled `calibrated` cases missing `human_calibration.reviewer` or `human_calibration.notes`.
      Initial result: failed because those cases were reported as `missing_official_text` before the gate checked whether human calibration metadata was actually present.
    - Added a human-calibration metadata guard before official fixture evaluation.
      Enabled calibrated cases now fail with `missing_human_calibration_metadata` and list the exact missing fields.
    - Updated the positive calibrated-output fixture test to include reviewer and notes, keeping the passing path tied to explicit human-review metadata.
    - Ran the gate against the checked-in golden set; all five cases remain disabled/skipped and pending human review, with 0 enabled and 0 failed.

Verification after golden human-calibration metadata guard expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_rejects_enabled_calibrated_cases_missing_human_metadata -q`
  RED result before implementation: failed because the gate returned `missing_official_text` instead of `missing_human_calibration_metadata`.
  Result after golden human-calibration metadata guard expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden human-calibration metadata guard expansion: 7 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-calibration-metadata.json --calibration-markdown-path /tmp/golden-calibration-metadata.md`
  Result after golden human-calibration metadata guard expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden human-calibration metadata guard expansion: 12 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden human-calibration metadata guard expansion: 140 passed, 117 warnings.
- `git diff --check`
  Result after golden human-calibration metadata guard expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after golden human-calibration metadata guard expansion: no new root artifacts found.

62. Bound calibrated golden official-output fixtures to SHA256 hashes:
    - Added a RED release-gate test for enabled calibrated cases whose official-output fixture has no approved SHA256 or whose current fixture content no longer matches the approved SHA256.
      Initial result: failed because the missing-hash case fell through to `evaluation_failed` instead of failing closed on fixture binding.
    - Added `human_calibration.official_text_fixture_sha256` enforcement for enabled calibrated cases after the fixture file exists and before deterministic quality evaluation.
    - Cases missing the approved fixture hash now fail with `missing_official_text_fixture_sha256`; cases with changed fixture content fail with `official_text_fixture_sha256_mismatch` and report both expected and actual hashes.
    - Updated the positive calibrated-output path to include an approved fixture hash, and added coverage that a hash-matching but low-quality fixture still fails the deterministic evaluator.
    - Ran the gate against the checked-in golden set; all five cases remain disabled/skipped and pending human review, so no hash is required until a case is explicitly enabled after calibration.

Verification after golden fixture SHA256 binding expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_rejects_enabled_calibrated_cases_without_matching_fixture_hash -q`
  RED result before implementation: failed because `missing_hash` returned `evaluation_failed` instead of `missing_official_text_fixture_sha256`.
  Result after golden fixture SHA256 binding expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_requires_calibrated_outputs_to_pass tests/test_golden_release_gate.py::test_golden_release_gate_still_evaluates_thresholds_after_fixture_hash_matches -q`
  Result after golden fixture SHA256 binding expansion: 2 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden fixture SHA256 binding expansion: 9 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-fixture-hash.json --calibration-markdown-path /tmp/golden-calibration-fixture-hash.md`
  Result after golden fixture SHA256 binding expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden fixture SHA256 binding expansion: 14 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden fixture SHA256 binding expansion: 142 passed, 117 warnings.
- `git diff --check`
  Result after golden fixture SHA256 binding expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after golden fixture SHA256 binding expansion: no new root artifacts found.

63. Enforced the deterministic-only golden release-gate contract:
    - Added a RED release-gate test for enabled calibrated cases that either disable `deterministic_checks.release_blocker` or mark `llm_judge.release_blocker=true`.
      Initial result: failed because both cases could pass the release gate when their fixture hashes and deterministic quality metrics were otherwise valid.
    - Added a release-gate contract guard before fixture evaluation.
      Enabled calibrated cases now require `deterministic_checks.release_blocker=true` and `llm_judge.release_blocker=false`.
    - Contract violations fail with `invalid_release_gate_contract` and list the exact violation, keeping LLM judge metadata diagnostic-only.
    - Ran the gate against the checked-in golden set; all five cases remain disabled/skipped and pending human review, with deterministic checks as blockers and LLM judge metadata non-blocking.

Verification after deterministic-only golden release-gate contract expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_requires_deterministic_blockers_and_nonblocking_llm_judge -q`
  RED result before implementation: failed because the unsafe contract cases returned `passed=true`.
  Result after deterministic-only golden release-gate contract expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_requires_calibrated_outputs_to_pass -q`
  Result after deterministic-only golden release-gate contract expansion: 1 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after deterministic-only golden release-gate contract expansion: 10 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-contract.json --calibration-markdown-path /tmp/golden-calibration-contract.md`
  Result after deterministic-only golden release-gate contract expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after deterministic-only golden release-gate contract expansion: 15 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after deterministic-only golden release-gate contract expansion: 143 passed, 117 warnings.
- `git diff --check`
  Result after deterministic-only golden release-gate contract expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after deterministic-only golden release-gate contract expansion: no new root artifacts found.

64. Surfaced actual SHA256 values for existing queued golden official-output fixtures:
    - Added RED release-gate coverage requiring the JSON calibration queue to include `official_text_fixture_sha256_actual` when a pending fixture file already exists.
      Initial result: failed with `KeyError: 'official_text_fixture_sha256_actual'`.
    - Added RED Markdown coverage requiring the human-readable calibration packet to show `Current fixture SHA256` for existing fixture files.
      Initial result: failed because the packet listed fixture path and existence state but omitted the current hash.
    - Updated `scripts/golden_quality_gate.py` so pending calibration entries compute the actual SHA256 from the current fixture text when the target file exists.
    - Updated the Markdown packet so human reviewers can copy the approved current hash into `human_calibration.official_text_fixture_sha256`.
    - Ran the gate against the checked-in golden set; all five cases remain disabled/skipped and pending human review, with no checked-in official-output fixture files yet, so the current SHA field is empty for those cases.

Verification after golden calibration actual-SHA expansion:

- `python -m pytest tests/test_golden_release_gate.py::test_golden_release_gate_reports_actionable_calibration_queue tests/test_golden_release_gate.py::test_golden_release_gate_writes_human_readable_calibration_packet -q`
  RED result before implementation: failed with missing `official_text_fixture_sha256_actual` in JSON and missing `Current fixture SHA256` in Markdown.
  Result after golden calibration actual-SHA expansion: 2 passed.
- `python -m pytest tests/test_golden_release_gate.py -q`
  Result after golden calibration actual-SHA expansion: 10 passed.
- `python scripts/golden_quality_gate.py --report-path /tmp/golden-quality-gate-actual-sha.json --calibration-markdown-path /tmp/golden-calibration-actual-sha.md`
  Result after golden calibration actual-SHA expansion: passed; 5 cases skipped, 5 pending calibration queue entries, 0 enabled, 0 failed, and current fixture SHA fields empty because the checked-in fixture files do not exist yet.
- `python -m pytest tests/test_golden_patent_cases.py tests/test_golden_release_gate.py -q`
  Result after golden calibration actual-SHA expansion: 15 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after golden calibration actual-SHA expansion: 143 passed, 117 warnings.
- `git diff --check`
  Result after golden calibration actual-SHA expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after golden calibration actual-SHA expansion: no new root artifacts found.

65. Expanded adversarial evidence-honesty coverage to fenced JSON metadata:
    - Added a RED adversarial harness test for generated drafts that hide evidence/source metadata inside Markdown `json` code fences.
      Initial result: failed first with `Unknown adversarial action: generated_fenced_json_metadata_honesty`, then, after registering the action, failed because the official compile only reported `markdown_fence` and did not surface a specific evidence-honesty blocker.
    - Added the `generated_fenced_json_metadata_honesty` action and FakeLLM case to `tests/adversarial_flow_harness.py`.
    - Updated `backend/app/official_compile.py` to detect JSON code fences containing evidence/source/citation/ref/material metadata keys before generic fence cleanup removes the original text.
    - Official compile now reports `fenced_json_metadata_citation` for this carrier, while still blocking generic Markdown fence pollution.

Verification after fenced JSON evidence-honesty expansion:

- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_fenced_json_metadata_honesty_action -q`
  RED result before implementation: failed first as an unknown action, then failed because `blocked_patterns` only contained `markdown_fence`.
  Result after fenced JSON evidence-honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_evidence_binding.py -q`
  Result after fenced JSON evidence-honesty expansion: 33 passed, 65 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after fenced JSON evidence-honesty expansion: 144 passed, 118 warnings.
- `git diff --check`
  Result after fenced JSON evidence-honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after fenced JSON evidence-honesty expansion: no new root artifacts found.

66. Closed the missing official-package-hash compile artifact gate:
    - Added a RED FlowDriver test for the case where the latest current official compile attempt is `completed` and has an official package, but its `official_package_hash` is missing.
      Initial result: failed because export readiness incorrectly returned `next_action=run_post_draft_review` instead of keeping the user at `run_official_compile`.
    - Updated `backend/app/main.py` so export readiness and official export both require `official_package_hash` before treating a completed official compile as current.
    - Updated the post-draft review creation gate so direct API callers cannot enter post-draft review from an incomplete official compile missing its package hash.
    - The readiness response now reports `compile_artifact_state=missing_official_package_hash`, and official export/post-draft review requests fail with the specific incomplete-compile detail.

Verification after missing official-package-hash gate expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_completed_compile_missing_official_package_hash -q`
  RED result before implementation: failed because readiness returned `run_post_draft_review`.
  Result after missing official-package-hash gate expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_official_compile.py tests/test_post_draft_review.py tests/test_export.py -q`
  Result after missing official-package-hash gate expansion: 91 passed, 60 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after missing official-package-hash gate expansion: 145 passed, 119 warnings.
- `git diff --check`
  Result after missing official-package-hash gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after missing official-package-hash gate expansion: no new root artifacts found.

67. Added an AsciiDoc attribute evidence-honesty variant:
    - Added a RED compiler test for AsciiDoc-style attribute metadata such as `:evidence: EV-...`, `:source-label: ...`, `:证据: ...`, and `:来源标签: ...`.
      Initial result: failed because official compile blocked only through broader residual metadata and did not report the specific `asciidoc_attribute_citation` carrier.
    - Added a RED adversarial harness test for `generated_asciidoc_attribute_honesty`.
      Initial result: failed because the action was not registered.
    - Updated `backend/app/official_compile.py` to scan raw hard-gated draft sections for AsciiDoc evidence/source/citation/ref/material attributes before inline cleanup strips the leading `:` marker.
    - Added the `generated_asciidoc_attribute_honesty` action and fixture LLM so generated drafts with evidence metadata hidden in AsciiDoc attributes are covered by replayable adversarial traces.

Verification after AsciiDoc attribute honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_asciidoc_attribute_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_asciidoc_attribute_honesty_action -q`
  RED result before implementation: failed because the compiler did not report `asciidoc_attribute_citation`, and the adversarial action was unknown.
  Result after AsciiDoc attribute honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after AsciiDoc attribute honesty expansion: 68 passed, 74 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after AsciiDoc attribute honesty expansion: 147 passed, 120 warnings.
- `git diff --check`
  Result after AsciiDoc attribute honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after AsciiDoc attribute honesty expansion: no new root artifacts found.

68. Matched direct post-draft review gating to incomplete official-package artifacts:
    - Added a RED FlowDriver assertion for direct `POST /api/projects/{project_id}/post-draft-reviews` when the latest completed current official compile run has no `official_package`.
      Initial result: failed because direct post-draft review returned the generic "Official draft compile is required" detail, even though export readiness and official export already identified `missing_official_package`.
    - Updated `_require_latest_completed_official_compile` so a completed compile missing its official package returns an explicit incomplete-compile 409 detail before post-draft review can start.
    - This aligns direct API behavior with `/export-readiness` and official export for corrupted or legacy compile artifacts.

Verification after direct post-draft missing official-package gate expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_completed_compile_missing_official_package -q`
  RED result before implementation: failed because direct post-draft review returned the generic compile-required detail.
  Result after direct post-draft missing official-package gate expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_official_compile.py tests/test_post_draft_review.py tests/test_export.py -q`
  Result after direct post-draft missing official-package gate expansion: 92 passed, 60 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after direct post-draft missing official-package gate expansion: 147 passed, 120 warnings.
- `git diff --check`
  Result after direct post-draft missing official-package gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after direct post-draft missing official-package gate expansion: no new root artifacts found.

69. Expanded FlowDriver post-draft review state matrix evidence:
    - Added a RED FlowDriver state test for latest current post-draft review attempts after an earlier passed review, covering `queued`, `running`, `failed`, `interrupted`, and completed-but-blocking review outcomes.
      Initial result: failed because `FlowDriver.state().gates["post_draft_review"]` collapsed the latest queued review attempt to `stale`.
    - Updated `tests/flow_driver.py` so review gates that match the current draft, official compile run, and official package hash preserve the actual latest attempt status instead of reporting every non-passing attempt as stale.
    - The adversarial trace harness now has sharper final-state evidence for active or failed post-draft review gates while preserving the existing stale behavior for old draft/compile hashes.

Verification after FlowDriver post-draft review state-matrix expansion:

- `python -m pytest tests/test_flow_driver.py::test_flow_driver_state_reports_latest_post_draft_review_attempt_status -q`
  RED result before implementation: failed because the latest queued current review attempt was reported as `stale`.
  Result after FlowDriver post-draft review state-matrix expansion: 1 passed, 6 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after FlowDriver post-draft review state-matrix expansion: 27 passed, 32 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_post_draft_review.py -q`
  Result after FlowDriver post-draft review state-matrix expansion: 87 passed, 128 warnings.
- `python -m pytest tests/test_golden_release_gate.py tests/test_golden_patent_cases.py -q`
  Result after FlowDriver post-draft review state-matrix expansion: 15 passed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py -q`
  Result after FlowDriver post-draft review state-matrix expansion: 148 passed, 125 warnings.

70. Aligned direct post-draft review with latest official-compile attempt gates:
    - Added RED FlowDriver coverage asserting direct `POST /api/projects/{project_id}/post-draft-reviews` is blocked when the current draft's latest official compile attempt is `failed` or `blocked`, even if an earlier completed compile package exists for the same source hash.
      Initial result: the latest blocked compile case failed because post-draft review still returned 200 by selecting the older completed compile package.
    - Updated `_require_latest_completed_official_compile` to inspect the latest current official compile attempt before selecting a completed package, and to return the same specific failed/blocked compile reason before post-draft review can start.
    - Updated older post-draft review tests that expected the generic compile-required message after a blocked official compile; direct API behavior now exposes the sharper blocked-compile cause.

Verification after direct post-draft latest official-compile attempt gate expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_uses_latest_failed_official_compile_attempt tests/test_flow_driver.py::test_export_readiness_uses_latest_blocked_official_compile_attempt -q`
  RED result before implementation: latest blocked compile failed because direct post-draft review returned 200.
  Result after direct post-draft latest official-compile attempt gate expansion: 2 passed, 3 warnings.
- `python -m pytest tests/test_flow_driver.py tests/test_post_draft_review.py tests/test_official_compile.py tests/test_export.py -q`
  Result after direct post-draft latest official-compile attempt gate expansion: 93 passed, 65 warnings.
- `python -m pytest tests/test_runtime_controls.py tests/test_adversarial_flow_explorer.py -q`
  Result after direct post-draft latest official-compile attempt gate expansion: 38 passed, 75 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after direct post-draft latest official-compile attempt gate expansion: 170 passed, 147 warnings.
- `git diff --check`
  Result after direct post-draft latest official-compile attempt gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after direct post-draft latest official-compile attempt gate expansion: no new root artifacts found.

71. Added a LaTeX command evidence-honesty adversarial variant:
    - Added a RED compiler test for LaTeX/TeX-style evidence metadata hidden in commands such as `\cite{source=...}` and `\footnote{证据: ...}`.
      Initial result: failed because the official compiler completed instead of reporting `latex_command_citation`.
    - Added a RED adversarial harness test for `generated_latex_command_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_latex_command_honesty`.
    - Updated `backend/app/official_compile.py` to block LaTeX citation/ref/footnote-style commands whose argument or option carries evidence/source/citation/ref/material metadata.
    - Added the `generated_latex_command_honesty` action and fixture LLM so generated drafts with LaTeX command evidence metadata are covered by replayable adversarial traces.

Verification after LaTeX command honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_latex_command_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_latex_command_honesty_action -q`
  RED result before implementation: compiler completed without `latex_command_citation`, and the adversarial action was unknown.
  Result after LaTeX command honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after LaTeX command honesty expansion: 70 passed, 75 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after LaTeX command honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after LaTeX command honesty expansion: 172 passed, 148 warnings.
- `git diff --check`
  Result after LaTeX command honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after LaTeX command honesty expansion: no new root artifacts found.

72. Added a BibTeX entry evidence-honesty adversarial variant:
    - Added a RED compiler test for BibTeX/BibLaTeX-style evidence metadata hidden in entries such as `@misc{..., note = {source: ...}}` and `@article{..., evidence = {...}}`.
      Initial result: the compiler blocked via existing generic evidence metadata cleanup, but did not report the carrier-specific `bibtex_entry_citation` pattern.
    - Added a RED adversarial harness test for `generated_bibtex_entry_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_bibtex_entry_honesty`.
    - Updated `backend/app/official_compile.py` to scan BibTeX-style entries for evidence/source/citation/ref/material metadata or EV/EVIDENCE identifiers before official compile can complete.
    - Added the `generated_bibtex_entry_honesty` action and fixture LLM so generated drafts with BibTeX evidence metadata are covered by replayable adversarial traces.

Verification after BibTeX entry honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_bibtex_entry_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_bibtex_entry_honesty_action -q`
  RED result before implementation: compiler did not report `bibtex_entry_citation`, and the adversarial action was unknown.
  Result after BibTeX entry honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after BibTeX entry honesty expansion: 72 passed, 76 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after BibTeX entry honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after BibTeX entry honesty expansion: 174 passed, 149 warnings.
- `git diff --check`
  Result after BibTeX entry honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after BibTeX entry honesty expansion: no new root artifacts found.

73. Added a reStructuredText directive evidence-honesty adversarial variant:
    - Added a RED compiler test for reStructuredText-style evidence metadata hidden in directives such as `.. source:: lab-note-001` and `.. evidence:: EV-...`.
      Initial result: failed because the official compiler completed instead of reporting `rst_directive_citation`.
    - Added a RED adversarial harness test for `generated_rst_directive_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_rst_directive_honesty`.
    - Updated `backend/app/official_compile.py` to block reStructuredText evidence/source/citation/ref/material directives before official compile can complete.
    - Added the `generated_rst_directive_honesty` action and fixture LLM so generated drafts with RST directive evidence metadata are covered by replayable adversarial traces.

Verification after reStructuredText directive honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_rst_directive_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_rst_directive_honesty_action -q`
  RED result before implementation: compiler completed without `rst_directive_citation`, and the adversarial action was unknown.
  Result after reStructuredText directive honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after reStructuredText directive honesty expansion: 74 passed, 77 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after reStructuredText directive honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after reStructuredText directive honesty expansion: 176 passed, 150 warnings.
- `git diff --check`
  Result after reStructuredText directive honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after reStructuredText directive honesty expansion: no new root artifacts found.

74. Surfaced detailed official compile and post-draft review gate evidence in the export UI:
    - Added RED `ExportView` coverage for the locked official-export card after quality checks have passed, covering an official compile blocked by a `support_gap` item and a completed post-draft review that blocks export with a specific issue.
      Initial result: both new UI tests failed because the export page still collapsed these states to the generic `正式稿入口已锁定` message.
    - Updated `ExportView` to consume `ExportReadiness`, map `compile_status`, `compile_blocked_items`, `review_gate_status`, and `review_blocking_issues` into explicit locked-gate titles and evidence lines, while preserving the existing quality-check detail copy.
    - Wired `ExportReadiness` through the production app path: `App.tsx` now loads `/api/projects/{project_id}/export-readiness` on project/run/hash/quality refreshes and background polling, and `PostDraftWorkspace` passes the readiness state to the export view.
    - Updated the AppRoot route fixture for the new `PostDraftWorkspaceState.exportReadiness` field.

Verification after export UI gate-evidence expansion:

- `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
  RED result before implementation: 1 test passed and 2 tests failed because the detailed compile/review gate titles were absent.
  Result after export UI gate-evidence expansion: 1 test file passed, 3 tests passed.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after export UI gate-evidence expansion: 4 test files passed, 61 tests passed.
- `npm run build`
  Initial result after wiring readiness: failed with `TS2741` because the route test fixture lacked `exportReadiness`.
  Result after fixture update: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after export UI gate-evidence expansion: 49 passed, 54 warnings.
- `git diff --check`
  Result after export UI gate-evidence expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after export UI gate-evidence expansion: no new root artifacts found.

75. Captured real-browser export UI gate evidence from current source:
    - Started the current-source backend on `http://127.0.0.1:8000` with isolated data under `output/playwright/export-gate-ui-20260628-180212/data`.
    - Started the current-source Vite frontend on `http://127.0.0.1:5174`; port `5173` was already serving a different Vite app, so it was not used for this evidence run.
    - Seeded two deterministic UI fixture projects in the isolated data directory:
      - `ui-compile-blocked`: quality bundle current, latest official compile attempt `blocked`, `compile_blocked_items=[{category: "support_gap", message: "说明书缺少实验数据"}]`.
      - `ui-review-blocked`: quality bundle current, official compile completed, latest matching post-draft review completed with `review_gate_status=blocked` and `review_blocking_issues=["权利要求1仍含内部评审说明"]`.
    - Used Playwright CLI against the real browser and current React app to select each fixture project, open `专家工具 → 导出文件`, and verify the export gate card renders the detailed readiness evidence.
    - Browser DOM evidence confirmed:
      - compile-blocked project: status strip `编译阻断`, gate title `正式稿编译被阻断`, evidence line `阻断项：support_gap；说明书缺少实验数据`.
      - review-blocked project: status strip `会审阻断`, gate title `成稿会审阻断导出`, evidence line `阻断问题：权利要求1仍含内部评审说明`.

Artifacts from real-browser export UI gate-evidence run:

- `output/playwright/export-gate-ui-20260628-180212/seed-manifest.json`
- `output/playwright/export-gate-ui-20260628-180212/compile-blocked-readiness.json`
- `output/playwright/export-gate-ui-20260628-180212/review-blocked-readiness.json`
- `output/playwright/export-gate-ui-20260628-180212/compile-blocked-page-text.txt`
- `output/playwright/export-gate-ui-20260628-180212/review-blocked-page-text.txt`
- `output/playwright/export-gate-ui-20260628-180212/network-requests.txt`
- `output/playwright/export-gate-ui-20260628-180212/compile-blocked.png`
- `output/playwright/export-gate-ui-20260628-180212/review-blocked.png`

Verification after real-browser export UI gate-evidence run:

- `curl -sS http://127.0.0.1:8000/api/health`
  Result: `ok=true`, data dir `/Users/leo/Projects/patents_agent/output/playwright/export-gate-ui-20260628-180212/data`.
- `curl -sS http://127.0.0.1:8000/api/projects/ui-compile-blocked/export-readiness`
  Result: `compile_status=blocked`, quality checks all `current`, blocked item `support_gap / 说明书缺少实验数据`.
- `curl -sS http://127.0.0.1:8000/api/projects/ui-review-blocked/export-readiness`
  Result: `review_gate_status=blocked`, quality checks all `current`, blocking issue `权利要求1仍含内部评审说明`.
- Playwright snapshot/text extraction of `http://127.0.0.1:5174/`
  Result: both detailed gate titles and evidence lines rendered in the real export UI; network log shows frontend `GET /api/projects/{project_id}/export-readiness` calls for both fixture projects returned 200.
- `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
  Result after real-browser export UI gate-evidence run: 1 test file passed, 3 tests passed.
- `git diff --check`
  Result after real-browser export UI gate-evidence run: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after real-browser export UI gate-evidence run: no new root artifacts found.

76. Added a Markdown list evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in ordinary Markdown or plain-text list items, such as `- evidence: EV-...`, `- source: ...`, `* 证据：...`, and `* 来源：...`.
      Initial result: failed because the official compiler completed without reporting a carrier-specific `markdown_list_citation` blocker.
    - Added a RED adversarial harness test for `generated_markdown_list_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_markdown_list_honesty`.
    - Updated `backend/app/official_compile.py` to block Markdown/list-item evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_markdown_list_honesty` action and fixture LLM so generated drafts with list-item evidence metadata are covered by replayable adversarial traces.

Verification after Markdown list honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_list_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_list_honesty_action -q`
  RED result before implementation: compiler completed without `markdown_list_citation`, and the adversarial action was unknown.
  Result after Markdown list honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown list honesty expansion: 76 passed, 78 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after Markdown list honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after Markdown list honesty expansion: 178 passed, 151 warnings.
- `git diff --check`
  Result after Markdown list honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown list honesty expansion: no new root artifacts found.

77. Added a Markdown blockquote evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in Markdown blockquote lines, such as `> evidence: EV-...`, `> source: ...`, `> 证据：...`, and `> 来源：...`.
      Initial result: failed because the official compiler completed without reporting a carrier-specific `markdown_blockquote_citation` blocker.
    - Added a RED adversarial harness test for `generated_markdown_blockquote_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_markdown_blockquote_honesty`.
    - Updated `backend/app/official_compile.py` to block Markdown blockquote evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_markdown_blockquote_honesty` action and fixture LLM so generated drafts with blockquote evidence metadata are covered by replayable adversarial traces.

Verification after Markdown blockquote honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_blockquote_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_blockquote_honesty_action -q`
  RED result before implementation: compiler completed without `markdown_blockquote_citation`, and the adversarial action was unknown.
  Result after Markdown blockquote honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown blockquote honesty expansion: 78 passed, 79 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after Markdown blockquote honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after Markdown blockquote honesty expansion: 180 passed, 152 warnings.
- `git diff --check`
  Result after Markdown blockquote honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown blockquote honesty expansion: no new root artifacts found.

78. Added a Markdown link-title evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in Markdown link or image title strings, such as `[实验记录](lab-note "evidence: EV-...")`, `[采集日志](material-log "证据：EV-...")`, and `![结构示意](figure.png "source: ...")`.
      Initial result: the compiler was blocked by broader citation scanning but did not report the carrier-specific `markdown_link_title_citation` blocker.
    - Added a RED adversarial harness test for `generated_markdown_link_title_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_markdown_link_title_honesty`.
    - Updated `backend/app/official_compile.py` to block Markdown link/image title evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_markdown_link_title_honesty` action and fixture LLM so generated drafts with link-title evidence metadata are covered by replayable adversarial traces.

Verification after Markdown link-title honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_link_title_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_link_title_honesty_action -q`
  RED result before implementation: compiler lacked `markdown_link_title_citation`, and the adversarial action was unknown.
  Result after Markdown link-title honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown link-title honesty expansion: 80 passed, 80 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after Markdown link-title honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after Markdown link-title honesty expansion: 182 passed, 153 warnings.
- `git diff --check`
  Result after Markdown link-title honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown link-title honesty expansion: no new root artifacts found.

79. Added an HTML visible-text evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden as visible text inside inline HTML tags, such as `<sup>evidence: EV-...</sup>`, `<span>证据：EV-...</span>`, and `<small>source: ...</small>`.
      Initial result: failed because the official compiler completed without reporting a carrier-specific `html_visible_text_citation` blocker.
    - Added a RED adversarial harness test for `generated_html_visible_text_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_visible_text_honesty`.
    - Updated `backend/app/official_compile.py` to block visible HTML evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_visible_text_honesty` action and fixture LLM so generated drafts with visible HTML evidence metadata are covered by replayable adversarial traces.

Verification after HTML visible-text honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_visible_text_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_visible_text_honesty_action -q`
  RED result before implementation: compiler completed without `html_visible_text_citation`, and the adversarial action was unknown.
  Result after HTML visible-text honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML visible-text honesty expansion: 82 passed, 81 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML visible-text honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML visible-text honesty expansion: 184 passed, 154 warnings.
- `git diff --check`
  Result after HTML visible-text honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML visible-text honesty expansion: no new root artifacts found.

80. Added an HTML entity-escaped evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML entity-escaped tags, such as `&lt;evidence ref=&quot;EV-...&quot;&gt;...&lt;/evidence&gt;` and `&lt;source&gt;...&lt;/source&gt;`.
      Initial result: failed because the official compiler completed without reporting a carrier-specific `html_entity_citation` blocker.
    - Added a RED adversarial harness test for `generated_html_entity_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_entity_honesty`.
    - Updated `backend/app/official_compile.py` to block HTML entity-escaped evidence/source/citation/ref/material tags in both raw draft sections and cleaned official text.
    - Added the `generated_html_entity_honesty` action and fixture LLM so generated drafts with entity-escaped evidence tags are covered by replayable adversarial traces.

Verification after HTML entity-escaped honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_entity_evidence_leakage tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_entity_honesty_action -q`
  RED result before implementation: compiler completed without `html_entity_citation`, and the adversarial action was unknown.
  Result after HTML entity-escaped honesty expansion: 2 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML entity-escaped honesty expansion: 84 passed, 82 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML entity-escaped honesty expansion: 57 passed, 57 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML entity-escaped honesty expansion: 186 passed, 155 warnings.
- `git diff --check`
  Result after HTML entity-escaped honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML entity-escaped honesty expansion: no new root artifacts found.

81. Covered queued/running official compile export-gate surfaces:
    - Added a RED FlowDriver/API test for current-source official compile attempts with `status=queued` and `status=running`.
      Initial result: failed because `OfficialCompileRun.status` only allowed `completed|blocked|failed`.
    - Expanded `OfficialCompileRun.status` to include `queued` and `running`.
    - Updated export-readiness, official export, and post-draft review prerequisite errors so queued/running official compile attempts are reported as in-flight compile states instead of a generic missing compile.
    - Updated `FlowDriver.state()` so queued/running official compile attempts keep Step 7 locked, surface `gates["official_compile"]` as `queued` or `running`, and list the compile run in `active_runs`.
    - Added a RED `ExportView` test for `compile_status=running`.
      Initial result: failed because the export UI fell back to the generic locked card and displayed `等待会审`.
    - Updated `ExportView` and frontend API types so queued/running compile readiness renders explicit locked-gate copy such as `正式稿编译运行中`.

Verification after queued/running official compile gate expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_in_flight_current_official_compile_attempts -q`
  RED result before implementation: `OfficialCompileRun.status` rejected `queued`.
  Intermediate RED result after schema/gate work: post-draft review still returned generic compile-required text.
  Result after queued/running official compile gate expansion: 1 passed, 3 warnings.
- `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
  RED result before implementation: the export UI did not render `正式稿编译运行中`.
  Result after queued/running official compile UI expansion: 1 test file passed, 4 tests passed.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after queued/running official compile gate expansion: 28 passed, 34 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after queued/running official compile gate expansion: 58 passed, 59 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after queued/running official compile UI expansion: 4 test files passed, 62 tests passed.
- `npm run build`
  Result after queued/running official compile UI expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after queued/running official compile gate expansion: 187 passed, 157 warnings.
- `git diff --check`
  Result after queued/running official compile gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after queued/running official compile gate expansion: no new root artifacts found.

82. Aligned FlowDriver state with failed current quality checks:
    - Added a RED FlowDriver state test for a current-source failed `draft_completion` run after filing-readiness and claim-defense checks have already matched the current draft hash.
      Initial result: failed because `FlowDriver.state().gates["quality"]` reported `missing` while backend export-readiness correctly reported `failed_quality_checks=["draft_completion"]`.
    - Updated the headless `FlowDriver` quality gate classifier so a failed current draft-completion attempt reports `gates["quality"]="failed"` and keeps Step 6 locked.
    - This keeps agent/explorer state traces aligned with backend export-readiness instead of collapsing failed quality work into a generic missing-check state.

Verification after FlowDriver failed-quality state alignment:

- `python -m pytest tests/test_flow_driver.py::test_flow_driver_state_reports_failed_current_quality_gate -q`
  RED result before implementation: FlowDriver reported `missing` instead of `failed`.
  Result after FlowDriver failed-quality state alignment: 1 passed, 2 warnings.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after FlowDriver failed-quality state alignment: 29 passed, 35 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after FlowDriver failed-quality state alignment: 59 passed, 60 warnings.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after FlowDriver failed-quality state alignment: 188 passed, 158 warnings.
- `git diff --check`
  Result after FlowDriver failed-quality state alignment: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after FlowDriver failed-quality state alignment: no new root artifacts found.

83. Covered unknown-hash legacy quality-bundle gates:
    - Added a RED backend/FlowDriver test for legacy filing-readiness, claim-defense worksheet, and draft-completion artifacts that exist but have no `draft_package_hash`.
      Initial result: failed because export-readiness collapsed all three artifacts into `missing_quality_checks` instead of preserving the more precise unknown-hash state.
    - Added a RED `ExportView` test for unknown-hash quality checks.
      Initial result: failed because the export UI did not render the quality-gate detail card or the `来源未知` line for unknown quality checks.
    - Updated backend quality-gate state to return `unknown_quality_checks`, keep `quality_required=true`, lock official export, and include `unknown-hash quality checks: ...` in the 409 detail.
    - Updated `FlowDriver.state()` so legacy no-hash quality artifacts surface `gates["quality"]="unknown"` and keep Step 6 locked.
    - Updated frontend API types and `ExportView` detail grouping so unknown quality checks render as `来源未知：...`.

Verification after unknown-hash quality-bundle gate expansion:

- `python -m pytest tests/test_flow_driver.py::test_export_readiness_reports_unknown_hash_legacy_quality_bundle -q`
  RED result before implementation: export-readiness returned all three checks in `missing_quality_checks`.
  Result after unknown-hash quality-bundle gate expansion: 1 passed, 2 warnings.
- `npm test -- --run src/views/exportView.test.tsx --reporter=dot`
  RED result before implementation: the export UI did not render `质量检查未完成` or `来源未知：提交前质量检查、权利要求防守工作表`.
  Result after unknown-hash quality-bundle UI expansion: 1 test file passed, 5 tests passed.
- `python -m pytest tests/test_flow_driver.py -q`
  Result after unknown-hash quality-bundle gate expansion: 30 passed, 36 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after unknown-hash quality-bundle gate expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after unknown-hash quality-bundle UI expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after unknown-hash quality-bundle UI expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after unknown-hash quality-bundle gate expansion: 189 passed, 159 warnings.
- `git diff --check`
  Result after unknown-hash quality-bundle gate expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after unknown-hash quality-bundle gate expansion: no new root artifacts found.

84. Added a Markdown image-alt evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in Markdown image alt text, such as `![evidence: EV-...](path-plan.png)`, `![证据：EV-...](collection-log.png)`, and `![source: ...](figure-1.png)`.
      Initial result: failed because the official compiler blocked the draft through broader citation guards but did not report a carrier-specific `markdown_image_alt_citation` blocker.
    - Added a RED adversarial harness test for `generated_markdown_image_alt_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_markdown_image_alt_honesty`.
    - Updated `backend/app/official_compile.py` to report `markdown_image_alt_citation` for Markdown image alt evidence metadata in both raw draft sections and cleaned official text.
    - Added the `generated_markdown_image_alt_honesty` action and fixture LLM so generated drafts with image-alt evidence metadata are covered by replayable adversarial traces.

Verification after Markdown image-alt honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_markdown_image_alt_evidence_leakage -q`
  RED result before implementation: compile was blocked, but no `markdown_image_alt_citation` blocker was reported.
  Result after Markdown image-alt honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_markdown_image_alt_honesty_action -q`
  RED result before implementation: `generated_markdown_image_alt_honesty` was an unknown adversarial action.
  Result after Markdown image-alt honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after Markdown image-alt honesty expansion: 86 passed, 83 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after Markdown image-alt honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after Markdown image-alt honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after Markdown image-alt honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after Markdown image-alt honesty expansion: 191 passed, 160 warnings.
- `git diff --check`
  Result after Markdown image-alt honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after Markdown image-alt honesty expansion: no new root artifacts found.

85. Added an HTML image-attribute evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML image attributes, such as `<img alt="evidence: EV-...">`, `<img title="证据：EV-...">`, and `<img alt="source: ...">`.
      Initial result: failed because the official compiler completed, allowing HTML image alt/title evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_image_attribute_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_image_attribute_honesty`.
    - Updated `backend/app/official_compile.py` to block HTML `<img>` `alt`, `title`, and `aria-label` attribute values carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_image_attribute_honesty` action and fixture LLM so generated drafts with HTML image attribute evidence metadata are covered by replayable adversarial traces.

Verification after HTML image-attribute honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_image_attribute_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML image attribute evidence metadata.
  Result after HTML image-attribute honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_image_attribute_honesty_action -q`
  RED result before implementation: `generated_html_image_attribute_honesty` was an unknown adversarial action.
  Result after HTML image-attribute honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML image-attribute honesty expansion: 88 passed, 84 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML image-attribute honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML image-attribute honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML image-attribute honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML image-attribute honesty expansion: 193 passed, 161 warnings.
- `git diff --check`
  Result after HTML image-attribute honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML image-attribute honesty expansion: no new root artifacts found.

86. Added an HTML caption evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML captions, such as `<figcaption>evidence: EV-...</figcaption>`, `<caption>证据：EV-...</caption>`, and `<figcaption>source: ...</figcaption>`.
      Initial result: failed because the official compiler completed, allowing HTML caption evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_caption_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_caption_honesty`.
    - Updated `backend/app/official_compile.py` to block HTML `<figcaption>` and `<caption>` visible text carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_caption_honesty` action and fixture LLM so generated drafts with HTML caption evidence metadata are covered by replayable adversarial traces.

Verification after HTML caption honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_caption_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML caption evidence metadata.
  Result after HTML caption honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_caption_honesty_action -q`
  RED result before implementation: `generated_html_caption_honesty` was an unknown adversarial action.
  Result after HTML caption honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML caption honesty expansion: 90 passed, 85 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML caption honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML caption honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML caption honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML caption honesty expansion: 195 passed, 162 warnings.
- `git diff --check`
  Result after HTML caption honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML caption honesty expansion: no new root artifacts found.

87. Added an HTML accessible-attribute evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in non-image HTML accessibility attributes, such as `<abbr title="evidence: EV-...">`, `<span aria-label="证据：EV-...">`, and `<a title="source: ...">`.
      Initial result: failed because the official compiler completed, allowing HTML title/aria-label evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_accessible_attribute_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_accessible_attribute_honesty`.
    - Updated `backend/app/official_compile.py` to block non-`<img>` HTML `alt`, `title`, and `aria-label` attribute values carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_accessible_attribute_honesty` action and fixture LLM so generated drafts with HTML accessible-attribute evidence metadata are covered by replayable adversarial traces.

Verification after HTML accessible-attribute honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_accessible_attribute_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML accessible-attribute evidence metadata.
  Result after HTML accessible-attribute honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_accessible_attribute_honesty_action -q`
  RED result before implementation: `generated_html_accessible_attribute_honesty` was an unknown adversarial action.
  Result after HTML accessible-attribute honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML accessible-attribute honesty expansion: 92 passed, 86 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML accessible-attribute honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML accessible-attribute honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML accessible-attribute honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML accessible-attribute honesty expansion: 197 passed, 163 warnings.
- `git diff --check`
  Result after HTML accessible-attribute honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML accessible-attribute honesty expansion: no new root artifacts found.

88. Added an SVG title/desc evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in SVG text metadata, such as `<svg><title>evidence: EV-...</title></svg>`, `<svg><desc>证据：EV-...</desc></svg>`, and `<svg><title>source: ...</title></svg>`.
      Initial result: failed because the official compiler completed, allowing SVG title/desc evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_svg_title_desc_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_svg_title_desc_honesty`.
    - Updated `backend/app/official_compile.py` to block SVG `<title>` and `<desc>` text carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_svg_title_desc_honesty` action and fixture LLM so generated drafts with SVG title/desc evidence metadata are covered by replayable adversarial traces.

Verification after SVG title/desc honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_svg_title_desc_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking SVG title/desc evidence metadata.
  Result after SVG title/desc honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_svg_title_desc_honesty_action -q`
  RED result before implementation: `generated_svg_title_desc_honesty` was an unknown adversarial action.
  Result after SVG title/desc honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after SVG title/desc honesty expansion: 94 passed, 87 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after SVG title/desc honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after SVG title/desc honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after SVG title/desc honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after SVG title/desc honesty expansion: 199 passed, 164 warnings.
- `git diff --check`
  Result after SVG title/desc honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after SVG title/desc honesty expansion: no new root artifacts found.

89. Added an SVG visible-text evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in SVG visible text, such as `<svg><text>evidence: EV-...</text></svg>`, `<svg><tspan>证据：EV-...</tspan></svg>`, and `<svg><text>source: ...</text></svg>`.
      Initial result: failed because the official compiler completed, allowing SVG visible text evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_svg_text_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_svg_text_honesty`.
    - Updated `backend/app/official_compile.py` to block SVG `<text>` and `<tspan>` text carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_svg_text_honesty` action and fixture LLM so generated drafts with SVG visible-text evidence metadata are covered by replayable adversarial traces.

Verification after SVG visible-text honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_svg_text_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking SVG visible-text evidence metadata.
  Result after SVG visible-text honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_svg_text_honesty_action -q`
  RED result before implementation: `generated_svg_text_honesty` was an unknown adversarial action.
  Result after SVG visible-text honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after SVG visible-text honesty expansion: 96 passed, 88 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after SVG visible-text honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after SVG visible-text honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after SVG visible-text honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after SVG visible-text honesty expansion: 201 passed, 165 warnings.
- `git diff --check`
  Result after SVG visible-text honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after SVG visible-text honesty expansion: no new root artifacts found.

90. Added an HTML style-tag evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML style tags and CSS content, such as `<style>/* evidence: EV-... */ ...</style>`, CSS `content: '证据：EV-...'`, and `<style>/* source: ... */</style>`.
      Initial result: failed because the official compiler completed, allowing style/CSS evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_style_tag_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_style_tag_honesty`.
    - Updated `backend/app/official_compile.py` to block `<style>...</style>` blocks carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_style_tag_honesty` action and fixture LLM so generated drafts with style-tag evidence metadata are covered by replayable adversarial traces.

Verification after HTML style-tag honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_style_tag_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML style-tag evidence metadata.
  Result after HTML style-tag honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_style_tag_honesty_action -q`
  RED result before implementation: `generated_html_style_tag_honesty` was an unknown adversarial action.
  Result after HTML style-tag honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML style-tag honesty expansion: 98 passed, 89 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML style-tag honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML style-tag honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML style-tag honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML style-tag honesty expansion: 203 passed, 166 warnings.
- `git diff --check`
  Result after HTML style-tag honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML style-tag honesty expansion: no new root artifacts found.

91. Added an HTML inline-style evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in inline HTML `style="..."` attributes, such as `<span style="--evidence: EV-...">`, CSS `content: '证据：EV-...'`, and `<span style="--source: ...">`.
      Initial result: failed because the official compiler completed, allowing inline-style evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_inline_style_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_inline_style_honesty`.
    - Updated `backend/app/official_compile.py` to block inline HTML style attributes carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_inline_style_honesty` action and fixture LLM so generated drafts with inline-style evidence metadata are covered by replayable adversarial traces.

Verification after HTML inline-style honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_inline_style_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML inline-style evidence metadata.
  Result after HTML inline-style honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_inline_style_honesty_action -q`
  RED result before implementation: `generated_html_inline_style_honesty` was an unknown adversarial action.
  Result after HTML inline-style honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML inline-style honesty expansion: 100 passed, 90 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML inline-style honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML inline-style honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML inline-style honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML inline-style honesty expansion: 205 passed, 167 warnings.
- `git diff --check`
  Result after HTML inline-style honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML inline-style honesty expansion: no new root artifacts found.

92. Added an HTML form-field evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML form fields, such as `<input name="evidence" value="EV-...">`, `<input name="证据" value="EV-...">`, and `<input value="source: ...">`.
      Initial result: failed because the official compiler completed, allowing form-field evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_form_field_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_form_field_honesty`.
    - Updated `backend/app/official_compile.py` to block HTML input/textarea/select/option field metadata carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_form_field_honesty` action and fixture LLM so generated drafts with form-field evidence metadata are covered by replayable adversarial traces.

Verification after HTML form-field honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_form_field_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML form-field evidence metadata.
  Result after HTML form-field honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_form_field_honesty_action -q`
  RED result before implementation: `generated_html_form_field_honesty` was an unknown adversarial action.
  Result after HTML form-field honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML form-field honesty expansion: 102 passed, 91 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML form-field honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML form-field honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML form-field honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML form-field honesty expansion: 207 passed, 168 warnings.
- `git diff --check`
  Result after HTML form-field honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML form-field honesty expansion: no new root artifacts found.

93. Added an HTML semantic-metadata evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in HTML Microdata/RDFa-style attributes, such as `<span itemprop="evidence" content="EV-...">`, `<span property="证据" content="EV-...">`, and `<span itemprop="source" content="...">`.
      Initial result: failed because the official compiler completed, allowing semantic metadata evidence through to the official package.
    - Added a RED adversarial harness test for `generated_html_semantic_metadata_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_semantic_metadata_honesty`.
    - Updated `backend/app/official_compile.py` to block non-`<meta>` HTML `itemprop`/`property` semantic metadata carrying evidence/source/citation/ref/material metadata in both raw draft sections and cleaned official text.
    - Added the `generated_html_semantic_metadata_honesty` action and fixture LLM so generated drafts with semantic metadata evidence are covered by replayable adversarial traces.

Verification after HTML semantic-metadata honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_semantic_metadata_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML semantic metadata evidence.
  Result after HTML semantic-metadata honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_semantic_metadata_honesty_action -q`
  RED result before implementation: `generated_html_semantic_metadata_honesty` was an unknown adversarial action.
  Result after HTML semantic-metadata honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML semantic-metadata honesty expansion: 104 passed, 92 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML semantic-metadata honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML semantic-metadata honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML semantic-metadata honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML semantic-metadata honesty expansion: 209 passed, 169 warnings.
- `git diff --check`
  Result after HTML semantic-metadata honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML semantic-metadata honesty expansion: no new root artifacts found.

94. Added an HTML JSON-script evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in non-JSON-LD HTML JSON scripts, such as `<script type="application/json">{"evidence": ...}</script>` and Chinese evidence/source JSON keys inside `application/json` script blocks.
      Initial result: failed because the official compiler completed, allowing HTML JSON-script evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_json_script_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_json_script_honesty`.
    - Updated `backend/app/official_compile.py` to block `application/json` and `application/x-json` script blocks carrying evidence/source/citation/ref/material JSON keys in both raw draft sections and cleaned official text.
    - Added the `generated_html_json_script_honesty` action and fixture LLM so generated drafts with HTML JSON-script evidence metadata are covered by replayable adversarial traces.

Verification after HTML JSON-script honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_json_script_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML JSON-script evidence metadata.
  Result after HTML JSON-script honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_json_script_honesty_action -q`
  RED result before implementation: `generated_html_json_script_honesty` was an unknown adversarial action.
  Result after HTML JSON-script honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML JSON-script honesty expansion: 106 passed, 93 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML JSON-script honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML JSON-script honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML JSON-script honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML JSON-script honesty expansion: 211 passed, 170 warnings.
- `git diff --check`
  Result after HTML JSON-script honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML JSON-script honesty expansion: no new root artifacts found.

95. Added an HTML class/id evidence-honesty adversarial variant:
    - Added a RED compiler test for evidence/source metadata hidden in ordinary HTML `class` and `id` attribute values, such as `<span class="evidence EV-...">`, `<section id="source-...">`, and Chinese evidence/source class names.
      Initial result: failed because the official compiler completed, allowing class/id evidence metadata through to the official package.
    - Added a RED adversarial harness test for `generated_html_class_id_honesty`.
      Initial result: failed with `ValueError: Unknown adversarial action: generated_html_class_id_honesty`.
    - Updated `backend/app/official_compile.py` to block `class`/`id` values carrying evidence/source/citation/ref/material metadata or EV/EVIDENCE identifiers in both raw draft sections and cleaned official text.
    - Added the `generated_html_class_id_honesty` action and fixture LLM so generated drafts with HTML class/id evidence metadata are covered by replayable adversarial traces.

Verification after HTML class/id honesty expansion:

- `python -m pytest tests/test_official_compile.py::test_compiler_blocks_html_class_id_evidence_leakage -q`
  RED result before implementation: compile completed instead of blocking HTML class/id evidence metadata.
  Result after HTML class/id honesty expansion: 1 passed, 1 warning.
- `python -m pytest tests/test_adversarial_flow_explorer.py::test_adversarial_flow_harness_can_run_generated_html_class_id_honesty_action -q`
  RED result before implementation: `generated_html_class_id_honesty` was an unknown adversarial action.
  Result after HTML class/id honesty expansion: 1 passed, 2 warnings.
- `python -m pytest tests/test_official_compile.py tests/test_adversarial_flow_explorer.py -q`
  Result after HTML class/id honesty expansion: 108 passed, 94 warnings.
- `python -m pytest tests/test_evidence_binding.py tests/test_flow_driver.py tests/test_post_draft_review.py -q`
  Result after HTML class/id honesty expansion: 60 passed, 61 warnings.
- `npm test -- --run src/views/exportView.test.tsx src/app/routes.test.tsx src/guidedFlow.test.ts src/GuidedPatentFlow.officialCompile.test.tsx --reporter=dot`
  Result after HTML class/id honesty expansion: 4 test files passed, 63 tests passed.
- `npm run build`
  Result after HTML class/id honesty expansion: passed; `tsc -b` and Vite production build completed.
- `python -m pytest tests/test_adversarial_flow_explorer.py tests/test_golden_patent_cases.py tests/test_golden_release_gate.py tests/test_flow_driver.py tests/test_runtime_controls.py tests/test_evidence_binding.py tests/test_official_compile.py tests/test_claim_defense.py tests/test_llm_cassette.py tests/test_post_draft_review.py -q`
  Result after HTML class/id honesty expansion: 213 passed, 171 warnings.
- `git diff --check`
  Result after HTML class/id honesty expansion: passed.
- Root artifact check for `chroma`, `*.sqlite`, `*.sqlite3`, and `*.db`
  Result after HTML class/id honesty expansion: no new root artifacts found.

Remaining after this continuation:

1. Continue broadening the INV matrix beyond the newly covered core cases, especially remaining legacy-project edge cases beyond the now-covered missing/stale/failed/latest-attempt/unknown-hash quality-bundle states.
2. Expand the adversarial explorer further with additional isolated honesty variants beyond the English metadata, Chinese metadata, URL leakage, bracketed citation, parenthetical citation, XML evidence tags, HTML comment/attribute/class-id/image-attribute/accessible-attribute/meta/JSON-LD/JSON-script/visible-text/caption/style/inline-style/form-field/semantic-metadata/entity-escaped metadata, SVG title/desc/text metadata, Markdown footnote/reference/table/list/blockquote/link-title/image-alt/YAML/TOML/INI/CSV metadata, fenced JSON metadata, AsciiDoc attribute metadata, LaTeX command metadata, BibTeX entry metadata, reStructuredText directive metadata, JSON wrapper, and source-footer actions now covered.
3. Human-calibrate the five queued golden/red-team patent-quality cases before enabling any judge/release regression gates; the release-gate script can now generate a Markdown calibration packet for the reviewer and fails closed if an enabled calibrated case lacks reviewer/notes metadata or violates the deterministic-only gate contract.
4. Add calibrated official-output fixture contents, record each approved fixture's SHA256 in `human_calibration.official_text_fixture_sha256`, and flip selected golden cases to `release_gate_enabled=true` once human review is complete; the release-gate report and Markdown packet now list the exact fixture target path, existence state, and current SHA256 when the fixture file already exists.
5. Keep watching for release-gate ergonomics around the stricter three-artifact quality bundle, especially any user-visible dead ends discovered during manual QA.
