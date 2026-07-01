#!/usr/bin/env python3
"""Incomplete-input flow exploration for the 2026-06-30 long QA run."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.main import create_app

QA_DIR = ROOT / "qa_runs" / "patent_flow_long_qa_20260630"
TEST_DATA = QA_DIR / "test_data"
OUTPUT = QA_DIR / "artifacts" / "incomplete-flow-exploration.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="patentagent-incomplete-flow-") as data_dir:
        client = TestClient(create_app(data_dir=Path(data_dir), load_env_file=False), raise_server_exceptions=False)
        cases: list[dict[str, Any]] = []

        empty_project = client.post(
            "/api/projects",
            json={"name": "Empty idea", "draft_text": "", "patent_type": "invention"},
        )
        cases.append(_response_case("create_empty_idea_project", empty_project))

        short_project = client.post(
            "/api/projects",
            json={"name": "Short marketing idea", "draft_text": "智能仓储助手，提高效率。", "patent_type": "invention"},
        )
        cases.append(_response_case("create_short_marketing_project", short_project))

        project_id = short_project.json()["id"] if short_project.status_code < 400 else ""
        if project_id:
            upload = client.post(
                f"/api/projects/{project_id}/materials",
                files={
                    "file": (
                        "incomplete_disclosure.md",
                        (TEST_DATA / "incomplete_disclosure.md").read_bytes(),
                        "text/markdown",
                    )
                },
            )
            cases.append(_response_case("upload_incomplete_disclosure", upload))
            cases.append(_response_case("export_readiness_before_draft", client.get(f"/api/projects/{project_id}/export-readiness")))
            cases.append(_response_case("generate_without_deliberation", client.post(f"/api/projects/{project_id}/generate", json={})))
            cases.append(_response_case("official_export_before_draft", client.get(f"/api/projects/{project_id}/official-export.md")))

        payload = {
            "data_dir": f"ephemeral:{data_dir}",
            "project_id": project_id,
            "cases": cases,
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(OUTPUT)
    return 0


def _response_case(name: str, response: Any) -> dict[str, Any]:
    try:
        payload: Any = response.json()
    except Exception:
        payload = response.text[:500]
    return {
        "name": name,
        "status_code": response.status_code,
        "ok": response.status_code < 400,
        "summary": _summarize(payload),
    }


def _summarize(payload: Any) -> Any:
    if isinstance(payload, dict):
        keys = [
            "id",
            "name",
            "draft_text",
            "status",
            "detail",
            "next_action",
            "export_allowed",
            "blocking_reasons",
            "file_name",
            "warnings",
        ]
        return {key: payload.get(key) for key in keys if key in payload}
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
