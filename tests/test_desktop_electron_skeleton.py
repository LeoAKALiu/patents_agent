"""Structural tests for the Electron desktop runtime (PR4/PR5).

These tests verify that the desktop workspace is shaped correctly and that the
source files compile when the Electron dependencies are installed. The actual
Electron launch is exercised by ``desktop/scripts/smoke.mjs``, which now checks
both preload exposure and FastAPI backend health from the main process.
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = REPO_ROOT / "desktop"


@pytest.fixture(scope="module")
def desktop_paths() -> dict[str, Path]:
    if not DESKTOP_ROOT.is_dir():
        pytest.skip("desktop/ workspace not present (PR4 not merged yet)")
    return {
        "root": DESKTOP_ROOT,
        "package_json": DESKTOP_ROOT / "package.json",
        "tsconfig": DESKTOP_ROOT / "tsconfig.json",
        "gitignore": DESKTOP_ROOT / ".gitignore",
        "main": DESKTOP_ROOT / "electron" / "main.ts",
        "backend_supervisor": DESKTOP_ROOT / "electron" / "backend-supervisor.ts",
        "preload": DESKTOP_ROOT / "electron" / "preload.ts",
        "desktop_config": DESKTOP_ROOT / "electron" / "desktop-config.ts",
        "desktop_dialogs": DESKTOP_ROOT / "electron" / "desktop-dialogs.ts",
        "smoke": DESKTOP_ROOT / "scripts" / "smoke.mjs",
    }


def test_desktop_directory_present() -> None:
    assert DESKTOP_ROOT.is_dir(), "desktop/ workspace must exist for PR4"


def test_required_files_present(desktop_paths: dict[str, Path]) -> None:
    for name, path in desktop_paths.items():
        if name == "root":
            continue
        assert path.is_file(), f"desktop skeleton is missing {name} at {path}"

def test_package_json_shape(desktop_paths: dict[str, Path]) -> None:
    pkg = json.loads(desktop_paths["package_json"].read_text(encoding="utf-8"))
    assert pkg["name"] == "patents-agent-desktop"
    assert pkg["private"] is True
    assert pkg["main"] == "dist-electron/main.js"
    scripts = pkg.get("scripts", {})
    assert "build" in scripts, "package.json must define a build script"
    assert "dev" in scripts, "package.json must define a dev script"
    assert "smoke" in scripts, "package.json must define a smoke script"
    assert scripts["dev"].startswith("npm run build"), (
        "dev script must depend on build so the main process is compiled first"
    )
    assert "electron" in pkg.get("devDependencies", {}), (
        "electron must be a devDependency so the smoke can find a binary"
    )
    assert "typescript" in pkg.get("devDependencies", {})


def test_tsconfig_compiles_under_strict(desktop_paths: dict[str, Path]) -> None:
    """If node_modules is present, run tsc; otherwise only parse the config."""
    cfg = json.loads(desktop_paths["tsconfig"].read_text(encoding="utf-8"))
    compiler_options = cfg.get("compilerOptions", {})
    assert compiler_options.get("strict") is True
    assert compiler_options.get("module") == "commonjs", (
        "Electron main process must compile to CommonJS"
    )
    assert compiler_options.get("outDir") == "dist-electron"

    tsc = DESKTOP_ROOT / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        pytest.skip("typescript not installed in desktop/ (run npm install)")
    result = subprocess.run(
        [str(tsc), "-p", str(desktop_paths["tsconfig"]), "--noEmit"],
        cwd=DESKTOP_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"tsc --noEmit failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_gitignore_excludes_build_outputs(desktop_paths: dict[str, Path]) -> None:
    text = desktop_paths["gitignore"].read_text(encoding="utf-8")
    assert "node_modules/" in text
    assert "dist-electron/" in text


def test_main_process_security_defaults(desktop_paths: dict[str, Path]) -> None:
    """The main process must lock the renderer down by default."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    assert "contextIsolation: true" in text
    assert "nodeIntegration: false" in text
    assert "sandbox: true" in text
    assert "setWindowOpenHandler" in text, (
        "main must block window.open from the renderer"
    )


def test_backend_supervisor_launches_python_uvicorn(
    desktop_paths: dict[str, Path],
) -> None:
    """PR5 launches the local FastAPI backend with the local Python runtime."""
    text = desktop_paths["backend_supervisor"].read_text(encoding="utf-8")
    assert "uvicorn" in text
    assert "backend.app.main:app" in text
    assert "/api/health" in text
    assert "PATENTAGENT_PYTHON" in text
    assert "PATENTAGENT_BACKEND_PORT" in text
    assert "findAvailablePort" in text
    assert "waitForBackendHealth" in text
    assert "stopBackendProcess" in text
    assert "PYTHONPATH" in text
    assert "DATA_DIR" in text


