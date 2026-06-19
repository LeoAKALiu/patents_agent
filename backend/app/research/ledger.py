"""Structured source ledger for every prior-art/search attempt.

Records: provider name, query, started/finished timestamps, hit count,
parsed count, dedupe count, failure reason, and citation snapshot.

This is surfaced in disclosure stage_results and in the package's
``research_ledger`` field so both the API and frontend can surface
low-evidence disclosure states.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SourceLedgerEntry(BaseModel):
    """One search attempt recorded in the source ledger."""

    entry_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    provider: str = ""
    kind: str = ""  # patent, arxiv, openalex, web, cnipa, semantic_scholar, tavily, exa
    query: str = ""
    started_at: str = Field(default_factory=_utc_now_iso)
    finished_at: str = ""
    status: str = Field(default="running", pattern="^(running|ok|failed|timeout|skipped)$")
    hit_count: int = 0
    parsed_count: int = 0
    dedupe_count: int = 0
    retained_count: int = 0
    failure_reason: str = ""
    citations: list[dict[str, str]] = Field(default_factory=list)

    def mark_ok(
        self,
        *,
        hit_count: int = 0,
        parsed_count: int = 0,
        dedupe_count: int = 0,
        retained_count: int = 0,
        citations: list[dict[str, str]] | None = None,
    ) -> None:
        self.status = "ok"
        self.hit_count = hit_count
        self.parsed_count = parsed_count
        self.dedupe_count = dedupe_count
        self.retained_count = retained_count
        self.citations = citations or []
        self.finished_at = _utc_now_iso()

    def mark_failed(self, reason: str) -> None:
        self.status = "failed"
        self.failure_reason = reason[:500]
        self.finished_at = _utc_now_iso()

    def mark_timeout(self, reason: str = "") -> None:
        self.status = "timeout"
        self.failure_reason = reason[:500]
        self.finished_at = _utc_now_iso()

    def mark_skipped(self, reason: str) -> None:
        self.status = "skipped"
        self.failure_reason = reason[:500]
        self.finished_at = _utc_now_iso()


class SourceLedger(BaseModel):
    """Append-only ledger of all search attempts."""

    entries: list[SourceLedgerEntry] = Field(default_factory=list)

    def start(
        self,
        *,
        provider: str,
        kind: str,
        query: str,
    ) -> SourceLedgerEntry:
        entry = SourceLedgerEntry(
            provider=provider,
            kind=kind,
            query=query,
        )
        self.entries.append(entry)
        return entry

    def total_hits(self) -> int:
        return sum(entry.retained_count for entry in self.entries if entry.status == "ok")

    def total_citations(self) -> int:
        return sum(len(entry.citations) for entry in self.entries if entry.status == "ok")

    def total_unique_citations(self) -> int:
        return len(self.unique_citation_keys())

    def unique_citation_keys(self) -> set[str]:
        keys: set[str] = set()
        for entry in self.entries:
            if entry.status != "ok":
                continue
            for citation in entry.citations:
                key = _citation_key(citation)
                if key:
                    keys.add(key)
        return keys

    def provider_warnings(self) -> list[str]:
        warnings: list[str] = []
        for entry in self.entries:
            if entry.status == "skipped":
                warnings.append(f"{entry.provider} skipped: {entry.failure_reason}")
            elif entry.status == "failed":
                warnings.append(f"{entry.provider} failed: {entry.failure_reason}")
            elif entry.status == "timeout":
                warnings.append(f"{entry.provider} timed out: {entry.failure_reason}")
        return warnings

    def to_stage_payload(self) -> dict[str, Any]:
        return {
            "entries": [entry.model_dump(mode="json") for entry in self.entries],
            "total_hits": self.total_hits(),
            "total_citations": self.total_citations(),
            "total_unique_citations": self.total_unique_citations(),
            "provider_warnings": self.provider_warnings(),
        }

    def research_confidence(self) -> str:
        """Return 'low', 'medium', or 'high' based on evidence collected.

        - low: 0 references or only skipped/failed providers
        - medium: 1-4 references or at least one provider with hits
        - high: 5+ references from multiple providers
        """
        unique_citations = self.total_unique_citations()
        hits = unique_citations or self.total_hits()
        ok_providers = {entry.provider for entry in self.entries if entry.status == "ok" and entry.retained_count > 0}
        if hits == 0:
            return "low"
        if hits < 5 or len(ok_providers) < 2:
            return "medium"
        return "high"


class ProviderDiagnostic(BaseModel):
    """Pre/post-flight provider diagnostic snapshot."""

    phase: str = Field(
        pattern="^(pre_flight|post_flight)$",
        description="When the diagnostic was collected: before or after search.",
    )
    available_providers: list[str] = Field(default_factory=list)
    skipped_providers: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {provider: reason} for skipped providers.",
    )
    active_chain: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utc_now_iso)


def citation_snapshot(hit: Any, *, max_abstract_length: int = 200) -> dict[str, str]:
    """Produce a compact citation snapshot from a PriorArtHit."""
    pub = getattr(hit, "publication_number", None) or ""
    title = getattr(hit, "title", "") or ""
    url = getattr(hit, "url", "") or ""
    abstract = getattr(hit, "abstract", None) or ""
    source = getattr(hit, "source", "") or ""
    if len(abstract) > max_abstract_length:
        abstract = abstract[:max_abstract_length].rstrip() + "…"
    return {
        "publication_number": pub,
        "title": title[:300],
        "url": url,
        "source": source,
        "abstract_snippet": abstract,
    }


def _citation_key(citation: dict[str, str]) -> str:
    publication_number = (citation.get("publication_number") or "").strip()
    if publication_number:
        return f"pub:{publication_number.upper()}"
    url = (citation.get("url") or "").strip()
    if url:
        return f"url:{url.lower()}"
    title = (citation.get("title") or "").strip()
    if title:
        return f"title:{title.lower()}"
    return ""
