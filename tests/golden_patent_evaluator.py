from __future__ import annotations

import re
from typing import Any


EVIDENCE_HONESTY_MARKERS = (
    "已验证",
    "实验表明",
    "效率提升30%",
    "模型生成但未验证",
    "可行未验证",
)


def evaluate_golden_case(case: dict[str, Any], official_text: str) -> dict[str, Any]:
    required_features = [str(item) for item in case["required_distinguishing_features"]]
    forbidden = [str(item) for item in case["forbidden_official_content"]]
    claim_text = _section_text(official_text, "权利要求书")
    spec_text = _section_text(official_text, "说明书")

    claim_feature_coverage = _coverage(required_features, claim_text)
    spec_support_coverage = _coverage(required_features, spec_text)
    forbidden_hits = _hits(forbidden, official_text)
    honesty_hits = _hits(EVIDENCE_HONESTY_MARKERS, official_text)
    official_cleanliness = 1.0 if not forbidden_hits else 0.0
    evidence_honesty = 1.0 if not honesty_hits else 0.0

    metrics = {
        "claim_feature_coverage": claim_feature_coverage,
        "spec_support_coverage": spec_support_coverage,
        "official_cleanliness": official_cleanliness,
        "evidence_honesty": evidence_honesty,
    }
    thresholds = case["expected_quality_thresholds"]
    threshold_failures = {
        field: {"actual": metrics[field], "threshold": thresholds[field]}
        for field in thresholds
        if metrics[field] < thresholds[field]
    }
    violations = {
        "forbidden_official_content": forbidden_hits,
        "evidence_honesty": honesty_hits,
        "thresholds": threshold_failures,
    }
    return {
        "case_id": case["case_id"],
        "passed": not threshold_failures,
        "metrics": metrics,
        "violations": violations,
    }


def _coverage(needles: list[str], haystack: str) -> float:
    if not needles:
        return 1.0
    matched = sum(1 for needle in needles if needle and needle in haystack)
    return round(matched / len(needles), 3)


def _hits(needles: tuple[str, ...] | list[str], haystack: str) -> list[str]:
    return [needle for needle in needles if needle and needle in haystack]


def _section_text(text: str, heading: str) -> str:
    pattern = re.compile(rf"##\s*{re.escape(heading)}\s*(.*?)(?=\n##\s|\Z)", re.S)
    match = pattern.search(text)
    if match:
        return match.group(1)
    return text
