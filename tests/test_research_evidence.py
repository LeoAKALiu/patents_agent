"""Tests for the deep-research evidence ledger and finding grounding."""

from __future__ import annotations

from backend.app.research.evidence import EvidenceLedger, ground_findings
from backend.app.schemas import DeepResearchEvidenceRef, DeepResearchFinding, PriorArtHit


def _hit(pub: str, title: str = "一种图像缺陷检测方法") -> PriorArtHit:
    return PriorArtHit(
        id=f"id-{pub}",
        source="Google Patents",
        query="图像 缺陷",
        title=title,
        publication_number=pub,
        url=f"https://patents.google.com/patent/{pub}",
        abstract="公开了一种图像缺陷检测方法。",
    )


def test_ledger_dedupes_by_publication_number() -> None:
    ledger = EvidenceLedger()
    ledger.add_hit(_hit("CN123A"), provider="patent")
    ledger.add_hit(_hit("CN123A", title="重复条目"), provider="patent")
    ledger.add_hit(_hit("CN456B"), provider="arxiv")
    entries = ledger.entries()
    assert len(entries) == 2
    assert entries[0].evidence_id == "E001"
    assert entries[1].evidence_id == "E002"
    assert entries[0].provider == "patent"
    assert entries[0].citable is True
    assert entries[0].retrieved_at  # timestamp recorded


def test_ledger_to_refs_round_trips_fields() -> None:
    ledger = EvidenceLedger()
    ledger.add_hit(_hit("CN123A"), provider="patent")
    refs = ledger.to_refs()
    assert len(refs) == 1
    assert refs[0].publication_number == "CN123A"
    assert refs[0].source == "Google Patents"


def test_ground_findings_keeps_grounded_differentiator_and_rebinds() -> None:
    ledger = EvidenceLedger()
    ledger.add_hit(_hit("CN123A"), provider="patent")
    finding = DeepResearchFinding(
        id="f1",
        category="differentiator",
        title="实时反馈差异",
        summary="现有技术未实现实时反馈。",
        severity="medium",
        evidence=[
            DeepResearchEvidenceRef(
                source="LLM-echo",
                title="模型回显的标题",
                publication_number="CN123A",  # matches ledger
                url="",
            )
        ],
    )
    grounded, warnings = ground_findings([finding], ledger)
    assert warnings == []
    assert grounded[0].category == "differentiator"
    # evidence was rebound to the canonical ledger entry (verified URL/title)
    assert grounded[0].evidence[0].url == "https://patents.google.com/patent/CN123A"
    assert grounded[0].evidence[0].source == "Google Patents"


def test_ground_findings_downgrades_ungrounded_prior_art_assertion() -> None:
    ledger = EvidenceLedger()
    ledger.add_hit(_hit("CN123A"), provider="patent")
    finding = DeepResearchFinding(
        id="f2",
        category="differentiator",
        title="凭空捏造的现有技术",
        summary="某专利公开了完全相同的方案。",
        severity="high",
        evidence=[
            DeepResearchEvidenceRef(
                source="hallucinated",
                title="不存在的文献",
                publication_number="CN999X",  # NOT in ledger
                url="",
            )
        ],
    )
    grounded, warnings = ground_findings([finding], ledger)
    assert grounded[0].category == "evidence_gap"
    assert grounded[0].summary.startswith("[未取证假设]")
    assert grounded[0].suggested_action
    assert any("downgraded to hypothesis" in w for w in warnings)


def test_ground_findings_keeps_forward_looking_finding_without_evidence() -> None:
    ledger = EvidenceLedger()
    novelty = DeepResearchFinding(
        id="f3",
        category="novelty_opportunity",
        title="可主张的新颖性方向",
        summary="实时闭环反馈可能构成区别点。",
        severity="medium",
        evidence=[],
    )
    constraint = DeepResearchFinding(
        id="f4",
        category="claim_constraint",
        title="撰写约束",
        summary="避免纯功能性概括。",
        severity="low",
        evidence=[],
    )
    grounded, warnings = ground_findings([novelty, constraint], ledger)
    assert [f.category for f in grounded] == ["novelty_opportunity", "claim_constraint"]
    assert warnings == []


def test_ledger_stage_payload_is_serializable() -> None:
    ledger = EvidenceLedger()
    ledger.add_hit(_hit("CN123A"), provider="patent")
    payload = ledger.to_stage_payload()
    assert payload["count"] == 1
    assert payload["entries"][0]["evidence_id"] == "E001"
    assert payload["entries"][0]["provider"] == "patent"
