from backend.app.draft_completion import run_draft_completion
from backend.app.draft_audit_rules import audit_draft_package
from backend.app.schemas import DraftPackage


def _package(description: str, mermaid: str = "flowchart TD\nA-->B") -> DraftPackage:
    return DraftPackage(
        title="一种方法",
        abstract="摘要",
        claims="1. 一种方法，其特征在于，根据 b^{cpu} 计算权重。",
        description=description,
        drawing_description="图1。",
        mermaid=mermaid,
        image_prompt="黑白线稿",
    )


def test_audit_flags_superscript_resource_dimension() -> None:
    issues = audit_draft_package(_package("公式为 $b^{cpu}=1$。"))

    assert any(issue.category == "format_pollution" and "维度上标" in issue.message for issue in issues)


def test_audit_flags_missing_prior_art_url_in_description() -> None:
    description = "现有技术 CN123456789A 公开了相关方案，但未给出公开 URL。"

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "prior_art_distinction_gap" and "公开 URL" in issue.message for issue in issues)


def test_audit_flags_internal_metadata_in_description() -> None:
    description = "本段包含 evidence_id: E001 和 generation_logs: project_scan。"

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "format_pollution" and "内部元信息" in issue.message for issue in issues)


def test_audit_flags_internal_metadata_in_title_and_abstract() -> None:
    package = _package("说明书正文干净。").model_copy(
        update={
            "title": "一种方法 evidence_id:E-01",
            "abstract": "摘要包含 generation_logs: internal",
        }
    )

    issues = audit_draft_package(package)

    assert any(issue.category == "format_pollution" and "内部元信息" in issue.message for issue in issues)


def test_audit_flags_publication_without_matching_url_when_multiple_publications_present() -> None:
    description = (
        "现有技术 CN123456789A 可见于 https://patents.google.com/patent/CN123456789A 。"
        "另一篇 CN999999999A 公开了相似方案，但此处只有 https://example.com/other 。"
    )

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "prior_art_distinction_gap" and "公开 URL" in issue.message for issue in issues)


def test_audit_scans_title_and_abstract_for_prior_art_url_gaps() -> None:
    package = _package("说明书正文没有现有技术公开号。").model_copy(
        update={
            "title": "针对 CN123456789A 的改进方法",
            "abstract": "摘要引用 US20240123456A1 但未给出公开链接。",
        }
    )

    issues = audit_draft_package(package)

    assert any(issue.category == "prior_art_distinction_gap" and "公开 URL" in issue.message for issue in issues)


def test_audit_accepts_prior_art_url_when_publication_number_is_in_url() -> None:
    package = _package("说明书正文没有现有技术公开号。").model_copy(
        update={
            "abstract": "现有技术 CN123456789A 公开于 https://patents.google.com/patent/CN123456789A 。",
        }
    )

    issues = audit_draft_package(package)

    assert not any(issue.category == "prior_art_distinction_gap" for issue in issues)


def test_audit_rejects_wrong_nearby_patent_link_for_publication() -> None:
    description = (
        "现有技术 CN123456789A 和 US20240123456A1 均涉及任务调度，"
        "其中 US20240123456A1 参见 https://patents.google.com/patent/US20240123456A1 。"
    )

    issues = audit_draft_package(_package(description))

    assert any(issue.category == "prior_art_distinction_gap" and "公开 URL" in issue.message for issue in issues)


def test_audit_flags_missing_mermaid_when_prompt_mentions_diagram() -> None:
    package = _package("说明书引用系统框图。", mermaid="")

    issues = audit_draft_package(package)

    assert any(issue.target == "drawing" and "Mermaid" in issue.message for issue in issues)


def test_draft_completion_includes_audit_rule_issues() -> None:
    package = _package("说明书包含 evidence_id: E001。")

    run = run_draft_completion(
        project_id="p1",
        package=package,
        filing_reports=[],
        worksheets=[],
        patent_points=[],
        disclosures=[],
        materials=[],
        evidence_bindings=[],
    )

    assert any(issue.source_refs == ["draft_audit_rules"] for issue in run.issues)
