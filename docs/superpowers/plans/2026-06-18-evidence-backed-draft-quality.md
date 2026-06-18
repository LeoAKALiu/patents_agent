# Evidence-backed Draft Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans if available. If those skills are unavailable, implement this plan task-by-task in order and keep checkbox state updated.

**Goal:** Improve final patent draft quality and drafting efficiency by carrying evidence through the whole drafting chain, replacing generic completion patches with evidence-backed local revisions, adding stage-level LLM caching, and extending deterministic golden quality gates.

**Architecture:** Add an internal evidence binding layer, extend claim-defense and draft-completion outputs with evidence refs, introduce a focused patch generator, wrap LLM stage calls with cache/timeout/retry infrastructure, and expand the v1.1 quality report with drafting-quality metrics. Preserve the existing official compile and post-draft review export gates.

**Design Spec:** `docs/superpowers/specs/2026-06-18-evidence-backed-draft-quality-design.md`

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLite, OpenAI-compatible LLM API, pytest, React 19, TypeScript, Vitest, Vite.

---

## Current Constraints

- The current checkout has unrelated frontend changes and local artifacts. Do not modify or revert those changes.
- There is no `.planning/` directory in this repository. Follow the existing `docs/superpowers/specs` and `docs/superpowers/plans` documentation convention.
- Official filing text must continue to export only from `OfficialDraftPackage`.
- `DraftPackage`, completion reports, evidence ledgers, prompts, generation logs, attorney memo, and review reports are internal-only unless explicitly compiled into a clean official package.
- Existing hash gates are authoritative:
  - `DraftPackage` source hash gates quality freshness.
  - `OfficialDraftPackage` hash gates post-draft review.
  - Latest blocking post-draft review invalidates earlier passing review for the same compile.
- Existing deterministic smoke must remain offline by default and must not require live provider secrets.

## File Structure

- Create: `backend/app/evidence_binding.py`
  - Build unified evidence bindings from disclosure runs, deep research ledgers, project materials, patent points, formulas, and draft citations.
- Create: `backend/app/patch_generator.py`
  - Generate local, evidence-backed `ProposedPatch` records from completion issues and support matrix rows.
- Create: `backend/app/llm_cache.py`
  - Provide stage cache keying, storage helpers, timeout/retry wrapper, and cache metadata.
- Modify: `backend/app/schemas.py`
  - Add `EvidenceBinding` and optional evidence fields to `FeatureRecord`, `ClaimSupportMatrixRow`, `ProposedPatch`, and supporting run models.
- Modify: `backend/app/claim_defense.py`
  - Thread evidence bindings into feature extraction and normalization.
- Modify: `backend/app/draft_completion.py`
  - Build evidence-backed support matrix, adjust scoring, and call patch generator.
- Modify: `backend/app/main.py`
  - Wire evidence binding construction, patch-generation endpoint, project cache clearing, and score-improvement safety behavior.
- Modify: `backend/app/storage.py`
  - Add `llm_stage_cache` table and helper methods. Optionally add `patch_generation_runs`.
- Modify: `backend/app/llm.py`
  - Add optional timeout/retry/cache-aware stage completion path while preserving `FakeLLMClient`.
- Modify: `frontend/src/api.ts`
  - Add evidence binding and patch-generation types/helpers.
- Modify: `frontend/src/flow/panels/QualityPanel.tsx`
  - Surface evidence support chain, stale state, patch evidence refs, and quality trend details.
- Modify: `frontend/src/domain.ts`
  - Add labels/helpers for evidence status, binding confidence, and patch safety.
- Modify: `frontend/src/guidedFlow.ts`
  - Preserve existing hash freshness gates and expose stale completion messaging.
- Modify: `scripts/v1_api_smoke.py`
  - Extend quality report metrics and gates.
- Add tests:
  - `tests/test_evidence_binding.py`
  - `tests/test_patch_generator.py`
  - `tests/test_llm_cache.py`
  - Extend `tests/test_draft_completion.py`
  - Extend `tests/test_draft_completion_api.py`
  - Extend `tests/test_v1_quality_gate.py`
  - Extend frontend tests for quality panel helpers and guided stale state.

---

