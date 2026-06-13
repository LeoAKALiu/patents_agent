# Changelog

## v1.1.0 — In Development

### Added

- **Desktop startup diagnostics**: Electron now records structured boot stages, backend health, renderer load state, failed subresources, and renderer crashes; users can inspect the report from `帮助 → 诊断信息` (PR6, issue #38).
- **Desktop blank-page guard**: packaged startup now shows a diagnostic page when `frontend/dist/index.html` is missing instead of leaving a blank renderer window (PR6, issue #38).
- **Desktop production-renderer smoke**: `npm --prefix desktop run smoke` probes the built frontend assets when `frontend/dist/index.html` exists, verifies the diagnostics preload bridge, and fails on renderer asset/crash regressions. Set `PATENTAGENT_SMOKE_SKIP_FRONTEND=1` to skip the production renderer probe intentionally (PR6, issue #38).
- **Release handoff checklist**: v1.1.0 now has a human release-manager handoff covering issue/task mapping, dependency graph, packaging proof, checksums, and human-only tag/release boundaries (PR8, issue #37).

## v1.0.0 — Electron Desktop Release

### Added

- **Electron desktop app**: standalone desktop runtime with BrowserWindow, typed preload, native menus, and headless smoke test (PR4, issue #18).
- **Backend supervision**: Electron main process spawns, health-checks, and lifecycle-manages the local FastAPI backend; renderer `/api/*` requests proxy to the supervised backend (PR5, issue #19).
- **Desktop settings & secret handling**: Electron settings window for Python path, backend port, data directory, and model provider configuration; secrets never written to Vite/React state (PR6, issue #20).
- **File import/export UX**: hardened desktop file dialogs with format detection, encoding safety, and atomic overwrite on export (PR7, issue #21).
- **Utility model lite**: promoted to first-class, type-aware patent type with independent workflow entry, fixed patent-type routing, and structured export (PR3, issue #17).
- **External draft intake salvage**: external Markdown/DOCX drafts are sealed read-only on import with content hash; mismatch on re-import triggers salvage not overwrite (PR2, issue #16).
- **v1 product polish & guided UX**: guided patent flow with five-step wizard (idea → invention point → draft → quality check → export), Liquid Glass visual system, PatentAgent logo/favicon, simplified three-section navigation, and expert tools grouped behind a clean entry panel (PR8, issue #22).
- **Release test harness**: `scripts/v1_smoke.sh` single-command release gate running pytest, API smoke on golden samples, frontend tests, frontend build, and Electron build; golden samples in `samples/` (PR9, issue #23).
- **v1 agent bootstrap**: idempotent pipeline helper creating GitHub labels, Hermes profile shells, and Kanban board for autonomous agent release automation (PR1, issue #14).
- **Baseline infrastructure**: explicit setuptools package discovery in `pyproject.toml`, editable install CI fix, clean worktree baseline (PR0, issue #13).

### Changed

- Version bumped from `0.6.0` to `1.0.0` across `pyproject.toml`, `frontend/package.json`, and `desktop/package.json`.
- README repositioned as v1.0.0 desktop app with non-developer install/run docs and known limitations section.
- Branding: "专利写作 Agent" → "PatentAgent" with independent logo and visual identity.

### Verified

- Backend: `231 passed, 1 skipped` (v1.0.0 baseline).
- Frontend: `58 passed` (Vitest), production build passes.
- Desktop: compiled Electron main/preload bundle builds successfully; launch smoke is environment-gated and records a skip reason when the Electron binary is unavailable.
- `scripts/v1_smoke.sh` passes as release gate.

### Fixed

- Restricted local FastAPI CORS to Electron/file renderer and Vite dev origins, with a separate Origin guard on `/api/desktop-config*` so arbitrary browser pages cannot read or mutate local LLM configuration.
- Added desktop build/smoke coverage to CI so Electron main/preload TypeScript and the desktop smoke entry are no longer only checked locally.
- Aligned frontend and desktop package-lock root versions with `1.0.0`.
- Clean up partial export files when desktop official export streaming fails or returns an empty body.

### Known Limitations

- Backend supervision relies on user's local Python runtime; standalone packaged backend is deferred.
- Linux requires `xvfb-run` for headless Electron smoke; macOS runs natively.
- Model API keys must be configured via `PATENTAGENT_*` env vars or desktop settings; no cloud key distribution.
- Signed/notarized DMG packaging and Electron auto-update are not yet configured.

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
