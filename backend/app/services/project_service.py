"""Project service - business logic for project management.

Extracts HTTP-independent helpers so the project router stays thin.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.disclosure.material_parser import read_project_material_text
from backend.app.schemas import (
    PatentPointCandidate,
    PatentPointCreate,
    PatentPointUpdate,
    ProjectCreate,
    ProjectMaterial,
    ProjectRecord,
    ProjectUpdate,
)
from backend.app.llm import LLMClient, MissingLLMClient
from backend.app.moat import score_moat


def build_project_record(payload: ProjectCreate) -> ProjectRecord:
    """Construct a new ProjectRecord from a creation payload."""
    return ProjectRecord(
        id=uuid.uuid4().hex,
        name=payload.name,
        draft_text=payload.draft_text,
        patent_type=payload.patent_type,
        applicant=payload.applicant,
        inventors=payload.inventors,
        technical_field=payload.technical_field,
        background=payload.background,
        pain_point=payload.pain_point,
        technical_solution=payload.technical_solution,
        innovation=payload.innovation,
        embodiments=payload.embodiments,
        beneficial_effects=payload.beneficial_effects,
    )


def apply_project_update(
    project_id: str,
    payload: ProjectUpdate,
    store,
) -> ProjectRecord | None:
    """Apply a partial update payload and return the updated project."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return store.get_project(project_id)
    return store.update_project(project_id, updates)


def import_project_material(
    *,
    project_id: str,
    file_name: str,
    stored_path: Path,
    store,
) -> ProjectMaterial:
    """Read and persist a project material file."""
    warnings: list[str] = []
    text = ""
    status = "processed"
    try:
        text, warnings = read_project_material_text(stored_path)
    except ValueError as exc:
        status = "failed"
        warnings = [str(exc)]

    material = ProjectMaterial(
        id=uuid.uuid4().hex,
        project_id=project_id,
        file_name=file_name,
        path=str(stored_path),
        file_type=stored_path.suffix.lower().lstrip("."),
        text=text,
        status=status,
        warnings=warnings,
    )
    store.add_project_material(material)
    return material


def build_patent_point_candidate(payload: PatentPointCreate) -> PatentPointCandidate:
    """Create a PatentPointCandidate from a creation payload."""
    return payload.to_candidate(payload.source_candidate_id or f"user-{uuid.uuid4().hex}")


def merge_patent_point_update(
    existing: PatentPointCandidate,
    payload: PatentPointUpdate,
) -> PatentPointCandidate:
    """Merge an update payload into an existing patent point candidate.

    Raises ValueError when null fields are present or validation fails.
    """
    from pydantic import ValidationError

    patch = payload.model_dump(exclude_unset=True)
    null_fields = [field for field, value in patch.items() if value is None]
    if null_fields:
        raise ValueError(
            f"Null fields are not allowed in patent point patches: {', '.join(null_fields)}"
        )
    if "moat_scores" in patch:
        patch["moat_scores"] = {
            **existing.moat_scores.model_dump(mode="json"),
            **patch["moat_scores"],
        }
    if patch.get("evidence_status") in {"feasible_unverified", "needs_experiment"} and not patch.get(
        "support_gaps"
    ) and not existing.support_gaps:
        patch["support_gaps"] = ["提交前需补充实验或工程样例。"]
    try:
        return PatentPointCandidate.model_validate(
            {**existing.model_dump(mode="json"), **patch}
        )
    except ValidationError as exc:
        raise ValueError(f"Validation failed: {exc.errors()}") from exc


def evaluate_point_moat(
    *,
    project,
    point: PatentPointCandidate,
    llm: LLMClient,
) -> PatentPointCandidate:
    """Evaluate moat scores for a patent point and return the updated candidate."""
    if isinstance(llm, MissingLLMClient):
        raise RuntimeError(
            "LLM is not configured. Set DEEPSEEK_API_KEY before evaluating moat scores."
        )
    scores, rationale = score_moat(llm=llm, project=project, point=point)
    return point.model_copy(
        update={"moat_scores": scores, "moat_rationale": rationale}
    )
