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


def contains_internal_metadata_field(text: str) -> bool:
    return bool(INTERNAL_METADATA_LINE_RE.search(text) or INTERNAL_METADATA_JSON_RE.search(text))


def contains_internal_metadata_marker(text: str) -> bool:
    return bool(contains_internal_metadata_field(text) or INTERNAL_METADATA_TOKEN_RE.search(text))
