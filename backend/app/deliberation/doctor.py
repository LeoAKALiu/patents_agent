from __future__ import annotations

import shutil
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


def inspect_agent_environment(
    command_lookup: Callable[[str], str | None] | None = None,
) -> AgentDoctorReport:
    lookup = command_lookup or shutil.which
    commands: dict[str, AgentProviderStatus] = {}
    active_provider_ids: list[str] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for provider_id, definition in PROVIDERS.items():
        command = definition["command"]
        path = lookup(command) or ""
        available = bool(path)
        commands[provider_id] = AgentProviderStatus(
            id=provider_id,
            label=str(definition["label"]),
            command=str(command),
            required=bool(definition["required"]),
            available=available,
            path=path,
            model_version=str(definition.get("model_version", "")),
            roles=[str(role) for role in definition.get("roles", [])],
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
