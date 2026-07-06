#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests"
DEFAULT_CASE_ROOT = TESTS_ROOT / "golden_patent_cases"
DEFAULT_OFFICIAL_TEXT_ROOT = TESTS_ROOT / "golden_patent_outputs"

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from golden_patent_evaluator import evaluate_golden_case  # noqa: E402


def run_gate(
    *,
    case_root: Path = DEFAULT_CASE_ROOT,
    official_text_root: Path = DEFAULT_OFFICIAL_TEXT_ROOT,
    report_path: Path | None = None,
    calibration_markdown_path: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    cases = _load_cases(case_root)
    entries: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case["case_id"])
        if not case.get("release_gate_enabled", False):
            entries.append(
                {
                    "case_id": case_id,
                    "status": "skipped",
                    "reason": "release_gate_disabled",
                }
            )
            continue

        calibration_status = case.get("human_calibration", {}).get("status")
        if calibration_status != "calibrated":
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "enabled_without_human_calibration",
                    "calibration_status": calibration_status,
                }
            )
            continue

        missing_calibration_fields = _missing_calibration_fields(case)
        if missing_calibration_fields:
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "missing_human_calibration_metadata",
                    "calibration_status": calibration_status,
                    "missing_calibration_fields": missing_calibration_fields,
                }
            )
            continue

        contract_violations = _release_gate_contract_violations(case)
        if contract_violations:
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "invalid_release_gate_contract",
                    "contract_violations": contract_violations,
                }
            )
            continue

        official_text_path = official_text_root / f"{case_id}.md"
        if not official_text_path.exists():
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "missing_official_text",
                    "official_text_path": str(official_text_path),
                }
            )
            continue

        official_text = official_text_path.read_text(encoding="utf-8")
        expected_fixture_sha256 = str(
            (case.get("human_calibration") or {}).get("official_text_fixture_sha256", "")
        ).strip()
        actual_fixture_sha256 = _sha256_text(official_text)
        if not expected_fixture_sha256:
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "missing_official_text_fixture_sha256",
                    "official_text_path": str(official_text_path),
                    "actual_sha256": actual_fixture_sha256,
                }
            )
            continue
        if expected_fixture_sha256 != actual_fixture_sha256:
            entries.append(
                {
                    "case_id": case_id,
                    "status": "failed",
                    "reason": "official_text_fixture_sha256_mismatch",
                    "official_text_path": str(official_text_path),
                    "expected_sha256": expected_fixture_sha256,
                    "actual_sha256": actual_fixture_sha256,
                }
            )
            continue

        evaluation = evaluate_golden_case(case, official_text)
        entries.append(
            {
                "case_id": case_id,
                "status": "passed" if evaluation["passed"] else "failed",
                "reason": "passed" if evaluation["passed"] else "evaluation_failed",
                "evaluation": evaluation,
            }
        )

    calibration_queue = _build_calibration_queue(cases, official_text_root)
    report = _build_report(entries, calibration_queue, strict=strict)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if calibration_markdown_path is not None:
        calibration_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        calibration_markdown_path.write_text(_render_calibration_markdown(calibration_queue), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic golden patent release gate.")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--official-text-root", type=Path, default=DEFAULT_OFFICIAL_TEXT_ROOT)
    parser.add_argument("--report-path", type=Path)
    parser.add_argument("--calibration-markdown-path", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail release mode when no golden cases are enabled.",
    )
    args = parser.parse_args(argv)

    report = run_gate(
        case_root=args.case_root,
        official_text_root=args.official_text_root,
        report_path=args.report_path,
        calibration_markdown_path=args.calibration_markdown_path,
        strict=args.strict,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def _load_cases(case_root: Path) -> list[dict[str, Any]]:
    case_paths = sorted(case_root.glob("*/case.json"))
    if not case_paths:
        raise RuntimeError(f"No golden patent cases found under {case_root}")
    cases = []
    for path in case_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("case_id") != path.parent.name:
            raise RuntimeError(f"case_id mismatch in {path}")
        cases.append(payload)
    return cases


def _missing_calibration_fields(case: dict[str, Any]) -> list[str]:
    calibration = case.get("human_calibration") or {}
    return [field for field in ("reviewer", "notes") if not str(calibration.get(field, "")).strip()]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _release_gate_contract_violations(case: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if not bool((case.get("deterministic_checks") or {}).get("release_blocker", False)):
        violations.append("deterministic_checks.release_blocker_must_be_true")
    if bool((case.get("llm_judge") or {}).get("release_blocker", False)):
        violations.append("llm_judge.release_blocker_must_be_false")
    return violations


def _build_report(
    entries: list[dict[str, Any]],
    calibration_queue: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    enabled = [entry for entry in entries if entry["status"] != "skipped"]
    failed = [entry for entry in entries if entry["status"] == "failed"]
    passed = [entry for entry in entries if entry["status"] == "passed"]
    skipped = [entry for entry in entries if entry["status"] == "skipped"]
    gate_failures = []
    if strict and not enabled:
        gate_failures.append(
            {
                "reason": "no_release_gate_cases_enabled",
                "message": "Strict release mode requires at least one enabled golden patent case.",
            }
        )
    return {
        "passed": not failed and not gate_failures,
        "strict_mode": strict,
        "case_count": len(entries),
        "enabled_count": len(enabled),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "gate_failures": gate_failures,
        "pending_calibration_count": len(calibration_queue),
        "calibration_queue_count": len(calibration_queue),
        "calibration_queue": calibration_queue,
        "cases": entries,
    }


def _build_calibration_queue(cases: list[dict[str, Any]], official_text_root: Path) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for case in cases:
        calibration = case.get("human_calibration") or {}
        status = calibration.get("status")
        if status == "calibrated":
            continue
        official_text_path = official_text_root / f"{case['case_id']}.md"
        official_text_exists = official_text_path.exists()
        actual_fixture_sha256 = (
            _sha256_text(official_text_path.read_text(encoding="utf-8")) if official_text_exists else ""
        )
        queue.append(
            {
                "case_id": case["case_id"],
                "category": case.get("category"),
                "application_type": case.get("application_type"),
                "input_kind": case.get("input_kind"),
                "release_gate_enabled": bool(case.get("release_gate_enabled", False)),
                "calibration_status": status,
                "reviewer": calibration.get("reviewer", ""),
                "notes": calibration.get("notes", ""),
                "required_distinguishing_features": case.get("required_distinguishing_features", []),
                "forbidden_official_content": case.get("forbidden_official_content", []),
                "official_text_fixture_path": str(official_text_path),
                "official_text_fixture_exists": official_text_exists,
                "official_text_fixture_sha256_actual": actual_fixture_sha256,
                "expected_quality_thresholds": case.get("expected_quality_thresholds", {}),
                "deterministic_checks": case.get("deterministic_checks", {}),
                "llm_judge": case.get("llm_judge", {}),
                "human_review_checklist": [
                    "confirm_required_distinguishing_features",
                    "confirm_forbidden_official_content",
                    "confirm_expected_quality_thresholds",
                    "approve_or_update_official_output_fixture",
                    "set_human_calibration_status_calibrated_before_enabling_release_gate",
                ],
            }
        )
    return queue


def _render_calibration_markdown(calibration_queue: list[dict[str, Any]]) -> str:
    lines = [
        "# Golden Patent Calibration Queue",
        "",
        f"Pending cases: {len(calibration_queue)}",
        "",
    ]
    if not calibration_queue:
        lines.append("No pending golden patent cases need human calibration.")
        lines.append("")
        return "\n".join(lines)

    for entry in calibration_queue:
        lines.extend(
            [
                f"## {entry['case_id']}",
                "",
                f"- Category: `{entry.get('category') or ''}`",
                f"- Application type: `{entry.get('application_type') or ''}`",
                f"- Input kind: `{entry.get('input_kind') or ''}`",
                f"- Calibration status: `{entry.get('calibration_status') or ''}`",
                f"- Release gate enabled: `{_yes_no(bool(entry.get('release_gate_enabled')))}`",
                f"- Fixture: `{entry.get('official_text_fixture_path') or ''}`",
                f"- Fixture exists: `{_yes_no(bool(entry.get('official_text_fixture_exists')))}`",
                f"- Current fixture SHA256: `{entry.get('official_text_fixture_sha256_actual') or ''}`",
                f"- Notes: {entry.get('notes') or ''}",
                "",
                "Required distinguishing features:",
                *_bullet_lines(entry.get("required_distinguishing_features", [])),
                "",
                "Forbidden official content:",
                *_bullet_lines(entry.get("forbidden_official_content", [])),
                "",
                "Expected quality thresholds:",
                *_key_value_lines(entry.get("expected_quality_thresholds", {})),
                "",
                "Human review checklist:",
                *_checkbox_lines(entry.get("human_review_checklist", [])),
                "",
            ]
        )
    return "\n".join(lines)


def _bullet_lines(items: list[Any]) -> list[str]:
    return [f"- {item}" for item in items] or ["- none"]


def _key_value_lines(items: dict[str, Any]) -> list[str]:
    return [f"- {key}: `{value}`" for key, value in items.items()] or ["- none"]


def _checkbox_lines(items: list[Any]) -> list[str]:
    return [f"- [ ] {item}" for item in items] or ["- [ ] none"]


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
