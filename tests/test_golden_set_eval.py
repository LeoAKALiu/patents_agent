from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.golden_eval import GoldenSetEvaluator, _construct_invention_brief, _gate_check, _sas, _ccs
from backend.app.generator import PatentDraftGenerator
from backend.app.llm import FakeLLMClient
from backend.app.schemas import (
    AbstractOutput,
    ClaimItem,
    ClaimsOutput,
    DescriptionOutput,
    DraftPackage,
    DrawingsOutput,
    EvalPatentResult,
    FigureItem,
    GoldenEvalReport,
    InventionBrief,
)


def _sample_golden_entry() -> dict:
    return {
        "id": "CN-test-001",
        "title": "一种测试方法",
        "technical_field": "ai_software",
        "input": {
            "description_full": (
                "技术领域\n本发明涉及测试领域。\n"
                "背景技术\n现有技术效率低。\n"
                "发明内容\n本发明提供一种测试方法，包括采集数据和输出结果。\n"
                "具体实施方式\n采集数据后进行预处理，然后输出结果。"
            ),
            "drawings_description": "图1为方法流程图。",
        },
        "ground_truth": {
            "claims": [
                {
                    "number": 1,
                    "kind": "independent",
                    "category": "method",
                    "depends_on": None,
                    "preamble": "一种测试方法，其特征在于，包括：",
                    "features": ["采集数据", "输出结果"],
                }
            ],
            "description_sections": {
                "technical_field": "本发明涉及测试领域。",
                "background": "现有技术效率低。",
                "summary": "本发明提供一种测试方法。",
                "embodiments": "采集数据后进行预处理。",
            },
            "figures": [{"figure_no": "图1", "title": "方法流程图"}],
        },
    }


def _make_package(claims_features=None):
    """Build a valid DraftPackage with structured fields."""
    if claims_features is None:
        claims_features = [["采集数据", "输出结果"]]
    return DraftPackage(
        title="一种测试方法",
        abstract="本发明公开了一种测试方法。",
        claims="1. 一种测试方法，其特征在于，采集数据和输出结果。",
        description="技术领域\n本发明涉及测试领域。\n背景技术\n现有技术效率低。\n发明内容\n本发明提供一种测试方法。\n附图说明\n图1为方法流程图。\n具体实施方式\n采集数据并输出结果。",
        drawing_description="图1为方法流程图。",
        mermaid="",
        image_prompt="",
        claims_struct=ClaimsOutput(
            claims=[
                ClaimItem(
                    number=1,
                    kind="independent",
                    category="method",
                    preamble="一种测试方法，其特征在于，包括：",
                    features=claims_features[0],
                )
            ]
        ),
        description_struct=DescriptionOutput(
            technical_field="本发明涉及测试技术领域，具体涉及自动化专利生成方法。",
            background="现有技术效率低且存在诸多问题与挑战难题。",
            summary="本发明提供一种测试方法，包括采集数据和输出结果两个步骤。",
            embodiments="采集数据并输出结果作为最终的测试步骤完成。",
        ),
        drawings_struct=DrawingsOutput(figures=[FigureItem(figure_no="图1", title="方法流程图")]),
        abstract_struct=AbstractOutput(abstract="本发明公开了一种测试方法。"),
    )


# --- Gate check tests ---


def test_gate_pass_with_valid_package():
    package = _make_package()
    passed, warnings = _gate_check(package)
    assert passed is True
    assert len(warnings) == 0


def test_gate_fail_when_no_independent_claim():
    package = _make_package()
    package.claims_struct.claims[0].kind = "dependent"
    passed, warnings = _gate_check(package)
    assert passed is False
    assert any("independent" in w for w in warnings)


def test_gate_warn_when_independent_claim_has_fewer_than_two_features():
    package = _make_package(claims_features=[["仅一个步骤"]])
    passed, warnings = _gate_check(package)
    assert passed is True
    assert any("features" in w for w in warnings)


def test_gate_warn_when_description_section_too_short():
    package = _make_package()
    package.description_struct.background = "短。"
    passed, warnings = _gate_check(package)
    assert passed is True
    assert any("背景技术" in w for w in warnings)


# --- SAS tests ---


