from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SectionType(str, Enum):
    ABSTRACT = "abstract"
    CLAIMS = "claims"
    DESCRIPTION = "description"
    TECHNICAL_FIELD = "technical_field"
    BACKGROUND = "background"
    SUMMARY = "summary"
    DRAWINGS = "drawings"
    EMBODIMENTS = "embodiments"
    OTHER = "other"


class PatentSection(BaseModel):
    type: SectionType
    heading: str
    text: str
    ordinal: int


class PatentClaim(BaseModel):
    number: int
    text: str
    kind: str = Field(pattern="^(independent|dependent)$")
    references: list[int] = Field(default_factory=list)
    category: str = Field(default="other", pattern="^(method|system|device|medium|other)$")


class PatentDocument(BaseModel):
    id: str
    title: str
    source_name: str
    text: str
    sections: list[PatentSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatentChunk(BaseModel):
    id: str
    document_id: str
    section_type: SectionType
    text: str
    ordinal: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    chunk: PatentChunk
    score: float


class PatentType(str, Enum):
    INVENTION = "invention"
    UTILITY_MODEL = "utility_model"


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    section_type: SectionType
    text: str


class EvidenceBindingSourceType(str, Enum):
    PROJECT_MATERIAL = "project_material"
    PRIOR_ART = "prior_art"
    DISCLOSURE = "disclosure"
    PATENT_POINT = "patent_point"
    FORMULA = "formula"
    DRAFT_CITATION = "draft_citation"
    MANUAL = "manual"


class EvidenceVerificationStatus(str, Enum):
    VERIFIED = "verified"
    RETRIEVED = "retrieved"
    USER_PROVIDED = "user_provided"
    FEASIBLE_UNVERIFIED = "feasible_unverified"
    NEEDS_EXPERIMENT = "needs_experiment"
    MODEL_GENERATED = "model_generated"


class EvidenceBinding(BaseModel):
    evidence_id: str = ""
    source_type: EvidenceBindingSourceType = EvidenceBindingSourceType.MANUAL
    source_id: str = ""
    source_label: str = ""
    quote: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.MODEL_GENERATED
    internal_only: bool = True
    citable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class InventionBrief(BaseModel):
    title: str
    technical_field: str
    technical_problem: str
    technical_solution: str
    beneficial_effects: list[str] = Field(default_factory=list)
    key_steps: list[str] = Field(default_factory=list)
    raw_draft: str | None = None
    disclosure_summary: str | None = None
    patent_point_summary: str | None = None
    prior_art_differences: str | None = None
    supporting_materials_summary: str | None = None
    patent_type: PatentType = PatentType.INVENTION


class ReviewFinding(BaseModel):
    category: str
    severity: str = Field(pattern="^(low|medium|high)$")
    message: str
    suggestion: str
    evidence: str | None = None


class DiagramSpec(BaseModel):
    mermaid: str
    image_prompt: str
    drawing_description: str


class AgentProviderStatus(BaseModel):
    id: str
    label: str
    command: str
    available: bool  # strict gate: installed AND auth_status=="ready" — required for deliberation
    path: str = ""
    required: bool = False
    model_version: str = ""
    roles: list[str] = Field(default_factory=list)
    installed: bool = False
    auth_status: str = Field(default="unknown", pattern="^(ready|not_authenticated|unavailable|timeout|unknown)$")
    diagnostic: str = ""
    repair_suggestion: str = ""
    selectable: bool = False  # user toggle: installed AND auth_status in (ready, unknown)


class AgentDoctorReport(BaseModel):
    status: str = Field(pattern="^(ready|degraded|blocked)$")
    run_mode: str = Field(pattern="^(full|partial|minimal|blocked)$")
    commands: dict[str, AgentProviderStatus]
    active_provider_ids: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)
    unknown_required: list[str] = Field(default_factory=list)


class AgentFailure(BaseModel):
    provider_id: str
    phase: str
    reason: str
    message: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class RuntimeStageState(BaseModel):
    """Heartbeat metadata exposed while a long-running pipeline is active."""

    current_stage: str = ""
    provider: str = ""
    query: str = ""
    subtask: str = ""
    heartbeat_at: str = Field(default_factory=_utc_now_iso)
    elapsed_ms: int = 0
    warning_count: int = 0
    partial_artifact_count: int = 0
    timeout_ms: int | None = None
    attempt: int | None = None


class RuntimeFailure(BaseModel):
    """Structured failure/cancel/timeout details for retryable runs."""

    flow: str = ""
    stage: str = ""
    provider: str = ""
    reason: str
    message: str
    retryable: bool = True
    elapsed_ms: int = 0
    repair_suggestion: str = ""
    partial_artifact_count: int = 0
    created_at: str = Field(default_factory=_utc_now_iso)


class DeliberationLogEntry(BaseModel):
    level: str = Field(pattern="^(info|warn|error)$")
    phase: str = ""
    provider_id: str = ""
    attempt: int | None = None
    message: str
    detail: str = ""
    repair_suggestion: str = ""
    elapsed_ms: int | None = None
    created_at: str = Field(default_factory=_utc_now_iso)


class DeliberationStageResult(BaseModel):
    phase: str
    provider_id: str
    label: str
    payload: dict[str, Any]
    status: str = Field(pattern="^(completed|failed|degraded)$")
    failure: AgentFailure | None = None


class PatentStrategyBrief(BaseModel):
    summary: str
    claim_strategy: list[str] = Field(default_factory=list)
    description_strategy: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=list)
    agent_consensus: str = ""
    disclosure_summary: str | None = None
    patent_point_summary: str | None = None
    prior_art_differences: str | None = None


class DeliberationRunCreate(BaseModel):
    providers: list[str] | None = None
    participant_providers: list[str] | None = None
    round_depth: str = "converged_two_round"
    trace: bool = False
    task_timeout_ms: int | None = None
    run_timeout_ms: int | None = None


