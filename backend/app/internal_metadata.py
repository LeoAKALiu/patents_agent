from __future__ import annotations

import re


INTERNAL_METADATA_KEYS = (
    "evidence_id",
    "evidence_refs",
    "research_ledger",
    "generation_logs",
    "provider_diagnostics",
    "self_check",
    "review_findings",
    "revision_ledger",
    "source_ledger",
    "sidecar_notes",
    "internal_only",
    "official_safe_patches",
    "attorney_memo",
    "system_trace",
    "material_id",
    "source_id",
    "source_label",
    "publication_number",
    "patent_url",
    "source_url",
    "url",
    "source",
    "sources",
    "reference",
    "references",
    "citation",
    "citations",
    "material",
    "materials",
    "patent_point",
    "修订记录",
    "检索来源台账",
    "自检结果",
    "证据编号",
    "材料编号",
    "来源标签",
    "引用来源",
    "引用链接",
    "证据来源",
    "参考资料",
    "参考文献",
    "资料来源",
    "依据材料",
    "支撑材料",
)

AMBIGUOUS_METADATA_TOKEN_KEYS = {
    "url",
    "source",
    "sources",
    "reference",
    "references",
    "citation",
    "citations",
    "material",
    "materials",
}

INTERNAL_METADATA_KEY_PATTERN = "|".join(re.escape(key) for key in INTERNAL_METADATA_KEYS)
UNAMBIGUOUS_METADATA_KEY_PATTERN = "|".join(
    re.escape(key) for key in INTERNAL_METADATA_KEYS if key not in AMBIGUOUS_METADATA_TOKEN_KEYS
)

INTERNAL_METADATA_LINE_RE = re.compile(
    rf"(?<![A-Za-z0-9_-])(?:[-*+]\s*)?(?:[\"']?)"
    rf"(?:{INTERNAL_METADATA_KEY_PATTERN})"
    rf"(?:[\"']?)\s*[:：=]",
    re.IGNORECASE,
)
INTERNAL_METADATA_JSON_RE = re.compile(
    rf"[\"'](?:{INTERNAL_METADATA_KEY_PATTERN})[\"']\s*[:：=]",
    re.IGNORECASE,
)
INTERNAL_METADATA_TOKEN_RE = re.compile(
    rf"(?<![A-Za-z0-9_-])(?:{UNAMBIGUOUS_METADATA_KEY_PATTERN})(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
DELIBERATION_TRACE_RE = re.compile(
    r"(?:"
    r"多\s*(?:智能体|代理|agent)\s*会审"
    r"|会审\s*(?:策略|主席|记录|意见|结果)"
    r"|agent\s*(?:对话|会审|角色|consensus)"
    r"|角色结果"
    r"|本轮启用\s*agent"
    r"|resolved_recommendation"
    r"|(?:codex|deepseek|claude|kimicode|kimi|mimo|gemini).{0,24}(?:主席|会审|交叉质询|角色结果|建议|认为)"
    r"|(?:主席|会审|交叉质询|角色结果).{0,24}(?:codex|deepseek|claude|kimicode|kimi|mimo|gemini)"
    r")",
    re.IGNORECASE,
)


def contains_internal_metadata_field(text: str) -> bool:
    return bool(INTERNAL_METADATA_LINE_RE.search(text) or INTERNAL_METADATA_JSON_RE.search(text))


def contains_internal_metadata_marker(text: str) -> bool:
    return bool(contains_internal_metadata_field(text) or INTERNAL_METADATA_TOKEN_RE.search(text))


def contains_deliberation_trace_marker(text: str) -> bool:
    return bool(DELIBERATION_TRACE_RE.search(text))
