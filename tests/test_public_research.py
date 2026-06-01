from __future__ import annotations

import csv
import json

from backend.app.research.public_search import (
    PublicSearchHit,
    build_reverse_modeling_search_plan,
    deduplicate_hits,
    export_research_package,
    parse_anysearch_payload,
    publication_number_from_text,
    run_anysearch_plan,
)


def test_build_reverse_modeling_search_plan_contains_patent_ready_queries():
    plan = build_reverse_modeling_search_plan()

    assert plan.topic == "既有建筑外立面逆建模与工程算量"
    assert {theme.id for theme in plan.themes} == {
        "geometry",
        "occlusion_semantics",
        "ifc_quantity",
        "hitl_quality",
    }
    assert all(theme.ipc_filters for theme in plan.themes)
    assert any("site:patents.google.com" in query.query for query in plan.queries)
    assert any(query.provider == "anysearch" and query.domain == "ip" for query in plan.queries)
    assert any("CNIPA" in prompt for prompt in plan.deepresearch_prompts)


def test_publication_number_from_text_extracts_chinese_publication_numbers():
    assert publication_number_from_text("https://patents.google.com/patent/CN107093205B/zh") == "CN107093205B"
    assert publication_number_from_text("公开文本 CN116894288A 基于BIM的工程量计算") == "CN116894288A"
    assert publication_number_from_text("no patent number here") == ""


def test_deduplicate_hits_prefers_better_quality_for_same_publication():
    hits = [
        PublicSearchHit(
            theme_id="geometry",
            title="低质量结果",
            url="https://patents.google.com/patent/CN107093205B/zh",
            description="old",
            provider="web",
            quality_score=0.2,
        ),
        PublicSearchHit(
            theme_id="geometry",
            title="高质量结果",
            url="https://example.com/CN107093205B",
            description="new",
            provider="anysearch",
            quality_score=0.9,
        ),
    ]

    deduped = deduplicate_hits(hits)

    assert len(deduped) == 1
    assert deduped[0].title == "高质量结果"
    assert deduped[0].publication_number == "CN107093205B"


def test_export_research_package_writes_queries_hits_and_summary(tmp_path):
    plan = build_reverse_modeling_search_plan()
    hits = [
        PublicSearchHit(
            theme_id="ifc_quantity",
            title="基于BIM的工程量计算方法、装置、设备及存储介质",
            url="https://patents.google.com/patent/CN116894288A/zh",
            description="BIM 构件名称和参数匹配工程量计算规则。",
            provider="seed",
            quality_score=0.8,
        )
    ]

    outputs = export_research_package(plan, hits, tmp_path)

    assert outputs["queries_json"].exists()
    assert outputs["candidate_csv"].exists()
    assert outputs["summary_md"].exists()
    assert outputs["deepresearch_prompts_md"].exists()
    assert outputs["cnipa_worklist_md"].exists()

    query_payload = json.loads(outputs["queries_json"].read_text(encoding="utf-8"))
    assert query_payload["topic"] == plan.topic
    assert len(query_payload["queries"]) == len(plan.queries)

    with outputs["candidate_csv"].open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["publication_number"] == "CN116894288A"
    assert rows[0]["theme_id"] == "ifc_quantity"
    assert "突破口" in outputs["summary_md"].read_text(encoding="utf-8")
    assert "CNIPA" in outputs["deepresearch_prompts_md"].read_text(encoding="utf-8")
    assert "导出字段" in outputs["cnipa_worklist_md"].read_text(encoding="utf-8")


def test_run_anysearch_plan_can_limit_queries_and_continue_after_errors():
    plan = build_reverse_modeling_search_plan()

    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        def search(self, query):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary provider timeout")
            return [
                PublicSearchHit(
                    theme_id=query.theme_id,
                    title=f"命中 {self.calls}",
                    url=f"https://patents.google.com/patent/CN10000000{self.calls}A/zh",
                    provider="fake",
                    quality_score=0.5,
                )
            ]

    client = FakeClient()
    hits, errors = run_anysearch_plan(plan, client=client, limit_per_query=1, max_queries=3, continue_on_error=True)

    assert client.calls == 3
    assert len(hits) == 2
    assert errors[0]["query_id"] == plan.queries[0].id


def test_parse_anysearch_payload_reads_nested_data_results():
    payload = {
        "code": 0,
        "data": {
            "results": [
                {
                    "title": "点云三维重建自动化生成建筑工程BIM模型的方法及装置",
                    "url": "https://patents.google.com/patent/CN117058337A/zh",
                    "content": "本发明公开了一种点云三维重建自动化生成建筑工程BIM模型的方法。",
                    "score": 74.75,
                    "quality_score": 74.75,
                }
            ]
        },
    }

    hits = parse_anysearch_payload(payload, theme_id="ifc_quantity")

    assert len(hits) == 1
    assert hits[0].publication_number == "CN117058337A"
    assert hits[0].provider == "anysearch"