class FormulaRunCreate(BaseModel):
    providers: list[str] | None = None
    stage_timeout_ms: int | None = None
    run_timeout_ms: int | None = None


class DeliberationRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    providers: list[str] = Field(default_factory=list)
    participant_providers: list[str] = Field(default_factory=list)
    run_mode: str = Field(pattern="^(full|partial|minimal|blocked)$")
    round_depth: str = "converged_two_round"
    trace: bool = False
    run_dir: str = ""
    stage_results: list[DeliberationStageResult] = Field(default_factory=list)
    strategy_brief: PatentStrategyBrief | None = None
    failures: list[AgentFailure] = Field(default_factory=list)
    failure_details: list[RuntimeFailure] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    runtime_state: RuntimeStageState | None = None
    cancel_requested: bool = False
    retry_of: str | None = None


class DraftPackage(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str
    mermaid: str
    image_prompt: str
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    generation_logs: list[str] = Field(default_factory=list)
    deliberation_run_id: str | None = None
    strategy_brief: PatentStrategyBrief | None = None
    agent_consensus: str | None = None
    disclosure_run_id: str | None = None
    disclosure_summary: str | None = None
    patent_point_summary: str | None = None
    formula_run_id: str | None = None
    core_formula_summary: str | None = None


class RevisionLedgerRecord(BaseModel):
    id: str
    project_id: str
    revision_kind: str = Field(
        pattern="^(material_merge|correction|protection_focus|post_draft_repair|official_cleanup|completion_patch)$"
    )
    baseline_artifact_hash: str
    new_artifact_hash: str
    user_intent_summary: str = ""
    affected_sections: list[str] = Field(default_factory=list)
    prior_art_changed: bool = False
    protection_scope_changed: bool = False
    artifact_refs: list[str] = Field(default_factory=list)
    created_at: str = ""


class OfficialFigurePlanItem(BaseModel):
    figure_no: str
    title: str
    description: str
    referenced_sections: list[str] = Field(default_factory=list)


class OfficialDraftPackage(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str
    figure_plan: list[OfficialFigurePlanItem] = Field(default_factory=list)
    compile_warnings: list[str] = Field(default_factory=list)
    source_draft_hash: str = ""
    official_package_hash: str = ""


class OfficialCompileRunCreate(BaseModel):
    pass


class OfficialCompileRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|blocked|failed)$")
    source_draft_hash: str = ""
    official_package_hash: str = ""
    official_package: OfficialDraftPackage | None = None
    contamination_removed: list[dict[str, str]] = Field(default_factory=list)
    blocked_items: list[dict[str, str]] = Field(default_factory=list)
    sidecar_notes: list[dict[str, str]] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class OfficialCompileCleanupResult(BaseModel):
    project_id: str
    compile_run_id: str
    applied_count: int = 0
    applied_actions: list[str] = Field(default_factory=list)
    previous_draft_hash: str = ""
    current_draft_hash: str = ""
    package: DraftPackage


class ProjectCreate(BaseModel):
    name: str
    draft_text: str = ""
    patent_type: PatentType = PatentType.INVENTION
    applicant: str = ""
    inventors: str = ""
    technical_field: str = ""
    background: str = ""
    pain_point: str = ""
    technical_solution: str = ""
    innovation: str = ""
    embodiments: str = ""
    beneficial_effects: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    draft_text: str | None = None
    patent_type: PatentType | None = None
    applicant: str | None = None
    inventors: str | None = None
    technical_field: str | None = None
    background: str | None = None
    pain_point: str | None = None
    technical_solution: str | None = None
    innovation: str | None = None
    embodiments: str | None = None
    beneficial_effects: str | None = None


class DraftPackageManualUpdate(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str


class ProjectRecord(BaseModel):
    id: str
    name: str
    draft_text: str = ""
    patent_type: PatentType = PatentType.INVENTION
    package: DraftPackage | None = None
    created_at: str = ""
    updated_at: str = ""
    applicant: str = ""
    inventors: str = ""
    technical_field: str = ""
    background: str = ""
    pain_point: str = ""
    technical_solution: str = ""
    innovation: str = ""
    embodiments: str = ""
    beneficial_effects: str = ""


class FilingReadinessIssue(BaseModel):
    category: str = Field(
        pattern="^(format_pollution|internal_trace|unfavorable_statement|unverified_effect|subject_matter_risk|support_gap)$"
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    target: str = Field(pattern="^(claims|description|abstract|drawings|export)$")
    matched_text: str
    message: str
    suggestion: str
    can_auto_clean: bool = False


class FilingReadinessReport(BaseModel):
    id: str
    project_id: str
    draft_package_hash: str = ""
    status: str = Field(pattern="^(clean|warning|high_risk)$")
    rules_version: str = "filing-readiness-v1"
    issues: list[FilingReadinessIssue] = Field(default_factory=list)
    created_at: str = ""


class FeatureRecord(BaseModel):
    feature_id: str
    text: str
    classification: str = Field(
        pattern="^(known_base|differentiator|core_combo|dependent_fallback|support_needed)$"
    )
    claim_refs: list[str] = Field(default_factory=list)
    description_refs: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)
    prior_art_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    support_explanation: str = ""
    risk_tags: list[str] = Field(default_factory=list)


class ClaimDefenseWorksheet(BaseModel):
    id: str
    project_id: str
    draft_package_hash: str = ""
    status: str = Field(default="draft", pattern="^(draft|reviewed|superseded)$")
    source: str = Field(default="draft", pattern="^(draft|disclosure|generated_package|manual)$")
    feature_records: list[FeatureRecord] = Field(default_factory=list)
    defense_recommendations: list[str] = Field(default_factory=list)
    support_gaps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""


class CompletionIssue(BaseModel):
    id: str
    category: str = Field(
        pattern=(
            "^(claim_support_gap|specification_sufficiency_gap|figure_consistency_gap|"
            "term_definition_gap|prior_art_distinction_gap|unverified_scheme_gap|"
            "unfavorable_statement|format_pollution|subject_matter_risk|claim_scope_risk)$"
        )
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    target: str = Field(pattern="^(claim|description|drawing|embodiment|term|evidence|prior_art|export)$")
    source_refs: list[str] = Field(default_factory=list)
    message: str
    why_it_matters: str
    suggested_action: str
    blocks_submission: bool = False


class CompletionTask(BaseModel):
    id: str
    issue_id: str
    task_type: str
    priority: int = 0
    input_refs: list[str] = Field(default_factory=list)
    expected_output: str
    draft_section_target: str
    status: str = Field(default="open", pattern="^(open|proposed|accepted|rejected|superseded)$")


class ProposedPatch(BaseModel):
    id: str
    task_id: str
    target_section: str
    patch_kind: str = Field(pattern="^(insert|replace|delete|rewrite|sidecar_only)$")
    before_text: str = ""
    after_text: str = ""
    rationale: str
    risk_delta: str
    evidence_refs: list[str] = Field(default_factory=list)
    can_enter_official_draft: bool = False
    status: str = Field(default="proposed", pattern="^(proposed|accepted|rejected|superseded)$")


class CompletionScoreCard(BaseModel):
    authorization_stability: int = Field(ge=0, le=100)
    protection_scope: int = Field(ge=0, le=100)
    support_strength: int = Field(ge=0, le=100)
    prior_art_distinction: int = Field(ge=0, le=100)
    filing_maturity: int = Field(ge=0, le=100)
    official_hygiene: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


class ClaimSupportMatrixRow(BaseModel):
    claim_ref: str
    feature_text: str
    feature_classification: str = Field(
        pattern="^(known_base|differentiator|core_combo|dependent_fallback|support_needed)$"
    )
    description_refs: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)
    embodiment_refs: list[str] = Field(default_factory=list)
    formula_refs: list[str] = Field(default_factory=list)
    data_structure_refs: list[str] = Field(default_factory=list)
    pseudo_code_refs: list[str] = Field(default_factory=list)
    prior_art_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    support_explanation: str = ""
    missing_evidence_reason: str = ""
    evidence_status: str = Field(
        default="model_generated",
        pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$",
    )
    risk_tags: list[str] = Field(default_factory=list)
    completion_status: str = Field(pattern="^(supported|partial|missing)$")


class DraftCompletionRun(BaseModel):
    id: str
    project_id: str
    snapshot_hash: str = ""
    draft_package_hash: str = ""
    status: str = Field(default="completed", pattern="^(completed|failed)$")
    issues: list[CompletionIssue] = Field(default_factory=list)
    tasks: list[CompletionTask] = Field(default_factory=list)
    patches: list[ProposedPatch] = Field(default_factory=list)
    support_matrix: list[ClaimSupportMatrixRow] = Field(default_factory=list)
    scorecard: CompletionScoreCard
    scorecard_baseline: CompletionScoreCard | None = None
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""


class ExternalDraftSourceCreate(BaseModel):
    source_type: str = Field(pattern="^(pasted_text|markdown_file|docx_file)$")
    text: str = ""
    file_name: str = ""
    file_content: str = ""

    @model_validator(mode="after")
    def validate_source_content(self) -> ExternalDraftSourceCreate:
        text = self.text.strip()
        file_content = self.file_content.strip()
        if self.source_type == "pasted_text" and not text:
            raise ValueError("pasted_text requires non-empty text")
        if self.source_type in {"markdown_file", "docx_file"} and not (text or file_content):
            raise ValueError(f"{self.source_type} requires non-empty text or file_content")
        return self


class ExternalDraftSource(BaseModel):
    id: str
    project_id: str
    source_type: str = Field(pattern="^(pasted_text|markdown_file|docx_file)$")
    file_name: str = ""
    content_hash: str
    raw_text: str
    raw_path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class SectionConfidenceItem(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    source_markers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SectionConfidence(BaseModel):
    title: SectionConfidenceItem
    abstract: SectionConfidenceItem
    claims: SectionConfidenceItem
    description: SectionConfidenceItem
    drawing_description: SectionConfidenceItem


class IntakeIssue(BaseModel):
    id: str
    category: str = Field(
        pattern=(
            "^(missing_section|duplicate_section|low_confidence_section|format_noise|"
            "unsupported_attachment|suspected_internal_text|malformed_claim_numbering)$"
        )
    )
    severity: str = Field(pattern="^(low|medium|high)$")
    section: str = Field(pattern="^(title|abstract|claims|description|drawing_description|raw_text)$")
    message: str
    suggested_action: str
    blocks_quality_run: bool = False


class ExternalDraftIntakeRun(BaseModel):
    id: str
    project_id: str
    source_id: str
    status: str = Field(pattern="^(completed|needs_review|failed)$")
    parser_version: str = "external-draft-parser-v1"
    source_hash: str = ""
    parsed_package: DraftPackage | None = None
    section_confidence: SectionConfidence | None = None
    intake_issues: list[IntakeIssue] = Field(default_factory=list)
    unassigned_fragments: list[str] = Field(default_factory=list)
    working_draft_hash: str = ""
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""


class ExternalDraftIntakeConfirmRequest(BaseModel):
    title: str
    abstract: str
    claims: str
    description: str
    drawing_description: str


class ExternalDraftReviewBundle(BaseModel):
    project_id: str
    source_id: str = ""
    intake_run_id: str = ""
    initial_score: int | None = Field(default=None, ge=0, le=100)
    latest_score: int | None = Field(default=None, ge=0, le=100)
    accepted_patch_ids: list[str] = Field(default_factory=list)
    completion_run_ids: list[str] = Field(default_factory=list)
    official_compile_run_id: str = ""
    post_draft_review_run_id: str = ""
    export_allowed: bool = False
    report_hash: str = ""


class ScoreImprovementRequest(BaseModel):
    max_rounds: int = Field(default=1, ge=1, le=3)
    target_score: int = Field(default=85, ge=0, le=100)


class ScoreImprovementResult(BaseModel):
    project_id: str
    before_score: int
    after_score: int
    accepted_patch_ids: list[str] = Field(default_factory=list)
    before_run: DraftCompletionRun
    after_run: DraftCompletionRun
    logs: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    deliberation_run_id: str | None = None
    formula_run_id: str | None = None


class FormulaNeedAssessment(BaseModel):
    required: bool
    signals: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class FormulaBlock(BaseModel):
    id: str
    name: str
    latex: str
    purpose: str
    claim_hook: str = ""


class FormulaVariableDefinition(BaseModel):
    symbol: str
    meaning: str
    unit: str = ""


class CoreFormulaPackage(BaseModel):
    summary: str
    formula_blocks: list[FormulaBlock] = Field(default_factory=list)
    variable_definitions: list[FormulaVariableDefinition] = Field(default_factory=list)
    derivation_notes: list[str] = Field(default_factory=list)
    claim_hooks: list[str] = Field(default_factory=list)
    description_insert: str = ""
    latex_markdown: str = ""
    generation_logs: list[str] = Field(default_factory=list)


class FormulaRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    providers: list[str] = Field(default_factory=list)
    requirement: FormulaNeedAssessment
    package: CoreFormulaPackage | None = None
    failures: list[str] = Field(default_factory=list)
    failure_details: list[RuntimeFailure] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    runtime_state: RuntimeStageState | None = None
    cancel_requested: bool = False
    retry_of: str | None = None
    created_at: str = ""
    updated_at: str = ""


class PostDraftReviewRunCreate(BaseModel):
    providers: list[str] | None = None
    participant_providers: list[str] | None = None
    stage_timeout_ms: int | None = None
    run_timeout_ms: int | None = None


class PostDraftReviewRoleResult(BaseModel):
    role: str = Field(pattern="^(claims_reviewer|spec_cleaner|technical_hardness)$")
    status: str = Field(pattern="^(passed|needs_revision|blocked)$")
    blocking_issues: list[str] = Field(default_factory=list)
    contamination_hits: list[str] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)
    official_safe_patches: list[str] = Field(default_factory=list)
    attorney_memo: list[str] = Field(default_factory=list)


class PostDraftReviewChairResult(BaseModel):
    status: str = Field(pattern="^(passed|needs_revision|blocked)$")
    export_allowed: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    contamination_hits: list[str] = Field(default_factory=list)
    claim_1_rewrite: str = ""
    system_claim_rewrite: str = ""
    abstract_rewrite: str = ""
    description_rewrite_tasks: list[str] = Field(default_factory=list)
    official_safe_patches: list[str] = Field(default_factory=list)
    attorney_memo: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class PostDraftReviewRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    providers: list[str] = Field(default_factory=list)
    participant_providers: list[str] = Field(default_factory=list)
    prompt_pack_version: str = "post-draft-review-v1"
    draft_package_hash: str = ""
    official_compile_run_id: str = ""
    official_package_hash: str = ""
    role_results: list[PostDraftReviewRoleResult] = Field(default_factory=list)
    chair_result: PostDraftReviewChairResult | None = None
    export_allowed: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    contamination_hits: list[str] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    failure_details: list[RuntimeFailure] = Field(default_factory=list)
    runtime_state: RuntimeStageState | None = None
    cancel_requested: bool = False
    retry_of: str | None = None
    created_at: str = ""
    updated_at: str = ""


class PostDraftSafePatchApplyResult(BaseModel):
    project_id: str
    review_run_id: str
    applied_count: int = 0
    skipped_count: int = 0
    applied_actions: list[str] = Field(default_factory=list)
    skipped_patches: list[str] = Field(default_factory=list)
    previous_draft_hash: str = ""
    current_draft_hash: str = ""
    package: DraftPackage


class DraftIssueAnchor(BaseModel):
    type: Literal["text", "section", "missing"]
    section: Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]
    start: int | None = None
    end: int | None = None
    snippet: str | None = None


class DraftReviewIssue(BaseModel):
    id: str
    kind: Literal["blocking", "hit", "suggestion"]
    severity: Literal["critical", "high", "medium", "low"]
    source: str
    message: str
    snippet: str | None = None
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description", "unknown"]
    anchor: DraftIssueAnchor
    status: Literal["open", "fixed", "skipped", "stale", "unanchored"] = "open"


class PostDraftRepairSession(BaseModel):
    project_id: str
    review_run_id: str
    draft_package_hash: str | None = None
    current_draft_hash: str | None = None
    stale: bool = False
    issues: list[DraftReviewIssue] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)


