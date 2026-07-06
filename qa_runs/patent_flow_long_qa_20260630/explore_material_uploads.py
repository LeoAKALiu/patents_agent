#!/usr/bin/env python3
"""Material upload exploration for the 2026-06-30 long QA run.

This script uses FastAPI TestClient, a temporary data directory, and synthetic
non-customer files. It does not modify production data or business code.
"""

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
OUTPUT = QA_DIR / "artifacts" / "material-upload-exploration.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="patentagent-material-upload-") as data_dir:
        client = TestClient(create_app(data_dir=Path(data_dir), load_env_file=False), raise_server_exceptions=False)
        project = _json(
            client.post(
                "/api/projects",
                json={
                    "name": "QA material upload exploration",
                    "draft_text": "一种用于智能仓储的货位推荐方法。",
                    "patent_type": "invention",
                },
            )
        )
        project_id = project["id"]
        cases = [
            _upload_file(client, project_id, TEST_DATA / "simple_invention.md", "simple_invention.md"),
            _upload_file(client, project_id, TEST_DATA / "simple_invention.md", "simple_invention.md"),
            _upload_bytes(client, project_id, b"", "empty.txt", "text/plain"),
            _upload_file(client, project_id, TEST_DATA / "boundary_prompt_injection.xyz", "boundary_prompt_injection.xyz"),
            _upload_bytes(client, project_id, b"not a real docx", "corrupt.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            _upload_file(client, project_id, TEST_DATA / "boundary_prompt_injection.md", "边界 prompt injection 材料.md"),
            _upload_bytes(client, project_id, b"long filename material with enough text for parsing", f"{'a' * 260}.md", "text/markdown"),
        ]
        materials = _json(client.get(f"/api/projects/{project_id}/materials"))
        payload = {
            "project_id": project_id,
            "data_dir": f"ephemeral:{data_dir}",
            "cases": cases,
            "material_count": len(materials.get("materials", [])),
            "materials": [
                {
                    "file_name": item.get("file_name"),
                    "status": item.get("status"),
                    "warnings": item.get("warnings"),
                    "text_length": len(item.get("text") or ""),
                }
                for item in materials.get("materials", [])
            ],
        }
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(OUTPUT)
    return 0


def _upload_file(client: TestClient, project_id: str, path: Path, filename: str) -> dict[str, Any]:
    return _upload_bytes(client, project_id, path.read_bytes(), filename, _content_type(filename))


def _upload_bytes(client: TestClient, project_id: str, content: bytes, filename: str, content_type: str) -> dict[str, Any]:
    response = client.post(
        f"/api/projects/{project_id}/materials",
        files={"file": (filename, content, content_type)},
    )
    payload: Any
    try:
        payload = response.json()
    except Exception:
        payload = response.text[:500]
    return {
        "filename": filename if len(filename) <= 80 else f"{filename[:40]}...{filename[-20:]}",
        "content_type": content_type,
        "status_code": response.status_code,
        "ok": response.status_code < 400,
        "detail": payload.get("detail") if isinstance(payload, dict) else payload,
        "material_status": payload.get("status") if isinstance(payload, dict) else None,
        "warnings": payload.get("warnings") if isinstance(payload, dict) else None,
    }


def _json(response: Any) -> dict[str, Any]:
    if response.status_code >= 400:
        raise RuntimeError(f"{response.request.method} {response.request.url} failed: {response.status_code} {response.text}")
    return response.json()


def _content_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix == ".txt":
        return "text/plain"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


if __name__ == "__main__":
    raise SystemExit(main())
