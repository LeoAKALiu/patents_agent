from __future__ import annotations

from backend.app.agents.registry import (
    STRICT_DELIBERATION_PROVIDERS,
    agent_provider_ids_for_role,
    selectable_agent_provider_ids,
)
from backend.app.schemas import AgentDoctorReport, AgentProviderStatus


def _status(
    provider_id: str,
    *,
    available: bool,
    selectable: bool,
    roles: list[str],
    required: bool = False,
) -> AgentProviderStatus:
    return AgentProviderStatus(
        id=provider_id,
        label=provider_id,
        command=provider_id,
        available=available,
        required=required,
        roles=roles,
        installed=True,
        auth_status="ready" if available else "unknown",
        selectable=selectable,
    )


def test_registry_preserves_strict_deliberation_provider_order() -> None:
    assert STRICT_DELIBERATION_PROVIDERS == ("codex", "deepseek", "claude")


def test_provider_ids_for_role_prepends_strict_providers_and_filters_by_role() -> None:
    doctor = AgentDoctorReport(
        status="ready",
        run_mode="full",
        commands={
            "codex": _status("codex", available=True, selectable=True, roles=["deliberation"], required=True),
            "deepseek": _status("deepseek", available=True, selectable=True, roles=["deliberation"], required=True),
            "claude": _status("claude", available=True, selectable=True, roles=["deliberation"], required=True),
            "kimicode": _status("kimicode", available=False, selectable=True, roles=["deliberation", "formula"]),
            "gemini": _status("gemini", available=False, selectable=True, roles=["deprecated"]),
        },
        active_provider_ids=["codex", "deepseek", "claude"],
        missing_required=[],
        missing_optional=[],
        unknown_required=[],
    )

    selected = agent_provider_ids_for_role(doctor, ["gemini", "kimicode", "codex"], "deliberation")

    assert selected == ["codex", "deepseek", "claude", "kimicode"]


def test_selectable_provider_ids_include_unknown_required_and_selectable_optional() -> None:
    doctor = AgentDoctorReport(
        status="degraded",
        run_mode="partial",
        commands={
            "codex": _status("codex", available=True, selectable=True, roles=["deliberation"], required=True),
            "deepseek": _status("deepseek", available=False, selectable=False, roles=["deliberation"], required=True),
            "claude": _status("claude", available=True, selectable=True, roles=["deliberation"], required=True),
            "mimo": _status("mimo", available=False, selectable=True, roles=["deliberation"]),
        },
        active_provider_ids=["codex", "claude"],
        missing_required=[],
        missing_optional=[],
        unknown_required=["deepseek"],
    )

    assert selectable_agent_provider_ids(doctor) == {"codex", "deepseek", "claude", "mimo"}
