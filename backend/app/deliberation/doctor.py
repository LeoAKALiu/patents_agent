from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable

from backend.app.deliberation.cli_paths import agent_subprocess_env, resolve_agent_command
from backend.app.schemas import AgentDoctorReport, AgentProviderStatus


PROVIDERS = {
    "codex": {
        "label": "Codex",
        "command": "codex",
        "required": True,
        "model_version": "codex-cli default",
        "roles": ["deliberation", "formula", "chair"],
    },
    "deepseek": {
        "label": "DeepSeek",
        "command": "reasonix",
        "required": False,
        "model_version": "reasonix deepseek-pro",
        "roles": ["deliberation", "formula", "critic"],
    },
    "claude": {
        "label": "Claude",
        "command": "claude",
        "required": False,
        "model_version": "claude-code default",
        "roles": ["deliberation", "formula", "critic"],
    },
    "gemini": {
        "label": "Gemini",
        "command": "gemini",
        "required": False,
        "model_version": "deprecated",
        "roles": ["deprecated"],
    },
    "kimicode": {
        "label": "KimiCode",
        "command": "kimicode",
        "required": False,
        "model_version": "kimi-code local",
        "roles": ["deliberation", "formula", "critic"],
    },
    "mimo": {
        "label": "MimoCode",
        "command": "mimo",
        "required": False,
        "model_version": "mimo-code local",
        "roles": ["deliberation", "formula", "critic"],
    },
}

# Per-provider auth probes — safe, short, non-destructive.
# Each probe entry: (args_tuple, description).
# Provider-specific probe functions interpret the output.
#
# Priority order:
# 1) Dedicated auth/status subcommand (codex login status, claude auth status, reasonix doctor)
# 2) Doctor/diagnostic subcommand (codex doctor)
# 3) Version fallback (gemini: no known auth subcommand)
#
# A probe must never: leak tokens, make API calls, or run prompts.

# Provider-specific probe functions.
# Each returns (auth_status, diagnostic, repair_suggestion) or None to fall through.
_CLAUDE_PRINT_SMOKE_PROMPT = 'Return exactly {"ok":true} as JSON only.'
_CLAUDE_PRINT_SMOKE_ARGS = [
    "-p",
    "--no-chrome",
    "--disable-slash-commands",
    "--tools",
    "",
    "--output-format",
    "text",
    "--no-session-persistence",
    _CLAUDE_PRINT_SMOKE_PROMPT,
]


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
    """Probe Claude Code using the same non-interactive mode used by the app.

    `claude auth status` can report a valid interactive login while `claude -p`
    still fails with a stale or unsupported print-mode credential.  The desktop
    app only uses print mode, so auth-status success is necessary but not enough.
    """
    exit_code, stdout, stderr = command_probe(command, ["auth", "status"], timeout_ms)
    if exit_code is None:
        return "timeout", _sanitize_diagnostic(f"claude auth status 超时 ({timeout_ms}ms)"), "探测命令超时，请检查网络连接。"

    auth_ready = False
    # Try JSON parse first
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            logged_in = data.get("loggedIn")
            if logged_in is True:
                auth_ready = True
            if logged_in is False:
                return "not_authenticated", "claude auth status 报告未登录。", "请运行 `claude auth login` 进行登录。"
            # json without loggedIn → unknown
    except (json.JSONDecodeError, TypeError):
        pass

    # Text fallback
    combined = (stdout + " " + stderr).lower()
    if "logged in" in combined or "loggedin" in combined:
        auth_ready = True
    if "not logged" in combined or "not authenticated" in combined or "expired" in combined:
        return "not_authenticated", _sanitize_diagnostic(f"claude 未登录：{stdout.strip()}", 200), "请运行 `claude auth login` 进行登录。"

    if auth_ready:
        return _probe_claude_print_mode(command, command_probe, timeout_ms)

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