class DraftRepairPatchCreate(BaseModel):
    issue_id: str
    draft_package_hash: str
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description"]
    selected_text: str | None = None
    nearby_context: str | None = None


class DraftRepairPatch(BaseModel):
    id: str
    issue_id: str
    project_id: str
    review_run_id: str
    status: Literal["proposed", "stale", "unsafe", "applied"]
    target_section: Literal["title", "abstract", "claims", "description", "drawing_description"]
    original: str
    patched: str
    diff_summary: str
    risk_notes: list[str] = Field(default_factory=list)
    draft_package_hash: str


class DraftRepairPatchApplyResult(BaseModel):
    package: DraftPackage
    current_draft_hash: str


class ProjectMaterial(BaseModel):
    id: str
    project_id: str
    file_name: str
    path: str
    file_type: str
    text: str = ""
    status: str = Field(pattern="^(uploaded|processed|failed)$")
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MoatScores(BaseModel):
    scope_width: float = Field(default=0.0, ge=0.0, le=1.0)
    designaround_difficulty: float = Field(default=0.0, ge=0.0, le=1.0)
    feasibility: float = Field(default=0.0, ge=0.0, le=1.0)
    support_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    prior_art_distance: float = Field(default=0.0, ge=0.0, le=1.0)
    strategic_value: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def weighted_total(self) -> float:
        return round(
            self.scope_width * 0.18
            + self.designaround_difficulty * 0.18
            + self.feasibility * 0.16
            + self.support_strength * 0.16
            + self.prior_art_distance * 0.16
            + self.strategic_value * 0.16,
            3,
        )


