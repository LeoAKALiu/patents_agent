from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from backend.app.schemas import DraftPackage, RevisionLedgerRecord


def draft_package_hash(package: DraftPackage) -> str:
    return hashlib.sha256(package.model_dump_json().encode("utf-8")).hexdigest()


def create_revision_record(
    *,
    project_id: str,
    baseline_package: DraftPackage,
    updated_package: DraftPackage,
    revision_kind: str,
    user_intent_summary: str,
    affected_sections: list[str],
    prior_art_changed: bool = False,
    protection_scope_changed: bool = False,
    artifact_refs: list[str] | None = None,
) -> RevisionLedgerRecord:
    return RevisionLedgerRecord(
        id=uuid.uuid4().hex,
        project_id=project_id,
        revision_kind=revision_kind,
        baseline_artifact_hash=draft_package_hash(baseline_package),
        new_artifact_hash=draft_package_hash(updated_package),
        user_intent_summary=user_intent_summary,
        affected_sections=list(dict.fromkeys(affected_sections)),
        prior_art_changed=prior_art_changed,
        protection_scope_changed=protection_scope_changed,
        artifact_refs=list(artifact_refs or []),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
