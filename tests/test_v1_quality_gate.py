from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "v1_api_smoke.py"
SMOKE_SH_PATH = Path(__file__).resolve().parents[1] / "scripts" / "v1_smoke.sh"


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
    workflow = _workflow_payload(smoke)

    report = smoke._build_report([workflow], [])
    smoke._write_report(tmp_path, report)

    md = (tmp_path / "v1_1_quality_report.md").read_text(encoding="utf-8")
    assert "live_provider_tests: opt-in only" in md
    assert "authorization_stability" in md
    assert "evidence_binding_rate" in md
    assert "core_feature_support_rate" in md
    assert "official_export_hygiene" in md
    assert "## Loop Engineering Gates" in md
    assert "full-process stability and reliability" in md
    assert (tmp_path / "v1_1_quality_report.json").exists()


def test_loop_gate_groups_cover_stability_reliability_and_final_draft_quality():
    smoke = load_smoke_module()

    groups = smoke.LOOP_GATE_GROUPS

    assert set(groups) == {"stability", "reliability", "final_draft_quality"}
    assert "quality_trend_present" in groups["stability"]
    assert "official_export_blocked_before_compile" in groups["reliability"]
    assert "official_export_blocked_before_review" in groups["reliability"]
    assert "post_draft_review_unlocks_export" in groups["reliability"]
    assert "grantability_report_present" in groups["final_draft_quality"]
    assert "core_feature_support_rate" in groups["final_draft_quality"]
    assert "unverified_effect_leak_count" in groups["final_draft_quality"]


def test_golden_grantability_uses_ready_project_knowledge_state():
    smoke = load_smoke_module()
    case = smoke.GOLDEN_CASES[0]

    state = smoke._golden_project_knowledge_state("project-1", case)

    assert state.project_id == "project-1"
    assert state.status == "ready"
    assert state.document_count == len(smoke.RESEARCH_SEEDS[case.category].prior_art)
    assert state.document_count >= 2
    assert state.candidate_count == state.document_count
    assert state.claim_coverage == 1.0
    assert state.fulltext_coverage == 1.0
    assert state.quality_flags == ["verified_golden_evidence"]


def test_release_smoke_runs_api_gate_with_repeatability_loop():
    smoke_sh = SMOKE_SH_PATH.read_text(encoding="utf-8")

    assert 'V1_1_REPEAT_COUNT="${PATENTAGENT_V1_1_REPEAT_COUNT:-2}"' in smoke_sh
    assert 'scripts/v1_api_smoke.py --repeat-count "$V1_1_REPEAT_COUNT" --report-dir "$V1_1_REPORT_DIR"' in smoke_sh


def test_loop_quality_signature_ignores_random_ids_and_preserves_quality_surface():
    smoke = load_smoke_module()
    first = _workflow_payload(
        smoke,
        project_id="p1",
        compile_id="c1",
        review_id="r1",
        official_package_hash="artifact-hash-1",
        grantability_id="grantability-1",
    )
    second = _workflow_payload(
        smoke,
        project_id="p2",
        compile_id="c2",
        review_id="r2",
        official_package_hash="artifact-hash-2",
        grantability_id="grantability-2",
    )

    assert smoke._loop_quality_signature(first) == smoke._loop_quality_signature(second)

    drifted = _workflow_payload(smoke, project_id="p2", compile_id="c2", review_id="r2")
    drifted["official_text_hash"] = "changed-official-text"

    assert smoke._loop_quality_signature(first) != smoke._loop_quality_signature(drifted)


def test_loop_repeatability_failures_report_quality_drift_between_rounds():
    smoke = load_smoke_module()
    first = _workflow_payload(smoke, project_id="p1", compile_id="c1", review_id="r1")
    second = _workflow_payload(smoke, project_id="p2", compile_id="c2", review_id="r2")
    third = _workflow_payload(smoke, project_id="p3", compile_id="c3", review_id="r3")
    second["quality_trend"]["overall"] = 79
    third["quality_trend"]["overall"] = 79

    failures = smoke._loop_repeatability_failures([first, second, third])

    assert failures == [
        {
            "workflow": "software",
            "category": "software",
            "classification": "code",
            "message": "loop repeatability drift detected for workflow software",
        }
    ]


def test_quality_report_uses_precomputed_repeatability_failures_and_separate_counters():
    smoke = load_smoke_module()
    first = _workflow_payload(smoke, project_id="p1", compile_id="c1", review_id="r1")
    second = _workflow_payload(smoke, project_id="p2", compile_id="c2", review_id="r2")
    second["quality_trend"]["overall"] = 79
    execution_failures = [
        {
            "workflow": "hardware",
            "category": "mechanical_device",
            "classification": "code",
            "message": "workflow execution failed",
        }
    ]
    repeatability_failures = [
        {
            "workflow": "software",
            "category": "software",
            "classification": "code",
            "message": "precomputed drift",
        }
    ]

    report = smoke._build_report(
        [first, second],
        execution_failures,
        repeat_count=2,
        repeatability_failures=repeatability_failures,
    )

    assert report["passed"] is False
    assert report["failures"] == execution_failures
    assert report["summary"]["failed_workflows"] == 1
    assert report["summary"]["repeatability_failures"] == 1
    assert report["summary"]["total_failures"] == 2
    assert report["loop_engineering"]["repeatability_failures"] == repeatability_failures


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


def _workflow_payload(
    smoke,
    *,
    project_id: str = "p1",
    compile_id: str = "c1",
    review_id: str = "r1",
    official_package_hash: str = "hash",
    grantability_id: str = "grantability",
) -> dict:
    return {
        "workflow": "software",
        "category": "software",
        "project_id": project_id,
        "official_compile_id": compile_id,
        "post_draft_review_id": review_id,
        "official_package_hash": official_package_hash,
        "official_text_hash": "official-text-hash",
        "research_evidence_count": 2,
        "research_confidence": "medium",
        "grantability": {
            "id": grantability_id,
            "status": "medium",
            "fail_closed": False,
            "claim_chart_rows": 2,
        },
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
            "grantability_report_present": {
                "passed": True,
                "expected": "claim_chart_rows>0 and fail_closed=false",
                "actual": "rows=2 fail_closed=False",
            },
            "quality_trend_present": {
                "passed": True,
                "expected": ",".join(smoke.TREND_FIELDS),
                "actual": "trend-present",
            },
            "official_export_hygiene": {"passed": True, "expected": "clean", "actual": "clean"},
            "official_export_blocked_before_compile": {"passed": True, "expected": "409", "actual": "409"},
            "official_export_blocked_before_review": {"passed": True, "expected": "409", "actual": "409"},
            "post_draft_review_unlocks_export": {
                "passed": True,
                "expected": "export_allowed=true",
                "actual": "true",
            },
            "evidence_binding_rate": {"passed": True, "expected": ">=0.1", "actual": "0.8"},
            "core_feature_support_rate": {"passed": True, "expected": ">=0.4", "actual": "0.75"},
            "unverified_effect_leak_count": {"passed": True, "expected": "0", "actual": "0"},
        },
    }
