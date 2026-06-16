#!/usr/bin/env python3
"""Local macOS smoke gate for the Tauri DMG artifact."""

import argparse
from dataclasses import asdict, dataclass
import json
import os
import plistlib
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


APP_BUNDLE_NAME = "PatentAgent.app"
APP_EXECUTABLE_RELATIVE = Path("Contents/MacOS/patentagent-tauri")
CODE_SIGNATURE_RELATIVE = Path("Contents/_CodeSignature/CodeResources")
BUNDLED_BACKEND_RELATIVE = Path("Contents/Resources/backend/app/main.py")
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_RE = re.compile(
    r"(?P<command>(?:\S*/)?(?:python(?:3(?:\.\d+)?)?|Python)\s+-m\s+uvicorn\s+"
    r"backend\.app\.main:app\s+--host\s+127\.0\.0\.1\s+--port\s+"
    r"(?P<port>\d+)(?:\s+.*)?)"
)


class SmokeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        smoke_dir: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.smoke_dir = smoke_dir
        self.summary = summary


@dataclass(frozen=True)
class BackendProcess:
    pid: int
    ppid: int
    port: int
    command: str


@dataclass(frozen=True)
class CleanupDecision:
    quit_app: bool
    terminate_app_pid: int | None
    terminate_backend_pid: int | None


@dataclass(frozen=True)
class DetachResult:
    ok: bool
    forced: bool
    normal_returncode: int
    force_returncode: int | None
    error: str | None


@dataclass(frozen=True)
class BundleMetadataResult:
    ok: bool
    info_plist: str | None
    executable: str | None
    bundle_identifier: str | None
    display_name: str | None
    version: str | None
    error: str | None = None


def parse_backend_process(line: str) -> BackendProcess | None:
    match = BACKEND_RE.search(line)
    if not match:
        return None

    pid_ppid = _parse_pid_ppid(line[: match.start()])
    if pid_ppid is None:
        return None

    pid, ppid = pid_ppid
    command = " ".join(match.group("command").split())
    return BackendProcess(
        pid=pid,
        ppid=ppid,
        port=int(match.group("port")),
        command=command,
    )


def classify_spctl(returncode: int, output: str) -> str:
    if returncode == 0:
        return "accepted"
    if "rejected" in output.lower():
        return "rejected-not-notarized"
    return "failed"


def cleanup_decision(
    *,
    app_launch_attempted: bool,
    app_pid: int | None,
    backend: BackendProcess | None,
) -> CleanupDecision:
    return CleanupDecision(
        quit_app=app_launch_attempted or app_pid is not None or backend is not None,
        terminate_app_pid=app_pid,
        terminate_backend_pid=backend.pid if backend else None,
    )


def format_failure_payload(exc: BaseException) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": str(exc)}
    if isinstance(exc, SmokeError):
        smoke_dir = exc.smoke_dir
        if smoke_dir is None and exc.summary is not None:
            raw_smoke_dir = exc.summary.get("smoke_dir")
            smoke_dir = str(raw_smoke_dir) if raw_smoke_dir else None
        if smoke_dir:
            payload["smoke_dir"] = smoke_dir
    return payload


def _parse_pid_ppid(prefix: str) -> tuple[int, int] | None:
    tokens = prefix.split()
    if len(tokens) >= 3 and tokens[1].isdigit() and tokens[2].isdigit():
        return int(tokens[1]), int(tokens[2])
    if len(tokens) >= 2 and tokens[0].isdigit() and tokens[1].isdigit():
        return int(tokens[0]), int(tokens[1])
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test a local PatentAgent Tauri DMG on macOS."
    )
    parser.add_argument("dmg", type=Path, help="Path to the Tauri DMG artifact")
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Document artifact retention; smoke artifacts are always kept under /private/tmp.",
    )
    return parser.parse_args(argv)