def _probe_claude_print_mode(
    command: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str]:
    smoke_timeout_ms = max(timeout_ms, 15_000)
    exit_code, stdout, stderr = command_probe(command, _CLAUDE_PRINT_SMOKE_ARGS, smoke_timeout_ms)
    combined = "\n".join([stdout.strip(), stderr.strip()]).strip()
    combined_lower = combined.lower()
    if exit_code is None:
        return (
            "timeout",
            _sanitize_diagnostic(f"claude -p 探测超时 ({smoke_timeout_ms}ms)"),
            "请在终端运行 `claude -p 'Return ok'`，确认 Claude Code 非交互 print 模式不会卡在网络或认证步骤。",
        )
    if exit_code == 0 and combined and "failed to authenticate" not in combined_lower and "invalid authentication" not in combined_lower:
        return "ready", "", ""
    if "401" in combined or "failed to authenticate" in combined_lower or "invalid authentication" in combined_lower:
        return (
            "not_authenticated",
            _sanitize_diagnostic(f"claude -p 探测失败：{combined}", 200),
            "Ghostty 中可打开 Claude 不代表非交互 print 模式可用；请运行 `claude -p 'Return ok'` 验证，并按 Claude Code 提示执行 `claude setup-token`、重新登录或修复 ANTHROPIC_API_KEY。",
        )
    return (
        "unknown",
        _sanitize_diagnostic(f"claude -p 返回非零退出码或空输出：{combined}", 200),
        "请运行 `claude -p 'Return ok'` 手动确认 Claude Code 非交互模式可用。",
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


def _probe_deepseek_auth(
    command: str,
    command_probe: Callable[[str, list[str], int], tuple[int | None, str, str]],
    timeout_ms: int,
) -> tuple[str, str, str] | None:
    """Probe DeepSeek through the official reasonix doctor output."""
    exit_code, stdout, stderr = command_probe(command, ["doctor", "--json"], timeout_ms)
    if exit_code is None:
        return "timeout", _sanitize_diagnostic(f"reasonix doctor --json 超时 ({timeout_ms}ms)"), "探测命令超时，请检查网络连接。"
    combined = "\n".join([stdout.strip(), stderr.strip()]).strip()
    if exit_code == 0:
        try:
            data = json.loads(stdout)
            providers = data.get("providers") if isinstance(data, dict) else None
            if isinstance(providers, list):
                deepseek_providers = [
                    provider
                    for provider in providers
                    if isinstance(provider, dict)
                    and (
                        "deepseek" in str(provider.get("name", "")).lower()
                        or "deepseek" in str(provider.get("model", "")).lower()
                        or "deepseek" in str(provider.get("base_url_host", "")).lower()
                    )
                ]
                if any(provider.get("key_present") is True for provider in deepseek_providers):
                    return "ready", "", ""
                if deepseek_providers:
                    return (
                        "not_authenticated",
                        "reasonix doctor 报告 DeepSeek provider 已配置但缺少 API key。",
                        "请运行 `reasonix setup` 或配置 DEEPSEEK_API_KEY。",
                    )
                return (
                    "not_authenticated",
                    "reasonix doctor 未发现 DeepSeek provider 配置。",
                    "请运行 `reasonix setup` 并选择 DeepSeek provider。",
                )
        except (json.JSONDecodeError, TypeError):
            pass
        return (
            "unknown",
            _sanitize_diagnostic("reasonix doctor --json 返回无法识别的输出，无法判断 DeepSeek 配置状态。"),
            "请运行 `reasonix doctor --json` 手动检查配置状态。",
        )
    return (
        "not_authenticated",
        _sanitize_diagnostic(f"reasonix doctor --json 返回非零退出码：{combined}", 200),
        "请运行 `reasonix doctor --json` 检查 DeepSeek 配置状态。",
    )


# Map from provider_id to auth probe function.
_PROVIDER_AUTH_PROBES: dict[str, Callable[..., tuple[str, str, str] | None]] = {
    "codex": _probe_codex_auth,
    "deepseek": _probe_deepseek_auth,
    "claude": _probe_claude_auth,
    "gemini": _probe_gemini_auth,
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
    return resolve_agent_command(command)


def _default_command_probe(command: str, args: list[str], timeout_ms: int) -> tuple[int | None, str, str]:
    """Run a command with timeout and return (exit_code, stdout, stderr)."""
    timeout_sec = timeout_ms / 1000.0
    executable = resolve_agent_command(command) or command
    try:
        result = subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=agent_subprocess_env(),
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
        return "unknown", "命令已安装，但无法验证其可调用状态。", ""

    result = probe_fn(path or command, command_probe, timeout_ms)
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
    - deepseek: `reasonix doctor --json` (official DeepSeek/Reasonix diagnostic output)
    - claude: `auth status` (JSON output)
    - gemini: legacy/deprecated, `--version` only and not part of required deliberation

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
    unknown_required: list[str] = []

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
            if installed and auth_status == "unknown":
                unknown_required.append(provider_id)
            else:
                missing_required.append(provider_id)
        elif not selectable:
            missing_optional.append(provider_id)

    selectable_deliberation_count = sum(
        1
        for provider_id, status in commands.items()
        if status.selectable and ("deliberation" in status.roles or provider_id == "codex")
    )

    if missing_required or selectable_deliberation_count < 3:
        status = "blocked"
        run_mode = "blocked"
    elif len(active_provider_ids) >= 3:
        status = "ready"
        run_mode = "full"
    elif len(active_provider_ids) == 2 or (len(active_provider_ids) + len(unknown_required) >= 3):
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
        unknown_required=unknown_required,
    )
