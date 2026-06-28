from backend.app.disclosure.prior_art import (
    PublicPriorArtProvider,
    dedupe_prior_art_hits,
    normalize_search_terms,
    prior_art_url_warnings,
)
from backend.app.schemas import PriorArtHit


def _hit(hit_id: str, publication: str | None, url: str, title: str) -> PriorArtHit:
    return PriorArtHit(
        id=hit_id,
        source="Google Patents",
        query="图像 缺陷",
        title=title,
        publication_number=publication,
        url=url,
        abstract="摘要",
    )


def test_normalize_search_terms_splits_long_sentence_and_caps_to_eight() -> None:
    terms = normalize_search_terms(
        ["一种基于神经网络实时反馈的图像缺陷识别方法及系统"],
        fallback_text="图像缺陷 神经网络 实时反馈 闭环控制 检测策略 误检率 采集调度 权重更新 质量评估",
    )

    assert 2 <= len(terms) <= 8
    assert all(len(term) <= 24 for term in terms)
    assert "图像缺陷" in terms[0]


def test_normalize_search_terms_keeps_single_valid_term_without_fallback_expansion() -> None:
    terms = normalize_search_terms(
        ["图像缺陷"],
        fallback_text="图像缺陷 神经网络 实时反馈 闭环控制",
    )

    assert terms == ["图像缺陷"]


def test_normalize_search_terms_drops_too_short_ascii_term() -> None:
    assert normalize_search_terms(["a"], fallback_text="") == []


def test_normalize_search_terms_drops_single_cjk_character() -> None:
    assert normalize_search_terms(["图"], fallback_text="") == []


def test_dedupe_prior_art_hits_prefers_publication_number_then_url() -> None:
    hits = [
        _hit("h1", "CN123456789A", "https://patents.google.com/patent/CN123456789A", "标题A"),
        _hit("h2", "CN123456789A", "https://example.com/duplicate", "标题A重复"),
        _hit("h3", None, "https://patents.google.com/patent/US20240123456A1", "标题B"),
        _hit("h4", None, "https://patents.google.com/patent/US20240123456A1", "标题B重复"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert [hit.id for hit in deduped] == ["h1", "h3"]


def test_prior_art_url_warnings_flags_missing_public_urls() -> None:
    warnings = prior_art_url_warnings([
        _hit("h1", "CN123456789A", "", "无 URL"),
        _hit("h2", None, "https://patents.google.com/patent/US20240123456A1", "有 URL"),
    ])

    assert warnings == ["prior_art missing public URL: CN123456789A 无 URL"]


def test_public_provider_calls_cnipa_once_per_normalized_term() -> None:
    class RecordingProvider(PublicPriorArtProvider):
        def __init__(self) -> None:
            super().__init__(cnipa_script=None)
            self.cnipa_terms: list[str] = []
            self.google_terms: list[str] = []

        def _search_cnipa(self, term: str, limit: int):
            self.cnipa_terms.append(term)
            return [], []

        def _search_google_patents(self, term: str, limit: int):
            self.google_terms.append(term)
            return [], []

    provider = RecordingProvider()

    provider.search(["图像缺陷 神经网络 实时反馈 闭环控制"], limit=4)

    assert len(provider.cnipa_terms) >= 2
    assert all(" " not in term.strip(" ") or len(term) <= 24 for term in provider.cnipa_terms)
