from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSER_BACKEND = ROOT / "qa_runs" / "patent_flow_long_qa_20260630" / "browser_evidence_backend.py"


def _load_browser_backend():
    spec = importlib.util.spec_from_file_location("browser_evidence_backend_under_test", BROWSER_BACKEND)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_browser_evidence_fake_llm_supports_first_mile_project_flow() -> None:
    module = _load_browser_backend()
    llm = module._fake_llm()

    disclosure_scan = json.loads(llm.complete_stage("disclosure_scan", "", ""))
    patent_points = json.loads(llm.complete_stage("patent_points", "", ""))
    prior_art_terms = json.loads(llm.complete_stage("prior_art_terms", "", ""))
    prior_art_relevance = json.loads(llm.complete_stage("prior_art_relevance", "", ""))
    disclosure_body = llm.complete_stage("disclosure_body", "", "")
    disclosure_mermaid = llm.complete_stage("disclosure_mermaid", "", "")
    disclosure_image_prompt = llm.complete_stage("disclosure_image_prompt", "", "")
    disclosure_self_check = json.loads(llm.complete_stage("disclosure_self_check", "", ""))
    core_formula = json.loads(llm.complete_stage("core_formula", "", ""))
    claims = llm.complete_stage("claims", "", "")
    post_draft_chair = json.loads(llm.complete_stage("post_draft_chair_synthesis", "", ""))

    assert disclosure_scan["summary"]
    assert "无人机" in disclosure_scan["materials_summary"]
    assert disclosure_scan["technical_keywords"]
    assert patent_points["selected_candidate_id"]
    assert patent_points["candidates"][0]["title"]
    assert prior_art_terms
    assert "区别" in prior_art_relevance["prior_art_differences"]
    assert "技术方案" in disclosure_body
    assert "flowchart" in disclosure_mermaid
    assert disclosure_image_prompt
    assert disclosure_self_check == []
    assert core_formula["formula_blocks"]
    assert core_formula["variable_definitions"]
    assert "1. 一种" in claims
    assert "内部备注" not in claims
    assert post_draft_chair["status"] == "passed"
    assert post_draft_chair["export_allowed"] is True


def test_browser_evidence_fake_agent_runtime_supports_deliberation_flow() -> None:
    module = _load_browser_backend()
    runtime = module._fake_agent_runtime()

    expected_labels = {
        "opening codex",
        "opening deepseek",
        "opening kimicode",
        "pair codex-vs-deepseek",
        "pair codex-vs-kimicode",
        "pair deepseek-vs-kimicode",
        "chair synthesis",
    }

    assert expected_labels.issubset(runtime.task_payloads)
    assert runtime.task_payloads["chair synthesis"]["claim_strategy"]
    assert "会审通过" in runtime.task_payloads["chair synthesis"]["agent_consensus"]
