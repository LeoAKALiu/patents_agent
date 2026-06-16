from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "tauri_dmg_smoke.py"


def load_smoke_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tauri_dmg_smoke", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_backend_process_extracts_pid_ppid_and_port() -> None:
    smoke = load_smoke_script()

    parsed = smoke.parse_backend_process(
        "501 12345 12344   0 10:10AM ?? 0:01.23 python3 -m uvicorn "
        "backend.app.main:app --host 127.0.0.1 --port 58743"
    )

    assert parsed == smoke.BackendProcess(
        pid=12345,
        ppid=12344,
        port=58743,
        command="python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 58743",
    )


def test_parse_backend_process_rejects_non_uvicorn_line() -> None:
    smoke = load_smoke_script()

    parsed = smoke.parse_backend_process(
        "501 23456 1   0 10:11AM ?? 0:00.10 python3 -m http.server 8000"
    )

    assert parsed is None


def test_parse_backend_process_accepts_python_venv_executable() -> None:
    smoke = load_smoke_script()

    parsed = smoke.parse_backend_process(
        "12345 12344 /private/tmp/.venv/bin/python -m uvicorn "
        "backend.app.main:app --host 127.0.0.1 --port 51001"
    )

    assert parsed == smoke.BackendProcess(
        pid=12345,
        ppid=12344,
        port=51001,
        command="/private/tmp/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 51001",
    )


def test_spctl_rejection_is_classified_as_not_notarized() -> None:
    smoke = load_smoke_script()

    status = smoke.classify_spctl(
        3,
        "/tmp/PatentAgent.app: rejected\nsource=no usable signature\n",
    )

    assert status == "rejected-not-notarized"


def test_spctl_too_many_open_files_is_classified_as_assessment_tool_error() -> None:
    smoke = load_smoke_script()

    status = smoke.classify_spctl(
        1,
        "/tmp/PatentAgent.app: Too many open files\n",
    )

    assert status == "assessment-tool-error-too-many-open-files"


def test_spctl_invalid_bundle_message_is_classified_as_assessment_tool_error() -> None:
    smoke = load_smoke_script()

    status = smoke.classify_spctl(
        1,
        "/tmp/PatentAgent.app: bundle format unrecognized, invalid, or unsuitable\n",
    )

    assert status == "assessment-tool-error-invalid-bundle"


def test_spctl_invalid_resource_directory_is_classified_as_assessment_tool_error() -> None:
    smoke = load_smoke_script()

    status = smoke.classify_spctl(
        1,
        "/tmp/PatentAgent.app: invalid resource directory (directory or signature have been modified)\n",
    )

    assert status == "assessment-tool-error-invalid-resource-directory"


def test_cleanup_attempts_app_quit_after_successful_launch_without_pid() -> None:
    smoke = load_smoke_script()

    decision = smoke.cleanup_decision(
        app_launch_attempted=True,
        app_pid=None,
        backend=None,
    )

    assert decision.quit_app is True
    assert decision.terminate_app_pid is None
    assert decision.terminate_backend_pid is None


def test_open_app_uses_launchpad_like_path_without_python_override(tmp_path: Path) -> None:
    smoke = load_smoke_script()
    calls: list[list[str]] = []

    def runner(args: list[str], output_path: Path, *, check: bool = False):
        calls.append(args)
        output_path.write_text("opened\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    smoke.run_text_command = runner

    smoke.open_app(tmp_path / "PatentAgent.app", tmp_path)

    assert calls == [
        [
            "open",
            "-n",
            "-o",
            str(tmp_path / "app_stdout.txt"),
            "--stderr",
            str(tmp_path / "app_stderr.txt"),
            "--env",
            f"PATH={smoke.LAUNCHPAD_PATH}",
            str(tmp_path / "PatentAgent.app"),
        ]
    ]
    assert not any("PATENTAGENT_PYTHON" in arg for arg in calls[0])


def test_restore_prompt_dismissal_clicks_system_recovery_prompt(tmp_path: Path) -> None:
    smoke = load_smoke_script()
    calls: list[list[str]] = []

    def runner(args: list[str], output_path: Path, *, check: bool = False):
        calls.append(args)
        output_path.write_text("dismissed\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="dismissed\n", stderr="")

    smoke.run_text_command = runner

    assert smoke.dismiss_restore_prompt(12345, tmp_path, timeout=0.1) is True
    assert calls
    assert calls[0][:2] == ["osascript", "-e"]
    assert "button 2 of window 1" in calls[0][2]


def test_failure_payload_includes_smoke_dir_when_available() -> None:
    smoke = load_smoke_script()

    payload = smoke.format_failure_payload(
        smoke.SmokeError("boom", smoke_dir="/private/tmp/patents-smoke-abc")
    )

    assert payload == {
        "error": "boom",
        "smoke_dir": "/private/tmp/patents-smoke-abc",
    }


def test_detach_retries_with_force_and_reports_failure(tmp_path: Path) -> None:
    smoke = load_smoke_script()
    calls: list[list[str]] = []

    def runner(args: list[str], output_path: Path, *, check: bool = False):
        calls.append(args)
        output_path.write_text("detach failed\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="busy")

    result = smoke.detach_dmg(Path("/Volumes/PatentAgent"), tmp_path, runner=runner)

    assert calls == [
        ["hdiutil", "detach", "/Volumes/PatentAgent"],
        ["hdiutil", "detach", "-force", "/Volumes/PatentAgent"],
    ]
    assert result.ok is False
    assert result.forced is True
    assert result.normal_returncode == 1
    assert result.force_returncode == 1


def test_bundle_metadata_validation_checks_executable_and_version(tmp_path: Path) -> None:
    smoke = load_smoke_script()
    contents = tmp_path / "PatentAgent.app" / "Contents"
    macos = contents / "MacOS"
    macos.mkdir(parents=True)
    (macos / "patentagent-tauri").write_text("#!/bin/sh\n", encoding="utf-8")
    plist_path = contents / "Info.plist"
    plist_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleDisplayName</key><string>PatentAgent</string>
<key>CFBundleExecutable</key><string>patentagent-tauri</string>
<key>CFBundleIdentifier</key><string>xin.liubo.patentagent</string>
<key>CFBundleShortVersionString</key><string>1.1.0</string>
<key>CFBundleVersion</key><string>1.1.0</string>
</dict></plist>
""",
        encoding="utf-8",
    )

    result = smoke.validate_bundle_metadata(tmp_path / "PatentAgent.app")

    assert result.ok is True
    assert result.info_plist == str(plist_path)
    assert result.executable == str(macos / "patentagent-tauri")
    assert result.version == "1.1.0"


def test_smoke_script_requires_bundled_backend_and_does_not_inject_repo_root() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "BUNDLED_BACKEND_RELATIVE" in source
    assert "Contents/Resources/backend/app/main.py" in source
    assert "bundled_backend_ok" in source
    assert "Copied app bundled backend is missing" in source
    assert "PATENTAGENT_REPO_ROOT" not in source
    assert "PATENTAGENT_PYTHON" not in source
    assert "LAUNCHPAD_PATH" in source
    assert "run_spctl_assessment" in source
    assert "spctl_attempt_" in source
    assert "backend_startup" in source
    assert "wait_for_backend_startup_diagnostics" in source
    assert "restore_prompt_dismissed" in source
