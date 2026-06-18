from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "v1_api_smoke.py"


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("v1_api_smoke", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_golden_cases_cover_required_v1_1_categories():
    smoke = load_smoke_module()

    categories = {case.category for case in smoke.GOLDEN_CASES}

    assert {"software", "sensing_inspection", "mechanical_device", "algorithmic"}.issubset(categories)
    assert len(smoke.GOLDEN_CASES) >= 5
    for case in smoke.GOLDEN_CASES:
        assert smoke.SAMPLES[case.sample].exists()
        assert case.category in smoke.RESEARCH_SEEDS


def test_failure_classification_distinguishes_code_environment_and_provider():
    smoke = load_smoke_module()

    assert smoke._classify_failure(AssertionError("gate failed")) == "code"
    assert smoke._classify_failure(RuntimeError("missing sample: samples/foo.md")) == "environment"
    assert smoke._classify_failure(RuntimeError("provider not configured: DEEPSEEK_API_KEY")) == "unavailable_provider"


def test_quality_report_contains_trends_gates_and_live_boundary(tmp_path):
    smoke = load_smoke_module()
    workflow = {
        "workflow": "software",
        "category": "software",
        "project_id": "p1",
        "official_compile_id": "c1",
        "post_draft_review_id": "r1",
        "official_package_hash": "hash",
        "research_evidence_count": 2,
        "research_confidence": "medium",
        "grantability": {"status": "medium", "fail_closed": False, "claim_chart_rows": 2},
        "quality_trend": {field: 80 for field in smoke.TREND_FIELDS},
        "drafting_quality": {
            "evidence_binding_rate": 0.8,
            "core_feature_support_rate": 0.75,
            "unsupported_core_feature_count": 1,
            "unverified_effect_leak_count": 0,
            "dependent_fallback_depth": 2,
            "embodiment_density": 0.6,
            "patch_delta": 1,
        },
        "gates": {
            "research_evidence_count": {"passed": True, "expected": ">=2", "actual": "2"},
            "official_export_hygiene": {"passed": True, "expected": "clean", "actual": "clean"},
            "evidence_binding_rate": {"passed": True, "expected": ">=0.1", "actual": "0.8"},
            "core_feature_support_rate": {"passed": True, "expected": ">=0.4", "actual": "0.75"},
            "unverified_effect_leak_count": {"passed": True, "expected": "0", "actual": "0"},
        },
    }

    report = smoke._build_report([workflow], [])
    smoke._write_report(tmp_path, report)

    md = (tmp_path / "v1_1_quality_report.md").read_text(encoding="utf-8")
    assert "live_provider_tests: opt-in only" in md
    assert "authorization_stability" in md
    assert "evidence_binding_rate" in md
    assert "core_feature_support_rate" in md
    assert "official_export_hygiene" in md
    assert (tmp_path / "v1_1_quality_report.json").exists()


def test_drafting_quality_metrics_are_deterministic():
    smoke = load_smoke_module()

    metrics = smoke._drafting_quality_metrics(
        {
            "support_matrix": [
                {
                    "feature_classification": "core_combo",
                    "completion_status": "supported",
                    "evidence_refs": ["E1"],
                    "description_refs": ["description:auto-match"],
                    "embodiment_refs": [],
                    "formula_refs": [],
                    "data_structure_refs": ["description:data-structure"],
                    "pseudo_code_refs": [],
                },
                {
                    "feature_classification": "core_combo",
                    "completion_status": "missing",
                    "evidence_refs": [],
                    "description_refs": [],
                    "embodiment_refs": [],
                    "formula_refs": [],
                    "data_structure_refs": [],
                    "pseudo_code_refs": [],
                },
                {
                    "feature_classification": "dependent_fallback",
                    "completion_status": "partial",
                    "evidence_refs": [],
                    "description_refs": ["description:auto-match"],
                    "embodiment_refs": [],
                    "formula_refs": [],
                    "data_structure_refs": [],
                    "pseudo_code_refs": [],
                },
            ],
            "issues": [{"category": "unverified_scheme_gap", "blocks_submission": False}],
            "patches": [
                {"can_enter_official_draft": True, "evidence_refs": ["E1"], "patch_kind": "insert"},
                {"can_enter_official_draft": False, "evidence_refs": [], "patch_kind": "sidecar_only"},
            ],
        }
    )

    assert metrics["evidence_binding_rate"] == 0.333
    assert metrics["core_feature_support_rate"] == 0.5
    assert metrics["unsupported_core_feature_count"] == 1
    assert metrics["unverified_effect_leak_count"] == 0
    assert metrics["dependent_fallback_depth"] == 1
    assert metrics["embodiment_density"] == 0.667
    assert metrics["patch_delta"] == 0