class ClaimChartItem(BaseModel):
    prior_art_id: str
    prior_art_title: str
    overlapping_features: list[str] = Field(default_factory=list)
    differentiating_features: list[str] = Field(default_factory=list)
    claim_drafting_advice: str = ""


class PatentPointCreate(BaseModel):
    source_candidate_id: str | None = None
    title: str
    technical_problem: str
    innovation: str
    technical_solution: str
    beneficial_effects: list[str] = Field(default_factory=list)
    protection_focus: list[str] = Field(default_factory=list)
    evidence_status: str = Field(
        default="feasible_unverified",
        pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$",
    )
    source_type: str = Field(default="user", pattern="^(user|model|imported)$")
    feasibility_basis: str = ""
    support_gaps: list[str] = Field(default_factory=list)
    experiment_needed: list[str] = Field(default_factory=list)
    moat_scores: MoatScores = Field(
        default_factory=lambda: MoatScores(feasibility=0.5, support_strength=0.2, strategic_value=0.6)
    )
    moat_rationale: str = ""
    claim_chart: list[ClaimChartItem] = Field(default_factory=list)
    selected: bool = False
    rationale: str = ""

    def to_candidate(self, point_id: str) -> "PatentPointCandidate":
        gaps = list(self.support_gaps)
        if self.evidence_status in {"feasible_unverified", "needs_experiment"} and not gaps:
            gaps.append("提交前需补充实验或工程样例。")
        return PatentPointCandidate(
            id=point_id,
            title=self.title,
            technical_problem=self.technical_problem,
            innovation=self.innovation,
            technical_solution=self.technical_solution,
            beneficial_effects=self.beneficial_effects,
            protection_focus=self.protection_focus,
            evidence_status=self.evidence_status,
            source_type=self.source_type,
            feasibility_basis=self.feasibility_basis,
            support_gaps=gaps,
            experiment_needed=self.experiment_needed,
            moat_scores=self.moat_scores,
            moat_rationale=self.moat_rationale,
            claim_chart=self.claim_chart,
            selected=self.selected,
            rationale=self.rationale,
        )