def run_text_command(args: list[str], output_path: Path, *, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    output_path.write_text(format_command_output(args, result), encoding="utf-8")
    if check and result.returncode != 0:
        raise SmokeError(
            f"Command failed with exit code {result.returncode}: {' '.join(args)}"
        )
    return result


def format_command_output(args: list[str], result: subprocess.CompletedProcess[str]) -> str:
    return (
        f"$ {' '.join(args)}\n"
        f"exit_code: {result.returncode}\n\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )


def attach_dmg(dmg: Path, smoke_dir: Path) -> tuple[Path, subprocess.CompletedProcess[bytes]]:
    result = subprocess.run(
        ["hdiutil", "attach", "-plist", "-nobrowse", "-readonly", str(dmg)],
        capture_output=True,
    )
    (smoke_dir / "attach.plist").write_bytes(result.stdout)
    (smoke_dir / "attach.stderr.txt").write_bytes(result.stderr)
    if result.returncode != 0:
        raise SmokeError(
            f"hdiutil attach failed with exit code {result.returncode}; see attach.stderr.txt"
        )

    try:
        plist = plistlib.loads(result.stdout)
    except plistlib.InvalidFileException as exc:
        raise SmokeError("hdiutil attach did not return a valid plist") from exc

    mount_point = find_mount_point(plist)
    if mount_point is None:
        raise SmokeError("hdiutil attach plist did not include a mount point")
    return Path(mount_point), result


def find_mount_point(plist: dict[str, Any]) -> str | None:
    for entity in plist.get("system-entities", []):
        mount_point = entity.get("mount-point")
        if mount_point:
            return str(mount_point)
    return None


def detach_dmg(
    mount_point: Path,
    smoke_dir: Path,
    *,
    runner=run_text_command,
) -> DetachResult:
    normal = runner(
        ["hdiutil", "detach", str(mount_point)],
        smoke_dir / "detach.txt",
        check=False,
    )
    if normal.returncode == 0:
        return DetachResult(
            ok=True,
            forced=False,
            normal_returncode=normal.returncode,
            force_returncode=None,
            error=None,
        )

    forced = runner(
        ["hdiutil", "detach", "-force", str(mount_point)],
        smoke_dir / "detach_force.txt",
        check=False,
    )
    return DetachResult(
        ok=forced.returncode == 0,
        forced=True,
        normal_returncode=normal.returncode,
        force_returncode=forced.returncode,
        error=None if forced.returncode == 0 else "hdiutil detach failed after normal and force attempts",
    )


def validate_bundle_metadata(app_bundle: Path) -> BundleMetadataResult:
    info_plist = app_bundle / "Contents" / "Info.plist"
    if not info_plist.is_file():
        return BundleMetadataResult(
            ok=False,
            info_plist=None,
            executable=None,
            bundle_identifier=None,
            display_name=None,
            version=None,
            error=f"Info.plist missing: {info_plist}",
        )

    with info_plist.open("rb") as handle:
        info = plistlib.load(handle)

    executable_name = str(info.get("CFBundleExecutable", ""))
    executable = app_bundle / "Contents" / "MacOS" / executable_name
    display_name = str(info.get("CFBundleDisplayName") or info.get("CFBundleName") or "")
    bundle_identifier = str(info.get("CFBundleIdentifier", ""))
    version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")

    errors: list[str] = []
    if executable_name != APP_EXECUTABLE_RELATIVE.name:
        errors.append(f"unexpected CFBundleExecutable: {executable_name!r}")
    if not executable.is_file():
        errors.append(f"bundle executable missing: {executable}")
    if display_name != "PatentAgent":
        errors.append(f"unexpected display name: {display_name!r}")
    if not bundle_identifier:
        errors.append("CFBundleIdentifier is missing")
    if not version:
        errors.append("bundle version is missing")

    return BundleMetadataResult(
        ok=not errors,
        info_plist=str(info_plist),
        executable=str(executable) if executable_name else None,
        bundle_identifier=bundle_identifier or None,
        display_name=display_name or None,
        version=version or None,
        error="; ".join(errors) if errors else None,
    )


def ps_lines() -> list[str]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SmokeError(f"ps failed: {result.stderr.strip()}")
    return result.stdout.splitlines()


def write_process_snapshot(smoke_dir: Path, name: str = "process_snapshot.txt") -> None:
    (smoke_dir / name).write_text("\n".join(ps_lines()) + "\n", encoding="utf-8")


def find_app_process(executable: Path) -> tuple[int, str] | None:
    target = str(executable)
    for line in ps_lines():
        stripped = line.strip()
        match = re.match(r"(?P<pid>\d+)\s+(?P<ppid>\d+)\s+(?P<command>.*)", stripped)
        if not match:
            continue
        command = match.group("command")
        if command == target or command.startswith(f"{target} "):
            return int(match.group("pid")), stripped
    return None


def find_backend_process(app_pid: int) -> tuple[BackendProcess, str] | None:
    for line in ps_lines():
        parsed = parse_backend_process(line)
        if parsed and parsed.ppid == app_pid:
            return parsed, line.strip()
    return None


def wait_for_app_process(executable: Path, timeout: float = 30.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = find_app_process(executable)
        if found:
            return found
        time.sleep(0.5)
    raise SmokeError(f"Timed out waiting for app process at {executable}")


def wait_for_backend_process(app_pid: int, timeout: float = 45.0) -> tuple[BackendProcess, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = find_backend_process(app_pid)
        if found:
            return found
        time.sleep(0.5)
    raise SmokeError(f"Timed out waiting for backend child process under PID {app_pid}")


def poll_health(port: int, smoke_dir: Path, timeout: float = 60.0) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            (smoke_dir / "health.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return payload
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise SmokeError(f"Timed out waiting for JSON health response from {url}: {last_error}")


def process_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def terminate_process(pid: int | None) -> None:
    if pid is None or not process_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def quit_app(smoke_dir: Path) -> subprocess.CompletedProcess[str]:
    return run_text_command(
        ["osascript", "-e", 'tell application "PatentAgent" to quit'],
        smoke_dir / "osascript_quit.txt",
        check=False,
    )


def open_app(copied_app: Path, smoke_dir: Path) -> subprocess.CompletedProcess[str]:
    args = [
        "open",
        "-n",
        "-o",
        str(smoke_dir / "app_stdout.txt"),
        "--stderr",
        str(smoke_dir / "app_stderr.txt"),
        "--env",
        f"PATENTAGENT_PYTHON={sys.executable}",
        str(copied_app),
    ]
    return run_text_command(args, smoke_dir / "open.txt", check=True)


def wait_until_gone(pid: int | None, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return False
        time.sleep(0.5)
    return process_alive(pid)


def write_summary(smoke_dir: Path, summary: dict[str, Any]) -> None:
    (smoke_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_smoke(dmg: Path, keep_artifacts: bool) -> dict[str, Any]:
    if not dmg.is_file():
        raise SmokeError(f"DMG does not exist: {dmg}")

    smoke_dir = Path(
        tempfile.mkdtemp(prefix="patents-tauri-dmg-smoke-", dir="/private/tmp")
    )
    summary: dict[str, Any] = {
        "smoke_dir": str(smoke_dir),
        "dmg": str(dmg.resolve()),
        "keep_artifacts": keep_artifacts,
        "bundle_metadata_ok": False,
        "bundle_metadata": None,
        "bundled_backend_ok": False,
        "bundled_backend": None,
        "codesign_strict_ok": False,
        "detach": None,
        "spctl": None,
        "app_alive_after_quit": None,
        "backend_alive_after_quit": None,
        "health": {
            "ok": None,
            "model": None,
            "llm_configured": None,
        },
    }

    mount_point: Path | None = None
    app_pid: int | None = None
    backend: BackendProcess | None = None
    app_launch_attempted = False
    copied_app = smoke_dir / APP_BUNDLE_NAME
    app_executable = copied_app / APP_EXECUTABLE_RELATIVE

    try:
        mount_point, _ = attach_dmg(dmg, smoke_dir)
        source_app = mount_point / APP_BUNDLE_NAME
        if not source_app.is_dir():
            raise SmokeError(f"Mounted DMG does not contain {APP_BUNDLE_NAME}: {source_app}")

        run_text_command(
            ["ditto", str(source_app), str(copied_app)],
            smoke_dir / "ditto.txt",
            check=True,
        )
        if not app_executable.is_file():
            raise SmokeError(f"Copied app executable is missing: {app_executable}")
        code_resources = copied_app / CODE_SIGNATURE_RELATIVE
        if not code_resources.is_file():
            raise SmokeError(f"Copied app CodeResources is missing: {code_resources}")
        bundled_backend = copied_app / BUNDLED_BACKEND_RELATIVE
        summary["bundled_backend"] = str(bundled_backend)
        summary["bundled_backend_ok"] = bundled_backend.is_file()
        if not bundled_backend.is_file():
            raise SmokeError(f"Copied app bundled backend is missing: {bundled_backend}")
        bundle_metadata = validate_bundle_metadata(copied_app)
        summary["bundle_metadata"] = asdict(bundle_metadata)
        summary["bundle_metadata_ok"] = bundle_metadata.ok
        if not bundle_metadata.ok:
            raise SmokeError(f"Copied app bundle metadata is invalid: {bundle_metadata.error}")

        codesign = run_text_command(
            [
                "codesign",
                "--verify",
                "--deep",
                "--strict",
                "--verbose=4",
                str(copied_app),
            ],
            smoke_dir / "codesign.txt",
            check=False,
        )
        summary["codesign_strict_ok"] = codesign.returncode == 0
        if codesign.returncode != 0:
            raise SmokeError("codesign strict verification failed; see codesign.txt")

        spctl = run_text_command(
            ["spctl", "--assess", "--type", "execute", "--verbose=4", str(copied_app)],
            smoke_dir / "spctl.txt",
            check=False,
        )
        spctl_output = f"{spctl.stdout}\n{spctl.stderr}"
        spctl_status = classify_spctl(spctl.returncode, spctl_output)
        summary["spctl"] = {
            "status": spctl_status,
            "returncode": spctl.returncode,
        }
        if spctl_status == "failed":
            raise SmokeError("spctl assessment failed for a reason other than rejection")

        open_app(copied_app, smoke_dir)
        app_launch_attempted = True
        app_pid, app_line = wait_for_app_process(app_executable)
        (smoke_dir / "app_process.txt").write_text(app_line + "\n", encoding="utf-8")
        write_process_snapshot(smoke_dir, "process_snapshot_after_app_launch.txt")

        try:
            backend, backend_line = wait_for_backend_process(app_pid)
        except SmokeError:
            write_process_snapshot(smoke_dir, "process_snapshot_backend_timeout.txt")
            raise
        (smoke_dir / "backend_process.txt").write_text(
            backend_line + "\n",
            encoding="utf-8",
        )

        health = poll_health(backend.port, smoke_dir)
        summary["health"] = {
            "ok": health.get("ok"),
            "model": health.get("model"),
            "llm_configured": health.get("llm_configured"),
        }
        if health.get("ok") is not True:
            raise SmokeError(f"Health endpoint did not return ok=true: {health!r}")

        quit_app(smoke_dir)
        summary["app_alive_after_quit"] = wait_until_gone(app_pid)
        summary["backend_alive_after_quit"] = wait_until_gone(backend.pid)
        if summary["app_alive_after_quit"] or summary["backend_alive_after_quit"]:
            raise SmokeError("App or backend process remained alive after quit")

        write_summary(smoke_dir, summary)
        return summary
    except BaseException as exc:
        decision = cleanup_decision(
            app_launch_attempted=app_launch_attempted,
            app_pid=app_pid,
            backend=backend,
        )
        if decision.quit_app:
            quit_app(smoke_dir)
            terminate_process(decision.terminate_backend_pid)
            terminate_process(decision.terminate_app_pid)
        summary.setdefault("health", {})
        if summary["app_alive_after_quit"] is None:
            summary["app_alive_after_quit"] = process_alive(app_pid)
        if summary["backend_alive_after_quit"] is None:
            summary["backend_alive_after_quit"] = process_alive(backend.pid if backend else None)
        summary["error"] = str(exc)
        write_summary(smoke_dir, summary)
        if isinstance(exc, SmokeError):
            exc.smoke_dir = str(smoke_dir)
            exc.summary = summary
        raise
    finally:
        if mount_point is not None:
            detach = detach_dmg(mount_point, smoke_dir)
            summary["detach"] = asdict(detach)
            write_summary(smoke_dir, summary)
            if not detach.ok and sys.exc_info()[1] is None:
                raise SmokeError(
                    detach.error or "hdiutil detach failed",
                    smoke_dir=str(smoke_dir),
                    summary=summary,
                )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = run_smoke(args.dmg, args.keep_artifacts)
    except SmokeError as exc:
        print(json.dumps(format_failure_payload(exc), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
