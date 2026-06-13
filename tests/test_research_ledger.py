"""Tests for the research source ledger and provider diagnostics."""

from __future__ import annotations

from backend.app.disclosure.prior_art import PublicPriorArtProvider
from backend.app.research.ledger import (
    ProviderDiagnostic,
    SourceLedger,
    SourceLedgerEntry,
    citation_snapshot,
)
from backend.app.schemas import PriorArtHit


def test_source_ledger_start_and_mark_ok() -> None:
    ledger = SourceLedger()
    entry = ledger.start(provider="google_patents", kind="patent", query="CN 图像 缺陷")
    assert entry.status == "running"
    assert entry.provider == "google_patents"
    assert len(ledger.entries) == 1

    entry.mark_ok(hit_count=5, parsed_count=5, dedupe_count=1, retained_count=4)
    assert entry.status == "ok"
    assert entry.retained_count == 4
    assert entry.finished_at


def test_source_ledger_mark_failed_and_skipped() -> None:
    ledger = SourceLedger()
    e1 = ledger.start(provider="cnipa", kind="cnipa", query="test")
    e1.mark_skipped("CNIPA EPUB helper not configured")

    e2 = ledger.start(provider="google_patents", kind="patent", query="test2")
    e2.mark_failed("network timeout")

    e3 = ledger.start(provider="google_patents", kind="patent", query="test3")
    e3.mark_timeout("operation timed out after 20s")

    assert e1.status == "skipped"
    assert e2.status == "failed"
    assert e3.status == "timeout"
    assert len(ledger.entries) == 3


def test_source_ledger_totals_and_confidence() -> None:
    ledger = SourceLedger()
    # No entries = low confidence
    assert ledger.research_confidence() == "low"
    assert ledger.total_hits() == 0

    # One provider with 0 hits = low
    e1 = ledger.start(provider="patent", kind="patent", query="q1")
    e1.mark_ok(hit_count=0, parsed_count=0, dedupe_count=0, retained_count=0)
    assert ledger.research_confidence() == "low"

    # One provider with 3 hits = medium
    e2 = ledger.start(provider="patent", kind="patent", query="q2")
    e2.mark_ok(
        hit_count=3, parsed_count=3, dedupe_count=0, retained_count=3,
        citations=[{"publication_number": "CN123A", "title": "test", "url": "http://x", "source": "patent", "abstract_snippet": "test"}],
    )
    assert ledger.research_confidence() == "medium"
    assert ledger.total_hits() == 3

    # A second provider with hits = high
    e3 = ledger.start(provider="arxiv", kind="arxiv", query="q3")
    e3.mark_ok(
        hit_count=2, parsed_count=2, dedupe_count=0, retained_count=2,
        citations=[{"publication_number": "2401.00001", "title": "paper", "url": "http://arxiv", "source": "arXiv", "abstract_snippet": "abstract"}],
    )
    assert ledger.research_confidence() == "high"
    assert ledger.total_hits() == 5


def test_source_ledger_stage_payload_includes_warnings() -> None:
    ledger = SourceLedger()
    e1 = ledger.start(provider="cnipa", kind="cnipa", query="q1")
    e1.mark_skipped("not configured")

    e2 = ledger.start(provider="patent", kind="patent", query="q2")
    e2.mark_ok(hit_count=1, retained_count=1)

    payload = ledger.to_stage_payload()
    assert payload["total_hits"] == 1
    assert payload["total_citations"] == 0
    assert len(payload["entries"]) == 2
    assert any("cnipa skipped" in w for w in payload["provider_warnings"])


def test_provider_diagnostics_pre_flight() -> None:
    diag = ProviderDiagnostic(
        phase="pre_flight",
        available_providers=["google_patents"],
        skipped_providers=[{"provider": "cnipa", "reason": "not configured"}],
        active_chain=["google_patents"],
    )
    assert diag.phase == "pre_flight"
    assert "cnipa" in diag.skipped_providers[0]["provider"]
    assert diag.warnings == []
    assert diag.created_at


def test_provider_diagnostics_post_flight_with_warnings() -> None:
    diag = ProviderDiagnostic(
        phase="post_flight",
        available_providers=["patent", "arxiv"],
        skipped_providers=[{"provider": "tavily", "reason": "no api key"}],
        active_chain=["patent", "arxiv"],
        warnings=["patent returned 0 hits", "tavily skipped: no api key"],
    )
    assert diag.phase == "post_flight"
    assert len(diag.warnings) == 2


def test_citation_snapshot_truncates_long_abstract() -> None:
    hit = PriorArtHit(
        id="h1",
        source="Google Patents",
        query="test",
        title="A Method for Defect Detection",
        publication_number="CN123456789A",
        url="https://patents.google.com/patent/CN123456789A",
        abstract="A" * 500,
    )
    snap = citation_snapshot(hit, max_abstract_length=50)
    assert snap["publication_number"] == "CN123456789A"
    assert len(snap["abstract_snippet"]) <= 51  # 50 + "…"
    assert snap["source"] == "Google Patents"


def test_disclosure_package_has_research_confidence_default_low() -> None:
    from backend.app.schemas import DisclosurePackage
    package = DisclosurePackage(
        title="test",
        summary="test",
        materials_summary="test",
        body_markdown="# test",
        mermaid="",
        image_prompt="",
    )
    assert package.research_confidence == "low"
    assert package.research_ledger == {}
    assert package.provider_diagnostics == []


def test_public_prior_art_provider_records_per_provider_attempts(monkeypatch) -> None:
    provider = PublicPriorArtProvider(cnipa_script=None)

    def fake_google(term: str, limit: int):
        return [
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query=term,
                title="一种图像缺陷检测方法",
                publication_number="CN123456789A",
                url="https://patents.google.com/patent/CN123456789A",
            )
        ][:limit], []

    monkeypatch.setattr(provider, "_search_google_patents", fake_google)
    ledger = SourceLedger()

    hits, warnings = provider.search_with_ledger(["图像 缺陷"], 3, ledger)

    assert hits[0].publication_number == "CN123456789A"
    assert warnings == ["CNIPA EPUB helper is not configured; set CNIPA_EPUB_SEARCH_SCRIPT to enable live CNIPA search."]
    assert [entry.provider for entry in ledger.entries] == ["cnipa", "google_patents"]
    assert ledger.entries[0].status == "skipped"
    assert ledger.entries[1].status == "ok"
