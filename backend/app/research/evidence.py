"""Evidence ledger for ``free_deep_research`` mode.

Every prior-art hit a provider returns is recorded as an :class:`EvidenceEntry`
with its source, retrieval query, timestamp, a confidence score and a
``citable`` flag. Findings produced by the LLM synthesis step are then
*grounded* against the ledger:

* A finding that asserts a **prior-art fact** (``prior_art_cluster`` /
  ``differentiator``) must point at ≥1 ledger entry. If it cannot be grounded
  it is downgraded to a non-asserting category (``evidence_gap``) and clearly
  marked as an unverified hypothesis — synthesis is never allowed to invent
  prior art out of thin air.
* Forward-looking, our-side findings (``novelty_opportunity``,
  ``claim_constraint``, ``completion_task``, ``warning``) are kept as-is.

The ledger is surfaced into ``stage_results`` / ``generation_logs`` for internal
review. It is **never** written into the canonical disclosure body or any
official-export surface.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from pydantic import BaseModel, Field

from backend.app.schemas import DeepResearchEvidenceRef, DeepResearchFinding, PriorArtHit


# Categories whose findings ASSERT the existence/content of prior art. These
# must be backed by ledger evidence or they get downgraded.
_PRIOR_ART_ASSERTING_CATEGORIES = {"prior_art_cluster", "differentiator"}
_HYPOTHESIS_PREFIX = "[未取证假设] "


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class EvidenceEntry(BaseModel):
    """One immutable, de-duplicated piece of evidence in the ledger."""

    evidence_id: str
    provider: str
    source: str
    title: str
    url: str = ""
    publication_number: str | None = None
    snippet: str = ""
    matched_query: str = ""
    retrieved_at: str = Field(default_factory=_utc_now_iso)
    confidence: float = 0.5
    citable: bool = True

    @property
    def labels(self) -> set[str]:
        """All identifiers a finding might use to cite this entry."""
        out: set[str] = set()
        for value in (self.publication_number, self.url, self.title, self.evidence_id):
            if value:
                out.add(_normalize_label(value))
        return out


def _normalize_label(value: str) -> str:
    return str(value).strip().upper()


def _dedup_key(*, publication_number: str | None, url: str, title: str) -> str:
    basis = (publication_number or url or title or "").strip().upper()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16] if basis else ""


class EvidenceLedger:
    """Append-only, de-duplicated store of evidence with citation binding."""

    def __init__(self) -> None:
        self._entries: dict[str, EvidenceEntry] = {}
        self._order: list[str] = []

    # -- ingestion ---------------------------------------------------------

    def add_hit(self, hit: PriorArtHit, *, provider: str, confidence: float = 0.5) -> EvidenceEntry:
        key = _dedup_key(
            publication_number=hit.publication_number,
            url=hit.url,
            title=hit.title,
        )
        if not key:
            key = _dedup_key(publication_number=None, url="", title=hit.id)
        if key in self._entries:
            return self._entries[key]
        entry = EvidenceEntry(
            evidence_id=f"E{len(self._order) + 1:03d}",
            provider=provider,
            source=hit.source or provider,
            title=hit.title,
            url=hit.url,
            publication_number=hit.publication_number,
            snippet=(hit.abstract or hit.relevance_summary or "")[:600],
            matched_query=hit.query,
            confidence=confidence,
            # Web snippets (Tavily/Exa) are weaker than patent/paper records;
            # the caller may pass a lower confidence, but we still keep them
            # citable so the attorney can verify.
            citable=True,
        )
        self._entries[key] = entry
        self._order.append(key)
        return entry

    def add_hits(self, hits: Iterable[PriorArtHit], *, provider: str, confidence: float = 0.5) -> list[EvidenceEntry]:
        return [self.add_hit(hit, provider=provider, confidence=confidence) for hit in hits]

    # -- access ------------------------------------------------------------

    def entries(self) -> list[EvidenceEntry]:
        return [self._entries[key] for key in self._order]

    def __len__(self) -> int:
        return len(self._order)

    def find_by_label(self, label: str) -> EvidenceEntry | None:
        if not label:
            return None
        needle = _normalize_label(label)
        for entry in self._entries.values():
            if needle in entry.labels:
                return entry
        return None

    def to_refs(self) -> list[DeepResearchEvidenceRef]:
        return [
            DeepResearchEvidenceRef(
                source=entry.source,
                query=entry.matched_query,
                title=entry.title,
                publication_number=entry.publication_number,
                url=entry.url,
                relevance=entry.snippet,
            )
            for entry in self.entries()
        ]

    def to_stage_payload(self) -> dict:
        return {
            "entries": [entry.model_dump(mode="json") for entry in self.entries()],
            "count": len(self),
        }


def ground_findings(
    findings: list[DeepResearchFinding],
    ledger: EvidenceLedger,
) -> tuple[list[DeepResearchFinding], list[str]]:
    """Bind each finding's evidence refs to ledger entries and downgrade any
    ungrounded prior-art assertion to a hypothesis.

    Returns ``(grounded_findings, warnings)``.
    """

    grounded: list[DeepResearchFinding] = []
    warnings: list[str] = []
    for finding in findings:
        matched_entries: list[EvidenceEntry] = []
        for ref in finding.evidence:
            for candidate in (ref.publication_number, ref.url, ref.title):
                entry = ledger.find_by_label(candidate) if candidate else None
                if entry is not None:
                    matched_entries.append(entry)
                    break

        has_grounding = len(matched_entries) > 0
        if finding.category in _PRIOR_ART_ASSERTING_CATEGORIES and not has_grounding:
            # Downgrade: this finding asserts prior-art facts but cites nothing
            # we actually retrieved. Re-class as an evidence gap / hypothesis.
            summary = finding.summary or ""
            if not summary.startswith(_HYPOTHESIS_PREFIX):
                summary = _HYPOTHESIS_PREFIX + summary
            grounded.append(
                finding.model_copy(
                    update={
                        "category": "evidence_gap",
                        "summary": summary,
                        "suggested_action": (
                            finding.suggested_action
                            or "该结论缺少检索证据支撑，提交前需人工补充现有技术证据或删除。"
                        ),
                    }
                )
            )
            warnings.append(
                f"finding '{finding.title[:40]}' downgraded to hypothesis: no retrieved evidence supports it"
            )
            continue

        # Rebind evidence refs to the canonical ledger entries (so URLs/numbers
        # are the verified ones, not whatever the LLM echoed back).
        if matched_entries:
            rebound_refs = [
                DeepResearchEvidenceRef(
                    source=entry.source,
                    query=entry.matched_query,
                    title=entry.title,
                    publication_number=entry.publication_number,
                    url=entry.url,
                    relevance=entry.snippet,
                )
                for entry in _dedupe_entries(matched_entries)
            ]
            grounded.append(finding.model_copy(update={"evidence": rebound_refs}))
        else:
            grounded.append(finding)
    return grounded, warnings


def _dedupe_entries(entries: list[EvidenceEntry]) -> list[EvidenceEntry]:
    seen: set[str] = set()
    out: list[EvidenceEntry] = []
    for entry in entries:
        if entry.evidence_id in seen:
            continue
        seen.add(entry.evidence_id)
        out.append(entry)
    return out
