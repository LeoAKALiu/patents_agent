from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable

from backend.app.schemas import AgentDoctorReport, AgentProviderStatus


PROVIDERS = {
    "codex": {
        "label": "Codex",
        "command": "codex",
        "required": True,
        "model_version": "codex-cli default",
        "roles": ["deliberation", "formula", "chair"],
    },
    "gemini": {
        "label": "Gemini",
        "command": "gemini",
        "required": True,
        "model_version": "gemini-cli default",
        "roles": ["deliberation", "formula", "critic"],
    },
    "claude": {
        "label": "Claude",
        "command": "claude",
        "required": True,
        "model_version": "claude-code default",
        "roles": ["deliberation", "formula", "critic"],
    },
    "kimicode": {
        "label": "KimiCode",
        "command": "kimicode",
        "required": False,
        "model_version": "kimi-code local",
        "roles": ["deliberation", "formula", "critic"],
    },
    "deepseek_pi": {
        "label": "DeepSeek + PI",
        "command": "deepseek-pi",
        "required": False,
        "model_version": "deepseek-pi route",
        "roles": ["formula", "critic"],
    },
}

# Per-provider auth probes — safe, short, non-destructive.
# Each probe entry: (args_tuple, description).
# Provider-specific probe functions interpret the output.
#
# Priority order:
# 1) Dedicated auth/status subcommand (codex login status, claude auth status)
# 2) Doctor/diagnostic subcommand (codex doctor)
# 3) Version fallback (gemini: no known auth subcommand)
#
# A probe must never: leak tokens, make API calls, or run prompts.

# Provider-specific probe functions.
# Each returns (auth_status, diagnostic, repair_suggestion) or None to fall through.


def _probe_codex_auth(
    command: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str] | None:
    """Probe codex via `login status` subcommand."""
    exit_code, stdout, stderr = command_probe(command, ["login", "status"], timeout_ms)
    if exit_code is None:
        return "timeout", _sanitize_diagnostic(f"codex login status 超时 ({timeout_ms}ms)"), "探测命令超时，请检查网络连接。"
    combined = (stdout + " " + stderr).lower()
    if exit_code == 0 and "logged in" in combined:
        return "ready", "", ""
    if exit_code == 0 and ("not logged" in combined or "not authenticated" in combined or "expired" in combined):
        return "not_authenticated", _sanitize_diagnostic(f"codex 未登录：{stdout.strip()}", 200), "请运行 `codex login` 进行登录。"
    # login status failed with non-zero exit → likely not a codex CLI or auth broken
    return (
        "not_authenticated",
        _sanitize_diagnostic(f"codex login status 返回非零退出码：{' '.join([stdout.strip(), stderr.strip()]).strip()}", 200),
        "请运行 `codex login` 进行登录。",
    )


def _probe_claude_auth(
    command: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str] | None:
    """Probe claude via `auth status` subcommand (JSON output)."""
    exit_code, stdout, stderr = command_probe(command, ["auth", "status"], timeout_ms)
    if exit_code is None:
        return "timeout", _sanitize_diagnostic(f"claude auth status 超时 ({timeout_ms}ms)"), "探测命令超时，请检查网络连接。"

    # Try JSON parse first
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            logged_in = data.get("loggedIn")
            if logged_in is True:
                return "ready", "", ""
            if logged_in is False:
                return "not_authenticated", "claude auth status 报告未登录。", "请运行 `claude auth login` 进行登录。"
            # json without loggedIn → unknown
    except (json.JSONDecodeError, TypeError):
        pass

    # Text fallback
    combined = (stdout + " " + stderr).lower()
    if "logged in" in combined or "loggedin" in combined:
        return "ready", "", ""
    if "not logged" in combined or "not authenticated" in combined or "expired" in combined:
        return "not_authenticated", _sanitize_diagnostic(f"claude 未登录：{stdout.strip()}", 200), "请运行 `claude auth login` 进行登录。"

    # Exit 0 but unrecognized output → unknown (not not_authenticated)
    if exit_code == 0:
        return (
            "unknown",
            _sanitize_diagnostic(f"claude auth status 返回无法识别的输出，无法判断认证状态。", 200),
            "请运行 `claude auth status` 手动检查登录状态。",
        )

    return (
        "not_authenticated",
        _sanitize_diagnostic(f"claude auth status 返回非零退出码：{' '.join([stdout.strip(), stderr.strip()]).strip()}", 200),
        "请运行 `claude auth login` 进行登录。",
    )


def _probe_gemini_auth(
    command: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str] | None:
    """Probe gemini — only --version is available; no auth-status subcommand exists."""
    exit_code, stdout, stderr = command_probe(command, ["--version"], timeout_ms)
    if exit_code is None:
        return "timeout", _sanitize_diagnostic(f"gemini --version 超时 ({timeout_ms}ms)"), "探测命令超时，请检查网络连接。"
    if exit_code == 0:
        # Version succeeds but tells us nothing about auth → unknown
        return (
            "unknown",
            f"gemini 命令可执行（{stdout.strip()}），但无 auth status 子命令可验证登录状态。",
            "请手动运行 `gemini` 检查是否已登录。",
        )
    # Non-zero exit → unexpected, treat as potentially broken
    return (
        "unknown",
        _sanitize_diagnostic(f"gemini --version 返回非零退出码：{' '.join([stdout.strip(), stderr.strip()]).strip()}", 200),
        "请运行 `gemini --version` 确认 CLI 正常工作。",
    )


