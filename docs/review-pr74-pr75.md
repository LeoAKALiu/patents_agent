# Code Review: PR #74 + PR #75

**PR #74:** `[codex] Add knowledge readiness gate` (`codex/knowledge-readiness-gate`)
**PR #75:** `[codex] Apply chair revisions after post-draft review` (`codex/chair-revision-apply`)
**Date:** 2026-06-16 · **Reviewer:** MiMoCode

---

## 1. PR #74 — Knowledge Readiness Gate

### Summary

Adds a required knowledge-readiness run before invention-point extraction and draft generation. Requires an uploaded DeepResearch report plus a >80/100 multi-role knowledge score before `/generate` proceeds.

| Metric | Value |
|--------|-------|
| Files changed | 16 |
| Lines added | 847 |
| Lines deleted | 4 |

### Test Results

| Suite | Result |
|-------|--------|
| `tests/test_knowledge_readiness.py` | ✅ 3 passed |
| `frontend/src/guidedFlow.test.ts` | ✅ 41 passed |
| All other backend tests | ✅ (via `seed_knowledge_ready` helper) |

### Architecture

```
POST /api/projects/{id}/knowledge-readiness
  → run_knowledge_readiness()
    → 3 LLM role calls (deep_research_auditor, prior_art_auditor, drafting_support_auditor)
    → average score + reference bonus
    → blocking if no DeepResearch report OR score ≤ 80
  → stored in SQLite (knowledge_readiness_runs table)

POST /api/projects/{id}/generate
  → require_knowledge_ready(latest_run)  ← NEW gate
  → existing deliberation gate
  → existing formula gate
```

### ✅ Strengths

1. **Clean gate pattern.** `require_knowledge_ready()` is a simple check-and-raise, same pattern as the existing deliberation gate. Easy to reason about.
2. **Robust JSON extraction.** `_extract_json()` handles raw JSON, fenced code blocks, and embedded JSON objects — covers common LLM output quirks.
3. **Bonus system is well-calibrated.** Max bonus is 10 points (`related_reference * 3 + min(4, corpus_docs)`), so a score of 71+ with references can pass. Borderline cases benefit from materials without gaming the system.
4. **Test helper `seed_knowledge_ready`.** Avoids duplicating run setup across 6 test files. Clean approach.
5. **Frontend step is well-integrated.** The `knowledge` step slots between `idea` and `invention` in the guided flow with proper status derivation.

### 🟡 Issues

**1. DeepResearch detection is keyword-based and fragile**

`knowledge_readiness.py:126-140` — `is_deep_research_report_material()` matches on filename/text keywords like "deepresearch", "深度研究", "检索报告". A user who uploads a research report named `report.md` with no keyword in the first 5000 chars will be blocked even with a valid report.

The frontend has the same logic duplicated in `GuidedPatentFlow.tsx:869-880` (`isDeepResearchMaterial`). Two copies of the same heuristic will drift.

**Recommendation:** Consider a dedicated `material_type` tag set during upload (e.g., `type: "deep_research"`), or at minimum extract the shared keyword list into a constant that both backend and frontend can reference.

**2. `proceed_allowed` condition is redundant**

`knowledge_readiness.py:103`:
```python
proceed_allowed = deep_research_uploaded and score > KNOWLEDGE_READINESS_THRESHOLD and not blocking_issues
```

`blocking_issues` already checks `deep_research_uploaded` and `score <= threshold`, so `proceed_allowed` is equivalent to `not blocking_issues`. The triple condition is not wrong but reads as if the three checks are independent.

**3. Error message in `require_knowledge_ready` is English-only**

`knowledge_readiness.py:146`:
```python
raise ValueError("Knowledge readiness score must be greater than 80 with an uploaded DeepResearch report before generating a draft.")
```

This surfaces as a 409 detail to the frontend. The entire UI is Chinese, but this error is English. Should match the Chinese blocking issues in `_blocking_issues`.

**4. `score > threshold` uses `>` but `blocking_issues` uses `<=`**

`knowledge_readiness.py:103`: `score > KNOWLEDGE_READINESS_THRESHOLD`
`knowledge_readiness.py:176`: `score <= KNOWLEDGE_READINESS_THRESHOLD`

A score of exactly 80 → `blocking_issues` has an issue, `proceed_allowed` is False. This is consistent but the UI says "需大于 80 分" while the backend code uses `> 80` — a score of 80.5 would pass the float comparison but 80 would not. Since scores are integers, this is fine, but the threshold boundary should be documented.

**5. No rate limiting on knowledge readiness runs**

Each `POST /knowledge-readiness` triggers 3 LLM calls. A user (or bot) can spam this endpoint. Same concern exists for deliberation, so this is a pre-existing pattern, not a regression.

---

## 2. PR #75 — Chair Revision Apply

### Summary

Adds an explicit API action to apply chair-approved official-text revisions from a completed post-draft review. Updates the draft package, then immediately recompiles the official package so hashes move forward.

| Metric | Value |
|--------|-------|
| Files changed | 7 |
| Lines added | 205 |
| Lines deleted | 0 |

### Test Results

| Suite | Result |
|-------|--------|
| `tests/test_post_draft_review.py` | ✅ 9 passed |
| `frontend/src/guidedFlow.test.ts` | ✅ 40 passed |

### Architecture

