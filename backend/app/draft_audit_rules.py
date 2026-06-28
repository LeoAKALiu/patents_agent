from __future__ import annotations

import hashlib
import re

from backend.app.schemas import CompletionIssue, DisclosureRun, DraftPackage


RESOURCE_SUPERSCRIPT_RE = re.compile(
    r"\^\{?(?:cpu|mem|io|gpu|peak|latency|throughput)\}?",
    re.IGNORECASE,
)
PUBLICATION_RE = re.compile(r"\b(?:CN|WO|US|EP|JP|KR)\s?\d{5,}[A-Z]\d?\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://")
INTERNAL_METADATA_RE = re.compile(
    r"(evidence_id|evidence_refs|research_ledger|generation_logs|provider_diagnostics|self_check|自检结果|检索来源台账)",
    re.IGNORECASE,
)


def audit_draft_package(
    package: DraftPackage,
    disclosures: list[DisclosureRun] | None = None,
) -> list[CompletionIssue]:
    del disclosures

    issues: list[CompletionIssue] = []
    combined_text = "\n".join([package.claims, package.description, package.drawing_description])
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
    if _has_publication_without_url(package.description):
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
    if INTERNAL_METADATA_RE.search(combined_text):
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
    return bool(PUBLICATION_RE.search(text)) and not URL_RE.search(text)


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
