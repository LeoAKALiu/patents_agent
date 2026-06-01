# v0.3 Filing Readiness + Claim Defense Foundation

## Purpose

`patentAgent` v0.3 should move from a patent text generator toward a filing-readiness and claim-defense workbench. The goal is not to automatically replace a patent attorney. The goal is to make generated outputs safer to hand off, and to expose the technical defense structure behind the claims before a user treats a draft as filing material.

This version uses a dual-core narrow scope:

1. Clean Filing Gate: detect filing-readiness risks and keep official exports clean.
2. Claim Defense Worksheet: persist a human-in-loop feature and defense worksheet for each project.

The current facade reverse-modeling case remains a manual validation sample, not an automated benchmark or hard-coded test fixture.

## Product Decisions

- Clean Filing Gate uses warning mode, not hard blocking.
- Official filing exports are always allowed, even when readiness status is `high_risk`.
- Official filing exports must not include readiness warnings, internal traces, strategy text, claim charts, generation logs, prompts, or debug material in the filing body.
- All warnings, matched text, and revision suggestions go into a sidecar `FILING_READINESS_REPORT.md`.
- Claim Defense v0.3 produces a human-in-loop worksheet. It does not overwrite final claims.
- Claim Defense worksheets are persisted per project.
- Worksheet history is lightweight multi-version. The UI shows latest worksheet and a history list, but v0.3 does not implement diffing.
- Worksheet manual editing is deferred to v0.4.

## Explicit Non-Goals

v0.3 does not implement:

- Automatic final claim rewriting.
- Manual worksheet editing.
- OA response simulation.
- FTO analysis.
- Full patent-family or divisional-case planning.
- Formal patent figure rendering.
- A hard-coded automated benchmark for the facade reverse-modeling case.

## Clean Filing Gate

### Inputs

Clean Filing Gate scans the current `DraftPackage`, including:

- `abstract`
- `claims`
- `description`
- `drawing_description`
- `mermaid`
- `image_prompt`
- `generation_logs`
- `strategy_brief`
- `disclosure_summary`
- `patent_point_summary`

### Filing Readiness Report Model

Create a persisted `FilingReadinessReport` object:

- `id`
- `project_id`
- `draft_package_hash` or equivalent package snapshot identifier
- `status`: `clean | warning | high_risk`
- `created_at`
- `rules_version`
- `issues`

Each issue contains:

- `category`: `format_pollution | internal_trace | unfavorable_statement | unverified_effect | subject_matter_risk | support_gap`
- `severity`: `low | medium | high`
- `target`: `claims | description | abstract | drawings | export`
- `matched_text`
- `message`
- `suggestion`
- `can_auto_clean`

### Rule Groups

#### Format Pollution

Detect:

- Markdown headings such as `#` and `##`.
- Code fences.
- Mermaid markers such as `flowchart`, `graph TD`, and `sequenceDiagram`.
- Field-name residues such as `claims`, `description`, `abstract`, `drawings`, `diagram`, and `image_prompt`.

#### Internal Process Traces

Detect:

- `多Agent会审`
- `deliberation`
- `generation_logs`
- `根据技术交底书`
- `根据会审策略`
- `主席汇总失败`
- `prompt`

#### Unfavorable Statements

Detect statements that should not appear in an official filing body, including:

- `可能不具备创造性`
- `容易被现有技术组合`
- `尚未验证`
- `存在充分公开风险`
- `禁止直接提交`

These may appear in internal reports, but not in official filing text.

#### Unverified Quantitative Effects

Detect quantitative effect claims such as:

- `提升\d+%`
- `降低\d+%`
- `提高\d+%`

If the project lacks verified evidence or the referenced patent point evidence status is not `verified`, mark the issue as warning or high risk.

#### Subject-Matter Risk Phrases

Detect weak technical-field or business-rule phrasing such as:

- `人工智能软件方法领域`
- `智能管理方法`
- `造价规则`

Suggest more technical phrasing such as:

`建筑信息模型、三维点云处理、计算机视觉与计算机辅助工程量计算技术领域`

### Export Behavior

Add export kinds:

- `official`: official filing draft containing only abstract, claims, description, and drawing description.
- `internal`: internal strategy draft retaining claim chart, moat scoring, deliberation, prior-art analysis, and risk material.
- `readiness`: `FILING_READINESS_REPORT.md`.

Because v0.3 uses warning mode:

- `official` export is allowed for all readiness statuses.
- UI shows readiness status near export controls.
- `high_risk` shows a red warning but does not disable export.
- Official export body remains clean. It does not include the warning report.

## Claim Defense Worksheet

### Worksheet Model

Create a persisted `ClaimDefenseWorksheet` object:

- `id`
- `project_id`
- `status`: `draft | reviewed | superseded`
- `source`: `draft | disclosure | generated_package | manual`
- `created_at`
- `feature_records`
- `defense_recommendations`
- `support_gaps`
- `notes`

Each feature record contains:

- `feature_id`
- `text`
- `classification`: `known_base | differentiator | core_combo | dependent_fallback | support_needed`
- `claim_refs`
- `description_refs`
- `figure_refs`
- `prior_art_refs`
- `risk_tags`

### Inputs

Use these sources in priority order:

1. Existing `DraftPackage.claims` and `DraftPackage.description`.
2. Completed `DisclosurePackage.candidates`.
3. Saved `PatentPointCandidate` records.
4. Project `draft_text`.