class PatentPointUpdate(BaseModel):
    title: str | None = None
    technical_problem: str | None = None
    innovation: str | None = None
    technical_solution: str | None = None
    beneficial_effects: list[str] | None = None
    protection_focus: list[str] | None = None
    evidence_status: str | None = Field(
        default=None,
        pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$",
    )
    source_type: str | None = Field(default=None, pattern="^(user|model|imported)$")
    feasibility_basis: str | None = None
    support_gaps: list[str] | None = None
    experiment_needed: list[str] | None = None
    moat_scores: MoatScores | None = None
    moat_rationale: str | None = None
    claim_chart: list[ClaimChartItem] | None = None
    selected: bool | None = None
    rationale: str | None = None


class PatentPointCandidate(BaseModel):
    id: str
    title: str
    technical_problem: str
    innovation: str
    technical_solution: str
    beneficial_effects: list[str] = Field(default_factory=list)
    protection_focus: list[str] = Field(default_factory=list)
    grantability_score: float = 0.0
    rationale: str = ""
    evidence_status: str = Field(default="model_generated", pattern="^(verified|feasible_unverified|needs_experiment|model_generated)$")
    source_type: str = Field(default="model", pattern="^(user|model|imported)$")
    feasibility_basis: str = ""
    support_gaps: list[str] = Field(default_factory=list)
    experiment_needed: list[str] = Field(default_factory=list)
    moat_scores: MoatScores = Field(default_factory=MoatScores)
    moat_rationale: str = ""
    claim_chart: list[ClaimChartItem] = Field(default_factory=list)
    selected: bool = False


class PriorArtHit(BaseModel):
    id: str
    source: str
    query: str
    title: str
    publication_number: str | None = None
    url: str
    abstract: str | None = None
    relevance_summary: str = ""
    differentiators: list[str] = Field(default_factory=list)


class DisclosureSelfCheckFinding(BaseModel):
    category: str
    severity: str = Field(pattern="^(low|medium|high)$")
    message: str
    suggestion: str


# --- Free Deep Research (internal-only research packet) ----------------------
# These models back the optional `free_deep_research` mode on
# DisclosureRunCreate. The packet they assemble is INTERNAL ONLY: it augments
# the disclosure stage_results and the supporting (non-canonical) parts of the
# disclosure package; it is never read by OfficialDraftCompiler nor exported.

DEEP_RESEARCH_CATEGORIES = (
    "prior_art_cluster",
    "novelty_opportunity",
    "differentiator",
    "claim_constraint",
    "evidence_gap",
    "warning",
    "completion_task",
)


class DeepResearchEvidenceRef(BaseModel):
    """Pointer to a single supporting source used in a deep-research finding."""

    source: str = ""
    query: str = ""
    title: str = ""
    publication_number: str | None = None
    url: str = ""
    relevance: str = ""


class DeepResearchFinding(BaseModel):
    """One structured finding produced by a deep-research cycle."""

    id: str
    category: str = Field(
        pattern="^(prior_art_cluster|novelty_opportunity|differentiator|claim_constraint|evidence_gap|warning|completion_task)$"
    )
    title: str
    summary: str = ""
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    suggested_action: str = ""
    evidence: list[DeepResearchEvidenceRef] = Field(default_factory=list)


