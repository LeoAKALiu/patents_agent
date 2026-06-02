# Changelog

## v0.6.0 - Guided Patent Flow

### Added

- Five-step guided patent generation flow: idea, invention point, draft, quality check, export.
- Patent goal modes: authorization stability, protection scope, fast draft, patent moat.
- Expert tools grouped behind a simplified three-section navigation.
- Guided quality orchestration across review, filing readiness, claim defense, and draft completion.
- Liquid Glass inspired frontend visual system.
- PatentAgent logo and favicon SVG assets.
- Formal README for public repository and future cloud deployment.

### Changed

- Default landing state now starts from a new idea instead of automatically selecting historical projects.
- Official filing export remains warning-mode: high risk warns but does not hard-block export.
- App branding changed from "专利写作 Agent" to "PatentAgent".

### Verified

- Backend tests: `79 passed, 1 skipped`.
- Frontend tests: `18 passed`.
- Frontend production build passed.
- Chrome smoke test passed for guided flow creation and expert-tool reachability.