def test_sas_perfect_match():
    package = _make_package()
    gold = _sample_golden_entry()
    score, detail = _sas(package, gold)
    assert score >= 0.8
    assert "claims_count_align" in detail


def test_sas_low_when_claims_count_mismatch():
    package = _make_package()
    gold = _sample_golden_entry()
    gold["ground_truth"]["claims"] = [
        {"number": i, "kind": "independent" if i == 1 else "dependent", "category": "method",
         "depends_on": 1 if i > 1 else None, "preamble": "...", "features": [f"步骤{i}"]}
        for i in range(1, 11)
    ]
    gold["claims_count"] = 10
    score, detail = _sas(package, gold)
    assert score < 0.6
    assert detail["claims_count_align"] < 0.3


def test_sas_category_coverage_partial():
    package = _make_package()
    gold = _sample_golden_entry()
    gold["ground_truth"]["claims"].append({
        "number": 2, "kind": "independent", "category": "system", "depends_on": None,
        "preamble": "一种测试系统", "features": ["模块A"]
    })
    gold["claims_count"] = 2
    score, detail = _sas(package, gold)
    assert detail["category_coverage"] < 1.0


# --- CCS tests ---


def test_ccs_full_coverage():
    package = _make_package()
    gold = _sample_golden_entry()
    score, detail = _ccs(package, gold)
    assert score > 0.5


def test_ccs_low_when_key_nouns_missing():
    package = _make_package(claims_features=[["无关步骤"]])
    # Also make description unrelated to gold to reduce overlap
    package.description = "技术领域\n本发明涉及全新领域。\n背景技术\n某领域存在空白。\n发明内容\n本发明提供一种全新方法。\n附图说明\n图1为流程图。\n具体实施方式\n使用无关步骤完成工作。"
    package.description_struct.technical_field = "本发明涉及全新领域。"
    package.description_struct.background = "某领域存在空白。"
    package.description_struct.summary = "本发明提供一种全新方法。"
    package.description_struct.embodiments = "使用无关步骤完成工作。"
    gold = _sample_golden_entry()
    score, detail = _ccs(package, gold)
    assert score < 0.5


def test_ccs_topic_term_recall():
    package = _make_package()
    gold = _sample_golden_entry()
    _, detail = _ccs(package, gold)
    assert "topic_term_recall" in detail
    assert 0.0 <= detail["topic_term_recall"] <= 1.0


# --- InventionBrief construction tests ---


def test_construct_invention_brief_from_golden_entry():
    entry = _sample_golden_entry()
    brief = _construct_invention_brief(entry)
    assert isinstance(brief, InventionBrief)
    assert brief.title == "一种测试方法"
    assert brief.technical_field == "人工智能软件方法"
    assert len(brief.technical_problem) > 0
    assert len(brief.technical_solution) > 0


# --- GoldenSetEvaluator integration tests ---


def test_evaluator_loads_golden_set(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries, errors = evaluator.load_golden_set()
    assert len(entries) == 1
    assert errors == []
    assert entries[0]["id"] == "CN-test-001"


def test_evaluator_run_one_produces_eval_result(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries, errors = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域，具体涉及一种用于自动化测试的专利生成方法。",
            "background": "现有技术效率低，且存在一致性差和人工成本高的问题。",
            "summary": "本发明提供一种测试方法，包括采集数据和输出结果的完整流程。",
            "embodiments": "采集数据后经过预处理，然后由处理器输出最终结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    result = evaluator.run_one(entries[0], generator)
    assert isinstance(result, EvalPatentResult)
    assert result.gate_pass is True
    assert result.sas > 0.5
    assert result.ccs > 0.3


def test_evaluator_run_full(tmp_path):
    entries_list = [_sample_golden_entry()]
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": e["id"], "title": e["title"], "technical_field": e["technical_field"], "claims_count": len(e["ground_truth"]["claims"])} for e in entries_list],
    }))
    for e in entries_list:
        (tmp_path / f"{e['id']}.json").write_text(json.dumps(e))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域，具体涉及一种用于自动化测试的专利生成方法。",
            "background": "现有技术效率低，且存在一致性差和人工成本高的问题。",
            "summary": "本发明提供一种测试方法，包括采集数据和输出结果的完整流程。",
            "embodiments": "采集数据后经过预处理，然后由处理器输出最终结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    assert isinstance(report, GoldenEvalReport)
    assert len(report.per_patent) == 1
    assert report.summary.pass_ is True
    assert report.summary.warnings == 0
    assert report.golden_set_version == "v1"