```
POST /api/projects/{id}/post-draft-reviews/{run_id}/apply-revisions
  → validate: completed, hash matches, has chair revisions
  → apply_chair_revisions_to_draft(package, run)
    → claim_1_rewrite → replace first claim
    → system_claim_rewrite → append system claim
    → abstract_rewrite → replace abstract
    → official_safe_patches → append to description
  → store.update_project_package()
  → OfficialDraftCompiler().compile()
  → return {package, official_compile_run, applied_revision_count, current_source_draft_hash}
```

### ✅ Strengths

1. **Hash guard prevents stale application.** `run.draft_package_hash != source_draft_hash(package)` ensures the review matches the current draft. No silent wrong-patch risk.
2. **Atomic update + recompile.** The package is updated and immediately recompiled, so `current_source_draft_hash` advances in one request. The test verifies the hash chain.
3. **`_append_once` prevents duplicate patches.** If the same text already exists in the target field, it's not appended again. Good idempotency.
4. **`_replace_first_claim` handles edge cases.** Uses regex to find claim 1 and claim 2 boundaries, handles missing claim 2 by replacing to end of string.
5. **UI is conditionally shown.** The "应用主席修订" button only appears when `blocked && hasChairRevision`. When there are no chair revisions, a hint message tells the user to handle it manually.

### 🟡 Issues

**6. `_replace_first_claim` regex doesn't handle all claim numbering formats**

`post_draft_review.py:221`:
```python
match = re.search(r"(?m)^\s*1[.、．]\s*", claims)
```

This matches `1.`, `1、`, `1．` but not `1)` or `(1)` or `Claim 1:`. If the LLM generates claims with different numbering, the replacement falls back to `_append_once` (appending instead of replacing). Not a bug per se — the fallback is safe — but the claim 1 rewrite would be lost as an append at the end.

**7. `description_rewrite_tasks` are logged but not applied**

`post_draft_review.py:207-210`:
```python
if chair.description_rewrite_tasks:
    logs.append(
        "post_draft_review: chair description tasks recorded for attorney follow-up: "
        + "；".join(chair.description_rewrite_tasks)
    )
```

These are tasks the chair wants an attorney to do manually, but they're only logged — not surfaced in the UI response. The frontend doesn't display them. An attorney reviewing the result would miss these follow-up items.

**Recommendation:** Include `description_rewrite_tasks` in the API response so the UI can display them as a checklist after applying revisions.

**8. No rollback if recompile fails**

`main.py:1196-1197`:
```python
store.update_project_package(project_id, revised_package)
compile_run = OfficialDraftCompiler().compile(project_id=project_id, package=revised_package)
```

If `compile()` throws, the package is already updated but no compile run is created. The project is in a half-updated state. Should either wrap in a try/rollback or update the package after compile succeeds.

---

## 3. Cross-PR Issues

### 🔴 Merge Conflict Risk

Both PRs modify the same 5 files from the same base commit (`87b7f54`):

| File | PR #74 changes | PR #75 changes |
|------|---------------|---------------|
| `backend/app/main.py` | +33 (knowledge readiness endpoints + gate) | +30 (apply-revisions endpoint) |
| `frontend/src/App.tsx` | +40 (state, handlers, props) | +22 (handleApplyChairRevision) |
| `frontend/src/GuidedPatentFlow.tsx` | +151 (KnowledgeReadinessPanel) | +30 (chair revision button) |
| `frontend/src/api.ts` | +46 (knowledge readiness types + functions) | +17 (applyPostDraftReviewRevisions) |
| `frontend/src/guidedFlow.ts` | +30 (knowledge step, busy labels) | +9 (chair-revision busy label) |

**These PRs will conflict on merge.** The second PR to merge will need manual conflict resolution.

**Recommendation:** Merge PR #74 first (larger, more structural), then rebase PR #75 on top. PR #75's changes are additive and localized.

### 9. PR #75's test depends on PR #74's `seed_knowledge_ready` (indirectly)

PR #75's `test_apply_chair_revision_updates_draft_and_recompiles_official_package` creates a project and runs generation, but doesn't call `seed_knowledge_ready`. This works because the test uses `_review_llm(export_allowed=False)` which sets up a post-draft review directly, bypassing the generate gate.

However, if PR #74 merges first and the test is rebased, the `generate` call in the test will hit the knowledge readiness gate and fail. The test will need `seed_knowledge_ready` added.

---

## 4. Risk Matrix

| # | Risk | PR | Severity | Likelihood |
|---|------|-----|----------|------------|
| 8 | Package updated before compile — no rollback on failure | #75 | 🟡 Important | Low |
| 7 | `description_rewrite_tasks` not surfaced to UI | #75 | 🟡 Important | Medium |
| 1 | DeepResearch detection is keyword-based, duplicated in frontend | #74 | 🟡 Important | Medium |
| 3 | English error message in Chinese UI | #74 | 🟢 Minor | Medium |
| — | Merge conflict on 5 shared files | Both | 🔴 Structural | Certain |
| 9 | PR #75 test will break after PR #74 merges | #75 | 🟡 Important | Certain |

---

## 5. Verdict

**PR #74** is well-structured. The knowledge readiness gate follows existing patterns (same as deliberation gate), the LLM scoring is reasonable, and test coverage is solid. The main concern is the fragile keyword-based DeepResearch detection — it works today but will silently break if users name files differently.

**PR #75** is clean and focused. The hash guard, atomic update+recompile, and conditional UI are all done correctly. The missing rollback on compile failure is the most important fix. `description_rewrite_tasks` should be surfaced in the response.

**Merge strategy:** Land PR #74 first, rebase PR #75, add `seed_knowledge_ready` to PR #75's test, then merge.
