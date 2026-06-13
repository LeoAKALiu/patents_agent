from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.schemas import PatentType, ProjectRecord

from backend.app.schemas import PatentType

UTILITY_MODEL_MODE_PREFIX = "目标模式：实用新型轻量版。"
UTILITY_MODEL_MARKERS = (
    "目标模式：实用新型",
    "专利类型：实用新型",
)


def is_utility_model_text(text: str | None) -> bool:
    """Legacy text-based detector. Kept for backward compatibility with
    existing projects that encode the type only as a Chinese marker in
    ``draft_text``. Prefer :func:`is_utility_model_project` for new code
    — it consults the explicit ``patent_type`` field first.
    """

    value = text or ""
    return any(marker in value for marker in UTILITY_MODEL_MARKERS)


def resolve_patent_type(
    project: "ProjectRecord | None",
    *,
    draft_text: str | None = None,
) -> PatentType:
    """Return the explicit patent type for ``project`` (or, when
    ``project`` is missing, for the provided ``draft_text``).  The explicit
    ``utility_model`` value on the record takes priority; otherwise the
    legacy ``draft_text`` marker is used as a fallback so that projects
    created before PR3 still classify correctly.  The default
    ``invention`` value does NOT block the fallback — only an explicit
    ``utility_model`` short-circuits.
    """

    if project is not None:
        # Explicit utility_model always wins.
        field_value = getattr(project, "patent_type", None)
        if field_value is not None:
            if isinstance(field_value, PatentType):
                if field_value == PatentType.UTILITY_MODEL:
                    return PatentType.UTILITY_MODEL
            else:
                try:
                    if PatentType(field_value) == PatentType.UTILITY_MODEL:
                        return PatentType.UTILITY_MODEL
                except ValueError:
                    pass
        # Fallback: legacy text-based detection (catches pre-PR3 projects
        # and projects created without an explicit patent_type).
        if is_utility_model_text(project.draft_text):
            return PatentType.UTILITY_MODEL
        return PatentType.INVENTION
    if draft_text is not None and is_utility_model_text(draft_text):
        return PatentType.UTILITY_MODEL
    return PatentType.INVENTION


def is_utility_model_project(project: "ProjectRecord | None") -> bool:
    """Type-aware utility-model detector. Returns True when the explicit
    ``patent_type`` field is ``utility_model`` *or* the legacy string
    marker is present in ``draft_text`` (back-compat)."""

    return resolve_patent_type(project) is PatentType.UTILITY_MODEL
