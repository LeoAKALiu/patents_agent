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
        "gates": {
            "research_evidence_count": {"passed": True, "expected": ">=2", "actual": "2"},
            "official_export_hygiene": {"passed": True, "expected": "clean", "actual": "clean"},
        },
    }

    report = smoke._build_report([workflow], [])
    smoke._write_report(tmp_path, report)

    md = (tmp_path / "v1_1_quality_report.md").read_text(encoding="utf-8")
    assert "live_provider_tests: opt-in only" in md
    assert "authorization_stability" in md
    assert "official_export_hygiene" in md
    assert (tmp_path / "v1_1_quality_report.json").exists()
