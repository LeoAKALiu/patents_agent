from __future__ import annotations

import json
from pathlib import Path

from golden_patent_evaluator import evaluate_golden_case


CASE_ROOT = Path(__file__).resolve().parent / "golden_patent_cases"
REQUIRED_CATEGORIES = {
    "invention",
    "utility_model",
    "existing_draft",
    "low_evidence",
    "internal_pollution",
}
THRESHOLD_FIELDS = {
    "claim_feature_coverage",
    "spec_support_coverage",
    "official_cleanliness",
    "evidence_honesty",
}


def test_golden_patent_case_fixtures_cover_required_quality_categories() -> None:
    cases = _load_cases()

    categories = {case["category"] for case in cases}

    assert REQUIRED_CATEGORIES.issubset(categories)
    assert len(cases) >= 5


def test_golden_patent_case_schema_has_quality_oracle_contract() -> None:
    for case in _load_cases():
        assert case["case_id"]
        assert case["category"] in REQUIRED_CATEGORIES
        assert case["application_type"] in {"invention", "utility_model"}
        assert case["input_kind"] in {"idea", "existing_draft"}
        assert case["technical_idea"] or case["existing_draft"]
        assert case["key_innovations"]
        assert case["prior_art_summary"]
        assert case["required_distinguishing_features"]
        assert case["forbidden_official_content"]
        assert set(case["expected_quality_thresholds"]) == THRESHOLD_FIELDS
        assert all(0 <= value <= 1 for value in case["expected_quality_thresholds"].values())
        assert case["deterministic_checks"]["release_blocker"] is True
        assert case["llm_judge"]["release_blocker"] is False


def test_uncalibrated_golden_cases_are_not_enabled_as_release_blockers() -> None:
    for case in _load_cases():
        calibration = case["human_calibration"]
        assert calibration["status"] in {"pending_human_review", "calibrated"}
        if calibration["status"] != "calibrated":
            assert case["release_gate_enabled"] is False


def test_golden_case_evaluator_accepts_text_covering_features_and_support() -> None:
    for case in _load_cases():
        official_text = _supported_official_text(case)

        result = evaluate_golden_case(case, official_text)

        assert result["passed"] is True
        for field, threshold in case["expected_quality_thresholds"].items():
            assert result["metrics"][field] >= threshold


def test_golden_case_evaluator_flags_forbidden_low_evidence_content() -> None:
    case = next(item for item in _load_cases() if item["category"] == "low_evidence")
    official_text = _supported_official_text(case) + "\n实验表明，效率提升30%，该效果已验证。"

    result = evaluate_golden_case(case, official_text)

    assert result["passed"] is False
    assert result["metrics"]["evidence_honesty"] < 1
    assert result["metrics"]["official_cleanliness"] < 1
    assert {"效率提升30%", "已验证", "实验表明"}.issubset(set(result["violations"]["forbidden_official_content"]))


def _load_cases() -> list[dict]:
    case_paths = sorted(CASE_ROOT.glob("*/case.json"))
    assert case_paths, f"No golden patent cases found under {CASE_ROOT}"
    cases = []
    for path in case_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["case_id"] == path.parent.name
        cases.append(payload)
    return cases


def _supported_official_text(case: dict) -> str:
    features = "；".join(case["required_distinguishing_features"])
    innovations = "；".join(case["key_innovations"])
    return (
        f"# {case['case_id']}\n"
        "## 权利要求书\n"
        f"1. 一种技术方案，其特征在于，包括{features}。\n"
        "2. 根据权利要求1所述的技术方案，其中还包括分层兜底特征。\n"
        "## 说明书\n"
        f"本发明针对现有技术问题，采用{features}形成技术手段，并通过{innovations}提供对应支撑。\n"
        f"相对于现有技术，{case['prior_art_summary']}，本发明至少包括{features}。\n"
    )
