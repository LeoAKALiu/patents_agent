from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable


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
    ) -> ProviderTaskResult:
        last_failure: ProviderFailure | None = None
        for attempt in range(1, 3):
            command, args = build_provider_command(provider_id, workdir, attempt)
            try:
                exit_code, stdout, stderr = await self.spawn_func(command, args, workdir, prompt, task_timeout_ms)
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
                last_failure = exc
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
    process = await asyncio.create_subprocess_exec(
        command,
        *args,
        cwd=str(workdir),
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
    if command == "codex":
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
