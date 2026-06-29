from __future__ import annotations

import hashlib
import re

from backend.app.internal_metadata import contains_internal_metadata_marker
from backend.app.patent_urls import (
    is_supported_public_patent_url,
    normalize_url as normalize_public_url,
)
from backend.app.schemas import CompletionIssue, DisclosureRun, DraftPackage


RESOURCE_SUPERSCRIPT_RE = re.compile(
    r"\^\{?(?:cpu|mem|io|gpu|peak|latency|throughput)\}?",
    re.IGNORECASE,
)
PUBLICATION_RE = re.compile(r"\b(?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def audit_draft_package(
    package: DraftPackage,
    disclosures: list[DisclosureRun] | None = None,
) -> list[CompletionIssue]:
    del disclosures

    issues: list[CompletionIssue] = []
    combined_text = "\n".join(
        [
            package.title,
            package.abstract,
            package.claims,
            package.description,
            package.drawing_description,
        ]
    )
    if RESOURCE_SUPERSCRIPT_RE.search(combined_text):
        issues.append(
            _issue(
                category="format_pollution",
                severity="medium",
                target="description",
                message="公式或权利要求中存在资源维度上标写法，建议改为下标加正体维度名。",
                suggested_action="将 b^{cpu}、a^{mem} 等改为 b_{i,\\mathrm{cpu}}、a_{j,\\mathrm{mem}} 等形式，并同步符号表。",
                blocks_submission=False,
            )
        )
    if _has_publication_without_url(combined_text):
        issues.append(
            _issue(
                category="prior_art_distinction_gap",
                severity="medium",
                target="prior_art",
                message="说明书现有技术段出现公开号但缺少可核验公开 URL。",
                suggested_action="为每个现有技术条目补充 CNIPA 或 Google Patents 等公开链接。",
                blocks_submission=False,
            )
        )
    if contains_internal_metadata_marker(combined_text):
        issues.append(
            _issue(
                category="format_pollution",
                severity="high",
                target="export",
                message="草稿包含内部元信息，不能进入正式稿或清洁交底书。",
                suggested_action="删除 evidence/source/log/self-check 等内部字段，保留在内部侧车报告。",
                blocks_submission=True,
            )
        )
    if _diagram_expected(package) and not package.mermaid.strip():
        issues.append(
            _issue(
                category="format_pollution",
                severity="low",
                target="drawing",
                message="草稿引用图示但缺少 Mermaid 图。",
                suggested_action="补充可渲染 Mermaid 系统框图或流程图。",
                blocks_submission=False,
            )
        )
    return issues


def _has_publication_without_url(text: str) -> bool:
    publication_matches = list(PUBLICATION_RE.finditer(text))
    if not publication_matches:
        return False

    url_matches = list(URL_RE.finditer(text))
    normalized_urls = [_normalize_url(match.group(0)) for match in url_matches]
    for publication in publication_matches:
        normalized_publication = _normalize_publication(publication.group(0))
        if not normalized_publication:
            continue
        if any(
            normalized_publication in url.upper() and _is_allowed_public_patent_url(url)
            for url in normalized_urls
        ):
            continue
        window_start, window_end = _publication_clause_bounds(text, publication.start(), publication.end())
        if any(
            _is_strictly_bound_patent_url(
                text=text,
                publication=publication,
                url_match=match,
                window_start=window_start,
                window_end=window_end,
            )
            for match in url_matches
        ):
            continue
        return True
    return False


def _normalize_publication(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _normalize_url(value: str) -> str:
    return normalize_public_url(value)


def _publication_clause_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left = max(
        text.rfind(marker, 0, start)
        for marker in ("\n", "。", "；", ";")
    )
    right_candidates = [position for marker in ("\n", "。", "；", ";") if (position := text.find(marker, end)) != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return (left + 1 if left >= 0 else 0, right)


def _is_strictly_bound_patent_url(
    *,
    text: str,
    publication: re.Match[str],
    url_match: re.Match[str],
    window_start: int,
    window_end: int,
) -> bool:
    if url_match.start() < window_start or url_match.end() > window_end:
        return False
    url = _normalize_url(url_match.group(0))
    if not _is_allowed_public_patent_url(url):
        return False
    normalized_publication = _normalize_publication(publication.group(0))
    if normalized_publication in url.upper():
        return True

    if publication.end() <= url_match.start() and _is_immediate_publication_url_binding(
        text[publication.end() : url_match.start()]
    ):
        return True

    return url_match.end() <= publication.start() and _is_immediate_publication_url_binding(
        text[url_match.end() : publication.start()]
    )


def _is_allowed_public_patent_url(url: str) -> bool:
    return is_supported_public_patent_url(url)


def _is_immediate_publication_url_binding(text: str) -> bool:
    if len(text) > 24 or PUBLICATION_RE.search(text):
        return False
    return bool(
        re.fullmatch(
            r"\s*(?:[（(【\[]?\s*)?(?:公开链接|公开URL|链接|URL|url|参见|见|载于|位于)?\s*[:：\-—,，；;、]?\s*(?:[）)】\]]?\s*)?",
            text,
            flags=re.IGNORECASE,
        )
    )


def _diagram_expected(package: DraftPackage) -> bool:
    text = "\n".join([package.description, package.drawing_description, package.image_prompt])
    return any(marker in text for marker in ("系统框图", "流程图", "图示", "图1", "附图"))


def _issue(
    *,
    category: str,
    severity: str,
    target: str,
    message: str,
    suggested_action: str,
    blocks_submission: bool,
) -> CompletionIssue:
    digest = hashlib.sha256(f"{category}|{severity}|{target}|{message}".encode("utf-8")).hexdigest()[:8]
    return CompletionIssue(
        id=f"i-audit-{digest}",
        category=category,
        severity=severity,
        target=target,
        source_refs=["draft_audit_rules"],
        message=message,
        why_it_matters="该问题会影响交底书清洁度、说明书支撑或正式提交成熟度。",
        suggested_action=suggested_action,
        blocks_submission=blocks_submission,
    )
