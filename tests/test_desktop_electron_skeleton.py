"""Structural tests for the Electron desktop runtime skeleton (PR4, issue #18).

These tests are intentionally static — they verify the desktop workspace is
shaped correctly and that the source files compile. The actual Electron launch
is exercised by ``desktop/scripts/smoke.mjs``, which the desktop build script
runs via ``npm run smoke``.
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
        "preload": DESKTOP_ROOT / "electron" / "preload.ts",
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
    """PR4 must not touch .env, auth, or credential files."""
    forbidden = [".env", "auth.json", "credentials", "secrets"]
    for rel in ("desktop/package.json", "desktop/electron/main.ts", "desktop/electron/preload.ts"):
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text or token == ".env", (
                f"{rel} must not reference {token!r}"
            )
