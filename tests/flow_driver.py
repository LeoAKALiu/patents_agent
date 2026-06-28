from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient


@dataclass(frozen=True)
class FlowState:
    step_status: dict[int, str]
    gates: dict[str, str]
    hashes: dict[str, str]
    active_runs: list[dict[str, Any]]
    export_allowed: bool


class FlowDriver:
    """Headless API driver for plan-level pipeline tests."""

    def __init__(self, client: TestClient, project_id: str | None = None) -> None:
        self.client = client
        self.project_id = project_id or ""

    def create_project(
        self,
        name: str,
        idea: str,
        *,
        patent_type: str = "invention",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"name": name, "draft_text": idea, "patent_type": patent_type}
        if metadata:
            payload.update(metadata)
        project = self._json(self.client.post("/api/projects", json=payload))
        self.project_id = str(project["id"])
        return project

    def intake_external_draft(self, content: str, *, filename: str = "external-draft.txt") -> dict[str, Any]:
        self._require_project_id()
        source = self._json(
            self.client.post(
                f"/api/projects/{self.project_id}/external-drafts",
                json={"source_type": "pasted_text", "file_name": filename, "text": content},
            )
        )
        run = self._json(
            self.client.post(
                f"/api/projects/{self.project_id}/external-drafts/{source['id']}/intake-runs"
            )
        )
        if run["status"] == "completed":
            return run

        package = run.get("parsed_package") or {}
        return self._json(
            self.client.post(
                f"/api/projects/{self.project_id}/external-draft-intake-runs/{run['id']}/confirm",
                json={
                    "title": package.get("title") or "未命名专利",
                    "abstract": package.get("abstract") or "本发明公开一种处理方法。",
                    "claims": package.get("claims") or "1. 一种处理方法。",
                    "description": package.get("description") or "本发明涉及数据处理技术领域。",
                    "drawing_description": package.get("drawing_description") or "图1为流程图。",
                },
            )
        )

    def run_quality(self) -> dict[str, Any]:
        self._require_project_id()
        filing = self._json(self.client.post(f"/api/projects/{self.project_id}/filing-readiness"))
        worksheet = self._json(self.client.post(f"/api/projects/{self.project_id}/claim-defense-worksheets"))
        completion = self._json(self.client.post(f"/api/projects/{self.project_id}/completion-runs"))
        return {"filing_readiness": filing, "claim_defense": worksheet, "draft_completion": completion}

    def compile_official(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.post(f"/api/projects/{self.project_id}/official-compile-runs", json={}))

    def run_post_draft_review(self, *, provider: str | None = None) -> dict[str, Any]:
        self._require_project_id()
        providers = [provider] if provider else None
        payload = {"providers": providers} if providers else {}
        return self._json(self.client.post(f"/api/projects/{self.project_id}/post-draft-reviews", json=payload))

    def formula_requirement(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}/formula-requirement"))

    def run_formula(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.post(f"/api/projects/{self.project_id}/formula-runs", json={}))

    def generate_draft(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.post(f"/api/projects/{self.project_id}/generate", json=payload or {}))

    def export_readiness(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}/export-readiness"))

    def project(self) -> dict[str, Any]:
        self._require_project_id()
        return self._json(self.client.get(f"/api/projects/{self.project_id}"))

    def export_official(self) -> dict[str, Any]:
        self._require_project_id()
        response = self.client.get(f"/api/projects/{self.project_id}/official-export.md")
        if response.status_code == 200:
            return {"ok": True, "blocked": False, "text": response.text}
        return {"ok": False, "blocked": True, "status_code": response.status_code, "detail": response.json().get("detail")}

    def export_internal(self) -> dict[str, Any]:
        self._require_project_id()
        response = self.client.get(f"/api/projects/{self.project_id}/export.md")
        if response.status_code == 200:
            return {"ok": True, "blocked": False, "text": response.text}
        return {"ok": False, "blocked": True, "status_code": response.status_code, "detail": response.json().get("detail")}

    def edit_source_draft(self, new_text: str) -> dict[str, Any]:
        self._require_project_id()
        project = self._json(self.client.get(f"/api/projects/{self.project_id}"))
        package = project.get("package")
        if not package:
            updated = self._json(
                self.client.put(f"/api/projects/{self.project_id}", json={"draft_text": new_text})
            )
            return updated
        payload = {
            "title": package["title"],
            "abstract": package["abstract"],
            "claims": package["claims"],
            "description": new_text,
            "drawing_description": package["drawing_description"],
        }
        return self._json(self.client.put(f"/api/projects/{self.project_id}/draft-package", json=payload))

    def raw_get(self, path: str) -> Any:
        response = self.client.get(path)
        return response.json() if _is_json(response.headers.get("content-type", "")) else response.text

    def raw_post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        response = self.client.post(path, json=body or {})
        return response.json() if _is_json(response.headers.get("content-type", "")) else response.text

    def state(self) -> FlowState:
        self._require_project_id()
        project = self._json(self.client.get(f"/api/projects/{self.project_id}"))
        filing = self._json(self.client.get(f"/api/projects/{self.project_id}/filing-readiness"))
        worksheets = self._json(self.client.get(f"/api/projects/{self.project_id}/claim-defense-worksheets"))
        completion = self._json(self.client.get(f"/api/projects/{self.project_id}/completion-runs"))
        compile_runs = self._json(self.client.get(f"/api/projects/{self.project_id}/official-compile-runs"))
        reviews = self._json(self.client.get(f"/api/projects/{self.project_id}/post-draft-reviews"))
        readiness = self._json(self.client.get(f"/api/projects/{self.project_id}/export-readiness"))

        current_hash = str(compile_runs.get("current_source_draft_hash") or "")
        latest_compile = _first(compile_runs.get("runs", []))
        latest_review = _first(reviews.get("runs", []))
        latest_filing = _first(filing.get("reports", []))
        latest_worksheet = _first(worksheets.get("worksheets", []))
        latest_completion = _first(completion.get("runs", []))

        quality_gate = _quality_gate(current_hash, latest_filing, latest_worksheet, latest_completion)
        compile_gate = _official_compile_gate(current_hash, latest_compile)
        review_gate = _review_gate(current_hash, latest_compile, latest_review)
        export_allowed = bool(readiness.get("export_allowed"))

        return FlowState(
            step_status={
                1: "completed" if project else "locked",
                2: "unknown",
                3: "unknown",
                4: "unknown",
                5: "completed" if project.get("package") else "locked",
                6: "completed" if quality_gate == "current" else "locked",
                7: "completed" if compile_gate == "current" else "locked",
                8: "completed" if review_gate == "current" else "locked",
                9: "completed" if export_allowed else "locked",
            },
            gates={
                "quality": quality_gate,
                "official_compile": compile_gate,
                "post_draft_review": review_gate,
            },
            hashes={
                "current_source_draft_hash": current_hash,
                "latest_official_source_hash": str(latest_compile.get("source_draft_hash") or ""),
                "latest_official_package_hash": str(latest_compile.get("official_package_hash") or ""),
                "latest_worksheet_draft_hash": str(latest_worksheet.get("draft_package_hash") or ""),
                "latest_review_draft_hash": str(latest_review.get("draft_package_hash") or ""),
                "latest_review_official_package_hash": str(latest_review.get("official_package_hash") or ""),
            },
            active_runs=_active_runs([latest_compile, latest_review]),
            export_allowed=export_allowed,
        )

    def _require_project_id(self) -> None:
        if not self.project_id:
            raise AssertionError("FlowDriver project_id is not set. Call create_project first.")

    @staticmethod
    def _json(response: Any) -> dict[str, Any]:
        if response.status_code >= 400:
            raise AssertionError(f"{response.request.method} {response.request.url} failed: {response.status_code} {response.text}")
        return response.json()


