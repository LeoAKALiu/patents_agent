from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.schemas import ProjectRecord


UTILITY_MODEL_MODE_PREFIX = "目标模式：实用新型轻量版。"
UTILITY_MODEL_MARKERS = (
    "目标模式：实用新型",
    "专利类型：实用新型",
)


def is_utility_model_text(text: str | None) -> bool:
    value = text or ""
    return any(marker in value for marker in UTILITY_MODEL_MARKERS)


def is_utility_model_project(project: "ProjectRecord | None") -> bool:
    if project is None:
        return False
    return is_utility_model_text(project.draft_text)