class DeepResearchPacket(BaseModel):
    """Internal supporting research packet for `free_deep_research` mode.

    This packet MUST NOT be consumed by OfficialDraftCompiler or any
    official-export path. It is persisted into the disclosure run's
    ``stage_results`` and surfaced to the user as supporting analysis.
    """

    status: str = Field(default="completed", pattern="^(completed|partial|failed)$")
    cycles: int = 0
    project_id: str = ""
    query_plan: list[str] = Field(default_factory=list)
    queries_run: list[str] = Field(default_factory=list)
    prior_art_clusters: list[dict[str, list[str]]] = Field(default_factory=list)
    novelty_opportunities: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    claim_drafting_constraints: list[str] = Field(default_factory=list)
    obviousness_risks: list[str] = Field(default_factory=list)
    evidence_map: dict[str, list[str]] = Field(default_factory=dict)
    evidence_ledger: list[dict] = Field(default_factory=list)
    provider_chain: list[str] = Field(default_factory=list)
    suggested_completion_tasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    findings: list[DeepResearchFinding] = Field(default_factory=list)
    generation_logs: list[str] = Field(default_factory=list)
    internal_only: bool = True


class DisclosurePackage(BaseModel):
    title: str
    summary: str
    materials_summary: str
    candidates: list[PatentPointCandidate] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    prior_art_hits: list[PriorArtHit] = Field(default_factory=list)
    prior_art_differences: str = ""
    body_markdown: str
    mermaid: str
    image_prompt: str
    self_check_findings: list[DisclosureSelfCheckFinding] = Field(default_factory=list)
    generation_logs: list[str] = Field(default_factory=list)
    export_warnings: list[str] = Field(default_factory=list)
    # V1.1: research source ledger and provider diagnostics
    research_ledger: dict[str, Any] = Field(default_factory=dict)
    provider_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    research_confidence: str = Field(
        default="low",
        pattern="^(low|medium|high)$",
        description="Confidence level derived from the source ledger: low (0 refs/failures), medium (1-4), high (5+)",
    )

    @property
    def selected_candidate(self) -> PatentPointCandidate | None:
        for candidate in self.candidates:
            if candidate.id == self.selected_candidate_id:
                return candidate
        return self.candidates[0] if self.candidates else None


class DisclosureRunCreate(BaseModel):
    trace: bool = False
    max_prior_art_results: int = Field(default=8, ge=0, le=20)
    stage_timeout_ms: int | None = None
    run_timeout_ms: int | None = None
    # research_mode toggles the internal-only "free deep research" supplement.
    # standard            -> existing disclosure pipeline, unchanged.
    # free_deep_research  -> run patent deep researcher AFTER the standard
    #                       generator, append findings to stage_results, and
    #                       surface internal analysis hints in the package.
    research_mode: str = Field(
        default="standard",
        pattern="^(standard|free_deep_research)$",
    )


class DisclosureRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    trace: bool = False
    max_prior_art_results: int = 8
    research_mode: str = Field(
        default="standard",
        pattern="^(standard|free_deep_research)$",
    )
    run_dir: str = ""
    stage_results: list[dict[str, Any]] = Field(default_factory=list)
    package: DisclosurePackage | None = None
    failures: list[str] = Field(default_factory=list)
    failure_details: list[RuntimeFailure] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    runtime_state: RuntimeStageState | None = None
    cancel_requested: bool = False
    retry_of: str | None = None


class CorpusQualityReport(BaseModel):
    total_files: int = 0
    processed_files: int = 0
    imported_documents: int = 0
    duplicate_documents: int = 0
    filtered_documents: int = 0
    failed_documents: int = 0
    indexed_chunks: int = 0
    fulltext_extractable_rate: float = 0.0
    section_coverage: dict[str, float] = Field(default_factory=dict)
    low_quality_documents: list[str] = Field(default_factory=list)
    failures: list[dict[str, str]] = Field(default_factory=list)


class CorpusVersion(BaseModel):
    id: str
    name: str
    domain: str = "ai_software"
    source_type: str = ""
    source_name: str = ""
    query: str = ""
    document_count: int = 0
    chunk_count: int = 0
    quality_report: CorpusQualityReport | None = None


class PatentAsset(BaseModel):
    id: str
    job_id: str
    file_name: str
    path: str
    file_type: str
    status: str = Field(pattern="^(uploaded|processed|failed)$")
    document_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorpusImportJobCreate(BaseModel):
    source_type: str
    source_name: str = ""
    query: str = ""
    domain: str = "ai_software"
    version_name: str = "ai-software-v1"


class CorpusImportJob(BaseModel):
    id: str
    source_type: str
    source_name: str = ""
    query: str = ""
    domain: str = "ai_software"
    version_name: str = "ai-software-v1"
    status: str = Field(default="queued", pattern="^(queued|running|completed|failed)$")
    input_paths: list[str] = Field(default_factory=list)
    total_files: int = 0
    processed_files: int = 0
    imported_documents: int = 0
    duplicate_documents: int = 0
    filtered_documents: int = 0
    failed_documents: int = 0
    errors: list[str] = Field(default_factory=list)
    quality_report: CorpusQualityReport | None = None


class ProjectKnowledgeState(BaseModel):
    project_id: str
    status: str = Field(
        default="not_started",
        pattern="^(not_started|search_plan_pending|search_running|candidates_pending|corpus_building|ready|needs_supplemental_search|stale|failed)$",
    )
    active_intent_id: str = ""
    active_plan_id: str = ""
    active_corpus_version_id: str = ""
    last_search_at: str = ""
    last_indexed_at: str = ""
    staleness_reason: str = ""
    document_count: int = 0
    candidate_count: int = 0
    claim_coverage: float = 0.0
    fulltext_coverage: float = 0.0
    quality_flags: list[str] = Field(default_factory=list)


class SearchIntent(BaseModel):
    id: str
    project_id: str
    source_project_hash: str = ""
    technical_object: str = ""
    technical_problem: str = ""
    technical_means: str = ""
    technical_effect: str = ""
    keywords_zh: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    ipc_candidates: list[str] = Field(default_factory=list)
    cpc_candidates: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    date_range: str = ""
    created_by: str = Field(default="agent", pattern="^(agent|user|system)$")
    created_at: str = ""


