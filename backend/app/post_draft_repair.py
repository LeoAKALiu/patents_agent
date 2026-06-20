from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.llm import LLMClient

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


# --- PR3: single-issue AI patch lifecycle ----------------------------------

UNSAFE_PATCH_TERMS = (
    "好的，根据",
    "注：",
    "待验证",
    "主席",
    "补充实施方式",
    "需补充",
    "提交前补充",
    "{\"action\"",
    "\"patched\"",
)


def validate_repair_patch_text(text: str) -> list[str]:
    """Return any unsafe-patch terms found in *text*."""
    return [term for term in UNSAFE_PATCH_TERMS if term in text]


def apply_section_patch(section_text: str, original: str, patched: str) -> str:
    """Replace **original** with **patched** in *section_text* once.

    Raises :exc:`ValueError` when *original* is not present.
    """
    if original not in section_text:
        raise ValueError("Patch original text is no longer present")
    return section_text.replace(original, patched, 1)


def _deterministic_patch_text(original: str) -> str:
    """Clean known internal terms from *original* without calling an external model."""
    text = original
    text = re.sub(r"方法方法", "方法", text)
    text = re.sub(r"颠覆", "改变", text)
    text = re.sub(r"好的，根据", "", text)
    for term in ("注：", "待验证", "补充实施方式", "需补充", "提交前补充"):
        text = text.replace(term, "")
    text = re.sub(r"主席[^，。,\n]{0,10}", "", text)
    return text.strip()


def create_repair_patch_payload(
    issue_id: str,
    target_section: str,
    draft_package_hash: str,
    selected_text: str | None,
    nearby_context: str | None,
    *,
    project_id: str | None = None,
    review_run_id: str | None = None,
    issue_message: str | None = None,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Deterministic single-issue patch proposal.

    Returns a dict with keys ``id``, ``issue_id``, ``status``,
    ``target_section``, ``original``, ``patched``, ``diff_summary``,
    ``risk_notes``, ``draft_package_hash``.
    """
    original = (selected_text or nearby_context or "").strip()
    if not original:
        return {
            "id": _patch_id(issue_id, project_id=project_id, review_run_id=review_run_id),
            "issue_id": issue_id,
            "project_id": project_id or "",
            "review_run_id": review_run_id or "",
            "status": "stale",
            "target_section": target_section,
            "original": "",
            "patched": "",
            "diff_summary": "No selected text to patch.",
            "risk_notes": [],
            "draft_package_hash": draft_package_hash,
        }

    llm_patch = _try_llm_repair_patch(
        issue_id=issue_id,
        target_section=target_section,
        draft_package_hash=draft_package_hash,
        original=original,
        nearby_context=nearby_context,
        issue_message=issue_message,
        project_id=project_id,
        review_run_id=review_run_id,
        llm=llm,
    )
    if llm_patch is not None:
        return llm_patch

    patched = _deterministic_patch_text(original)
    patched_risks = validate_repair_patch_text(patched)
    cleaned_terms = validate_repair_patch_text(original)
    status: Literal["proposed", "stale", "unsafe", "applied"] = "unsafe" if patched_risks else "proposed"
    return {
        "id": _patch_id(issue_id, project_id=project_id, review_run_id=review_run_id),
        "issue_id": issue_id,
        "project_id": project_id or "",
        "review_run_id": review_run_id or "",
        "status": status,
        "target_section": target_section,
        "original": original,
        "patched": patched,
        "diff_summary": "补丁仍含不安全标记" if patched_risks else "清理重复与内部引导语",
        "risk_notes": patched_risks or cleaned_terms,
        "draft_package_hash": draft_package_hash,
    }


def _patch_id(issue_id: str, *, project_id: str | None = None, review_run_id: str | None = None) -> str:
    digest = hashlib.sha1(f"patch:{project_id or ''}:{review_run_id or ''}:{issue_id}".encode("utf-8")).hexdigest()[:12]
    return f"patch-{digest}"


REPAIR_PATCH_SYSTEM_PROMPT = """你是中国专利正式稿的局部修稿助手。
只对给定片段做最小必要修改，目标是提高正式稿清洁度、权利要求可执行性和说明书支撑一致性。
不要新增未在上下文中出现的技术事实，不要输出解释性前言，不要保留内部会审痕迹。
只输出 JSON 对象：{"patched":"修正后的片段","diff_summary":"一句话说明修改","risk_notes":["需要人工确认的风险"]}。"""


def _try_llm_repair_patch(
    *,
    issue_id: str,
    target_section: str,
    draft_package_hash: str,
    original: str,
    nearby_context: str | None,
    issue_message: str | None,
    project_id: str | None,
    review_run_id: str | None,
    llm: LLMClient | None,
) -> dict[str, Any] | None:
    if llm is None:
        return None

    try:
        raw = llm.complete_stage(
            "post_draft_repair_patch",
            REPAIR_PATCH_SYSTEM_PROMPT,
            _repair_patch_prompt(
                issue_message=issue_message,
                target_section=target_section,
                original=original,
                nearby_context=nearby_context,
            ),
        )
        parsed = _parse_llm_patch_json(raw)
    except Exception:
        return None

    patched = str(parsed.get("patched") or "").strip()
    if not patched:
        return None

    patched_risks = validate_repair_patch_text(patched)
    if patched_risks:
        return None

    risk_notes = parsed.get("risk_notes")
    if not isinstance(risk_notes, list):
        risk_notes = []

    return {
        "id": _patch_id(issue_id, project_id=project_id, review_run_id=review_run_id),
        "issue_id": issue_id,
        "project_id": project_id or "",
        "review_run_id": review_run_id or "",
        "status": "proposed",
        "target_section": target_section,
        "original": original,
        "patched": patched,
        "diff_summary": str(parsed.get("diff_summary") or "生成正式稿局部修正").strip(),
        "risk_notes": [str(note).strip() for note in risk_notes if str(note).strip()],
        "draft_package_hash": draft_package_hash,
    }


def _repair_patch_prompt(
    *,
    issue_message: str | None,
    target_section: str,
    original: str,
    nearby_context: str | None,
) -> str:
    return (
        f"问题：{issue_message or '未提供'}\n"
        f"目标段落：{target_section}\n"
        f"待修片段：\n{original}\n\n"
        f"附近上下文：\n{nearby_context or original}\n\n"
        "请返回一个只替换待修片段的正式稿 patch。"
    )


def _parse_llm_patch_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("LLM patch response must be a JSON object")
    return payload
