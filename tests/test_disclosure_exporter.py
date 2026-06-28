from backend.app.disclosure.exporter import (
    clean_disclosure_to_markdown,
    disclosure_sidecar_to_markdown,
)
from backend.app.schemas import DisclosurePackage, DisclosureSelfCheckFinding, PatentPointCandidate, PriorArtHit


def _package() -> DisclosurePackage:
    return DisclosurePackage(
        title="一种图像缺陷识别方法",
        summary="摘要",
        materials_summary="材料覆盖",
        candidates=[
            PatentPointCandidate(
                id="p1",
                title="闭环反馈",
                technical_problem="效率低",
                innovation="实时反馈",
                technical_solution="检测后回写采集策略",
                protection_focus=["方法"],
            )
        ],
        selected_candidate_id="p1",
        prior_art_hits=[
            PriorArtHit(
                id="h1",
                source="Google Patents",
                query="图像 缺陷",
                title="一种图像缺陷检测方法",
                publication_number="CN123456789A",
                url="https://patents.google.com/patent/CN123456789A",
                abstract="公开了缺陷检测。",
                differentiators=["缺少闭环反馈"],
            )
        ],
        prior_art_differences="现有技术缺少闭环反馈。",
        body_markdown="# 技术交底书正文\n\n## 一、背景\n正文。",
        mermaid="flowchart TD\nA-->B",
        image_prompt="黑白线稿",
        self_check_findings=[
            DisclosureSelfCheckFinding(category="url", severity="low", message="URL 存在", suggestion="无")
        ],
        generation_logs=["project_scan: summarized draft", "warning: internal"],
        research_ledger={"entries": [{"provider": "google_patents"}]},
        provider_diagnostics=[{"phase": "post_flight"}],
        research_confidence="medium",
    )


def test_clean_disclosure_excludes_internal_sections() -> None:
    markdown = clean_disclosure_to_markdown(_package())

    assert "技术交底书正文" in markdown
    assert "https://patents.google.com/patent/CN123456789A" in markdown
    assert "Claim Chart" not in markdown
    assert "检索来源台账" not in markdown
    assert "自检结果" not in markdown
    assert "生成日志" not in markdown
    assert "provider_diagnostics" not in markdown
    assert "evidence_id" not in markdown


def test_sidecar_contains_internal_sections() -> None:
    markdown = disclosure_sidecar_to_markdown(_package())

    assert "Claim Chart" in markdown
    assert "检索来源台账" in markdown
    assert "自检结果" in markdown
    assert "生成日志" in markdown
    assert "Google Patents" in markdown


def test_clean_disclosure_appends_only_missing_public_prior_art_urls() -> None:
    package = _package().model_copy(
        update={
            "body_markdown": (
                "# 技术交底书正文\n\n"
                "正文已引用 https://patents.google.com/patent/CN123456789A 。"
            ),
            "prior_art_hits": [
                *_package().prior_art_hits,
                PriorArtHit(
                    id="h2",
                    source="Google Patents",
                    query="图像 缺陷",
                    title="另一篇现有技术",
                    publication_number="US20240123456A1",
                    url="https://patents.google.com/patent/US20240123456A1",
                    abstract="公开了另一种处理方式。",
                ),
                PriorArtHit(
                    id="h3",
                    source="Google Patents",
                    query="图像 缺陷",
                    title="无公开链接条目",
                    publication_number="CN000000001A",
                    url="",
                ),
            ],
        }
    )

    markdown = clean_disclosure_to_markdown(package)

    assert markdown.count("https://patents.google.com/patent/CN123456789A") == 1
    assert "https://patents.google.com/patent/US20240123456A1" in markdown
    assert "无公开链接条目" not in markdown