class SearchPlanStrategyGroup(BaseModel):
    id: str
    label: str
    purpose: str
    queries: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class PatentSourceCapability(BaseModel):
    source_id: str
    display_name: str
    jurisdictions: list[str] = Field(default_factory=list)
    modes: list[Literal["live_search", "official_export", "assisted_capture", "authorized_api"]] = Field(
        default_factory=list
    )
    availability: Literal["available", "manual_import", "config_required", "unavailable"]
    trusted_patent_source: bool = False
    evidence_origin: Literal["official_export", "authorized_api", "public_web", "third_party", "legacy_helper"]
    setup_hint: str = ""


class CnipaQueryPackStrategy(BaseModel):
    strategy_group_id: str
    label: str
    purpose: str
    queries: list[str] = Field(default_factory=list)


class CnipaQueryPack(BaseModel):
    project_id: str
    plan_id: str
    intent_id: str
    source_id: str = "cnipa_official_export"
    technical_object: str = ""
    technical_problem: str = ""
    technical_means: str = ""
    keywords_zh: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    ipc_candidates: list[str] = Field(default_factory=list)
    cpc_candidates: list[str] = Field(default_factory=list)
    date_range: str = ""
    strategies: list[CnipaQueryPackStrategy] = Field(default_factory=list)


class PatentSearchFilters(BaseModel):
    jurisdictions: list[str] = Field(default_factory=list)
    date_range: str = ""
    ipc: list[str] = Field(default_factory=list)
    cpc: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)


class ProviderAttempt(BaseModel):
    id: str
    provider: str
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="ok", pattern="^(ok|skipped|failed|timed_out|partial)$")
    hit_count: int = 0
    retained_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str = ""
    started_at: str = ""
    finished_at: str = ""


class PatentSearchHit(BaseModel):
    id: str
    source: str
    query: str
    title: str
    url: str
    provider_attempt_id: str = ""
    publication_number: str | None = None
    application_number: str | None = None
    applicant: str = ""
    publication_date: str = ""
    grant_date: str = ""
    abstract: str | None = None
    ipc: list[str] = Field(default_factory=list)
    cpc: list[str] = Field(default_factory=list)
    family_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_candidate(
        self,
        *,
        project_id: str,
        plan_id: str,
        strategy_group_id: str,
    ) -> "PriorArtCandidate":
        from backend.app.knowledge.patent_search import patent_hit_to_candidate

        return patent_hit_to_candidate(
            self,
            project_id=project_id,
            plan_id=plan_id,
            strategy_group_id=strategy_group_id,
        )


class CnipaExportImportFailure(BaseModel):
    source_file_name: str
    row_number: int = 0
    code: str
    message: str


class CnipaExportImportResult(BaseModel):
    import_ledger_id: str
    source_id: str = "cnipa_official_export"
    raw_file_hash: str = ""
    detected_schema: str = ""
    row_count: int = 0
    parsed_count: int = 0
    hits: list[PatentSearchHit] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[CnipaExportImportFailure] = Field(default_factory=list)


class AgentSearchPlan(BaseModel):
    id: str
    project_id: str
    intent_id: str
    status: str = Field(default="draft", pattern="^(draft|confirmed|running|completed|failed)$")
    strategy_groups: list[SearchPlanStrategyGroup] = Field(default_factory=list)
    target_sources: list[str] = Field(default_factory=list)
    target_result_count: int = 50
    filters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = ""
    confirmed_at: str = ""
    run_started_at: str = ""
    run_finished_at: str = ""


class ProjectSearchLedger(BaseModel):
    id: str
    project_id: str
    plan_id: str
    attempts: list[ProviderAttempt] = Field(default_factory=list)
    retained_candidate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = ""


class ProjectKnowledgeImportLedger(BaseModel):
    id: str
    project_id: str
    plan_id: str
    source_id: str
    source_file_name: str
    raw_file_hash: str = ""
    detected_schema: str = ""
    row_count: int = 0
    parsed_count: int = 0
    attachments: list[str] = Field(default_factory=list)
    retained_candidate_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[CnipaExportImportFailure] = Field(default_factory=list)
    created_at: str = ""


class PriorArtCandidate(BaseModel):
    id: str
    project_id: str
    plan_id: str
    source: str
    title: str
    publication_number: str | None = None
    application_number: str | None = None
    applicant: str = ""
    publication_date: str = ""
    grant_date: str = ""
    abstract: str | None = None
    url: str
    relevance_score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    ipc: list[str] = Field(default_factory=list)
    cpc: list[str] = Field(default_factory=list)
    family_id: str = ""
    duplicate_of: str = ""
    fulltext_status: str = Field(default="unknown", pattern="^(unknown|available|unavailable|failed)$")
    recommended_action: str = Field(default="review", pattern="^(include|exclude|review)$")
    recommendation_reason: str = ""
    user_decision: str = Field(default="pending", pattern="^(pending|include|exclude)$")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class ProjectCorpusVersion(BaseModel):
    id: str
    project_id: str
    name: str
    source_plan_id: str = ""
    candidate_set_id: str = ""
    status: str = Field(
        default="building",
        pattern="^(building|ready|needs_supplemental_search|failed|superseded)$",
    )
    document_count: int = 0
    chunk_count: int = 0
    claim_coverage: float = 0.0
    fulltext_coverage: float = 0.0
    quality_report: CorpusQualityReport | None = None
    created_at: str = ""
    superseded_by: str = ""


class ProjectKnowledgeOverview(BaseModel):
    state: ProjectKnowledgeState
    latest_intent: SearchIntent | None = None
    latest_plan: AgentSearchPlan | None = None
    candidates: list[PriorArtCandidate] = Field(default_factory=list)
    latest_corpus_version: ProjectCorpusVersion | None = None