def test_evaluator_handles_missing_golden_file(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-missing", "title": "缺失", "technical_field": "ai_software", "claims_count": 1}],
    }))
    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    entries, errors = evaluator.load_golden_set()
    assert len(entries) == 0
    assert len(errors) == 1
    assert "missing" in errors[0]


def test_evaluator_run_one_failure_does_not_stop_full_run(tmp_path):
    good = _sample_golden_entry()
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [
            {"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1},
            {"id": "CN-test-002", "title": "另一种测试", "technical_field": "ai_software", "claims_count": 1},
        ],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(good))
    (tmp_path / "CN-test-002.json").write_text(json.dumps(good))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path)
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域，具体涉及一种用于自动化测试的专利生成方法。",
            "background": "现有技术效率低，且存在一致性差和人工成本高的问题。",
            "summary": "本发明提供一种测试方法，包括采集数据和输出结果的完整流程。",
            "embodiments": "采集数据后经过预处理，然后由处理器输出最终结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    assert len(report.per_patent) == 2


# --- LLM-Judge tests (marked llm_judge) ---


@pytest.mark.llm_judge
def test_llm_judge_produces_score_dict(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    judge_llm = FakeLLMClient({
        "clarity": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "清晰", "reason_b": "边界模糊"}),
        "support": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "有支撑", "reason_b": "支撑不足"}),
        "effect": json.dumps({"score_a": 4, "score_b": 3, "reason_a": "效果明确", "reason_b": "效果笼统"}),
        "cleanliness": json.dumps({"score_a": 5, "score_b": 5, "reason_a": "无污染", "reason_b": "无污染"}),
    })

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path, judge_llm=judge_llm)
    entries, _ = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({
            "claims": [
                {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
                 "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
            ]
        }),
        "description": json.dumps({
            "technical_field": "本发明涉及测试领域，具体涉及一种用于自动化测试的专利生成方法。",
            "background": "现有技术效率低，且存在一致性差和人工成本高的问题。",
            "summary": "本发明提供一种测试方法，包括采集数据和输出结果的完整流程。",
            "embodiments": "采集数据后经过预处理，然后由处理器输出最终结果。",
        }),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    result = report.per_patent[0]
    assert result.llm_judge is not None
    assert "clarity" in result.llm_judge
    assert isinstance(result.llm_judge["clarity"], float)
    assert result.llm_judge["clarity"] >= 1.0
    assert result.llm_judge["cleanliness"] == 5.0
    assert report.summary.llm_judge_avg is not None


@pytest.mark.llm_judge
def test_llm_judge_skipped_when_judge_llm_is_none(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "v1", "created": "2026-06-08",
        "entries": [{"id": "CN-test-001", "title": "一种测试方法", "technical_field": "ai_software", "claims_count": 1}],
    }))
    (tmp_path / "CN-test-001.json").write_text(json.dumps(_sample_golden_entry()))

    evaluator = GoldenSetEvaluator(golden_set_dir=tmp_path, judge_llm=None)
    entries, _ = evaluator.load_golden_set()
    llm = FakeLLMClient({
        "claims": json.dumps({"claims": [
            {"number": 1, "kind": "independent", "category": "method", "depends_on": None,
             "preamble": "一种测试方法，其特征在于，包括：", "features": ["采集数据", "输出结果"]}
        ]}),
        "description": json.dumps({"technical_field": "本发明涉及测试领域。", "background": "现有技术效率低。", "summary": "本发明提供一种测试方法。", "embodiments": "采集数据并输出结果。"}),
        "abstract": json.dumps({"abstract": "本发明公开了一种测试方法。"}),
        "drawings": json.dumps({"figures": [{"figure_no": "图1", "title": "方法流程图"}]}),
        "diagram": "flowchart TD\nA-->B",
        "image_prompt": "黑白线稿。",
    })
    generator = PatentDraftGenerator(llm)

    report = evaluator.run(generator)
    result = report.per_patent[0]
    assert result.llm_judge is None
    assert report.summary.llm_judge_avg is None
