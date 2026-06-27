from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_scenario_pipeline_does_not_assume_bug_ledger_already_exists() -> None:
    text = (ROOT / "docs/qa/ai-scenario-testing-pipeline.md").read_text(encoding="utf-8")

    bugs = "BUGS" + ".md"
    forbidden_phrases = [
        f"-> {bugs} ->",
        "按 " + bugs + " 模板记录",
        "## 4. " + bugs + " 台账",
        "请读取 " + bugs,
        "更新 " + bugs + " 状态",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in text

    assert "首次使用" in text
    assert "缺陷台账" in text
    assert "如果 `BUGS.md` 尚不存在" in text