### Task 1: Add Evidence Binding Models and Builder

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/evidence_binding.py`
- Create: `tests/test_evidence_binding.py`

- [ ] **Step 1: Add failing tests for evidence extraction**

Create tests that cover:

- Prior-art hits from `DisclosurePackage.prior_art_hits` become `EvidenceBinding(source_type="prior_art")`.
- Deep research ledger entries preserve `evidence_id`, publication number, URL, source, snippet, and confidence.
- Patent points with `evidence_status="feasible_unverified"` become internal evidence bindings that cannot upgrade verified support.
- Project materials become user-provided evidence bindings.
- Duplicate publication numbers are de-duplicated.

Expected first run:

```bash
python3 -m pytest tests/test_evidence_binding.py -q
```

Expected: FAIL because the module and schema do not exist.

- [ ] **Step 2: Add `EvidenceBinding` schema**

Add to `backend/app/schemas.py`:

- `EvidenceBinding`
- `EvidenceBindingSourceType`
- `EvidenceVerificationStatus`

Use default values so old JSON records remain readable.

- [ ] **Step 3: Implement `build_evidence_bindings`**

Create `backend/app/evidence_binding.py` with pure functions:

- `build_evidence_bindings(project, materials, disclosures, patent_points, formula_runs=None) -> list[EvidenceBinding]`
- `bindings_by_label(bindings) -> dict[str, list[EvidenceBinding]]`
- `evidence_refs_for_text(text, bindings, min_confidence=0.6) -> list[str]`
- `normalize_evidence_label(value) -> str`

Keep it deterministic and side-effect free.

- [ ] **Step 4: Verify**

Run:

```bash
python3 -m pytest tests/test_evidence_binding.py -q
```

Acceptance criteria:

- Evidence ids are stable within one build.
- Prior-art evidence is citable but internal-only when sourced from research ledger.
- User materials and patent points are represented separately.
- No official export code imports or serializes evidence bindings.

---

### Task 2: Thread Evidence Through Claim Defense

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/claim_defense.py`
- Extend: `tests/test_claim_defense.py`

- [ ] **Step 1: Extend `FeatureRecord`**

Add fields:

- `evidence_refs: list[str] = []`
- `source_refs: list[str] = []`
- `support_explanation: str = ""`

- [ ] **Step 2: Update feature extraction**

Modify `generate_claim_defense_worksheet` to accept optional `evidence_bindings`.

Rules:

- Claim fragments matching prior-art differentiators receive prior-art refs.
- Patent point fragments receive patent point source refs.
- Materials-supported terms receive material refs.
- Low-confidence matches stay attached but should not classify as verified support.

- [ ] **Step 3: Preserve backward compatibility**

Existing callers can omit evidence bindings. Existing tests should pass without changing fixtures unless they assert exact model dumps.

- [ ] **Step 4: Verify**

Run:

```bash
python3 -m pytest tests/test_claim_defense.py tests/test_evidence_binding.py -q
```

Acceptance criteria:

- Existing claim defense behavior is preserved.
- New evidence refs appear when bindings are supplied.
- Feature classification does not upgrade to differentiator solely from model-generated evidence.

---

### Task 3: Evidence-backed Draft Completion Matrix

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/draft_completion.py`
- Modify: `backend/app/main.py`
- Extend: `tests/test_draft_completion.py`
- Extend: `tests/test_draft_completion_api.py`

- [ ] **Step 1: Extend `ClaimSupportMatrixRow`**

Add:

- `evidence_refs`
- `source_refs`
- `support_explanation`
- `missing_evidence_reason`

- [ ] **Step 2: Build evidence bindings in quality cycle**

In `main.py`:

- Build evidence bindings inside `create_claim_defense_worksheet`, `create_draft_completion_run`, and `_run_quality_cycle`.
- Pass bindings into `generate_claim_defense_worksheet` and `run_draft_completion`.

- [ ] **Step 3: Update matrix scoring**

Rules:

- `prior_art_distinction` should only increase materially when differentiator/core combo rows have prior-art refs.
- `support_strength` should penalize core rows that have only model-generated evidence.
- Missing evidence should produce `missing_evidence_reason`.
- Verified project material or verified patent point support can improve authorization stability.

- [ ] **Step 4: Update completion report**

`completion_run_to_markdown` should include compact evidence refs for each matrix row and show missing evidence reasons.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m pytest tests/test_draft_completion.py tests/test_draft_completion_api.py -q
```

Acceptance criteria:

- Old completion runs deserialize with empty evidence refs.
- A core claim feature without evidence does not receive strong prior-art distinction credit.
- Completion report shows evidence refs and does not leak full evidence ledger contents into official markdown.

---

### Task 4: Add Evidence-backed Patch Generator

**Files:**
- Create: `backend/app/patch_generator.py`
- Modify: `backend/app/draft_completion.py`
- Modify: `backend/app/main.py`
- Create: `tests/test_patch_generator.py`
- Extend: `tests/test_draft_completion.py`

- [ ] **Step 1: Write failing patch-generator tests**

Cover:

- Claim support gap with strong evidence creates an `insert` patch for description.
- Unverified quantitative effect creates `sidecar_only` or a non-official patch.
- Patch output includes evidence refs.
- Patch text does not include prompt/log/internal markers.
- Patch has enough `before_text` or an insertion anchor to be reviewable.

