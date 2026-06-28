# Task 1 Report: DeepResearch Markdown Parser

## What I implemented

- Added `backend/app/research/deep_research_intake.py` with deterministic Markdown-only DeepResearch intake.
- Implemented the required public functions:
  - `is_deep_research_markdown_material(file_name: str, text: str) -> bool`
  - `parse_deep_research_markdown(project_id: str, text: str, *, source_label: str = "") -> DeepResearchPacket`
  - `parse_deep_research_materials(materials: Iterable[ProjectMaterial]) -> list[DeepResearchPacket]`
  - `packet_prior_art_hits(packet: DeepResearchPacket) -> list[PriorArtHit]`
- Added `tests/test_deep_research_intake.py` covering:
  - markdown material detection
  - packet construction from a structured DeepResearch Markdown report
  - conversion into `PriorArtHit`
  - graceful handling of unrecognized Markdown
  - filtering of non-DeepResearch materials

## TDD evidence

### RED

Command:

```bash
pytest tests/test_deep_research_intake.py -v
```

Result:

```text
E   ModuleNotFoundError: No module named 'backend.app.research.deep_research_intake'
```

### GREEN

Command:

```bash
pytest tests/test_deep_research_intake.py -v
```

Result:

```text
5 passed in 0.13s
```

## Test commands and results

- `pytest tests/test_deep_research_intake.py -v` -> passed

## Files changed

- `backend/app/research/deep_research_intake.py`
- `tests/test_deep_research_intake.py`

## Self-review findings

- The parser stays deterministic and Markdown-only, with no Office conversion, external skill runtime, or workflow restructuring.
- Evidence hits are emitted with the stable source label `DeepResearch Markdown`, which matches the test expectations and keeps downstream `PriorArtHit` conversion predictable.
- Unrecognized Markdown returns a partial packet with a warning instead of throwing.

## Concerns

- The worktree already contains unrelated dirty files outside Task 1 ownership; I left them untouched.

## Commit

- `f82cbc49 feat: parse deepresearch markdown materials`

## Fix follow-up

- Made DeepResearch Markdown parsing deterministic by replacing random finding and fallback hit IDs with stable content-derived IDs.
- Propagated the provided `source_label` into evidence refs and ledger entries via a dedicated ledger `source_label` field, while keeping public `PriorArtHit.source` unchanged as `DeepResearch Markdown`.
- Added a regression test proving repeated parses of the same Markdown yield identical finding IDs, ledger entries, and prior-art hit IDs.

## Fix test output

Command:

```bash
pytest tests/test_deep_research_intake.py -v
```

Result:

```text
tests/test_deep_research_intake.py::test_is_deep_research_markdown_material_detects_markdown_report PASSED [ 16%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_builds_internal_packet PASSED [ 33%]
tests/test_deep_research_intake.py::test_packet_prior_art_hits_converts_ledger_entries PASSED [ 50%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_is_stable_across_repeated_runs PASSED [ 66%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_handles_unrecognized_markdown PASSED [ 83%]
tests/test_deep_research_intake.py::test_parse_deep_research_materials_filters_markdown_materials PASSED [100%]

6 passed in 0.13s
```

## Blocking fix follow-up

- Kept `DeepResearchEvidenceRef.source` on the stable public value `DeepResearch Markdown` so downstream code does not leak per-file labels into public `PriorArtHit.source`.
- Preserved the file provenance separately in `evidence_ledger[...]["source_label"]`.
- Updated the regression test to assert both the public evidence source and the ledger provenance label.

## Blocking fix test output

Command:

```bash
pytest tests/test_deep_research_intake.py -v
```

Result:

```text
tests/test_deep_research_intake.py::test_is_deep_research_markdown_material_detects_markdown_report PASSED [ 16%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_builds_internal_packet PASSED [ 33%]
tests/test_deep_research_intake.py::test_packet_prior_art_hits_converts_ledger_entries PASSED [ 50%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_is_stable_across_repeated_runs PASSED [ 66%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_handles_unrecognized_markdown PASSED [ 83%]
tests/test_deep_research_intake.py::test_parse_deep_research_materials_filters_markdown_materials PASSED [100%]

6 passed in 0.15s
```

## Deterministic ID fix follow-up

- Removed `project_id` and `source_label` from the stable finding ID inputs so the same Markdown content hashes to the same finding IDs across projects and renamed files.
- Switched evidence ledger IDs to content-derived hashes based on evidence identity/content instead of packet-local ordinals.
- Made `PriorArtHit.id` reuse the stable evidence ID, with a content-derived fallback that still ignores provenance labels.
- Added regression coverage for cross-project/file stability and for non-collision between distinct prior-art evidence.

## Deterministic ID fix test output

Command:

```bash
pytest tests/test_deep_research_intake.py -v
```

Result:

```text
tests/test_deep_research_intake.py::test_is_deep_research_markdown_material_detects_markdown_report PASSED [ 12%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_builds_internal_packet PASSED [ 25%]
tests/test_deep_research_intake.py::test_packet_prior_art_hits_converts_ledger_entries PASSED [ 37%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_is_stable_across_repeated_runs PASSED [ 50%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_keeps_ids_stable_across_project_and_file_changes PASSED [ 62%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_does_not_collide_on_distinct_evidence PASSED [ 75%]
tests/test_deep_research_intake.py::test_parse_deep_research_markdown_handles_unrecognized_markdown PASSED [ 87%]
tests/test_deep_research_intake.py::test_parse_deep_research_materials_filters_markdown_materials PASSED [100%]

8 passed in 0.13s
```
