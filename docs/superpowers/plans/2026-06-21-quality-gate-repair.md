# Quality Gate Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement the assigned slice. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the closed-loop defects found by the 2026-06-21 high-intensity QA pass before sustained production use: Tauri packaging must build from the same Python interpreter that passed preflight, existing project selection must reopen the real guided workbench instead of a blank intake, and project-list export status must not imply a legally gated official export is available.

**Source Identity:** Worktree `/Users/leo/Projects/patents_agent`, branch `main`, short SHA `37b883af`, dirty tree contains only pre-existing untracked `reasonix.toml`.

**Architecture:** Keep repairs narrowly scoped. Introduce a shared sidecar-build script used by Tauri and smoke/package scripts; add a single project-selection handler in `App.tsx` so all selection paths reset start-choice state and navigate to the guided workbench; make project-list export status conservative unless the UI has explicit gate evidence. Add regression tests for each issue.

**Tech Stack:** FastAPI/Pytest, React 19, Vite/Vitest, Tauri v2/Cargo, PyInstaller.

---

### PR 1: Tauri Packaging Sidecar Reliability

**Worker ownership:** Packaging scripts and Tauri packaging tests only.

**Files:**
- Create: `scripts/build_backend_sidecar.sh`
- Modify: `src-tauri/tauri.conf.json`
- Modify: `scripts/v1_smoke.sh`
- Modify: `scripts/package_dmg.sh`
- Modify: `tests/test_tauri_desktop_skeleton.py`

- [ ] Add `scripts/build_backend_sidecar.sh` that chooses `PYTHON="${PYTHON:-$(command -v python3)}"`, sets `PYINSTALLER_CONFIG_DIR=build/pyinstaller-cache`, verifies `python -m PyInstaller --version`, removes backend `__pycache__`, and runs `python -m PyInstaller scripts/backend.spec --noconfirm --distpath build/backend --workpath build/pyinstaller-work`.
- [ ] Replace the hardcoded `python3 -m PyInstaller ...` in `src-tauri/tauri.conf.json` with `scripts/build_backend_sidecar.sh` after the frontend build command.
- [ ] Call the same sidecar script in `scripts/v1_smoke.sh` before `cargo check --manifest-path src-tauri/Cargo.toml` so fresh checkouts do not fail on missing `build/backend/patentagent-backend`.
- [ ] Ensure `scripts/package_dmg.sh` exports the selected Python interpreter to Tauri builds via `PYTHON="$PYTHON_BIN"` so the preflight interpreter and Tauri `beforeBuildCommand` interpreter are identical.
- [ ] Update `tests/test_tauri_desktop_skeleton.py` to assert the shared sidecar script is the Tauri build hook and the v1 smoke desktop gate invokes it before Cargo checks.
- [ ] Run `python3 -m pytest tests/test_tauri_desktop_skeleton.py -q`.
- [ ] Run `PYTHON=$(command -v python3) scripts/build_backend_sidecar.sh`.
- [ ] Run `cargo check --manifest-path src-tauri/Cargo.toml`.

### PR 2: Existing Project Selection Reopens Workbench

**Worker ownership:** App-level project selection flow and its frontend regression tests only.

**Files:**
- Modify: `frontend/src/App.tsx`
- Create or modify: `frontend/src/AppProjectSelectionFlow.test.tsx`

- [ ] Add a single `selectProjectForWorkbench(projectId: string)` handler in `App.tsx` that sets `selectedProjectId`, clears `startChoice`, clears stale message/error if appropriate, and navigates `activeSection` to `"generate"` when `projectId` is non-empty.
- [ ] Use this handler for topbar `ProjectSelect` and `ProjectsOverview onSelect`; keep deletion and data-refresh preservation logic unchanged.
- [ ] Ensure selecting an existing project after a fresh refresh renders `GuidedPatentFlowView` with that project instead of a new-project intake.
- [ ] Ensure choosing the external-draft entry after selecting a project keeps `project={selectedProject}` and uses `initialIntakeMode="external"`.
- [ ] Add Vitest regression coverage that mocks project loading and verifies a selected project name appears as the current guided project, not `当前项目 未选择`, after using the project selector/list selection path.
- [ ] Run `npm --prefix frontend test -- --run frontend/src/AppProjectSelectionFlow.test.tsx`.
- [ ] Run `npm --prefix frontend run build`.

### PR 3: Project List Export Status Is Conservative

**Worker ownership:** Project overview status copy and tests only.

**Files:**
- Modify: `frontend/src/views/projectViews.tsx`
- Create or modify: `frontend/src/projectViews.test.tsx`

- [ ] Change `getProjectExportStatus` so a project with an internal draft package does not display `可进入导出` unless this overview has explicit export-readiness evidence. With the current `ProjectRecord` shape, use a conservative label such as `需成稿会审` or `待正式门禁`.
- [ ] Keep the no-package label as `未生成初稿`.
- [ ] Add a Vitest render test for `ProjectsOverview` proving a packaged project renders the conservative gate label and never renders `可进入导出`.
- [ ] Include a mobile-card assertion if the test renders both desktop and mobile markup from the same component.
- [ ] Run `npm --prefix frontend test -- --run frontend/src/projectViews.test.tsx`.
- [ ] Run `npm --prefix frontend run build`.

### Integration And Final Verification

**Integrator ownership:** Main agent only.

- [ ] Review worker diffs for unrelated edits or conflicts with the pre-existing untracked `reasonix.toml`.
- [ ] Run `python3 -m pytest tests/test_tauri_desktop_skeleton.py -q`.
- [ ] Run `python3 -m pytest -q`.
- [ ] Run `npm --prefix frontend test -- --run`.
- [ ] Run `npm --prefix frontend run build`.
- [ ] Run `PYTHON=$(command -v python3) scripts/build_backend_sidecar.sh`.
- [ ] Run `cargo check --manifest-path src-tauri/Cargo.toml`.
- [ ] Run `cargo test --manifest-path src-tauri/Cargo.toml`.
- [ ] Run at least one headless browser smoke against the dev server that selects an existing project and verifies the guided workbench is current-project-bound.
- [ ] If DMG packaging is rerun, follow `docs/release/dmg-ui-regression-guard.md`, `docs/release/v1.1.0-tauri-release-gate.md`, and `docs/release/v1.1.0-tauri-packaging.md` exactly.
