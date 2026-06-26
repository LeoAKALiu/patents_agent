from __future__ import annotations

import json
import tomllib
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAURI_DIR = ROOT / "src-tauri"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tauri_v2_scaffold_is_the_only_desktop_runtime() -> None:
    cargo = TAURI_DIR / "Cargo.toml"
    config = TAURI_DIR / "tauri.conf.json"
    main_rs = TAURI_DIR / "src" / "main.rs"

    assert cargo.exists()
    assert config.exists()
    assert main_rs.exists()
    assert (ROOT / "frontend" / "package.json").exists()
    assert not (ROOT / "desktop").exists()

    cargo_toml = tomllib.loads(read(cargo))
    dependencies = cargo_toml["dependencies"]
    tauri_dependency = dependencies["tauri"]
    assert str(tauri_dependency.get("version", tauri_dependency)).startswith("2")
    assert "tauri-plugin-dialog" in dependencies
    assert "tauri-plugin-opener" in dependencies

    tauri_config = json.loads(read(config))
    build = tauri_config["build"]
    assert build["frontendDist"] == "../frontend/dist"
    assert build["devUrl"] == "http://127.0.0.1:5173"
    assert "npm --prefix frontend run build" in build["beforeBuildCommand"]
    assert "PyInstaller scripts/backend.spec" in build["beforeBuildCommand"]
    assert "__pycache__" in build["beforeBuildCommand"]
    project = tomllib.loads(read(ROOT / "pyproject.toml"))
    packaging_dependencies = project["project"]["optional-dependencies"].get("packaging", [])
    assert any(dependency.lower().startswith("pyinstaller") for dependency in packaging_dependencies)
    gitignore = read(ROOT / ".gitignore")
    assert "\nbuild/\n" in f"\n{gitignore}\n"
    assert (ROOT / "scripts" / "backend.spec").exists()
    assert (ROOT / "scripts" / "backend_server.py").exists()
    assert tauri_config["bundle"]["icon"] == [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico",
    ]
    assert tauri_config["bundle"]["resources"] == {
        "../backend": "backend",
        "../build/backend/patentagent-backend": "patentagent-backend",
    }


def test_tauri_backend_supervision_matches_fastapi_sidecar_contract() -> None:
    main_rs = read(TAURI_DIR / "src" / "main.rs")

    assert "fn backend_root" in main_rs
    assert "PATENTAGENT_REPO_ROOT" in main_rs
    assert ".resource_dir()" in main_rs
    assert 'path.join("backend").join("app").join("main.py").is_file()' in main_rs
    assert "enum BackendLaunchMode" in main_rs
    assert "struct BackendRoot" in main_rs
    assert "BackendLaunchMode::SourceDev" in main_rs
    assert "BackendLaunchMode::Packaged" in main_rs
    assert "fn python_candidates" in main_rs
    assert "fn bundled_backend_executable" in main_rs
    assert "fn start_backend_with_executable" in main_rs
    assert "if launch_mode == BackendLaunchMode::Packaged" in main_rs
    assert "trying bundled backend:" in main_rs
    assert "patentagent-backend" in main_rs
    assert "PATENTAGENT_PYTHON" in main_rs
    assert "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" in main_rs
    assert "/usr/local/bin/python3" in main_rs
    assert '"python3"' in main_rs
    assert "fn start_backend_with_python" in main_rs
    assert "backend did not start with bundled backend or any Python interpreter" in main_rs
    assert "backend-startup-error.txt" in main_rs
    assert "backend-startup.log" in main_rs
    assert "patentagent-tauri-startup.log" in main_rs
    assert "trying python:" in main_rs
    assert "PatentAgent backend startup failed" in main_rs
    assert "backend.app.main:app" in main_rs
    assert "python3" in main_rs
    assert "--host" in main_rs
    assert "127.0.0.1" in main_rs
    assert "--port" in main_rs
    assert "DATA_DIR" in main_rs
    assert "PYTHONPATH" in main_rs
    assert "PYTHONUNBUFFERED" in main_rs
    assert "PYTHONDONTWRITEBYTECODE" in main_rs
    assert "/api/health" in main_rs
    assert "backend stdout:" in main_rs
    assert "backend stderr:" in main_rs
    assert "get_backend_base_url" in main_rs
    assert "kill" in main_rs or "Child" in main_rs


def test_tauri_dom_smoke_is_env_gated_and_checks_real_renderer_root() -> None:
    main_rs = read(TAURI_DIR / "src" / "main.rs")

    assert "PATENTAGENT_TAURI_DOM_SMOKE" in main_rs
    assert "PATENTAGENT_TAURI_DOM_SMOKE_REPORT" in main_rs
    assert "eval_with_callback" in main_rs
    assert "PageLoadEvent::Finished" in main_rs
    assert "DOM_SMOKE_PROBE_ATTEMPTS" in main_rs
    assert "DOM_SMOKE_PROBE_INTERVAL_MS" in main_rs
    assert "run_on_main_thread" in main_rs
    assert "is_final_attempt" in main_rs
    assert 'document.getElementById("root")' in main_rs
    assert 'document.querySelector(".app-shell")' in main_rs
    assert 'document.querySelector(".sidebar")' in main_rs
    assert 'document.querySelector(".topbar")' in main_rs
    assert "rootChildren > 0" in main_rs
    assert "shutdown_backend(&app_handle_for_callback)" in main_rs
    assert "app_handle_for_callback.exit(if ok { 0 } else { 2 })" in main_rs