### Generation Flow

Use a rules-first, LLM-assisted flow:

1. Rule parser extracts claim numbering, dependent-claim relationships, and candidate feature spans.
2. LLM extracts structured feature records from natural language.
3. Pydantic validation checks LLM output.
4. If validation fails, fall back to rule-extracted feature records and record a warning in the worksheet.

### Classification Strategy

Classify each feature as one of:

- `known_base`: known base features such as ordinary data acquisition or generic image processing.
- `differentiator`: a single feature that appears different from known prior art.
- `core_combo`: features that should be asserted as a combined defense rather than isolated novelty points.
- `dependent_fallback`: features suitable for dependent claims or fallback narrowing.
- `support_needed`: features that the user wants to assert but that lack adequate description, embodiment, figure, formula, data structure, or evidence support.

Classification considers:

- Whether the feature appears in selected patent points.
- Whether the feature appears in prior-art claim chart differentiators.
- Whether the feature has description, figure, embodiment, formula, or data-structure support.
- Whether it is likely covered by one or more prior-art references.
- Whether it is unverified.

### Recommendations

The worksheet outputs three groups:

1. Independent claim defense recommendations:
   - Which features should be combined in the independent claim.
   - Which single features are too weak to carry inventiveness alone.
   - Suggested `其特征在于` focus points.
   - Optional independent-claim skeletons for human review.

2. Dependent claim layout recommendations:
   - Which features should narrow in layers.
   - Which features map naturally to method, system, device, and medium claims.
   - Which features look like future divisional leads, without doing portfolio planning in v0.3.

3. Specification support gaps:
   - Missing formulas.
   - Missing data structures.
   - Missing pseudo-code or pseudo-IFC snippets.
   - Missing end-to-end embodiment.
   - Missing figure references.
   - Missing verification evidence.

## API Design

Add endpoints:

- `POST /api/projects/{project_id}/filing-readiness`
- `GET /api/projects/{project_id}/filing-readiness`
- `GET /api/projects/{project_id}/filing-readiness/{report_id}/export.md`
- `POST /api/projects/{project_id}/claim-defense-worksheets`
- `GET /api/projects/{project_id}/claim-defense-worksheets`
- `GET /api/projects/{project_id}/claim-defense-worksheets/{worksheet_id}`

v0.3 does not need PATCH endpoints for manual worksheet editing. Reserve status fields for later review and edit workflows.

## Frontend Design

Add two workbench entries between `分步撰写` and `导出`:

1. `提交成熟度`
2. `权利要求防线`

### Filing Readiness View

Shows:

- Latest status: `clean | warning | high_risk`.
- Issue list with category, severity, target section, matched text, and suggestion.
- Export actions for:
  - official filing draft
  - internal strategy draft
  - `FILING_READINESS_REPORT.md`

When status is `high_risk`, show a red warning but keep export enabled.

### Claim Defense View

Shows:

- Latest worksheet summary.
- Feature records table.
- Classification badges:
  - 已知基础
  - 区别特征
  - 核心组合
  - 从属兜底
  - 需支撑
- Independent claim defense recommendations.
- Dependent claim layout recommendations.
- Specification support gaps.
- Worksheet history list.

v0.3 is read-only except for generating a new worksheet.

## Testing And Verification

### Backend Tests

Cover:

- Clean Gate detects Markdown, Mermaid, prompt residue, generation logs, and internal strategy phrasing.
- Clean Gate detects unfavorable statements.
- Clean Gate detects unverified quantitative effects.
- Clean Gate reports subject-matter risk phrases.
- Official export does not include warnings, Mermaid, prompts, logs, or strategy material.
- `FILING_READINESS_REPORT.md` includes matched issues and suggestions.
- `warning` and `high_risk` statuses still allow official export.
- Claim Defense Worksheet persists multiple versions per project.
- Worksheet generation uses claims, disclosures, and saved patent points.
- Invalid LLM worksheet output falls back to rule extraction.
- API list/detail/export endpoints behave correctly.

### Frontend Tests

Cover:

- New tab order.
- Readiness status rendering.
- `high_risk` warning with enabled official export action.
- Worksheet latest-version rendering.
- Worksheet history list rendering.
- Empty states for both views.

### Full Verification

Run:

```bash
python3 -m pytest -q
cd frontend && npm test -- --run && npm run build
```

Browser smoke:

1. Create a project.
2. Generate or inject a package containing internal traces.
3. Run Clean Gate.
4. Export official draft and readiness report.
5. Confirm official draft omits Mermaid, prompt, logs, and internal strategy text.
6. Confirm readiness report contains matched issues.
7. Generate Claim Defense Worksheet.
8. Confirm latest worksheet and history list render.

## Future Extensions

v0.4 candidates:

- Manual worksheet editing.
- Support Builder using worksheet feature records.
- Figure Planner using worksheet feature records.
- Deeper Risk Judge scoring.
- Claim amendment suggestions.
- OA response simulation.
- Patent-family planning.

## Self-Review Notes

- No hard-coded facade reverse-modeling benchmark is included.
- Clean Gate warning mode is explicit and does not block official export.
- Official filing exports are separated from readiness reports and internal strategy exports.
- Claim Defense remains human-in-loop and does not overwrite claims.
- Worksheet persistence and lightweight history are in scope.
- Manual editing, OA, FTO, portfolio planning, and formal figures are out of scope.
