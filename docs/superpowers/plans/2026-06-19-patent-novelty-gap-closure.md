# Patent Novelty Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the product-level prior-art novelty workflow gaps found in review.

**Architecture:** Add a persisted grantability report API that consumes completed drafts, disclosures, patent points, deliberation strategy, and deep-research packets. Harden prior-art evidence handling in the disclosure and deep-research paths while keeping official export boundaries unchanged.

**Tech Stack:** FastAPI, Pydantic, SQLite storage, pytest, React/TypeScript API client.

---

### Task 1: Grantability Report API

**Files:**
- Modify: `backend/app/storage.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/api.ts`
- Test: `tests/test_grantability.py`
- Test: `tests/test_api.py`

- [x] **Step 1: Write failing tests**
  - Add storage tests that create/list/get `GrantabilityReport`.
  - Add API tests for `POST /api/projects/{project_id}/grantability-reports`, `GET /api/projects/{project_id}/grantability-reports`, and report markdown export.
  - Add a unit test proving deep-research packets are extracted from disclosure `stage_results`.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_grantability.py::test_grantability_reports_persist_in_store tests/test_api.py::test_grantability_report_api_generates_persists_and_exports -q
```

Expected: fail because storage methods and API routes do not exist.

- [x] **Step 3: Implement storage/API**
  - Add `grantability_reports` table.
  - Add `create_grantability_report`, `list_grantability_reports`, `get_grantability_report`.
  - Add API routes using `generate_grantability_report` and `grantability_report_to_markdown`.
  - Add frontend `GrantabilityReport` types and API helpers.

- [x] **Step 4: Run tests to verify pass**

Run:

```bash
python3 -m pytest tests/test_grantability.py tests/test_api.py -q
```

### Task 2: Evidence-Grounded Standard Prior-Art Relevance

**Files:**
- Modify: `backend/app/disclosure/generator.py`
- Test: `tests/test_patent_points.py`

- [x] **Step 1: Write failing test**
  - Add a test where the relevance LLM returns differentiators but no valid claim-chart rows.
  - Assert the final package does not present unbound differentiators as verified differences and emits a manual-review warning.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_patent_points.py::test_disclosure_relevance_without_bound_claim_chart_is_marked_unverified -q
```

- [x] **Step 3: Implement minimal guard**
  - Track accepted claim-chart rows.
  - If there are hits but no accepted claim-chart rows, strip LLM differentiators and replace the overall difference paragraph with an explicit unverified/manual-review message.

- [x] **Step 4: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_patent_points.py tests/test_disclosure.py -q
```

### Task 3: Structured Metadata Into Research Prompts

**Files:**
- Modify: `backend/app/disclosure/generator.py`
- Modify: `backend/app/research/deep_researcher.py`
- Test: `tests/test_disclosure.py`
- Test: `tests/test_deep_research.py`

- [x] **Step 1: Write failing tests**
  - Assert disclosure scan / terms prompts include project `technical_field`, `background`, `pain_point`, `technical_solution`, `innovation`, `embodiments`, and `beneficial_effects` when present.
  - Assert deep-research planning prompt includes the same technical metadata.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_disclosure.py::test_disclosure_research_prompts_include_structured_project_metadata tests/test_deep_research.py::test_deep_research_plan_prompt_includes_project_metadata -q
```

- [x] **Step 3: Implement metadata prompt helper**
  - Add a helper that formats non-empty technical metadata.
  - Include it in scan, terms, and deep-research plan prompts.

- [x] **Step 4: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_disclosure.py tests/test_deep_research.py -q
```

### Task 4: Research Confidence and Empty-Result Retry

**Files:**
- Modify: `backend/app/research/ledger.py`
- Modify: `backend/app/research/deep_researcher.py`
- Test: `tests/test_research_ledger.py`
- Test: `tests/test_deep_research.py`

- [x] **Step 1: Write failing tests**
  - Assert confidence counts unique citations, not duplicate retained counts.
  - Assert a first-cycle no-hit search broadens queries and performs one retry before returning partial.

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_research_ledger.py::test_research_confidence_uses_unique_citations tests/test_deep_research.py::test_deep_research_broadens_queries_after_empty_cycle -q
```

- [x] **Step 3: Implement minimal behavior**
  - Compute unique citation keys in `SourceLedger`.
  - Add one empty-result retry using query tokens and project title before stopping.

- [x] **Step 4: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_research_ledger.py tests/test_deep_research.py -q
```

### Task 5: Final Verification and PR

- [x] Run backend targeted suite:

```bash
python3 -m pytest tests/test_deep_research.py tests/test_research_providers.py tests/test_research_evidence.py tests/test_research_ledger.py tests/test_grantability.py tests/test_disclosure.py tests/test_patent_points.py tests/test_api.py -q
```

- [x] Run frontend targeted tests if affected:

```bash
npm --prefix frontend test -- --run
```

- [x] Commit all changes and create PR with summary and test plan.