def _first(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    return items[0] if items else {}


def _hash_gate(current_hash: str, run_hash: object) -> str:
    if not run_hash:
        return "missing"
    return "current" if str(run_hash) == current_hash else "stale"


def _quality_artifact_gate(
    current_hash: str,
    artifact: dict[str, Any],
    *,
    completed_only: bool = False,
) -> str:
    if not artifact:
        return "missing"
    artifact_hash = artifact.get("draft_package_hash")
    status = str(artifact.get("status") or "")
    if completed_only:
        if status == "failed" and bool(current_hash) and artifact_hash == current_hash:
            return "failed"
        if status != "completed":
            return "missing"
    if artifact_hash == current_hash:
        return "current"
    if artifact_hash:
        return "stale"
    return "unknown"


def _official_compile_gate(current_hash: str, run: dict[str, Any]) -> str:
    if not run:
        return "missing"
    if str(run.get("source_draft_hash") or "") != current_hash:
        return "stale"
    status = str(run.get("status") or "")
    if status in {"queued", "running", "blocked", "failed"}:
        return status
    if status == "completed" and run.get("official_package") and run.get("official_package_hash"):
        return "current"
    return "missing"


def _quality_gate(
    current_hash: str,
    filing: dict[str, Any],
    worksheet: dict[str, Any],
    completion: dict[str, Any],
) -> str:
    filing_state = _quality_artifact_gate(current_hash, filing)
    worksheet_state = _quality_artifact_gate(current_hash, worksheet)
    completion_state = _quality_artifact_gate(current_hash, completion, completed_only=True)
    states = [filing_state, worksheet_state, completion_state]
    if "failed" in states:
        return "failed"
    if all(state == "current" for state in states):
        return "current"
    if "stale" in states:
        return "stale"
    if "unknown" in states:
        return "unknown"
    return "missing"


def _review_gate(current_hash: str, compile_run: dict[str, Any], review: dict[str, Any]) -> str:
    if not review:
        return "missing"
    if (
        review.get("draft_package_hash") == current_hash
        and review.get("official_compile_run_id") == compile_run.get("id")
        and review.get("official_package_hash") == compile_run.get("official_package_hash")
    ):
        status = str(review.get("status") or "")
        if status != "completed":
            return status or "stale"
        return "current" if review.get("export_allowed") is True else _blocked_review_gate_status(review)
    return "stale"


def _blocked_review_gate_status(review: dict[str, Any]) -> str:
    chair_result = review.get("chair_result")
    if isinstance(chair_result, dict) and chair_result.get("status"):
        return str(chair_result["status"])
    return "blocked"


def _active_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [run for run in runs if run.get("status") in {"queued", "running"}]


def _is_json(content_type: str) -> bool:
    return "application/json" in content_type
