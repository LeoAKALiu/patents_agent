from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from backend.app.agents.models import AgentRuntimeFailure, AgentTaskRequest, AgentTaskResult
from backend.app.deliberation.cli_paths import agent_subprocess_env, resolve_agent_command
from backend.app.schemas import DeliberationLogEntry

try:
    from json_repair import repair_json as _repair_json
except ImportError:  # pragma: no cover - optional in old local envs
    _repair_json = None


DEFAULT_TASK_TIMEOUT_MS = 180_000
PROMPT_ARG = "{prompt}"
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

SpawnFunc = Callable[[str, list[str], Path, str, int], Awaitable[tuple[int, str, str]]]
LogCallback = Callable[[DeliberationLogEntry], None]


class CliAgentAdapter:
    def __init__(self, spawn_func: SpawnFunc | None = None) -> None:
        self.spawn_func = spawn_func or _spawn_process

    async def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        workdir = request.workdir.resolve()
        last_failure: AgentRuntimeFailure | None = None
        for attempt in range(1, request.attempt_limit + 1):
            command, args = build_provider_command(request.provider_id, workdir, attempt)
            started_at = time.perf_counter()
            _emit_log(
                request.log_callback,
                level="info",
                provider_id=request.provider_id,
                label=request.label,
                attempt=attempt,
                message="attempt started",
                detail=f"{command} {' '.join(args[:4])}".strip(),
            )
            try:
                try:
                    exit_code, stdout, stderr = await self.spawn_func(
                        command,
                        args,
                        workdir,
                        request.prompt,
                        request.timeout_ms,
                    )
                except OSError as exc:
                    raise AgentRuntimeFailure(
                        "provider_missing",
                        f"{request.label} could not start {command}: {exc}",
                        provider_id=request.provider_id,
                        stderr=str(exc),
                    ) from exc
                if exit_code != 0:
                    raise AgentRuntimeFailure(
                        "process_error",
                        f"{request.label} failed with exit code {exit_code}",
                        provider_id=request.provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                if not stdout.strip():
                    raise AgentRuntimeFailure(
                        "empty_output",
                        f"{request.label} completed without output",
                        provider_id=request.provider_id,
                        stdout=stdout,
                        stderr=stderr,
                    )
                payload = _extract_json_payload(stdout)
                _emit_log(
                    request.log_callback,
                    level="info",
                    provider_id=request.provider_id,
                    label=request.label,
                    attempt=attempt,
                    message="attempt completed",
                    detail=_trim(stdout or stderr),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if request.trace:
                    _write_trace(workdir, request.provider_id, request.label, attempt, request.prompt, stdout, stderr, "ok")
                return AgentTaskResult(
                    provider_id=request.provider_id,
                    payload=payload,
                    stdout=stdout,
                    stderr=stderr,
                    attempts=attempt,
                )
            except AgentRuntimeFailure as exc:
                exc.provider_id = request.provider_id
                last_failure = exc
                _emit_log(
                    request.log_callback,
                    level="error",
                    provider_id=request.provider_id,
                    label=request.label,
                    attempt=attempt,
                    message="attempt failed",
                    detail=_failure_detail(exc),
                    repair_suggestion=repair_suggestion_for_failure(exc.reason, request.provider_id),
                    elapsed_ms=_elapsed_ms(started_at),
                )
                if request.trace:
                    _write_trace(
                        workdir,
                        request.provider_id,
                        request.label,
                        attempt,
                        request.prompt,
                        exc.stdout,
                        exc.stderr,
                        exc.reason,
                    )
                if attempt == request.attempt_limit:
                    raise exc
        raise last_failure or AgentRuntimeFailure("unknown", f"{request.label} failed", provider_id=request.provider_id)

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
    ) -> AgentTaskResult:
        return await self.run_task(
            AgentTaskRequest(
                provider_id=provider_id,
                role="deliberation",
                prompt=prompt,
                workdir=workdir,
                label=label,
                trace=trace,
                timeout_ms=task_timeout_ms,
                log_callback=log_callback,
            )
        )


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
    if provider_id == "deepseek":
        return ("reasonix", ["run", "--model", "deepseek-pro"])
    if provider_id == "gemini":
        return ("gemini", ["--prompt", "", "--approval-mode", "plan", "--output-format", "text"])
    if provider_id == "kimicode":
        return ("kimicode", ["-p", PROMPT_ARG, "--output-format", "text"])
    if provider_id == "mimo":
        return ("mimo", ["run", "--format", "default", PROMPT_ARG])
    return (provider_id, [])


async def _spawn_process(
    command: str,
    args: list[str],
    workdir: Path,
    prompt: str,
    timeout_ms: int,
) -> tuple[int, str, str]:
    executable = resolve_agent_command(command) or command
    prompt_is_arg = PROMPT_ARG in args
    process_args = [prompt if arg == PROMPT_ARG else arg for arg in args]
    process = await asyncio.create_subprocess_exec(
        executable,
        *process_args,
        cwd=str(workdir),
        env=agent_subprocess_env(),
        stdin=asyncio.subprocess.PIPE if not prompt_is_arg else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(None if prompt_is_arg else prompt.encode("utf-8")),
            timeout=timeout_ms / 1000 if timeout_ms else None,
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise AgentRuntimeFailure("timeout", f"{command} timed out", provider_id=command) from exc
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
    for candidate in _json_payload_candidates(text):
        payload = _loads_json_object(candidate)
        if payload is not None:
            return payload
    raise AgentRuntimeFailure("invalid_json", "Provider returned invalid JSON", stdout=text)


def _json_payload_candidates(text: str) -> list[str]:
    candidates: list[str] = []

    def add(candidate: str) -> None:
        stripped = candidate.strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)

    for source in (text, _strip_ansi(text)):
        add(source)
        if "```" in source:
            for part in source.split("```"):
                if "{" not in part:
                    continue
                stripped = part.strip()
                if stripped.lower().startswith("json"):
                    stripped = stripped[4:].lstrip()
                add(stripped)
        first = source.find("{")
        last = source.rfind("}")
        if first >= 0 and last > first:
            add(source[first : last + 1])
    return candidates


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _loads_json_object(candidate: str) -> dict | None:
    try:
        payload = json.loads(candidate)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    if _repair_json is None:
        return None
    try:
        repaired = _repair_json(candidate, return_objects=True)
    except Exception:
        return None
    if isinstance(repaired, dict):
        return repaired
    return None


def repair_suggestion_for_failure(reason: str, provider_id: str) -> str:
    if provider_id == "claude" and reason == "process_error":
        return "Claude Code 交互模式可用不代表非交互 print 模式可用；请运行 `claude -p 'Return ok'` 验证，并按 Claude Code 提示执行 `claude setup-token`、重新登录或修复 ANTHROPIC_API_KEY。"
    if reason == "not_authenticated":
        return f"{provider_id} CLI 认证未就绪；请按诊断信息完成登录、token 或 API key 配置后刷新运行状态。"
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


def _failure_detail(exc: AgentRuntimeFailure) -> str:
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