- [ ] **Step 2: Implement rules-first patch generator**

Create:

- `PatchGenerationContext`
- `generate_evidence_backed_patches(context) -> list[ProposedPatch]`

Use deterministic rules first:

- data structure support
- formula support
- pseudo-code support
- term definition
- unverified effect rewrite
- subject matter risk rewrite

Do not call LLM in the first pass unless the existing app LLM is explicitly supplied.

- [ ] **Step 3: Replace generic template patching**

Update `_patches_from_tasks` and `_patch_text` in `draft_completion.py` so generic fallback still exists but evidence-backed generator is preferred.

- [ ] **Step 4: Add patch-generation endpoint**

Add:

```text
POST /api/projects/{project_id}/completion-runs/{run_id}/patches/generate
```

This endpoint should regenerate or append candidate patches for the current matching draft hash only.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m pytest tests/test_patch_generator.py tests/test_draft_completion.py tests/test_draft_completion_api.py -q
```

Acceptance criteria:

- Existing score improvement still works.
- Patches are more specific than the old generic `input_data/processing_rule` template.
- Official-safe patches require evidence and pass filing readiness after application.

---

### Task 5: Harden Score Improvement Safety

**Files:**
- Modify: `backend/app/main.py`
- Extend: `tests/test_draft_completion_api.py`
- Extend: `tests/test_official_compile.py`

- [ ] **Step 1: Add tests for safe application**

Test that:

- Score improvement does not apply patches for stale completion runs.
- Score improvement does not apply official-safe patches without evidence refs when target is a core feature.
- Patch application invalidates official compile and post-draft review through existing hashes.

- [ ] **Step 2: Update `_apply_completion_patch`**

Rules:

- Require current draft hash to match run `draft_package_hash`.
- Prefer anchor/before_text replacement over blind append.
- If appending, add section heading only once and keep patent-section style.
- Do not apply sidecar-only patches.

- [ ] **Step 3: Re-run gates after patch application**

After applying patches:

- run filing readiness
- run draft completion
- do not automatically run official compile or post review

- [ ] **Step 4: Verify**

Run:

```bash
python3 -m pytest tests/test_draft_completion_api.py tests/test_official_compile.py tests/test_post_draft_review.py -q
```

Acceptance criteria:

- No stale patch can modify current draft.
- Export stays blocked until official compile and post-draft review are rerun.

---

### Task 6: Add Stage-level LLM Cache

**Files:**
- Create: `backend/app/llm_cache.py`
- Modify: `backend/app/storage.py`
- Modify: `backend/app/llm.py`
- Extend or create: `tests/test_llm_cache.py`

- [ ] **Step 1: Add cache schema tests**

Test:

- cache key changes when stage, prompt, model, source hash, or prompt pack changes.
- cache hit returns stored response.
- project cache clear deletes only one project's entries.

- [ ] **Step 2: Add storage table**

Create `llm_stage_cache` in `_migrate`:

- `cache_key text primary key`
- `project_id text not null`
- `stage text not null`
- `model text not null`
- `prompt_hash text not null`
- `input_hash text not null`
- `prompt_pack_version text not null default ''`
- `response_text text not null`
- `response_json text`
- `status text not null`
- `created_at text not null default current_timestamp`
- `expires_at text`

- [ ] **Step 3: Implement wrapper**

`llm_cache.py` should expose:

- `stage_cache_key`
- `complete_stage_cached`
- `clear_project_llm_cache`

The wrapper must accept a fallback callable so `FakeLLMClient` tests remain simple.

- [ ] **Step 4: Add timeout/retry boundary**

Add optional timeout/retry config without changing the `LLMClient` protocol required by existing code. Prefer wrapper functions over widening every call signature in one PR.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m pytest tests/test_llm_cache.py tests/test_generator.py tests/test_post_draft_review.py -q
```

Acceptance criteria:

- Cache never changes response semantics.
- Cache misses call the underlying LLM exactly once.
- Cache hits do not call the underlying LLM.

---

### Task 7: Integrate Cache Into Expensive Stages

**Files:**
- Modify: `backend/app/disclosure/generator.py`
- Modify: `backend/app/generator.py`
- Modify: `backend/app/post_draft_review.py`
- Modify: `backend/app/main.py`
- Extend relevant tests.

- [ ] **Step 1: Integrate draft-generation cache**

Wrap:

- claims
- description
- abstract
- drawings
- diagram
- image_prompt

Use project/source hash from caller. If unavailable, skip cache.

- [ ] **Step 2: Integrate post-draft review cache**

Wrap role stages and chair synthesis with prompt pack version in cache key.

- [ ] **Step 3: Integrate patch generator cache if LLM mode exists**

