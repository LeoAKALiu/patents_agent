---
status: implemented
owner: frontend
created: 2026-06-18
source: OpenDesign project GetYourPatentsDown / index.html
supersedes_visual_direction: docs/ui-redesign/01-UI-SPEC.md aesthetic section
---

# OpenDesign Refero-Style Implementation Kanban

This plan translates the latest OpenDesign artifact into small, reviewable PRs.
The new visual direction is the Refero/Zapier-style enterprise settings
workspace: flat, light-first, clear side navigation, large page titles,
grouped settings sections, and horizontal action cards.

## Source of Truth

- OpenDesign project: `GetYourPatentsDown`
- Active entry: `app-new.html`, redirecting to `index.html`
- Design files reviewed: `index.html`, `projects.html`, `expert-tools.html`,
  `workflow-quality.html`, `workflow-export.html`, `external-import.html`,
  `external-export.html`, `shared.css`
- Existing app target: React + Vite + Tauri frontend under `frontend/src`

## Direction Change

The older redesign contract emphasized glassmorphism. The current OpenDesign
artifact uses a flatter enterprise-control-panel language. Implementation
should keep the existing PatentAgent palette and tokens, but reduce the visible
glass treatment on primary working surfaces.

Keep:
- Current PatentAgent colors, logo/brand mark, semantic status colors, and
  Chinese product copy.
- Existing feature architecture and workflow gates.
- Lucide-style line icons.

Adopt:
- Fixed left sidebar with icon + label navigation and pale active row.
- Topbar with page title/subtitle on the left and compact controls on the right.
- Status strip of dense summary tiles.
- `settings-group` sections with headers and `info-card` rows:
  icon, title/body, right-side badge/button/action.
- Thin borders, 8px radius, restrained shadow, high scanability.
- Mobile: bottom nav, card-list replacement for dense tables, sticky action dock.

Avoid:
- Marketing-style hero layouts.
- Decorative illustrations or gradient/orb backgrounds.
- Heavy nested cards or excessive blur.
- Copying Zapier orange/purple or source product labels.

## PR Slicing

### PR-0: Shell and Shared Enterprise Surface System

Goal: establish the flat shell primitives used by all later PRs.

