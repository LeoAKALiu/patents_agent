from __future__ import annotations

from dataclasses import dataclass

from backend.app.schemas import AgentDoctorReport

DELIBERATION_CHAIR_PROVIDER = "codex"
DELIBERATION_EXPERT_SEAT_COUNT = 3
STRICT_DELIBERATION_PROVIDERS = ("codex", "deepseek", "claude")


@dataclass(frozen=True, slots=True)
class AgentCapability:
    provider_id: str
    role: str
    output_modes: frozenset[str]
    supports_streaming: bool = False
    supports_resume: bool = False
    supports_cancel: bool = False
    supports_artifacts: bool = False
    max_context_tokens: int | None = None


DEFAULT_AGENT_CAPABILITIES: tuple[AgentCapability, ...] = (
    AgentCapability("codex", "deliberation", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("codex", "formula", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("codex", "chair", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("deepseek", "deliberation", frozenset({"json"})),
    AgentCapability("deepseek", "formula", frozenset({"json"})),
    AgentCapability("deepseek", "critic", frozenset({"json"})),
    AgentCapability("claude", "deliberation", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("claude", "formula", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("claude", "critic", frozenset({"json"}), supports_artifacts=True),
    AgentCapability("kimicode", "deliberation", frozenset({"json"})),
    AgentCapability("kimicode", "formula", frozenset({"json"})),
    AgentCapability("kimicode", "critic", frozenset({"json"})),
    AgentCapability("mimo", "deliberation", frozenset({"json"})),
    AgentCapability("mimo", "formula", frozenset({"json"})),
    AgentCapability("mimo", "critic", frozenset({"json"})),
    AgentCapability(
        "langgraph-local",
        "workflow",
        frozenset({"json"}),
        supports_streaming=True,
        supports_resume=True,
        supports_cancel=True,
        supports_artifacts=True,
    ),
)


def selectable_agent_provider_ids(doctor: AgentDoctorReport) -> set[str]:
    return (
        set(doctor.active_provider_ids)
        | set(doctor.unknown_required)
        | {provider_id for provider_id, status in doctor.commands.items() if status.selectable}
    )


def agent_provider_ids_for_role(doctor: AgentDoctorReport, requested: list[str], role: str) -> list[str]:
    provider_role = "deliberation" if role == "post_review" else role
    normalized: list[str] = []
    for provider_id in STRICT_DELIBERATION_PROVIDERS:
        if provider_id not in normalized:
            normalized.append(provider_id)
    for provider_id in requested:
        if provider_id in normalized:
            continue
        status = doctor.commands.get(provider_id)
        if not status or not status.selectable:
            continue
        if provider_role not in status.roles:
            continue
        normalized.append(provider_id)
    return normalized