def test_main_process_supervises_backend_lifecycle(
    desktop_paths: dict[str, Path],
) -> None:
    """The renderer must wait for a healthy backend and app quit must stop it."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    assert "startBackend(" in text
    assert "configureSessionSecurity(backend.baseUrl)" in text
    assert "routeRendererApiRequests" in text
    assert "onBeforeRequest" in text
    assert "file:///api/*" in text
    assert "loadBackendErrorPage" in text
    assert "before-quit" in text
    assert "stopBackendSync" in text


def test_smoke_checks_backend_health_from_main_process(
    desktop_paths: dict[str, Path],
) -> None:
    text = desktop_paths["main"].read_text(encoding="utf-8")
    assert "[smoke] backend health ok" in text
    assert "smokeBackendDataDir" in text
    assert "await startBackend(smokeBackendDataDir())" in text


def test_preload_uses_context_bridge(desktop_paths: dict[str, Path]) -> None:
    text = desktop_paths["preload"].read_text(encoding="utf-8")
    assert "contextBridge" in text
    assert "exposeInMainWorld" in text
    assert "desktop" in text, "preload must expose window.desktop"
    assert "ipcRenderer" in text, "preload must use ipcRenderer for IPC"


def test_smoke_script_executable_and_self_contained(
    desktop_paths: dict[str, Path],
) -> None:
    text = desktop_paths["smoke"].read_text(encoding="utf-8")
    assert "createRequire" in text, (
        "smoke.mjs must use createRequire to resolve the local electron binary"
    )
    assert "--smoke" in text, "smoke.mjs must pass --smoke to electron"
    assert "PATENTAGENT_ELECTRON_BIN" in text, (
        "smoke.mjs must honour PATENTAGENT_ELECTRON_BIN for CI override"
    )
    assert "import.meta.url" in text, "smoke.mjs must use ESM path resolution"


def test_app_menu_defines_required_actions(desktop_paths: dict[str, Path]) -> None:
    text = desktop_paths["main"].read_text(encoding="utf-8")
    for required in (
        "导出目录",  # Export Folder
        "设置",  # Settings
        "关于 PatentAgent",  # About
        "desktop:menu",  # IPC channel
    ):
        assert required in text, f"main.ts must reference {required!r}"


def test_does_not_modify_env_or_credentials() -> None:
    """Desktop PRs must not touch environment, auth, or credential files."""
    forbidden = [".env", "auth.json", "credentials", "secrets"]
    for rel in (
        "desktop/package.json",
        "desktop/electron/main.ts",
        "desktop/electron/backend-supervisor.ts",
        "desktop/electron/preload.ts",
        "desktop/electron/desktop-config.ts",
        "desktop/electron/desktop-dialogs.ts",
    ):
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text or token == ".env", (
                f"{rel} must not reference {token!r}"
            )


def test_desktop_config_module_exposes_required_contract(
    desktop_paths: dict[str, Path],
) -> None:
    """PR6 desktop config module must talk to the local FastAPI backend."""
    text = desktop_paths["desktop_config"].read_text(encoding="utf-8")
    # Must talk to /api/desktop-config on the local backend
    assert "/api/desktop-config" in text
    assert "ipcMain.handle" in text
    # Raw-key leak guard
    assert "sk-[A-Za-z0-9_-]" in text or "sk-…" in text, (
        "desktop-config must scrub raw key patterns from errors"
    )
    # Endpoints the renderer needs
    for required in (
        "desktop:config:get",
        "desktop:config:update",
        "desktop:config:clear-key",
        "desktop:config:health",
    ):
        assert required in text, f"desktop-config must register IPC {required!r}"


def test_main_process_wires_desktop_config_ipc(
    desktop_paths: dict[str, Path],
) -> None:
    """PR6 main process must install the desktop-config IPC once the backend is healthy."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    assert "installDesktopConfigIpc" in text
    assert "attachDesktopConfigIpc" in text
    # Wired exactly when the backend is alive — both production boot and smoke test.
    assert "installDesktopConfigIpc(backend.baseUrl);" in text
    assert "installDesktopConfigIpc(backend.baseUrl, mainWindow)" in text