Only for LLM-backed patch generation. Rules-first patch generation does not need cache.

- [ ] **Step 4: Add cache clear endpoint**

Add:

```text
POST /api/projects/{project_id}/llm-cache/clear
```

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m pytest tests/test_generator.py tests/test_post_draft_review.py tests/test_llm_cache.py -q
```

Acceptance criteria:

- Existing fake LLM tests still pass.
- Cached post-draft review remains hash-bound and cannot unlock export for changed drafts.

---

### Task 8: Frontend Evidence and Patch UI

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/domain.ts`
- Modify: `frontend/src/flow/panels/QualityPanel.tsx`
- Modify: `frontend/src/guidedFlow.ts`
- Extend frontend tests.

- [ ] **Step 1: Add API types**

Add fields for:

- evidence refs on matrix rows
- missing evidence reason
- patch evidence refs
- patch safety
- optional stale indicators

- [ ] **Step 2: Add domain labels**

Add helpers:

- `evidenceVerificationLabel`
- `evidenceBindingConfidenceLabel`
- `patchSafetyLabel`
- `completionRunFreshnessLabel`

- [ ] **Step 3: Update QualityPanel**

Add compact sections:

- evidence support chain
- top missing evidence reasons
- candidate patch list with evidence refs
- stale result warning when hashes do not match

Do not create a marketing-style page or separate dashboard. Keep it in the existing workflow panel.

- [ ] **Step 4: Verify**

Run:

```bash
npm --prefix frontend test -- Quality
npm --prefix frontend test
npm --prefix frontend run build
```

Acceptance criteria:

- Text does not overflow compact panels.
- Existing guided-flow steps are unchanged.
- Users can distinguish stale quality results from current ones.

---

### Task 9: Extend Golden Quality Gate

**Files:**
- Modify: `scripts/v1_api_smoke.py`
- Modify: `tests/test_v1_quality_gate.py`
- Modify: `docs/release/v1.1.0-quality-gates.md`

- [ ] **Step 1: Add quality metrics**

In `scripts/v1_api_smoke.py`, compute per workflow:

- `evidence_binding_rate`
- `core_feature_support_rate`
- `unsupported_core_feature_count`
- `unverified_effect_leak_count`
- `dependent_fallback_depth`
- `embodiment_density`
- `patch_delta`

- [ ] **Step 2: Add gates**

Add deterministic gates:

- `official_export_hygiene == clean`
- `unverified_effect_leak_count == 0`
- `core_feature_support_rate >= floor`
- `evidence_binding_rate >= floor`

Use conservative floors at first so the gate detects regressions without forcing live-provider behavior.

- [ ] **Step 3: Update docs**

Update `docs/release/v1.1.0-quality-gates.md` to explain drafting-quality gates separately from export hygiene gates.

- [ ] **Step 4: Verify**

Run:

```bash
python3 -m pytest tests/test_v1_quality_gate.py -q
python3 scripts/v1_api_smoke.py --report-dir /tmp/patentagent-v1-quality
```

Acceptance criteria:

- Report JSON and Markdown include new metrics.
- Default gate remains deterministic and offline.

---

### Task 10: Full Regression and Documentation Sweep

**Files:**
- Modify as needed:
  - `README.md`
  - `CHANGELOG.md`
  - `docs/release/v1.1.0-quality-gates.md`

- [ ] **Step 1: Backend regression**

Run:

```bash
python3 -m pytest -q
```

- [ ] **Step 2: Frontend regression**

Run:

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 3: Deterministic smoke**

Run:

```bash
scripts/v1_smoke.sh
```

If desktop/Tauri build dependencies are unavailable, record the exact missing dependency and run the API/backend/frontend subsets.

- [ ] **Step 4: Documentation check**

Update docs to mention:

- evidence support chain
- local patch generation
- cache behavior and clear-cache action
- drafting-quality golden metrics

- [ ] **Step 5: Git hygiene**

Before commit:

```bash
git status --short
git diff --check
```

Do not include unrelated existing frontend changes or local DMG/artifact files.

---

## Rollout Strategy

Recommended PR split:

1. Evidence binding models and builder.
2. Claim defense and completion matrix evidence refs.
3. Evidence-backed patch generator and score-improvement safety.
4. LLM stage cache.
5. Frontend quality panel enhancements.
6. Golden quality gate and docs.

This split keeps official export safety reviewable at each step.

## Success Criteria

- Core claim features show support status plus evidence refs in quality output.
- Unverified or model-generated claims do not inflate quality scores.
- Patch suggestions are local, reviewable, and evidence-backed.
- Stage cache reduces repeated LLM calls for identical draft snapshots.
- Official export remains locked behind current official compile and matching post-draft review.
- Deterministic golden report tracks drafting quality trends offline.
