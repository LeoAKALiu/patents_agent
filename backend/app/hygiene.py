"""Package-save hygiene: strip or sidecar non-patent content before
the DraftPackage is persisted.

The official compile gate catches contamination that reaches it, but legacy
exports (``/export.docx``, ``/export.md``) bypass the gate.  This module runs
BEFORE the package hits the store so that obvious LLM-prompt leakage,
conversational prefaces, Markdown, support-gap markers, and internal traces
are cleaned from the patent-body fields at save time.

Kept conceptually separate from ``official_compile.py`` because the compile
step must also be able to block on contamination that survives cleaning, but
the order is always: clean → compile → gate.
"""

from __future__ import annotations

import re

from backend.app.schemas import DraftPackage, ReviewFinding

# ── patterns carried forward from official_compile.py ────────────────────────
_CONVERSATIONAL_PREFACE_RE = re.compile(r"^好的[，,]下面.*撰写")

# Annotation-style support-gap markers. Each entry is a (label, require_separator)
# pair where ``require_separator`` means the label must be followed by a label
# separator (``[:：=]``) on the same line to count as a marker. The English
# ``support_gap(s)`` label is always required to have a separator (it is a JSON
# key form); the Chinese labels only count as a marker when they appear as
# the leading label of the line — background prose that merely *mentions*
# 支撑不足提示/撰写说明 must survive.
_SUPPORT_GAP_ANNOTATION_PATTERNS = (
    re.compile(
        r"""^\s*["']?(?:support_gaps?)["']?\s*[:：=]""",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*撰写说明(?:\s*[:：]|\s*与\s*支撑不足提示\b)"),
    re.compile(r"^\s*支撑不足提示\s*[:：]"),
)

_INTERNAL_FIELD_PATTERNS = (
    "image_prompt",
    "prompt",
    "diagram",
    "generation_logs",
    "attorney_memo",
    "system_trace",
    "official_safe_patches",
)

# Catch "image_prompt: …" and similar key:value lines (case-insensitive).
_INTERNAL_FIELD_RE = re.compile(
    r"""^\s*["']?(image_prompt|prompt|diagram|generation_logs|attorney_memo|system_trace|official_safe_patches|mermaid)["']?\s*[:：=]""",
    re.IGNORECASE,
)

# Lines that are nothing but JSON wrapper chars.
_JSON_WRAPPER_RE = re.compile(r"^[{}\[\],]+$")

# Empty official-field JSON lines e.g.  "title": ""
_EMPTY_OFFICIAL_FIELD_RE = re.compile(
    r"""^\s*["']?(title|abstract|claims|description|drawing_description)["']?\s*[:：=]\s*["']?\s*["']?\s*,?\s*$""",
    re.IGNORECASE,
)

_INTERNAL_TRACE_PATTERNS = (
    "根据会审策略",
    "多 agent 会审",
    "多agent会审",
    "主席汇总",
    "deliberation",
    "generation_logs",
)

_UNFAVORABLE_STATEMENTS = (
    "可能不具备创造性",
    "禁止直接提交",
    "存在充分公开风险",
)

_MERMAID_STARTERS = (
    "flowchart",
    "graph",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "erdiagram",
    "gantt",
)

_MERMAID_ARROW_RE = re.compile(r"\w+\s*(-->|---|==>|-.->)\s*\w+")

# Title indicates a QA/test project rather than a real filing.
_QA_TITLE_RE = re.compile(r"(?i)^(qa[-_]|test[-_]|tauri[-_])(.*)")

# ── cleaning logic ────────────────────────────────────────────────────────────


def _strip_inline_markdown(line: str) -> str:
    """Remove leading Markdown heading markers."""
    return re.sub(r"^\s*#{1,6}\s*", "", line).strip()


def _looks_like_mermaid(line: str) -> bool:
    lower = line.strip().lower()
    for starter in _MERMAID_STARTERS:
        if lower.startswith(starter):
            return True
    return bool(_MERMAID_ARROW_RE.search(lower))


def _is_conversational(line: str) -> bool:
    return bool(_CONVERSATIONAL_PREFACE_RE.match(line))


def _is_support_gap_line(line: str) -> bool:
    """Return True when ``line`` is an annotation-style support-gap marker.

    A line counts as a marker only when the label appears in label/key
    position:

    - ``support_gap:`` / ``support_gaps:`` (English key form, including the
      quoted JSON form ``"support_gap":``)
    - ``撰写说明：`` / ``撰写说明与支撑不足提示 …`` (Chinese label form)
    - ``支撑不足提示：`` (Chinese label form)

    Normal background prose that happens to mention 支撑不足提示/撰写说明
    (e.g. "背景技术中存在传感器数据支撑不足提示的问题。") must NOT match.
    """
    return any(pattern.search(line) for pattern in _SUPPORT_GAP_ANNOTATION_PATTERNS)


def _is_internal_field_line(line: str) -> bool:
    return bool(_INTERNAL_FIELD_RE.match(line))


def _is_json_wrapper_line(line: str) -> bool:
    return bool(_JSON_WRAPPER_RE.match(line))


def _is_empty_official_field_line(line: str) -> bool:
    return bool(_EMPTY_OFFICIAL_FIELD_RE.match(line))


def _is_internal_trace_line(line: str) -> bool:
    lower = line.lower()
    return any(pattern.lower() in lower for pattern in _INTERNAL_TRACE_PATTERNS)


def _is_unfavorable_statement(line: str) -> bool:
    return any(pattern in line for pattern in _UNFAVORABLE_STATEMENTS)


def _should_remove_line(
    line: str,
    *,
    in_fence: bool,
) -> tuple[bool, str]:
    """Return ``(remove, category)`` for a single line.

    The ``category`` string describes WHY the line is removed — used to
    populate sidecar notes for transparency.
    """
    stripped = line.strip()
    if not stripped:
        return False, ""

    if in_fence:
        return True, "markdown_fence"

    if _is_conversational(stripped):
        return True, "conversational_preface"

    if _is_support_gap_line(stripped):
        return True, "support_gap"

    if _is_internal_field_line(stripped):
        return True, "internal_field"

    if _is_json_wrapper_line(stripped):
        return True, "json_wrapper"

    if _is_empty_official_field_line(stripped):
        return True, "empty_official_field"

    if _is_internal_trace_line(stripped):
        return True, "internal_trace"

    if _is_unfavorable_statement(stripped):
        return True, "unfavorable_statement"

    if _looks_like_mermaid(stripped):
        return True, "mermaid"

    # Markdown heading lines (##, ###, etc.) — remove the marker but keep text.
    if re.match(r"^#{1,6}\s+", stripped):
        return False, ""  # inline markdown strip handled below

    return False, ""


def _clean_text(text: str) -> tuple[str, list[dict[str, str]]]:
    """Clean a single text block (e.g. claims, description).

    Returns ``(cleaned_text, sidecar_items)``.  ``sidecar_items`` record every
    removed line for auditability.

    Fence handling: a line that starts with ```` ``` ```` is a fence toggle and
    is ALWAYS removed (both the opening ```` ```mermaid ```` line and the
    closing ```` ``` ```` line). The state flips on each toggle, so any
    content between toggles is also removed as ``markdown_fence`` pollution.
    This prevents the opening fence marker from leaking into patent fields
    when an LLM emits a fenced code block (mermaid, json, etc.) inline.
    """
    kept: list[str] = []
    sidecar: list[dict[str, str]] = []
    in_fence = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        # Fence toggles take priority over all other checks. A line that
        # starts with ``` is never patent content — it is the wrapper for
        # either a fenced code block or a closing marker. Remove it and
        # flip the in-fence state for subsequent lines.
        if stripped.startswith("```"):
            in_fence = not in_fence
            sidecar.append(
                {
                    "category": "markdown_fence",
                    "text": stripped[:200],
                    "pattern": "markdown_fence",
                }
            )
            continue

        if not stripped:
            if kept and kept[-1] != "":
                kept.append("")
            continue

        # If we are inside a fence block (between toggles), drop the line
        # as fence pollution. This catches mermaid/json/python bodies.
        if in_fence:
            sidecar.append(
                {
                    "category": "markdown_fence",
                    "text": stripped[:200],
                    "pattern": "markdown_fence",
                }
            )
            continue

        remove, category = _should_remove_line(stripped, in_fence=False)
        if remove:
            sidecar.append(
                {"category": category, "text": stripped[:200], "pattern": category}
            )
            continue

        # Strip inline markdown from kept lines
        cleaned = _strip_inline_markdown(line)
        if cleaned:
            kept.append(cleaned)
        elif kept and kept[-1] != "":
            kept.append("")

    return "\n".join(kept).strip(), sidecar


def _clean_title(title: str) -> tuple[str, list[dict[str, str]]]:
    """Clean the patent title field with extra rules."""
    sidecar: list[dict[str, str]] = []
    cleaned = title.strip()

    # Remove QA/test markers from title start
    qa_match = _QA_TITLE_RE.match(cleaned)
    if qa_match:
        # Keep only the portion after the QA prefix
        original = cleaned
        cleaned = qa_match.group(2).strip()
        if cleaned != original:
            sidecar.append(
                {
                    "category": "qa_title_marker",
                    "text": original[:200],
                    "pattern": "qa_prefix",
                }
            )

    # Remove conversational prefaces
    conv_match = _CONVERSATIONAL_PREFACE_RE.match(cleaned)
    if conv_match:
        original = cleaned
        cleaned = cleaned[conv_match.end() :].strip()
        if cleaned != original:
            sidecar.append(
                {
                    "category": "conversational_preface",
                    "text": original[:200],
                    "pattern": "好的，下面",
                }
            )

    # Remove internal trace phrases from title
    for pattern in _INTERNAL_TRACE_PATTERNS:
        if pattern.lower() in cleaned.lower():
            original = cleaned
            cleaned = re.sub(
                re.escape(pattern), "", cleaned, flags=re.IGNORECASE
            ).strip()
            if cleaned != original:
                sidecar.append(
                    {
                        "category": "internal_trace",
                        "text": original[:200],
                        "pattern": pattern,
                    }
                )

    # Remove unfavorable statements from title (unlikely but possible)
    for pattern in _UNFAVORABLE_STATEMENTS:
        if pattern in cleaned:
            original = cleaned
            cleaned = cleaned.replace(pattern, "").strip()
            if cleaned != original:
                sidecar.append(
                    {
                        "category": "unfavorable_statement",
                        "text": original[:200],
                        "pattern": pattern,
                    }
                )

    # Remove any remaining "方法。方法" or "系统。系统" suffix duplication
    while cleaned.endswith("方法。方法") or cleaned.endswith("系统。系统"):
        cleaned = cleaned.rsplit("。", 1)[0] + "。"
        sidecar.append(
            {
                "category": "duplicate_title_suffix",
                "text": cleaned[:200],
                "pattern": "duplicate_suffix",
            }
        )

    return cleaned.strip(), sidecar


def clean_draft_package(package: DraftPackage) -> tuple[DraftPackage, dict]:
    """Normalise a DraftPackage before saving, removing obvious LLM
    contamination from patent-body fields.

    This function is intentionally non-mutating: it returns a new
    ``DraftPackage`` instance (via ``model_copy``) so callers can keep the
    original around for auditing / retries. Mutating in-place made the
    function surprising to reason about and was a reviewer-flagged
    regression on PR-10.

    Returns ``(cleaned_package, sidecar)`` where ``sidecar`` is a dict of
    audit records keyed by field.
    """
    all_sidecar: dict[str, list[dict[str, str]]] = {}

    title, title_sidecar = _clean_title(package.title)
    if title_sidecar:
        all_sidecar["title"] = title_sidecar

    body_sidecar: dict[str, list[dict[str, str]]] = {}
    field_updates: dict[str, str] = {}
    for field in ("abstract", "claims", "description", "drawing_description"):
        original = getattr(package, field)
        cleaned, sidecar = _clean_text(original)
        if sidecar:
            body_sidecar[field] = sidecar
        if cleaned != original:
            field_updates[field] = cleaned

    if body_sidecar:
        all_sidecar.update(body_sidecar)

    # If title became empty after cleaning, use a fallback placeholder so the
    # package remains loadable.
    if not title.strip():
        field_updates["title"] = "(未命名发明)"
        all_sidecar.setdefault("title", []).append(
            {
                "category": "empty_title_fallback",
                "text": "title was empty after cleaning",
                "pattern": "fallback",
            }
        )
    elif title != package.title:
        field_updates["title"] = title

    if field_updates:
        package = package.model_copy(update=field_updates)

    return package, all_sidecar
