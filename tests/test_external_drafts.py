import pytest
from pydantic import ValidationError

from backend.app.schemas import (
    DraftPackage,
    ExternalDraftIntakeRun,
    ExternalDraftReviewBundle,
    ExternalDraftSource,
    ExternalDraftSourceCreate,
    IntakeIssue,
    SectionConfidence,
    SectionConfidenceItem,
)


def test_external_draft_models_capture_source_intake_and_confidence():
    source = ExternalDraftSource(
        id="src-1",
        project_id="project-1",
        source_type="pasted_text",
        file_name="pasted.txt",
        content_hash="hash-raw",
        raw_text="权利要求书\n1. 一种方法。\n说明书\n本发明涉及数据处理。",
        raw_path="",
        metadata={"input": "paste"},
    )
    confidence = SectionConfidence(
        title=SectionConfidenceItem(score=0.4, source_markers=[], warnings=["未识别发明名称"]),
        abstract=SectionConfidenceItem(score=0.0, source_markers=[], warnings=["未识别摘要"]),
        claims=SectionConfidenceItem(score=0.95, source_markers=["权利要求书"], warnings=[]),
        description=SectionConfidenceItem(score=0.9, source_markers=["说明书"], warnings=[]),
        drawing_description=SectionConfidenceItem(score=0.0, source_markers=[], warnings=["未识别附图说明"]),
    )
    issue = IntakeIssue(
        id="intake-1",
        category="missing_section",
        severity="medium",
        section="abstract",
        message="未识别摘要章节。",
        suggested_action="在章节确认界面补充摘要。",
        blocks_quality_run=False,
    )
    run = ExternalDraftIntakeRun(
        id="run-1",
        project_id="project-1",
        source_id=source.id,
        status="needs_review",
        parser_version="external-draft-parser-v1",
        source_hash=source.content_hash,
        parsed_package=DraftPackage(
            title="未命名发明",
            abstract="",
            claims="1. 一种方法。",
            description="本发明涉及数据处理。",
            drawing_description="",
            mermaid="",
            image_prompt="",
            review_findings=[],
            citations=[],
            generation_logs=[],
        ),
        section_confidence=confidence,
        intake_issues=[issue],
        unassigned_fragments=[],
        working_draft_hash="hash-working",
    )

    create = ExternalDraftSourceCreate(source_type="pasted_text", text=source.raw_text, file_name="pasted.txt")

    assert create.source_type == "pasted_text"
    assert source.content_hash == "hash-raw"
    assert run.status == "needs_review"
    assert run.section_confidence.claims.score == 0.95
    assert run.intake_issues[0].category == "missing_section"


@pytest.mark.parametrize(
    "payload",
    [
        {"source_type": "pasted_text", "text": ""},
        {"source_type": "pasted_text", "text": "   "},
        {"source_type": "markdown_file", "text": "", "file_content": ""},
        {"source_type": "markdown_file", "text": "  ", "file_content": "\n\t"},
        {"source_type": "docx_file", "text": "", "file_content": ""},
        {"source_type": "docx_file", "text": "  ", "file_content": "\n\t"},
    ],
)
def test_external_draft_source_create_rejects_empty_content_for_source_type(payload):
    with pytest.raises(ValidationError):
        ExternalDraftSourceCreate(**payload)


def test_external_draft_review_bundle_scores_are_bounded_when_present():
    assert ExternalDraftReviewBundle(project_id="project-1", initial_score=0, latest_score=100).latest_score == 100

    with pytest.raises(ValidationError):
        ExternalDraftReviewBundle(project_id="project-1", initial_score=-1)

    with pytest.raises(ValidationError):
        ExternalDraftReviewBundle(project_id="project-1", latest_score=999)