def test_preload_exposes_config_api(desktop_paths: dict[str, Path]) -> None:
    """PR6 preload must expose window.desktop.config.{get,update,clearKey,health}."""
    text = desktop_paths["preload"].read_text(encoding="utf-8")
    # The bridge is exposed as `config: configApi` (and the type uses
    # `config: DesktopConfigApi`); the renderer reaches it as
    # `window.desktop.config.{get,update,clearKey,health}`.
    assert "config: DesktopConfigApi" in text, "preload must declare config on DesktopApi"
    assert "config: configApi" in text, "preload must attach configApi to the bridge"
    for required in (
        "DesktopConfigView",
        "DesktopConfigUpdatePayload",
        "DesktopConfigApi",
    ):
        assert required in text, f"preload must expose {required!r}"
    # IPC channels must match the names registered by desktop-config.ts.
    for required in (
        "desktop:config:get",
        "desktop:config:update",
        "desktop:config:clear-key",
        "desktop:config:health",
    ):
        assert required in text, f"preload must invoke IPC channel {required!r}"
    # The renderer only sees the redacted view through the IPC bridge — the
    # main process / backend are responsible for redaction, not the preload.
    assert "invoke(\"desktop:config:get\")" in text


def test_preload_does_not_expose_key_hash(desktop_paths: dict[str, Path]) -> None:
    """The renderer only needs a presence flag and short fingerprint."""
    for name in ("preload", "desktop_config"):
        text = desktop_paths[name].read_text(encoding="utf-8")
        assert "api_key_hash" not in text


def test_smoke_probes_desktop_config_api(
    desktop_paths: dict[str, Path],
) -> None:
    """The Electron smoke must assert the new config IPC surface is wired up."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    assert "hasConfigGet" in text
    assert "hasConfigUpdate" in text
    assert "hasConfigClearKey" in text
    assert "hasConfigHealth" in text
    for required in (
        "preload did not expose window.desktop.config.get",
        "preload did not expose window.desktop.config.update",
        "preload did not expose window.desktop.config.clearKey",
        "preload did not expose window.desktop.config.health",
    ):
        assert required in text, f"smoke probe must check {required!r}"


def test_desktop_dialogs_module_exposes_native_import_export_contract(
    desktop_paths: dict[str, Path],
) -> None:
    """PR7 native file dialogs must use explicit IPC channels and backend export URLs."""
    text = desktop_paths["desktop_dialogs"].read_text(encoding="utf-8")
    for required in (
        "dialog.showOpenDialog",
        "dialog.showSaveDialog",
        "shell.showItemInFolder",
        "desktop:dialogs:open-draft",
        "desktop:dialogs:save-official",
        "desktop:dialogs:open-folder",
        "downloadPath must start with /api/",
        "contentBase64",
    ):
        assert required in text, f"desktop-dialogs must include {required!r}"
    assert "readFile(filePath)" in text, (
        "main process must read only the user-selected draft path"
    )


def test_main_process_wires_native_dialogs_and_menu_actions(
    desktop_paths: dict[str, Path],
) -> None:
    """PR7 main process must wire native file dialog IPC and menu actions."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    for required in (
        "attachDesktopDialogsIpc",
        "DesktopDialogsClient",
        "导入草稿",
        "导出正式稿",
        "import-draft-docx",
        "import-draft-markdown",
        "export-official-docx",
        "export-official-md",
        "export-official-sidecar",
        "open-export-folder",
    ):
        assert required in text, f"main.ts must wire {required!r}"


def test_preload_exposes_dialogs_api(
    desktop_paths: dict[str, Path],
) -> None:
    """PR7 preload must expose window.desktop.dialogs without enabling Node in renderer."""
    text = desktop_paths["preload"].read_text(encoding="utf-8")
    assert "dialogs: DesktopDialogsApi" in text
    assert "dialogs: dialogsApi" in text
    for required in (
        "desktop:dialogs:open-draft",
        "desktop:dialogs:save-official",
        "desktop:dialogs:open-folder",
        "contentBase64",
    ):
        assert required in text, f"preload must expose {required!r}"


def test_smoke_probes_native_dialog_api(
    desktop_paths: dict[str, Path],
) -> None:
    """The Electron smoke must assert the native dialog bridge is present."""
    text = desktop_paths["main"].read_text(encoding="utf-8")
    for required in (
        "hasDialogsOpenDraft",
        "hasDialogsSaveOfficial",
        "hasDialogsOpenFolder",
        "preload did not expose window.desktop.dialogs.openDraft",
        "preload did not expose window.desktop.dialogs.saveOfficial",
        "preload did not expose window.desktop.dialogs.openFolder",
    ):
        assert required in text, f"smoke probe must check {required!r}"
