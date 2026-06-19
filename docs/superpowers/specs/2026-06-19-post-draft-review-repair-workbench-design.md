# Post-Draft Review Repair Workbench Design

## Goal

Improve the post-draft review repair experience without waiting for the larger Word-like editor: long blocker lists should scroll independently, the current internal draft should open in a larger editor surface, and each blocker should expose manual and AI repair affordances.

## Scope

- Add an independent half-width scroll area for post-draft blocking issues and contamination hits.
- Add a larger draft editor dialog launched from the post-draft review panel.
- Allow manual edits to the five user-facing draft package fields: title, abstract, claims, description, and drawing description.
- Keep existing safe-patch behavior as the current one-click AI repair path.
- Show per-issue buttons for manual repair and one-click AI repair, with AI repair disabled unless safe patches are available.

## Architecture

The panel remains in `frontend/src/flow/panels/PostDraftReviewPanel.tsx`. It receives the current `DraftPackage` and a save callback from `GuidedPatentFlowView` and `App`. A narrow backend endpoint saves manual draft package edits by merging the five edited fields into the existing package, preserving internal metadata such as logs, citations, and formula references.

## Non-Goals

- No inline rich text annotations inside textarea content yet.
- No automatic semantic location matching beyond issue text and section hints.
- No new AI patch generation flow; the existing post-draft safe patch API remains the one-click AI path for this increment.

## Success Criteria

- Long blocker lists no longer force the entire right-side draft surface out of view.
- Users can open a large draft editor from the post-draft review panel and save manual edits.
- Blocker cards consistently show `人工修正` and `一键AI修正`.
- Manual draft edits invalidate prior official compile and post-draft review through the existing draft hash gate.
