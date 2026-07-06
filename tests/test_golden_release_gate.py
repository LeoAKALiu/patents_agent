from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "golden_quality_gate.py"
CI_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("golden_quality_gate", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_golden_release_gate_skips_disabled_uncalibrated_cases(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    report_path = tmp_path / "reports" / "golden.json"
    _write_case(
        case_root,
        case_id="disabled_pending",
        release_gate_enabled=False,
        calibration_status="pending_human_review",
    )

    report = gate.run_gate(
        case_root=case_root,
        official_text_root=tmp_path / "official",
        report_path=report_path,
    )

    assert report["passed"] is True
    assert report["case_count"] == 1
    assert report["enabled_count"] == 0
    assert report["skipped_count"] == 1
    assert report["failed_count"] == 0
    assert report["cases"] == [
        {
            "case_id": "disabled_pending",
            "status": "skipped",
            "reason": "release_gate_disabled",
        }
    ]
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_golden_release_gate_strict_mode_rejects_zero_enabled_cases(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    _write_case(
        case_root,
        case_id="disabled_pending",
        release_gate_enabled=False,
        calibration_status="pending_human_review",
    )

    report = gate.run_gate(
        case_root=case_root,
        official_text_root=tmp_path / "official",
        strict=True,
    )

    assert report["passed"] is False
    assert report["strict_mode"] is True
    assert report["enabled_count"] == 0
    assert report["failed_count"] == 0
    assert report["gate_failures"] == [
        {
            "reason": "no_release_gate_cases_enabled",
            "message": "Strict release mode requires at least one enabled golden patent case.",
        }
    ]


def test_golden_release_gate_reports_actionable_calibration_queue(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    fixture_text = "human-reviewed official fixture"
    _write_case(
        case_root,
        case_id="disabled_pending",
        release_gate_enabled=False,
        calibration_status="pending_human_review",
        notes="Need patent attorney review.",
    )
    _write_case(
        case_root,
        case_id="disabled_calibrated",
        release_gate_enabled=False,
        calibration_status="calibrated",
        reviewer="attorney-a",
    )
    official_root.mkdir(parents=True)
    (official_root / "disabled_pending.md").write_text(fixture_text, encoding="utf-8")

    report = gate.run_gate(case_root=case_root, official_text_root=official_root)

    assert report["pending_calibration_count"] == 1
    assert report["calibration_queue_count"] == 1
    assert len(report["calibration_queue"]) == 1
    queue_entry = report["calibration_queue"][0]
    assert queue_entry["case_id"] == "disabled_pending"
    assert queue_entry["calibration_status"] == "pending_human_review"
    assert queue_entry["release_gate_enabled"] is False
    assert queue_entry["notes"] == "Need patent attorney review."
    assert queue_entry["required_distinguishing_features"] == ["特征A", "特征B"]
    assert queue_entry["forbidden_official_content"] == ["效率提升30%", "已验证"]
    assert queue_entry["official_text_fixture_path"] == str(official_root / "disabled_pending.md")
    assert queue_entry["official_text_fixture_exists"] is True
    assert queue_entry["official_text_fixture_sha256_actual"] == _sha256(fixture_text)
    assert queue_entry["expected_quality_thresholds"] == {
        "claim_feature_coverage": 1.0,
        "spec_support_coverage": 1.0,
        "official_cleanliness": 1.0,
        "evidence_honesty": 1.0,
    }
    assert queue_entry["human_review_checklist"] == [
        "confirm_required_distinguishing_features",
        "confirm_forbidden_official_content",
        "confirm_expected_quality_thresholds",
        "approve_or_update_official_output_fixture",
        "set_human_calibration_status_calibrated_before_enabling_release_gate",
    ]


def test_golden_release_gate_writes_human_readable_calibration_packet(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    packet_path = tmp_path / "reports" / "calibration.md"
    fixture_text = "human-readable reviewed fixture"
    _write_case(
        case_root,
        case_id="disabled_pending",
        release_gate_enabled=False,
        calibration_status="pending_human_review",
        notes="Need patent attorney review.",
    )
    official_root.mkdir(parents=True)
    (official_root / "disabled_pending.md").write_text(fixture_text, encoding="utf-8")

    report = gate.run_gate(
        case_root=case_root,
        official_text_root=official_root,
        calibration_markdown_path=packet_path,
    )

    assert report["pending_calibration_count"] == 1
    packet = packet_path.read_text(encoding="utf-8")
    assert "# Golden Patent Calibration Queue" in packet
    assert "## disabled_pending" in packet
    assert f"Fixture: `{official_root / 'disabled_pending.md'}`" in packet
    assert "Fixture exists: `yes`" in packet
    assert f"Current fixture SHA256: `{_sha256(fixture_text)}`" in packet
    assert "Need patent attorney review." in packet
    assert "- 特征A" in packet
    assert "- 效率提升30%" in packet
    assert "- [ ] confirm_required_distinguishing_features" in packet
    assert "- [ ] approve_or_update_official_output_fixture" in packet
    assert "- [ ] set_human_calibration_status_calibrated_before_enabling_release_gate" in packet


def test_golden_release_gate_rejects_enabled_uncalibrated_cases(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    _write_case(
        case_root,
        case_id="enabled_pending",
        release_gate_enabled=True,
        calibration_status="pending_human_review",
    )

    report = gate.run_gate(case_root=case_root, official_text_root=tmp_path / "official")

    assert report["passed"] is False
    assert report["enabled_count"] == 1
    assert report["failed_count"] == 1
    assert report["cases"][0]["status"] == "failed"
    assert report["cases"][0]["reason"] == "enabled_without_human_calibration"


def test_golden_release_gate_rejects_enabled_calibrated_cases_missing_human_metadata(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    _write_case(
        case_root,
        case_id="missing_reviewer",
        release_gate_enabled=True,
        calibration_status="calibrated",
        notes="Approved by patent attorney after fixture review.",
    )
    _write_case(
        case_root,
        case_id="missing_notes",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
    )

    report = gate.run_gate(case_root=case_root, official_text_root=official_root)

    assert report["passed"] is False
    assert report["failed_count"] == 2
    failures = {entry["case_id"]: entry for entry in report["cases"]}
    assert failures["missing_reviewer"]["reason"] == "missing_human_calibration_metadata"
    assert failures["missing_reviewer"]["missing_calibration_fields"] == ["reviewer"]
    assert failures["missing_notes"]["reason"] == "missing_human_calibration_metadata"
    assert failures["missing_notes"]["missing_calibration_fields"] == ["notes"]


def test_golden_release_gate_rejects_enabled_calibrated_cases_without_matching_fixture_hash(
    tmp_path: Path,
) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    _write_case(
        case_root,
        case_id="missing_hash",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
    )
    _write_case(
        case_root,
        case_id="mismatched_hash",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
        official_text_fixture_sha256="0" * 64,
    )
    official_root.mkdir(parents=True)
    (official_root / "missing_hash.md").write_text("fixture reviewed text", encoding="utf-8")
    (official_root / "mismatched_hash.md").write_text("fixture reviewed text", encoding="utf-8")

    report = gate.run_gate(case_root=case_root, official_text_root=official_root)

    assert report["passed"] is False
    assert report["failed_count"] == 2
    failures = {entry["case_id"]: entry for entry in report["cases"]}
    assert failures["missing_hash"]["reason"] == "missing_official_text_fixture_sha256"
    assert failures["mismatched_hash"]["reason"] == "official_text_fixture_sha256_mismatch"
    assert failures["mismatched_hash"]["expected_sha256"] == "0" * 64
    assert failures["mismatched_hash"]["actual_sha256"] == _sha256("fixture reviewed text")


def test_golden_release_gate_requires_calibrated_outputs_to_pass(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    case = _write_case(
        case_root,
        case_id="calibrated_case",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
    )
    supported_text = _supported_official_text(case)
    case["human_calibration"]["official_text_fixture_sha256"] = _sha256(supported_text)
    (case_root / "calibrated_case" / "case.json").write_text(
        json.dumps(case, ensure_ascii=False),
        encoding="utf-8",
    )

    missing_report = gate.run_gate(case_root=case_root, official_text_root=official_root)
    assert missing_report["passed"] is False
    assert missing_report["cases"][0]["reason"] == "missing_official_text"

    official_root.mkdir(parents=True)
    (official_root / "calibrated_case.md").write_text(supported_text, encoding="utf-8")
    passed_report = gate.run_gate(case_root=case_root, official_text_root=official_root)
    assert passed_report["passed"] is True
    assert passed_report["passed_count"] == 1
    assert passed_report["cases"][0]["status"] == "passed"
    assert passed_report["cases"][0]["evaluation"]["passed"] is True


def test_golden_release_gate_still_evaluates_thresholds_after_fixture_hash_matches(tmp_path: Path) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    official_root.mkdir(parents=True)
    failing_text = "# calibrated_case\n## 权利要求书\n1. 一种方案，包括特征A。\n## 说明书\n仅说明特征A。\n"
    _write_case(
        case_root,
        case_id="calibrated_case",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
        official_text_fixture_sha256=_sha256(failing_text),
    )
    (official_root / "calibrated_case.md").write_text(failing_text, encoding="utf-8")

    failed_report = gate.run_gate(case_root=case_root, official_text_root=official_root)

    assert failed_report["passed"] is False
    assert failed_report["cases"][0]["status"] == "failed"
    assert "claim_feature_coverage" in failed_report["cases"][0]["evaluation"]["violations"]["thresholds"]


def test_golden_release_gate_requires_deterministic_blockers_and_nonblocking_llm_judge(
    tmp_path: Path,
) -> None:
    gate = load_gate_module()
    case_root = tmp_path / "cases"
    official_root = tmp_path / "official"
    official_root.mkdir(parents=True)
    deterministic_text = _supported_official_text(
        {
            "case_id": "deterministic_not_blocking",
            "required_distinguishing_features": ["特征A", "特征B"],
            "key_innovations": ["创新支撑A", "创新支撑B"],
            "prior_art_summary": "现有方案缺少特征A和特征B的组合。",
        }
    )
    llm_text = _supported_official_text(
        {
            "case_id": "llm_blocking",
            "required_distinguishing_features": ["特征A", "特征B"],
            "key_innovations": ["创新支撑A", "创新支撑B"],
            "prior_art_summary": "现有方案缺少特征A和特征B的组合。",
        }
    )
    _write_case(
        case_root,
        case_id="deterministic_not_blocking",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
        official_text_fixture_sha256=_sha256(deterministic_text),
        deterministic_release_blocker=False,
    )
    _write_case(
        case_root,
        case_id="llm_blocking",
        release_gate_enabled=True,
        calibration_status="calibrated",
        reviewer="attorney-a",
        notes="Approved by patent attorney after fixture review.",
        official_text_fixture_sha256=_sha256(llm_text),
        llm_release_blocker=True,
    )
    (official_root / "deterministic_not_blocking.md").write_text(deterministic_text, encoding="utf-8")
    (official_root / "llm_blocking.md").write_text(llm_text, encoding="utf-8")

    report = gate.run_gate(case_root=case_root, official_text_root=official_root)

    assert report["passed"] is False
    assert report["failed_count"] == 2
    failures = {entry["case_id"]: entry for entry in report["cases"]}
    assert failures["deterministic_not_blocking"]["reason"] == "invalid_release_gate_contract"
    assert failures["deterministic_not_blocking"]["contract_violations"] == [
        "deterministic_checks.release_blocker_must_be_true"
    ]
    assert failures["llm_blocking"]["reason"] == "invalid_release_gate_contract"
    assert failures["llm_blocking"]["contract_violations"] == ["llm_judge.release_blocker_must_be_false"]


def test_ci_runs_golden_release_gate_after_backend_quality_gate() -> None:
    ci = CI_PATH.read_text(encoding="utf-8")

    assert "python scripts/v1_api_smoke.py --report-dir .artifacts/v1.1.0-quality" in ci
    assert "python scripts/golden_quality_gate.py --report-path .artifacts/golden-quality-gate.json" in ci
    assert "python scripts/golden_quality_gate.py --strict --report-path .artifacts/golden-quality-gate.json" not in ci


def _write_case(
    case_root: Path,
    *,
    case_id: str,
    release_gate_enabled: bool,
    calibration_status: str,
    reviewer: str = "",
    notes: str = "",
    official_text_fixture_sha256: str = "",
    deterministic_release_blocker: bool = True,
    llm_release_blocker: bool = False,
) -> dict:
    case = {
        "case_id": case_id,
        "category": "invention",
        "application_type": "invention",
        "input_kind": "idea",
        "technical_idea": "一种用于测试黄金门禁的技术方案。",
        "existing_draft": "",
        "key_innovations": ["创新支撑A", "创新支撑B"],
        "prior_art_summary": "现有方案缺少特征A和特征B的组合。",
        "required_distinguishing_features": ["特征A", "特征B"],
        "forbidden_official_content": ["效率提升30%", "已验证"],
        "expected_quality_thresholds": {
            "claim_feature_coverage": 1.0,
            "spec_support_coverage": 1.0,
            "official_cleanliness": 1.0,
            "evidence_honesty": 1.0,
        },
        "deterministic_checks": {"release_blocker": deterministic_release_blocker},
        "llm_judge": {"release_blocker": llm_release_blocker},
        "human_calibration": {
            "status": calibration_status,
            "reviewer": reviewer,
            "notes": notes,
            "official_text_fixture_sha256": official_text_fixture_sha256,
        },
        "release_gate_enabled": release_gate_enabled,
    }
    case_dir = case_root / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "case.json").write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
    return case


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
