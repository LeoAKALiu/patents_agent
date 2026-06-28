# Final Review Fix Report

## Session Identity
- Branch: `codex/automation-test-plan`
- HEAD at start: `9e8bfbea`
- Worktree: `/Users/leo/Projects/patents_agent`
- Dirty tree at start: yes; preserved unrelated pre-existing edits exactly as instructed

## Findings Addressed

### 1. DeepResearch Markdown no longer enters disclosure-generation prompts as raw body text
- Excluded processed DeepResearch markdown materials from the raw `material_context` block in [`backend/app/disclosure/generator.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/generator.py).
- Kept structured DeepResearch prompt context injection so prior-art hits, differentiators, claim constraints, and completion tasks still reach the prompt.
- Preserved non-DeepResearch processed materials in the raw material block.
- Preserved failed/unprocessed material warning behavior in `_format_materials(...)`.
- Added regression coverage proving the disclosure body prompt still contains structured DeepResearch substance while excluding raw markdown markers and internal-only fields.

### 2. `/score-improvement` now records completion-patch revision ledger entries
- Added completion-patch ledger recording in [`backend/app/main.py`](/Users/leo/Projects/patents_agent/backend/app/main.py) when `/score-improvement` mutates the package.
- Recorded:
  - `revision_kind="completion_patch"`
  - `affected_sections=_completion_patch_affected_sections(patch)`
  - `protection_scope_changed=patch.target_section == "claim"`
  - `artifact_refs=[f"completion-run:{current_run.id}", f"completion-patch:{patch.id}"]`
- Added API regression coverage proving score-improvement creates a completion-patch ledger row.

### 3. Prior-art dedupe now catches overlapping identifiers
- Updated [`backend/app/disclosure/prior_art.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/prior_art.py) to track normalized publication numbers, URLs, and titles independently.
- A hit is now treated as duplicate when any non-empty identifier was already seen.
- Existing order is preserved and the first hit wins.
- Added regression coverage for the publication+URL vs URL-only overlap case.

### 4. Clean disclosure prior-art appendix now appends only missing public URLs
- Updated [`backend/app/disclosure/exporter.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/exporter.py) so clean disclosure exports:
  - append only prior-art URLs not already present in the disclosure body
  - skip prior-art entries without a public URL
- Applied the same logic to DOCX export appendix handling.
- Added focused exporter regression coverage.

## Files Changed
- [`backend/app/disclosure/generator.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/generator.py)
- [`backend/app/disclosure/prior_art.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/prior_art.py)
- [`backend/app/disclosure/exporter.py`](/Users/leo/Projects/patents_agent/backend/app/disclosure/exporter.py)
- [`backend/app/main.py`](/Users/leo/Projects/patents_agent/backend/app/main.py)
- [`tests/test_deep_research_intake_integration.py`](/Users/leo/Projects/patents_agent/tests/test_deep_research_intake_integration.py)
- [`tests/test_disclosure_prior_art.py`](/Users/leo/Projects/patents_agent/tests/test_disclosure_prior_art.py)
- [`tests/test_disclosure_exporter.py`](/Users/leo/Projects/patents_agent/tests/test_disclosure_exporter.py)
- [`tests/test_draft_completion_api.py`](/Users/leo/Projects/patents_agent/tests/test_draft_completion_api.py)

## Tests Run
- `pytest tests/test_deep_research_intake_integration.py tests/test_disclosure_prior_art.py tests/test_disclosure_exporter.py tests/test_revision_ledger_api.py tests/test_draft_completion_api.py -v`
- Result: `29 passed`

## Concerns
- Test run emitted existing `chromadb` deprecation warnings from the environment (`_ChromaHashEmbedding` legacy config), but no functional failures.
