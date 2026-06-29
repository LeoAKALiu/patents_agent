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


def test_dedupe_prior_art_hits_removes_overlap_when_later_hit_only_has_url() -> None:
    hits = [
        _hit("h1", "CN123456789A", "https://patents.google.com/patent/CN123456789A", "标题A"),
        _hit("h2", None, "https://patents.google.com/patent/CN123456789A", "标题A备用网址"),
        _hit("h3", None, "https://patents.google.com/patent/CN999999999A", "标题B"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert [hit.id for hit in deduped] == ["h1", "h3"]


def test_dedupe_prior_art_hits_merges_richer_duplicate_in_place() -> None:
    hits = [
        PriorArtHit(
            id="h1",
            source="CNIPA EPUB",
            query="图像 缺陷",
            title="标题A",
            publication_number="CN123456789A",
            url="",
            abstract=None,
        ),
        PriorArtHit(
            id="h2",
            source="Google Patents",
            query="图像 缺陷",
            title="标题A",
            publication_number=None,
            url="https://patents.google.com/patent/CN123456789A",
            abstract="更完整摘要",
        ),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert len(deduped) == 1
    assert deduped[0].id == "h1"
    assert deduped[0].url == "https://patents.google.com/patent/CN123456789A"
    assert deduped[0].abstract == "更完整摘要"


def test_dedupe_prior_art_hits_does_not_bridge_mismatched_public_url_publication() -> None:
    hits = [
        _hit("h1", "CN123456789A", "https://example.com/cn123", "标题A"),
        _hit("h2", None, "https://patents.google.com/patent/US20240123456A1", "标题B"),
        _hit("h3", "CN123456789A", "https://patents.google.com/patent/US20240123456A1", "桥接标题"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert len(deduped) == 2
    assert deduped[0].id == "h1"
    assert deduped[0].publication_number == "CN123456789A"
    assert deduped[0].url == "https://example.com/cn123"
    assert deduped[1].id == "h2"
    assert deduped[1].publication_number is None
    assert deduped[1].url == "https://patents.google.com/patent/US20240123456A1"


def test_dedupe_prior_art_hits_still_merges_matched_publication_url_alias() -> None:
    hits = [
        _hit("h1", "CN123456789A", "https://example.com/cn123", "标题A"),
        _hit("h2", None, "https://patents.google.com/patent/CN123456789A", "标题A公开链接"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert len(deduped) == 1
    assert deduped[0].id == "h1"
    assert deduped[0].publication_number == "CN123456789A"
    assert deduped[0].url == "https://patents.google.com/patent/CN123456789A"


def test_dedupe_prior_art_hits_prefers_richer_fields_and_unions_differentiators() -> None:
    hits = [
        PriorArtHit(
            id="h1",
            source="CNIPA EPUB",
            query="图像 缺陷",
            title="短标题",
            publication_number="CN123456789A",
            url="https://example.com/generic",
            abstract="短摘要",
            relevance_summary="相关",
            differentiators=["低延迟"],
        ),
        PriorArtHit(
            id="h2",
            source="Google Patents",
            query="图像 缺陷",
            title="更完整的图像缺陷识别公开标题",
            publication_number="CN123456789A",
            url="https://patents.google.com/patent/CN123456789A",
            abstract="这是一个明显更完整的摘要，用于描述技术方案的输入、处理和输出。",
            relevance_summary="该文献更具体地涉及图像缺陷识别和任务调度。",
            differentiators=["动态阈值", "低延迟"],
        ),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert len(deduped) == 1
    assert deduped[0].id == "h1"
    assert deduped[0].title == "更完整的图像缺陷识别公开标题"
    assert deduped[0].publication_number == "CN123456789A"
    assert deduped[0].url == "https://patents.google.com/patent/CN123456789A"
    assert deduped[0].abstract == "这是一个明显更完整的摘要，用于描述技术方案的输入、处理和输出。"
    assert deduped[0].relevance_summary == "该文献更具体地涉及图像缺陷识别和任务调度。"
    assert deduped[0].differentiators == ["低延迟", "动态阈值"]


def test_dedupe_prior_art_hits_keeps_same_title_when_publications_differ() -> None:
    hits = [
        _hit("h1", "CN123456789A", "", "通用任务调度方法"),
        _hit("h2", "US20240123456A1", "", "通用任务调度方法"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert [hit.id for hit in deduped] == ["h1", "h2"]


def test_dedupe_prior_art_hits_falls_back_to_title_when_publication_and_url_missing() -> None:
    hits = [
        _hit("h1", None, "", "通用任务调度方法"),
        _hit("h2", None, "", "通用任务调度方法"),
    ]

    deduped = dedupe_prior_art_hits(hits)

    assert [hit.id for hit in deduped] == ["h1"]


def test_prior_art_url_warnings_flags_missing_public_urls() -> None:
    warnings = prior_art_url_warnings([
        _hit("h1", "CN123456789A", "", "无 URL"),
        _hit("h2", None, "https://patents.google.com/patent/US20240123456A1", "有 URL"),
    ])

    assert warnings == ["prior_art missing public URL: CN123456789A 无 URL"]


def test_prior_art_url_warnings_flags_unsupported_public_urls() -> None:
    warnings = prior_art_url_warnings([
        _hit("h1", "CN123456789A", "https://example.com/patent/CN123456789A", "非公开视频链接"),
        _hit("h2", None, "https://patents.google.com/patent/US20240123456A1", "有 URL"),
    ])

    assert warnings == ["prior_art unsupported public URL: CN123456789A 非公开视频链接"]


def test_prior_art_url_warnings_flags_mismatched_publication_public_url() -> None:
    warnings = prior_art_url_warnings([
        _hit("h1", "CN123456789A", "https://patents.google.com/patent/US20240123456A1", "公开视频错链"),
    ])

    assert warnings == ["prior_art mismatched public URL: CN123456789A 公开视频错链"]


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


def test_public_provider_uses_deduped_quota_before_stopping() -> None:
    class RecordingProvider(PublicPriorArtProvider):
        def __init__(self) -> None:
            super().__init__(cnipa_script=None)
            self.cnipa_terms: list[str] = []

        def _search_cnipa(self, term: str, limit: int):
            self.cnipa_terms.append(term)
            if len(self.cnipa_terms) == 1:
                return [
                    _hit("h1", "CN123456789A", "https://patents.google.com/patent/CN123456789A", "标题A"),
                    _hit("h2", "CN123456789A", "https://patents.google.com/patent/CN123456789A", "标题A重复"),
                ], []
            if len(self.cnipa_terms) == 2:
                return [
                    _hit("h3", "CN999999999A", "https://patents.google.com/patent/CN999999999A", "标题B"),
                ], []
            return [], []

        def _search_google_patents(self, term: str, limit: int):
            raise AssertionError("google fallback should not run before deduped quota is filled")

    provider = RecordingProvider()

    hits, warnings = provider.search(["图像缺陷 神经网络 实时反馈 闭环控制"], limit=2)

    assert warnings == []
    assert len(provider.cnipa_terms) >= 2
    assert [hit.publication_number for hit in hits] == ["CN123456789A", "CN999999999A"]
