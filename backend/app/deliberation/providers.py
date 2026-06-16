from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from backend.app.deliberation.cli_paths import agent_subprocess_env, resolve_agent_command
from backend.app.schemas import DeliberationLogEntry


DEFAULT_TASK_TIMEOUT_MS = 180_000


class ProviderFailure(RuntimeError):
    def __init__(
        self,
        reason: str,
        message: str,
        *,
        provider_id: str = "",
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.provider_id = provider_id
        self.stdout = stdout
        self.stderr = stderr


@dataclass
class ProviderTaskResult:
    provider_id: str
    payload: dict
    stdout: str
    stderr: str
    attempts: int


SpawnFunc = Callable[[str, list[str], Path, str, int], Awaitable[tuple[int, str, str]]]
LogCallback = Callable[[DeliberationLogEntry], None]


class AgentProviderRunner:
    def __init__(self, spawn_func: SpawnFunc | None = None) -> None:
        self.spawn_func = spawn_func or _spawn_process

    async def run_json_task(
        self,
        *,
        provider_id: str,
        prompt: str,
        workdir: Path,
        label: str,
        trace: bool,
        task_timeout_ms: int = DEFAULT_TASK_TIMEOUT_MS,
        log_callback: LogCallback | None = None,
    ) -> ProviderTaskResult:
        workdir = workdir.resolve()
        last_failure: ProviderFailure | None = None
        for attempt in range(1, 3):
            command, args = build_provider_command(provider_id, workdir, attempt)
            started_at = time.perf_counter()
            _emit_log(
                log_callback,
                level="info",
                provider_id=provider_id,
                label=label,
                attempt=attempt,
                message="attempt started",
                detail=f"{command} {' '.join(args[:4])}".strip(),
            )
            try:
                try:
                    exit_code, stdout, stderr = await self.spawn_func(command, args, workdir, prompt, task_timeout_ms)
                except OSError as exc:
                    raise ProviderFailure(
                        "provider_missing",
                        f"{label} could not start {command}: {exc}",
                        provider_id=provider_id,
                        stderr=str(exc),
                    ) from exc
                if exit_code != 0:
                    raise ProviderFailure(
                        "process_error",
                        f"{label} failed with exit code {exit_code}",
                        provider_id=provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                if not stdout.strip():
                    raise ProviderFailure(
                        "empty_output",
                        f"{label} completed without output",
                        provider_id=provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                payload = _extract_json_payload(stdout)
                _emit_log(
                    log_callback,
                    level="info",
                    provider_id=provider_id,
                    label=label,
                    attempt=attempt,
                    message="attempt completed",
                    detail=_trim(stdout or stderr),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if trace:
                    _write_trace(workdir, provider_id, label, attempt, prompt, stdout, stderr, "ok")
                return ProviderTaskResult(
                    provider_id=provider_id,
                    payload=payload,
                    stdout=stdout,
                    stderr=stderr,
                    attempts=attempt,
                )
            except ProviderFailure as exc:
                if not exc.provider_id:
                    exc.provider_id = provider_id
                last_failure = exc
                _emit_log(
                    log_callback,
                    level="error",
                    provider_id=provider_id,
                    label=label,
                    attempt=attempt,
                    message="attempt failed",
                    detail=_failure_detail(exc),
                    repair_suggestion=repair_suggestion_for_failure(exc.reason, provider_id),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if trace:
                    _write_trace(
                        workdir,
                        provider_id,
                        label,
                        attempt,
                        prompt,
                        exc.stdout,
                        exc.stderr,
                        exc.reason,
                    )
                if attempt == 2:
                    raise exc
        raise last_failure or ProviderFailure("unknown", f"{label} failed", provider_id=provider_id)


def build_provider_command(provider_id: str, workdir: Path, attempt: int) -> tuple[str, list[str]]:
    if provider_id == "codex":
        last_message_path = workdir / f".codex-last-{attempt}.txt"
        return (
            "codex",
            [
                "e",
                "--skip-git-repo-check",
                "-C",
                str(workdir),
                "--json",
                "--output-last-message",
                str(last_message_path),
                "-",
            ],
        )
    if provider_id == "claude":
        return (
            "claude",
            ["-p", "--no-chrome", "--disable-slash-commands", "--tools", "", "--output-format", "text", "-"],
        )
    if provider_id == "gemini":
        return ("gemini", ["--prompt", "", "--approval-mode", "plan", "--output-format", "text"])
    return (provider_id, [])


async def _spawn_process(
    command: str,
    args: list[str],
    workdir: Path,
    prompt: str,
    timeout_ms: int,
) -> tuple[int, str, str]:
    executable = resolve_agent_command(command) or command
    process = await asyncio.create_subprocess_exec(
        executable,
        *args,
        cwd=str(workdir),
        env=agent_subprocess_env(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(prompt.encode("utf-8")),
            timeout=timeout_ms / 1000 if timeout_ms else None,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise ProviderFailure("timeout", f"{command} timed out", provider_id=command) from exc
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    if Path(command).name == "codex" or Path(executable).name == "codex":
        output_last_message = _read_codex_last_message(args)
        if output_last_message:
            stdout = output_last_message
    return process.returncode or 0, stdout, stderr


def _read_codex_last_message(args: list[str]) -> str:
    if "--output-last-message" not in args:
        return ""
    index = args.index("--output-last-message")
    if index + 1 >= len(args):
        return ""
    path = Path(args[index + 1])
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_json_payload(text: str) -> dict:
    stripped = text.strip()
    candidates = [stripped]
    if "```" in stripped:
        parts = stripped.split("```")
        candidates.extend(part.replace("json", "", 1).strip() for part in parts if "{" in part)
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    raise ProviderFailure("invalid_json", "Provider returned invalid JSON", stdout=text)


def repair_suggestion_for_failure(reason: str, provider_id: str) -> str:
    if reason == "process_error":
        return f"检查 {provider_id} CLI 是否可直接运行、登录状态是否有效、后端是否以非沙箱权限启动，并查看 stderr 摘要。"
    if reason == "timeout":
        return f"{provider_id} 调用超时；建议降低上下文长度、重试该阶段，或检查该 CLI 是否卡在交互式确认。"
    if reason == "invalid_json":
        return f"{provider_id} 返回内容不是结构化 JSON；建议重试，必要时收窄提示词并开启 trace 查看原始输出。"
    if reason == "empty_output":
        return f"{provider_id} 没有返回内容；建议确认模型额度、网络、CLI 输出格式和登录状态。"
    if reason == "provider_missing":
        return f"本机未找到 {provider_id} CLI；请安装或修复 PATH 后重新会审。"
    return f"检查 {provider_id} 的本地 CLI、模型配置、网络和 trace 日志。"


def _emit_log(
    callback: LogCallback | None,
    *,
    level: str,
    provider_id: str,
    label: str,
    attempt: int | None,
    message: str,
    detail: str = "",
    repair_suggestion: str = "",
    elapsed_ms: int | None = None,
) -> None:
    if callback is None:
        return
    callback(
        DeliberationLogEntry(
            level=level,
            phase=_phase_from_label(label),
            provider_id=provider_id,
            attempt=attempt,
            message=message,
            detail=detail,
            repair_suggestion=repair_suggestion,
            elapsed_ms=elapsed_ms,
        )
    )


def _phase_from_label(label: str) -> str:
    if label.startswith("opening"):
        return "opening"
    if label.startswith("pair"):
        return "pair"
    if label.startswith("chair"):
        return "chair"
    return label.split(" ", 1)[0] if label else ""


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _failure_detail(exc: ProviderFailure) -> str:
    parts = [str(exc)]
    if exc.stderr:
        parts.append(f"stderr: {_trim(exc.stderr)}")
    if exc.stdout:
        parts.append(f"stdout: {_trim(exc.stdout)}")
    return "\n".join(part for part in parts if part)


def _trim(value: str, limit: int = 1200) -> str:
    stripped = value.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit] + "...[truncated]"


def _write_trace(
    workdir: Path,
    provider_id: str,
    label: str,
    attempt: int,
    prompt: str,
    stdout: str,
    stderr: str,
    status: str,
) -> None:
    trace_dir = workdir / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)
    safe_label = label.replace(" ", "-").replace("/", "-")
    path = trace_dir / f"{provider_id}-{safe_label}-{attempt}.json"
    path.write_text(
        json.dumps(
            {
                "provider_id": provider_id,
                "label": label,
                "attempt": attempt,
                "status": status,
                "prompt": prompt,
                "stdout": stdout,
                "stderr": stderr,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