# Map from provider_id to auth probe function.
_PROVIDER_AUTH_PROBES: dict[str, Callable[..., tuple[str, str, str] | None]] = {
    "codex": _probe_codex_auth,
    "gemini": _probe_gemini_auth,
    "claude": _probe_claude_auth,
}


def _sanitize_diagnostic(text: str, max_length: int = 200) -> str:
    """Remove token-like strings and truncate diagnostic output."""
    if not text:
        return ""
    scrubbed = re.sub(r"\b[0-9a-fA-F]{32,}\b", "<scrubbed>", text)
    scrubbed = re.sub(r"\b[A-Za-z0-9+/]{24,}={0,2}\b", "<scrubbed>", scrubbed)
    scrubbed = re.sub(r"\b(?:sk|pk|ak|gk)-[A-Za-z0-9]{16,}\b", "<scrubbed>", scrubbed)
    scrubbed = re.sub(r"(?i)(token|api[_-]?key|secret|password)\s*[:=]?\s*\S+", "<scrubbed>", scrubbed)
    if len(scrubbed) > max_length:
        scrubbed = scrubbed[:max_length] + "..."
    return scrubbed


def _default_command_lookup(command: str) -> str | None:
    return shutil.which(command)


def _default_command_probe(command: str, args: list[str], timeout_ms: int) -> tuple[int | None, str, str]:
    """Run a command with timeout and return (exit_code, stdout, stderr)."""
    timeout_sec = timeout_ms / 1000.0
    try:
        result = subprocess.run(
            [command, *args],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return None, stdout if isinstance(stdout, str) else stdout.decode("utf-8", errors="replace"), stderr if isinstance(stderr, str) else stderr.decode("utf-8", errors="replace")
    except FileNotFoundError:
        return None, "", "命令文件不存在或已被删除。"
    except PermissionError:
        return None, "", "命令文件无执行权限。"
    except Exception as exc:
        return None, "", str(exc)


def _resolve_auth_status(
    provider_id: str,
    command: str,
    path: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str]:
    """Determine auth_status for a provider using its dedicated probe function.

    Returns (auth_status, diagnostic, repair_suggestion).
    """
    if not path:
        return "unavailable", "命令未安装或不在 PATH 中。", "请安装该 CLI 并确保其在 PATH 中可用。"

    probe_fn = _PROVIDER_AUTH_PROBES.get(provider_id)
    if probe_fn is None:
        # No custom probe → installed but can't verify auth
        return "unknown", f"命令存在：{path}，但无法验证其可调用状态。", ""

    result = probe_fn(command, command_probe, timeout_ms)
    if result is not None:
        return result

    # Fallthrough — should not happen with well-formed probe functions
    return "unknown", f"命令可执行但无法判断认证状态。", f"请运行 `{command} --version` 确认 CLI 正常工作。"


def inspect_agent_environment(
    command_lookup: Callable[[str], str | None] | None = None,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]] | None = None,
    probe_timeout_ms: int = 3000,
) -> AgentDoctorReport:
    """Inspect the local agent environment and report per-provider status.

    Each provider is probed with a dedicated, non-destructive auth-check command:
    - codex: `login status` (text output)
    - claude: `auth status` (JSON output)
    - gemini: `--version` (no auth subcommand exists — always "unknown")

    Safety: probes never leak tokens, API keys, or config content.
    Diagnostics are token-scrubbed and truncated.

    Fail-closed: required providers must report auth_status="ready" to
    enter active_provider_ids. "unknown" (can't verify) blocks the gate
    but keeps the provider selectable for manual opt-in.
    """
    lookup = command_lookup or _default_command_lookup
    probe = command_probe or _default_command_probe

    commands: dict[str, AgentProviderStatus] = {}
    active_provider_ids: list[str] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for provider_id, definition in PROVIDERS.items():
        command = str(definition["command"])
        path = lookup(command) or ""
        installed = bool(path)

        auth_status, diagnostic, repair_suggestion = _resolve_auth_status(
            provider_id, command, path, probe, probe_timeout_ms
        )

        available = installed and auth_status == "ready"
        selectable = installed and auth_status in ("ready", "unknown")

        commands[provider_id] = AgentProviderStatus(
            id=provider_id,
            label=str(definition["label"]),
            command=command,
            available=available,
            path=path,
            required=bool(definition["required"]),
            model_version=str(definition.get("model_version", "")),
            roles=[str(role) for role in definition.get("roles", [])],
            installed=installed,
            auth_status=auth_status,
            diagnostic=diagnostic,
            repair_suggestion=repair_suggestion,
            selectable=selectable,
        )

        if available:
            active_provider_ids.append(provider_id)
        elif definition["required"]:
            missing_required.append(provider_id)
        else:
            missing_optional.append(provider_id)

    if missing_required:
        status = "blocked"
        run_mode = "blocked"
    elif len(active_provider_ids) >= 3:
        status = "ready"
        run_mode = "full"
    elif len(active_provider_ids) == 2:
        status = "degraded"
        run_mode = "partial"
    else:
        status = "degraded"
        run_mode = "minimal"

    return AgentDoctorReport(
        status=status,
        run_mode=run_mode,
        commands=commands,
        active_provider_ids=active_provider_ids,
        missing_required=missing_required,
        missing_optional=missing_optional,
    )
