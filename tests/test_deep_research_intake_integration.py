from backend.app.disclosure.generator import DisclosureGenerator
from backend.app.disclosure.prior_art import StaticPriorArtProvider
from backend.app.evidence_binding import build_evidence_bindings
from backend.app.llm import FakeLLMClient
from backend.app.schemas import (
    EvidenceBindingSourceType,
    ProjectMaterial,
    ProjectRecord,
)


DEEP_RESEARCH_MD = """
# DeepResearch

## 现有技术
- CN123456789A 一种图像缺陷检测方法 https://patents.google.com/patent/CN123456789A
  摘要：公开了基于神经网络的图像缺陷检测，但未涉及实时闭环反馈。

## 差异点
- 本方案将检测结果实时回写至采集策略，形成闭环反馈。

## 权利要求约束
- 独立权利要求应突出检测结果回写采集策略的闭环控制。

## 任务
- 补充实时回写策略的时序实施例。
"""

DEEP_RESEARCH_MD_WITH_MISSING_URL = """
# DeepResearch

## 现有技术
- CN987654321A 一种无公开链接的图像缺陷检测方法
  摘要：公开了图像缺陷检测，但未给出可访问 URL。

## 差异点
- 本方案将检测结果实时回写至采集策略。
"""

DEEP_RESEARCH_MD_WITH_UNSUPPORTED_URL = """
# DeepResearch

## 现有技术
- CN123456789A 一种非公开视频链接的图像缺陷检测方法 https://example.com/patent/CN123456789A
  摘要：公开了图像缺陷检测，但链接不是公开专利来源。

## 差异点
- 本方案将检测结果实时回写至采集策略。
"""


def _responses() -> dict[str, str]:
    return {
        "disclosure_scan": '{"summary":"图像缺陷识别","materials_summary":"材料覆盖","technical_keywords":["图像"],"implementation_gaps":[]}',
        "patent_points": '{"candidates":[{"id":"p1","title":"图像缺陷识别方法","technical_problem":"效率低","innovation":"闭环反馈","technical_solution":"采集并检测后实时回写策略","beneficial_effects":["提高效率"],"protection_focus":["方法","系统"],"grantability_score":0.8,"rationale":"完整"}],"selected_candidate_id":"p1"}',
        "prior_art_terms": '["图像 缺陷 神经网络"]',
        "prior_art_relevance": '{"prior_art_differences":"区别在实时反馈。","hits":[],"claim_charts":[]}',
        "disclosure_body": "# 技术交底书",
        "disclosure_mermaid": "flowchart TD\\nA[采集] --> B[反馈]",
        "disclosure_image_prompt": "黑白线稿。",
        "disclosure_self_check": "[]",
    }


def test_deepresearch_material_adds_disclosure_stage_context() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD,
        status="processed",
    )
    llm = FakeLLMClient(_responses())
    generator = DisclosureGenerator(llm, StaticPriorArtProvider())

    package, stages, warnings = generator.generate(
        project=project,
        materials=[material],
        context_chunks=[],
        max_prior_art_results=0,
    )

    assert any(stage["phase"] == "deep_research_material_intake" for stage in stages)
    assert any("deep_research_intake" in log for log in package.generation_logs)
    body_call = next(call for call in llm.calls if call.stage == "disclosure_body")
    assert "CN123456789A" in body_call.user_prompt
    assert "实时闭环反馈" in body_call.user_prompt
    assert "关键差异点" in body_call.user_prompt
    assert "技术补充待办" in body_call.user_prompt
    assert "\n# DeepResearch\n" not in body_call.user_prompt
    assert "## 现有技术" not in body_call.user_prompt
    assert "## 差异点" not in body_call.user_prompt
    assert "## 任务" not in body_call.user_prompt
    assert "generation_logs" not in body_call.user_prompt
    assert "provider_chain" not in body_call.user_prompt
    assert "internal_only" not in body_call.user_prompt
    assert warnings == []


def test_deepresearch_markdown_hits_are_included_in_missing_url_warnings() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD_WITH_MISSING_URL,
        status="processed",
    )
    generator = DisclosureGenerator(FakeLLMClient(_responses()), StaticPriorArtProvider())

    package, stages, warnings = generator.generate(
        project=project,
        materials=[material],
        context_chunks=[],
        max_prior_art_results=0,
    )

    assert any(hit.publication_number == "CN987654321A" and not hit.url for hit in package.prior_art_hits)
    assert warnings == ["prior_art missing public URL: CN987654321A 一种无公开链接的图像缺陷检测方法"]
    search_stage = next(stage for stage in stages if stage["phase"] == "prior_art_search")
    assert search_stage["payload"]["warnings"] == warnings


def test_deepresearch_markdown_hits_with_unsupported_urls_reach_warning_path() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD_WITH_UNSUPPORTED_URL,
        status="processed",
    )
    generator = DisclosureGenerator(FakeLLMClient(_responses()), StaticPriorArtProvider())

    package, stages, warnings = generator.generate(
        project=project,
        materials=[material],
        context_chunks=[],
        max_prior_art_results=0,
    )

    assert any(
        hit.publication_number == "CN123456789A" and hit.url == "https://example.com/patent/CN123456789A"
        for hit in package.prior_art_hits
    )
    assert warnings == ["prior_art unsupported public URL: CN123456789A 一种非公开视频链接的图像缺陷检测方法"]
    search_stage = next(stage for stage in stages if stage["phase"] == "prior_art_search")
    assert search_stage["payload"]["warnings"] == warnings


def test_deepresearch_material_becomes_prior_art_evidence_binding() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD,
        status="processed",
    )

    bindings = build_evidence_bindings(project, materials=[material], disclosures=[], patent_points=[])

    prior_art_bindings = [binding for binding in bindings if binding.source_type == EvidenceBindingSourceType.PRIOR_ART]
    assert prior_art_bindings
    assert prior_art_bindings[0].source_id == "CN123456789A"
    assert prior_art_bindings[0].metadata["url"] == "https://patents.google.com/patent/CN123456789A"


def test_deepresearch_iterator_materials_still_become_prior_art_evidence_binding() -> None:
    project = ProjectRecord(id="p1", name="图像缺陷", draft_text="一种图像缺陷识别方法。")
    material = ProjectMaterial(
        id="m1",
        project_id="p1",
        file_name="deepresearch.md",
        path="data/deepresearch.md",
        file_type="md",
        text=DEEP_RESEARCH_MD,
        status="processed",
    )

    bindings = build_evidence_bindings(
        project,
        materials=iter([material]),
        disclosures=[],
        patent_points=[],
    )

    prior_art_bindings = [binding for binding in bindings if binding.source_type == EvidenceBindingSourceType.PRIOR_ART]
    assert prior_art_bindings
    assert prior_art_bindings[0].source_id == "CN123456789A"
