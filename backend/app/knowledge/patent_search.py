from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Protocol

from backend.app.research.providers import sanitize_untrusted_text
from backend.app.schemas import PatentSearchFilters, PatentSearchHit, PriorArtCandidate


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def normalize_publication_number(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", value).upper()


class PatentSearchProvider(Protocol):
    name: str
    source_id: str

    def available(self) -> tuple[bool, str | None]: ...

    def search(
        self,
        query: str,
        *,
        filters: PatentSearchFilters,
        limit: int,
        ) -> tuple[list[PatentSearchHit], list[str]]: ...


def _sanitize_candidate_text(value: str | None) -> str:
    return sanitize_untrusted_text(value) if value else ""


def _sanitize_candidate_metadata(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_candidate_text(value)
    if isinstance(value, list):
        return [_sanitize_candidate_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_candidate_metadata(item) for item in value)
    if isinstance(value, dict):
        return {key: _sanitize_candidate_metadata(item) for key, item in value.items()}
    return value


def _dedupe_key(hit: PatentSearchHit) -> str:
    publication = normalize_publication_number(hit.publication_number)
    family = hit.family_id.strip().lower()
    url = hit.url.strip().lower()
    fallback = f"{hit.title.strip().lower()}::{hit.applicant.strip().lower()}::{hit.publication_date[:4]}"
    return publication or family or url or fallback


def _merge_metadata(*values: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for value in values:
        merged.update(value)
    return merged


def dedupe_patent_search_hits(hits: list[PatentSearchHit]) -> list[PatentSearchHit]:
    retained: list[PatentSearchHit] = []
    by_key: dict[str, int] = {}
    for hit in hits:
        sanitized_hit = hit.model_copy(
            update={
                "title": sanitize_untrusted_text(hit.title, max_len=300) or hit.title,
                "abstract": sanitize_untrusted_text(hit.abstract) if hit.abstract else None,
            }
        )
        key = _dedupe_key(sanitized_hit)
        if key not in by_key:
            by_key[key] = len(retained)
            retained_hit = sanitized_hit.model_copy(
                update={
                    "metadata": {
                        **sanitized_hit.metadata,
                        "provider_sources": [sanitized_hit.source],
                        "source_attempt_ids": [sanitized_hit.provider_attempt_id]
                        if sanitized_hit.provider_attempt_id
                        else [],
                    },
                }
            )
            retained.append(retained_hit)
            continue

        existing = retained[by_key[key]]
        combined_sources = list(
            dict.fromkeys(
                [
                    *existing.metadata.get("provider_sources", []),
                    sanitized_hit.source,
                ]
            )
        )
        combined_attempt_ids = list(
            dict.fromkeys(
                [
                    *existing.metadata.get("source_attempt_ids", []),
                    *( [sanitized_hit.provider_attempt_id] if sanitized_hit.provider_attempt_id else [] ),
                ]
            )
        )
        merged = existing.model_copy(
            update={
                "metadata": _merge_metadata(
                    existing.metadata,
                    {
                        "provider_sources": combined_sources,
                        "source_attempt_ids": combined_attempt_ids,
                    },
                )
            }
        )
        retained[by_key[key]] = merged
    return retained


def patent_hit_to_candidate(
    hit: PatentSearchHit,
    *,
    project_id: str,
    plan_id: str,
    strategy_group_id: str,
) -> PriorArtCandidate:
    normalized_pub = normalize_publication_number(hit.publication_number)
    matched_terms = hit.query.split()
    sanitized_query = sanitize_untrusted_text(hit.query)
    sanitized_metadata = _sanitize_candidate_metadata(hit.metadata)
    if isinstance(sanitized_metadata, dict):
        sanitized_metadata["source_attempt_ids"] = sanitized_metadata.get("source_attempt_ids") or (
            [hit.provider_attempt_id] if hit.provider_attempt_id else []
        )
    else:
        sanitized_metadata = {}
    return PriorArtCandidate(
        id=stable_id(project_id, plan_id, strategy_group_id, hit.source, normalized_pub or hit.url),
        project_id=project_id,
        plan_id=plan_id,
        source=hit.source,
        title=sanitize_untrusted_text(hit.title, max_len=300) or hit.title,
        publication_number=normalized_pub or hit.publication_number,
        application_number=hit.application_number,
        applicant=_sanitize_candidate_text(hit.applicant),
        publication_date=hit.publication_date,
        grant_date=hit.grant_date,
        abstract=sanitize_untrusted_text(hit.abstract) if hit.abstract else None,
        url=hit.url,
        relevance_score=0.0,
        matched_terms=matched_terms,
        ipc=hit.ipc,
        cpc=hit.cpc,
        family_id=hit.family_id,
        fulltext_status="unknown",
        recommended_action="review",
        recommendation_reason="真实专利检索命中，等待全文与相关度复核。",
        metadata={
            **sanitized_metadata,
            "query": sanitized_query,
            "strategy_group": strategy_group_id,
            "normalized_publication_number": normalized_pub,
            "source_attempt_ids": hit.metadata.get("source_attempt_ids")
            or ([hit.provider_attempt_id] if hit.provider_attempt_id else []),
        },
        created_at=now_iso(),
    )
