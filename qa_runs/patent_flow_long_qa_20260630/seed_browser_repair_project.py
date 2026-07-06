#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx


BASE_URL = os.environ.get("PATENTAGENT_QA_BASE_URL", "http://127.0.0.1:8000")
ARTIFACT_DIR = Path("qa_runs/patent_flow_long_qa_20260630/current-artifacts/browser-smoke-current")


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        wait_for_backend(client)
        project = create_project(client)
        project_id = project["id"]
        material = upload_material(client, project_id)
        package = checked_json(client.post(f"/api/projects/{project_id}/generate", json={}))
        compile_run = checked_json(client.post(f"/api/projects/{project_id}/official-compile-runs", json={}))
        review = checked_json(client.post(f"/api/projects/{project_id}/post-draft-reviews", json={}))
        repair_session = checked_json(
            client.get(f"/api/projects/{project_id}/post-draft-reviews/{review['id']}/repair-session")
        )
        export_readiness = checked_json(client.get(f"/api/projects/{project_id}/export-readiness"))
        post_draft_reviews = checked_json(client.get(f"/api/projects/{project_id}/post-draft-reviews"))
        official_compile_runs = checked_json(client.get(f"/api/projects/{project_id}/official-compile-runs"))
        refreshed_project = checked_json(client.get(f"/api/projects/{project_id}"))

    summary = {
        "project_id": project_id,
        "project_name": refreshed_project["name"],
        "material_id": material["id"],
        "material_status": material["status"],
        "package_title": package["title"],
        "official_compile_run_id": compile_run["id"],
        "official_compile_status": compile_run["status"],
        "post_draft_review_id": review["id"],
        "post_draft_review_status": review["status"],
        "post_draft_export_allowed": review["export_allowed"],
        "repair_issue_count": len(repair_session["issues"]),
        "repair_section_keys": sorted(repair_session["sections"].keys()),
        "export_readiness": {
            "export_allowed": export_readiness.get("export_allowed"),
            "next_action": export_readiness.get("next_action"),
            "review_gate_status": export_readiness.get("review_gate_status"),
            "compile_status": export_readiness.get("compile_status"),
        },
    }
    write_json("seed-summary.json", summary)
    write_json("repair-session.json", repair_session)
    write_json("export-readiness.json", export_readiness)
    write_json("post-draft-reviews.json", post_draft_reviews)
    write_json("official-compile-runs.json", official_compile_runs)
    write_json("project.json", refreshed_project)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def wait_for_backend(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = client.get("/api/health")
            if response.status_code == 200:
                return
            last_error = f"{response.status_code} {response.text[:200]}"
        except Exception as exc:  # pragma: no cover - only for dev-server wait loop
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Backend did not become ready: {last_error}")


def create_project(client: httpx.Client) -> dict[str, Any]:
    return checked_json(
        client.post(
            "/api/projects",
            json={
                "name": "QA 标注修复证据项目",
                "draft_text": "实用新型：一种城市体检指标驱动无人机主动采集系统。",
                "patent_type": "utility_model",
                "technical_field": "城市体检、无人机任务规划",
                "technical_solution": "基于城市体检指标置信度生成无人机采集任务包。",
                "beneficial_effects": "减少重复采集并提升低置信度区域补采效率。",
            },
        )
    )


def upload_material(client: httpx.Client, project_id: str) -> dict[str, Any]:
    response = client.post(
        f"/api/projects/{project_id}/materials",
        files={
            "file": (
                "qa-repair-disclosure.md",
                (
                    "# 技术交底\n"
                    "系统包括城市体检指标接入模块、置信度热力图模块和无人机任务包生成模块。\n"
                    "实施例：当道路病害识别置信度低于阈值时，系统生成补采任务并回写任务状态。\n"
                ).encode("utf-8"),
                "text/markdown",
            )
        },
    )
    return checked_json(response)


def checked_json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        raise RuntimeError(f"{response.request.method} {response.request.url} failed: {response.status_code} {response.text}")
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected object response from {response.request.url}: {data!r}")
    return data


def write_json(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