def test_tauri_shutdown_explicitly_stops_python_sidecar() -> None:
    main_rs = read(TAURI_DIR / "src" / "main.rs")

    assert "fn shutdown_backend" in main_rs
    assert ".take()" in main_rs
    assert "tauri::RunEvent::ExitRequested" in main_rs
    assert "tauri::RunEvent::Exit" in main_rs
    assert "shutdown_backend(app_handle)" in main_rs
    assert ".build(tauri::generate_context!())" in main_rs
    assert ".run(|app_handle, event|" in main_rs


def test_tauri_bridge_dialogs_and_config_are_exposed_without_raw_key_leaks() -> None:
    main_rs = read(TAURI_DIR / "src" / "main.rs")
    bridge_ts = ROOT / "frontend" / "src" / "tauriDesktopBridge.ts"
    main_tsx = read(ROOT / "frontend" / "src" / "main.tsx")

    for command in [
        "get_backend_base_url",
        "desktop_config_get",
        "desktop_config_update",
        "desktop_config_clear_key",
        "desktop_config_health",
        "open_draft",
        "save_official",
        "open_folder",
    ]:
        assert command in main_rs

    assert "api_key_present" in main_rs
    assert "api_key_fingerprint" in main_rs
    assert "sk-" not in main_rs
    assert "DialogExt" in main_rs
    assert "blocking_pick_file" in main_rs
    assert "blocking_save_file" in main_rs
    assert "set_file_name" in main_rs
    assert "add_filter" in main_rs

    assert bridge_ts.exists()
    bridge = read(bridge_ts)
    assert "installTauriDesktopBridge" in bridge
    assert "desktopWindow.desktop" in bridge
    assert "open_draft" in bridge
    assert "save_official" in bridge
    assert "desktop_config_get" in bridge
    assert "desktop_config_update" in bridge
    assert "desktop_config_clear_key" in bridge
    assert "desktop_config_health" in bridge
    assert "installTauriDesktopBridge" in main_tsx


def test_frontend_api_adapter_preserves_web_and_supports_tauri_backend_base_url() -> None:
    api_ts = read(ROOT / "frontend" / "src" / "api.ts")

    assert "resolveApiUrl" in api_ts
    assert "getTauriBackendBaseUrl" in api_ts
    assert "__TAURI__" in api_ts
    assert "url.startsWith(\"/api/\")" in api_ts
    assert "const resolvedUrl = await resolveApiUrl(url)" in api_ts
    assert "fetch(resolvedUrl, init)" in api_ts


def test_tauri_smoke_is_the_desktop_release_gate() -> None:
    smoke = read(ROOT / "scripts" / "v1_smoke.sh")

    assert "run_tauri_smoke_if_present" in smoke
    assert "cargo check" in smoke
    assert "cargo test" in smoke
    assert "npm --prefix desktop" not in smoke
    assert "run_electron_smoke_if_feasible" not in smoke


def test_v1_smoke_prepares_tauri_resource_placeholder_for_clean_worktrees() -> None:
    smoke = read(ROOT / "scripts" / "v1_smoke.sh")

    assert "ensure_tauri_resource_placeholders" in smoke
    assert "build/backend/patentagent-backend" in smoke
    assert "mkdir -p build/backend/patentagent-backend" not in smoke
    assert 'mkdir -p "$(dirname "$sidecar_path")"' in smoke
    assert 'touch "$sidecar_path"' in smoke
    assert 'chmod +x "$sidecar_path"' in smoke
    assert smoke.index("ensure_tauri_resource_placeholders") < smoke.index("cargo check")


def test_tauri_cargo_checks_are_the_only_desktop_ci_gate() -> None:
    ci = read(ROOT / ".github" / "workflows" / "ci.yml")

    assert "Tauri cargo check and tests" in ci
    assert "cargo check --manifest-path src-tauri/Cargo.toml" in ci
    assert "cargo test --manifest-path src-tauri/Cargo.toml" in ci
    assert "libwebkit2gtk-4.1-dev" in ci
    assert "Desktop build and smoke" not in ci
    assert "desktop/package-lock.json" not in ci
    assert "npm run smoke" not in ci


def test_tauri_macos_bundle_gets_ad_hoc_resource_seal() -> None:
    tauri_config = json.loads(read(TAURI_DIR / "tauri.conf.json"))

    macos = tauri_config["bundle"]["macOS"]
    assert macos["signingIdentity"] == "-"
    assert macos["hardenedRuntime"] is False


def test_tauri_icon_png_is_decodable_for_bundle_generation() -> None:
    icon = TAURI_DIR / "icons" / "icon.png"
    data = icon.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    width = height = color_type = bit_depth = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length : offset + 12 + length])[0]
        assert zlib.crc32(kind + payload) & 0xFFFFFFFF == crc
        if kind == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", payload[:10])
        if kind == b"IDAT":
            idat.extend(payload)
        if kind == b"IEND":
            break
        offset += 12 + length

    assert width == height
    assert width >= 512
    assert (bit_depth, color_type) == (8, 6)
    assert zlib.decompress(bytes(idat))
    for generated_icon in [
        "32x32.png",
        "128x128.png",
        "128x128@2x.png",
        "icon.icns",
        "icon.ico",
    ]:
        assert (TAURI_DIR / "icons" / generated_icon).is_file()


def test_tauri_packaging_follow_up_is_explicitly_manual() -> None:
    doc = ROOT / "docs" / "release" / "v1.1.0-tauri-packaging.md"

    assert doc.exists()
    text = read(doc)
    assert "manual" in text.lower()
    assert "DMG" in text
    assert "signing" in text
    assert "notarization" in text
    assert "auto-update" in text
    assert "Do not publish" in text