Owned files:
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/base.css`
- `frontend/src/styles.css`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- Optional new primitives under `frontend/src/ui/`

Tasks:
- Tune tokens/surfaces away from heavy glass while preserving PatentAgent brand
  colors.
- Add reusable layout classes or components for `status-strip`, `status-tile`,
  `settings-group`, `section-head`, `info-card`, `boundary-card`, and
  `action-dock`.
- Align sidebar/topbar with OpenDesign structure and current app navigation.
- Keep existing tests/build green.

Acceptance:
- Shell visually resembles OpenDesign latest layout language.
- No functionality changes.
- `npm run build` passes.

### PR-1: Start and Guided Flow First Mile

Goal: implement the latest `index.html` direction for the default start path.

Owned files:
- `frontend/src/views/projectViews.tsx`
- `frontend/src/GuidedPatentFlow.tsx`
- `frontend/src/flow/panels/IdeaIntakePanel.tsx`
- `frontend/src/flow/panels/ExternalDraftIntakePanel.tsx`
- `frontend/src/flow/panels/MaterialSummary.tsx`
- Related guided-flow tests only when needed.

Tasks:
- Convert the start screen and project setup into grouped `info-card` rows.
- Add status-strip summary for entry mode, goal mode, parsing queue, next step.
- Make goal modes read like OpenDesign's settings cards with action buttons.
- Keep the three default entry routes and all existing business behavior.
- Preserve material upload and external draft intake behavior.

Acceptance:
- Default landing experience is the actual usable workflow, not a marketing page.
- Current workflow actions still create projects and continue to the next step.
- Mobile layout has no horizontal overflow.

### PR-2: Projects and Expert Tools

Goal: bring project management and expert-tool entry points into the new
settings/workbench pattern.

Owned files:
- `frontend/src/views/projectViews.tsx`
- `frontend/src/views/expertViews.tsx`
- `frontend/src/guidedFlow.ts` only if labels/grouping need small alignment
- Related tests only when needed.

Tasks:
- Convert `ProjectsOverview` from glass card grid to OpenDesign-style desktop
  table plus mobile project cards.
- Add summary status strip and quick filters where supported by existing state.
- Convert `ExpertToolChooser` to grouped `settings-group` sections:
  knowledge base, invention, review/strategy, quality, export.
- Keep expert tools secondary; do not interrupt default path.

Acceptance:
- Project list is scan-friendly on desktop and card-based on mobile.
- Expert tools show grouped rows with clear right-side status/action.
- No backend/API contract changes.

### PR-3: Quality Gate Pages

Goal: implement OpenDesign's quality-check rhythm for filing readiness,
claim defense, draft completion, and review surfaces.

Owned files:
- `frontend/src/views/qualityViews.tsx`
- `frontend/src/views/filingViews.tsx`
- `frontend/src/flow/panels/QualityPanel.tsx`
- `frontend/src/ui/RiskBanner.tsx`
- Related tests only when needed.

Tasks:
- Show quality status through status tiles, boundary cards, and issue rows.
- Visually distinguish "allowed with risk" from "formal export blocked."
- Convert score cards and issue lists into `info-card` rows.
- Keep patch accept/reject and report download behavior unchanged.

Acceptance:
- High-risk-but-allowed and blocking states cannot be confused.
- Scores, risk tags, patch actions, and report links remain functional.
- No success text uses low-contrast bright green.

### PR-4: Export and Official Boundary

Goal: implement OpenDesign's export confirmation model.

Owned files:
- `frontend/src/views/exportView.tsx`
- `frontend/src/flow/panels/ExportConfirmationPanel.tsx`
- `frontend/src/flow/panels/OfficialCompilePanel.tsx`
- `frontend/src/flow/panels/PostDraftReviewPanel.tsx`
- `frontend/src/lib/officialContamination.ts` only if UI labels need tests

Tasks:
- Split official draft, internal strategy draft, reports, hashes, and risk
  confirmation into separate visual containers.
- Keep official contamination warning prominent.
- Add confirmation affordance for high-risk official export.
- Preserve native export, download URLs, hash matching, and desktop folder open.

Acceptance:
- Official vs internal material boundaries are visually obvious.
- Export buttons obey existing `officialAllowed` and `enabled` gates.
- Existing official contamination tests still pass.

### PR-5: Cleanup, Visual QA, and Legacy CSS Reduction

Goal: finish consistency after the feature PRs land.

Owned files:
- `frontend/src/styles.css`
- `frontend/src/styles/*.css`
- Cross-cutting test updates
- Screenshots under `docs/ui-redesign/screenshots/`

Tasks:
- Remove unused legacy classes after PR-1 through PR-4.
- Run desktop and mobile screenshots.
- Fix overflow, spacing, tap target, and contrast regressions.
- Update `docs/ui-redesign/01-UI-SPEC.md` or add a short amendment that the
  latest OpenDesign direction replaces the prior glass-heavy aesthetic.

Acceptance:
- `npm run build` passes.
- Relevant frontend tests pass.
- Desktop and mobile screenshots show no overlap or horizontal overflow.
- Kanban below has all implementation cards closed.

## Kanban

### Backlog

| ID | Card | PR | Owner | Notes |
|---|---|---|---|---|
| - | - | - | - | - |

### Ready

| ID | Card | Dependencies | Review Focus |
|---|---|---|---|
| - | - | - | - |

### In Progress

| ID | Card | Owner | Branch/Thread | Status |
|---|---|---|---|---|
| - | - | - | - | - |

### Review

| ID | Card | Reviewer | Checklist |
|---|---|---|---|
| - | - | - | - |

### Done

| ID | Card | Owner | Evidence |
|---|---|---|---|
| OD-01 | Flatten surface tokens while preserving palette | kimiworker + Codex review | Build/test green; warn text tokenized |
| OD-02 | Add shared enterprise row/card primitives | kimiworker + Codex review | `status-strip`, `settings-group`, `info-card`, `boundary-card`, `action-dock` added |
| OD-03 | Align shell sidebar/topbar | kimiworker + Codex review | Topbar now handles main, expert, and utility sections |
| OD-04 | Convert start/project setup first mile | kimiworker + Codex review | Start choices, CreateProjectView, and corpus utilities use enterprise rows/cards |
| OD-05 | Convert guided material/external intake panels | kimiworker + Codex review | Idea intake, external draft intake, and material summary use status strips and action docks |
| OD-06 | Convert projects overview desktop/mobile | deepseekworker + Codex review | Build/test green; desktop table and mobile cards render without overflow |
| OD-07 | Convert expert tool chooser groups | deepseekworker + Codex review | Build/test green; grouped tool rows render after selecting a start path |
| OD-08 | Convert quality/check pages | deepseekworker + Codex review | Quality, filing, claim defense, review, and risk banner moved to dense enterprise surfaces |
| OD-09 | Convert export/official boundary pages | Codex | Export, official compile, and post-draft review split official/internal/report boundaries |
| OD-10 | Cleanup legacy CSS and screenshot QA | Codex | Full build/test green; Playwright desktop/mobile no horizontal overflow on start/projects |

## Review Checklist

Use this for every worker PR:

- No unrelated file rewrites or user-change reverts.
- Existing Chinese business copy and workflow gates preserved.
- Shared components use PatentAgent tokens, not hard-coded Refero/Zapier colors.
- No marketing hero as first screen.
- Cards are not nested inside larger decorative cards.
- Buttons and links maintain accessible names.
- Mobile has no horizontal overflow.
- `npm run build` passes; targeted tests pass when touched logic has coverage.