class CnipaExportImportResponse(BaseModel):
    overview: ProjectKnowledgeOverview
    ledger: ProjectKnowledgeImportLedger


class CandidateDecisionPatch(BaseModel):
    user_decision: str = Field(pattern="^(include|exclude|pending)$")


class CandidateBulkDecision(BaseModel):
    candidate_ids: list[str]
    user_decision: str = Field(pattern="^(include|exclude|pending)$")


class BuildProjectCorpusRequest(BaseModel):
    plan_id: str = Field(min_length=1)


class DesktopConfigView(BaseModel):
    """Redacted view of the desktop LLM configuration (PR6, issue #20).

    The raw API key is never included; only its presence and a short,
    non-reversible fingerprint.
    """

    provider: str
    base_url: str
    model: str
    api_key_present: bool
    api_key_fingerprint: str
    updated_at: str = ""
    version: int = 1
    api_key_source: str = "none"


class DesktopConfigUpdate(BaseModel):
    """Update payload for the desktop configuration.

    Pass ``clear_api_key=True`` to remove the stored key. ``api_key`` and
    ``clear_api_key`` are mutually exclusive.
    """

    provider: str | None = Field(default=None, max_length=32)
    base_url: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False

    @model_validator(mode="after")
    def _api_key_exclusive(self) -> "DesktopConfigUpdate":
        if self.clear_api_key and self.api_key is not None:
            raise ValueError("Pass either api_key or clear_api_key, not both.")
        return self


class DesktopConfigHealthResult(BaseModel):
    """Result of probing the configured LLM with a tiny request."""

    ok: bool
    model: str
    api_key_source: str
    latency_ms: int = 0
    status_code: int = 0
    error: str = ""


class EvidenceSourceConfig(BaseModel):
    source_id: str
    display_name: str
    source_type: str = Field(pattern="^(patent|non_patent_literature|web_discovery)$")
    evidence_tier: str = Field(pattern="^(primary_patent|supplemental_literature|discovery_signal)$")
    enabled: bool = True
    status: str = Field(pattern="^(not_configured|configured|unavailable|quota_limited)$")
    base_url: str = ""
    api_key_present: bool = False
    api_key_masked: str = ""
    api_key_source: str = Field(default="none", pattern="^(env|local|none)$")
    last_checked_at: str = ""
    last_error: str = ""
    application_url: str = ""
    docs_url: str = ""
    guidance: str = ""
    can_satisfy_patent_gate: bool = False


class EvidenceSourceConfigPatch(BaseModel):
    api_key: str | None = None
    clear_api_key: bool = False
    base_url: str | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def _api_key_exclusive(self) -> "EvidenceSourceConfigPatch":
        if self.clear_api_key and self.api_key is not None:
            raise ValueError("Pass either api_key or clear_api_key, not both.")
        return self


class EvidenceSourceCheckResult(BaseModel):
    source_id: str
    ok: bool
    status: str = Field(pattern="^(not_configured|configured|unavailable|quota_limited)$")
    detail: str = ""
    live_search_available: bool = False
    last_checked_at: str = ""


# --- V1.1 PR2: Grantability claim chart and patentability attack analysis -----


class FeaturePlacement(str, Enum):
    """Where a feature should appear in the claims/description."""

    INDEPENDENT_CLAIM_REQUIRED = "independent_claim_required"
    DEPENDENT_CLAIM_OPTIONAL = "dependent_claim_optional"
    DESCRIPTION_ONLY_SUPPORT = "description_only_support"
    SHOULD_DELETE = "should_delete"


class NoveltyAttack(BaseModel):
    """A single novelty attack on one of our claim features using a prior-art reference."""

    feature_text: str
    prior_art_title: str = ""
    prior_art_ref: str = ""
    citation_source: str = ""
    overlap_analysis: str = ""
    attack_strength: str = Field(default="weak", pattern="^(strong|moderate|weak|none)$")
    evidence_quality: str = Field(default="low", pattern="^(verified|unverified|low)$")


class InventiveStepAttackCombo(BaseModel):
    """An obviousness / inventive-step attack combining one or more prior-art references."""

    title: str
    primary_reference: str = ""
    secondary_references: list[str] = Field(default_factory=list)
    combination_rationale: str = ""
    attack_strength: str = Field(default="moderate", pattern="^(strong|moderate|weak)$")
    defense_suggestion: str = ""


class GrantabilityClaimChartRow(BaseModel):
    """One row in the grantability claim chart — maps a claim feature to prior art."""

    claim_ref: str
    feature_text: str
    feature_placement: FeaturePlacement
    closest_prior_art_refs: list[str] = Field(default_factory=list)
    novelty_distinction: str = ""
    novelty_attack: NoveltyAttack | None = None
    inventive_step_combos: list[InventiveStepAttackCombo] = Field(default_factory=list)
    support_status: str = Field(default="weak", pattern="^(strong|partial|weak|missing)$")
    overbreadth_risk: bool = False
    recommended_scope_adjustment: str = ""


class GrantabilityReport(BaseModel):
    """Structured grantability analysis: prior art, claim chart, attacks, risks.

    Low-evidence / no-prior-art cases MUST set ``status`` to ``"low"`` or
    ``"uncertain"`` and ``fail_closed=True`` — they can never be presented as
    high grant probability.
    """

    id: str
    project_id: str
    status: str = Field(default="low", pattern="^(high|medium|low|uncertain)$")
    overall_assessment: str = ""
    closest_prior_art_summary: str = ""
    claim_chart: list[GrantabilityClaimChartRow] = Field(default_factory=list)
    novelty_attacks: list[NoveltyAttack] = Field(default_factory=list)
    inventive_step_attacks: list[InventiveStepAttackCombo] = Field(default_factory=list)
    risk_summary: dict[str, str] = Field(default_factory=dict)
    low_evidence_flags: list[str] = Field(default_factory=list)
    fail_closed: bool = False
    recommendation: str = ""
    source_ledger_citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
