from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

SectionName = Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]

SECTION_KEYWORDS: list[tuple[SectionName, tuple[str, ...]]] = [
    ("title", ("标题", "方法方法")),
    ("abstract", ("摘要",)),
    ("claims", ("权利要求", "权利要求书", "claim")),
    ("description", ("说明书", "具体实施方式", "有益效果", "背景技术")),
    ("drawing_description", ("附图说明", "图1", "图2", "图3")),
]

CONTAMINATION_TERMS = (
    "好的，根据",
    "注：",
    "待验证",
    "补充实施方式",
    "主席修订",
    "主席补充",
    "需补充",
    "提交前补充",
    "方法方法",
    "颠覆",
)


def infer_target_section(message: str | None) -> SectionName:
    text = message or ""
    for section, keywords in SECTION_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return section
    return "unknown"


def _clean_snippet(snippet: str | None) -> str | None:
    if not snippet:
        return None
    value = re.sub(r"\s+", " ", snippet).strip()
    return value or None


def locate_issue_anchor(
    sections: dict[str, str],
    *,
    target_section: SectionName,
    snippet: str | None,
) -> dict[str, Any]:
    clean = _clean_snippet(snippet)
    candidate_sections = [target_section] if target_section != "unknown" else []
    candidate_sections.extend(
        section for section in ("title", "abstract", "claims", "description", "drawing_description")
        if section not in candidate_sections
    )

    if clean:
        for section in candidate_sections:
            text = sections.get(section, "") or ""
            index = text.find(clean)
            if index >= 0:
                return {
                    "type": "text",
                    "section": section,
                    "start": index,
                    "end": index + len(clean),
                    "snippet": clean,
                }

    contamination_sections = [target_section] if target_section != "unknown" else candidate_sections
    for term in CONTAMINATION_TERMS:
        for section in contamination_sections:
            text = sections.get(section, "") or ""
            index = text.find(term)
            if index >= 0:
                return {
                    "type": "text",
                    "section": section,
                    "start": index,
                    "end": index + len(term),
                    "snippet": term,
                }

    if target_section != "unknown":
        return {"type": "section", "section": target_section, "start": None, "end": None, "snippet": clean}

    return {"type": "missing", "section": "unknown", "start": None, "end": None, "snippet": clean}


def _issue_id(kind: str, index: int, message: str) -> str:
    digest = hashlib.sha1(f"{kind}:{index}:{message}".encode("utf-8")).hexdigest()[:10]
    return f"{kind}-{digest}"


def _append_review_item(items: list[tuple[str, str, str | None]], kind: str, value: Any) -> None:
    if isinstance(value, dict):
        message = str(value.get("content") or value.get("snippet") or value).strip()
        snippet = value.get("snippet")
        snippet_text = str(snippet).strip() if snippet is not None else None
    else:
        message = str(value).strip()
        snippet_text = None
    if message:
        items.append((kind, message, snippet_text))


def _iter_review_items(review: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    items: list[tuple[str, str, str | None]] = []
    for value in review.get("blocking_issues") or []:
        _append_review_item(items, "blocking", value)
    for value in review.get("contamination_hits") or []:
        _append_review_item(items, "hit", value)
    for value in review.get("rewrite_suggestions") or []:
        _append_review_item(items, "suggestion", value)

    for role_result in review.get("role_results") or []:
        if not isinstance(role_result, dict):
            continue
        for value in role_result.get("blocking_issues") or []:
            _append_review_item(items, "blocking", value)
        for value in role_result.get("contamination_hits") or []:
            _append_review_item(items, "hit", value)
        for value in role_result.get("rewrite_suggestions") or []:
            _append_review_item(items, "suggestion", value)

    chair_result = review.get("chair_result")
    if isinstance(chair_result, dict):
        for value in chair_result.get("blocking_issues") or []:
            _append_review_item(items, "blocking", value)
        for value in chair_result.get("contamination_hits") or []:
            _append_review_item(items, "hit", value)
        for value in chair_result.get("description_rewrite_tasks") or []:
            _append_review_item(items, "suggestion", value)
        for value in chair_result.get("next_actions") or []:
            _append_review_item(items, "suggestion", value)

    deduped: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for item in items:
        key = (item[0], item[1], item[2])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def normalize_post_draft_issues(review: dict[str, Any], sections: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, (kind, message, snippet) in enumerate(_iter_review_items(review)):
        target_section = infer_target_section(message)
        anchor = locate_issue_anchor(sections, target_section=target_section, snippet=snippet or message)
        status = "unanchored" if anchor["type"] == "missing" else "open"
        severity = "critical" if kind == "blocking" else "high" if kind == "hit" else "medium"
        issues.append(
            {
                "id": _issue_id(kind, index, message),
                "kind": kind,
                "severity": severity,
                "source": "post_draft_review",
                "message": message,
                "snippet": snippet,
                "target_section": anchor["section"] if anchor["section"] != "unknown" else target_section,
                "anchor": anchor,
                "status": status,
            }
        )
    return issues
