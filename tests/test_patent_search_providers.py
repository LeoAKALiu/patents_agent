from backend.app.knowledge.patent_search import (
    dedupe_patent_search_hits,
    normalize_publication_number,
    patent_hit_to_candidate,
)
from backend.app.schemas import PatentSearchHit


def test_normalize_publication_number_collapses_spaces_and_case():
    assert normalize_publication_number(" cn  112233445 a ") == "CN112233445A"


def test_dedupe_patent_search_hits_merges_provider_sources():
    cnipa = PatentSearchHit(
        id="h1",
        source="cnipa_epub",
        title="城市体检任务编排方法",
        publication_number="CN112233445A",
        url="https://epub.cnipa.gov.cn/patent/CN112233445A",
        query="城市体检 任务编排",
        provider_attempt_id="attempt-cnipa",
    )
    google = PatentSearchHit(
        id="h2",
        source="google_patents",
        title="城市体检任务编排方法",
        publication_number="cn112233445a",
        url="https://patents.google.com/patent/CN112233445A",
        query="urban health task orchestration",
        provider_attempt_id="attempt-google",
    )

    deduped = dedupe_patent_search_hits([cnipa, google])

    assert len(deduped) == 1
    assert deduped[0].source == "cnipa_epub"
    assert deduped[0].metadata["provider_sources"] == ["cnipa_epub", "google_patents"]
    assert deduped[0].metadata["source_attempt_ids"] == ["attempt-cnipa", "attempt-google"]


def test_patent_hit_to_candidate_preserves_real_source_and_url():
    hit = PatentSearchHit(
        id="h1",
        source="google_patents",
        title="可信复核系统",
        publication_number="CN109999999A",
        url="https://patents.google.com/patent/CN109999999A",
        query="可信复核",
        provider_attempt_id="attempt-1",
        abstract="公开了一种复核方法。",
    )

    candidate = patent_hit_to_candidate(hit, project_id="p1", plan_id="plan1", strategy_group_id="closest")

    assert candidate.source == "google_patents"
    assert candidate.publication_number == "CN109999999A"
    assert candidate.url == "https://patents.google.com/patent/CN109999999A"
    assert candidate.metadata["strategy_group"] == "closest"
    assert candidate.metadata["source_attempt_ids"] == ["attempt-1"]
