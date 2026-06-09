from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    section_type: SectionType
    text: str


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
    round_depth: str = "converged_two_round"
    trace: bool = False
    task_timeout_ms: int | None = None
    run_timeout_ms: int | None = None


class FormulaRunCreate(BaseModel):
    providers: list[str] | None = None


class DeliberationRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    providers: list[str] = Field(default_factory=list)
    run_mode: str = Field(pattern="^(full|partial|minimal|blocked)$")
    round_depth: str = "converged_two_round"
    trace: bool = False
    run_dir: str = ""
    stage_results: list[DeliberationStageResult] = Field(default_factory=list)
    strategy_brief: PatentStrategyBrief | None = None
    failures: list[AgentFailure] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)


class ClaimItem(BaseModel):
    """One structured claim. Canonical claim text is rendered deterministically from this."""

    number: int
    kind: str = Field(default="independent", pattern="^(independent|dependent)$")
    depends_on: int | None = None
    category: str = Field(default="other", pattern="^(method|system|device|medium|other)$")
    preamble: str = ""
    features: list[str] = Field(default_factory=list)


class ClaimsOutput(BaseModel):
    claims: list[ClaimItem] = Field(default_factory=list)


class DescriptionOutput(BaseModel):
    """Specification body sections. 附图说明 is NOT here; it is single-sourced from DrawingsOutput."""

    technical_field: str = ""
    background: str = ""
    summary: str = ""
    embodiments: str = ""


class FigureItem(BaseModel):
    figure_no: str
    title: str


class DrawingsOutput(BaseModel):
    figures: list[FigureItem] = Field(default_factory=list)


class AbstractOutput(BaseModel):
    abstract: str = ""


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
    # Structured source-of-truth for canonical text (Component 1). Optional for backward compatibility
    # with stored drafts; when present, the official compiler assembles from these via allowlist.
    claims_struct: ClaimsOutput | None = None
    description_struct: DescriptionOutput | None = None
    drawings_struct: DrawingsOutput | None = None
    abstract_struct: AbstractOutput | None = None


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
    status: str = Field(pattern="^(completed|blocked|failed)$")
    source_draft_hash: str = ""
    official_package_hash: str = ""
    official_package: OfficialDraftPackage | None = None
    contamination_removed: list[dict[str, str]] = Field(default_factory=list)
    blocked_items: list[dict[str, str]] = Field(default_factory=list)
    sidecar_notes: list[dict[str, str]] = Field(default_factory=list)
    logs: list[DeliberationLogEntry] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class ProjectCreate(BaseModel):
    name: str
    draft_text: str


class ProjectRecord(BaseModel):
    id: str
    name: str
    draft_text: str
    package: DraftPackage | None = None
    created_at: str = ""
    updated_at: str = ""


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
    risk_tags: list[str] = Field(default_factory=list)


class ClaimDefenseWorksheet(BaseModel):
    id: str
    project_id: str
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
    status: str = Field(default="completed", pattern="^(completed|failed)$")
    issues: list[CompletionIssue] = Field(default_factory=list)
    tasks: list[CompletionTask] = Field(default_factory=list)
    patches: list[ProposedPatch] = Field(default_factory=list)
    support_matrix: list[ClaimSupportMatrixRow] = Field(default_factory=list)
    scorecard: CompletionScoreCard
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""


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
    status: str = Field(pattern="^(queued|running|completed|failed)$")
    providers: list[str] = Field(default_factory=list)
    requirement: FormulaNeedAssessment
    package: CoreFormulaPackage | None = None
    failures: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class PostDraftReviewRunCreate(BaseModel):
    providers: list[str] | None = None


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
    status: str = Field(pattern="^(queued|running|completed|failed)$")
    providers: list[str] = Field(default_factory=list)
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
    created_at: str = ""
    updated_at: str = ""


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


# --- Deep Research (free_deep_research) models --------------------------------------


class DeepResearchEvidenceRef(BaseModel):
    """Pointer to a source used in a deep-research finding."""

    source: str = Field(description="Provider label, e.g. Google Patents / CNIPA EPUB / SearXNG")
    query: str = ""
    title: str = ""
    publication_number: str | None = None
    url: str = ""
    relevance: str = ""


class DeepResearchFinding(BaseModel):
    """One structured finding from a deep-research cycle."""

    id: str
    category: str = Field(pattern="^(prior_art_cluster|novelty_opportunity|differentiator|claim_constraint|evidence_gap|warning|completion_task)$")
    title: str
    summary: str
    evidence: list[DeepResearchEvidenceRef] = Field(default_factory=list)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    suggested_action: str = ""


class DeepResearchPacket(BaseModel):
    """Internal-only research package produced by free_deep_research mode.

    This packet MUST NOT be read by OfficialDraftCompiler or any official-export path.
    It is stored in disclosure stage_results_json for internal review and to augment the
    DisclosurePackage with richer prior-art analysis, claim charts, and completion hints.
    """

    status: str = Field(pattern="^(completed|partial|failed)$")
    cycles: int = 0
    queries_run: list[str] = Field(default_factory=list)
    prior_art_clusters: list[dict[str, list[str]]] = Field(
        default_factory=list, description="Grouped prior-art references by technical sub-area."
    )
    novelty_opportunities: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    claim_drafting_constraints: list[str] = Field(default_factory=list)
    evidence_map: dict[str, list[str]] = Field(
        default_factory=dict, description="claim feature -> evidence/source ids"
    )
    warnings: list[str] = Field(default_factory=list)
    suggested_completion_tasks: list[str] = Field(default_factory=list)
    findings: list[DeepResearchFinding] = Field(default_factory=list)
    generation_logs: list[str] = Field(default_factory=list)
    internal_notes: list[str] = Field(default_factory=list, description="Not for official export.")


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

    @property
    def selected_candidate(self) -> PatentPointCandidate | None:
        for candidate in self.candidates:
            if candidate.id == self.selected_candidate_id:
                return candidate
        return self.candidates[0] if self.candidates else None


class DisclosureRunCreate(BaseModel):
    trace: bool = False
    max_prior_art_results: int = Field(default=8, ge=0, le=20)
    research_mode: str = Field(default="standard", pattern="^(standard|free_deep_research)$")


class DisclosureRun(BaseModel):
    id: str
    project_id: str
    status: str = Field(pattern="^(queued|running|completed|failed|interrupted)$")
    trace: bool = False
    max_prior_art_results: int = 8
    run_dir: str = ""
    stage_results: list[dict[str, Any]] = Field(default_factory=list)
    package: DisclosurePackage | None = None
    failures: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)


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


# --- Golden-set evaluation models -------------------------------------------------


class EvalPatentResult(BaseModel):
    """Single patent evaluation result within a golden-set run."""

    patent_id: str
    title: str
    technical_field: str
    gate_pass: bool
    gate_warnings: list[str] = Field(default_factory=list)
    sas: float  # 0-1
    sas_detail: dict[str, float] = Field(default_factory=dict)
    ccs: float  # 0-1
    ccs_detail: dict[str, float] = Field(default_factory=dict)
    llm_judge: dict[str, float | None] | None = None


class GoldenEvalSummary(BaseModel):
    """Aggregated summary across all patents in a golden-set run."""

    sas_avg: float
    ccs_avg: float
    gate_pass_rate: float
    llm_judge_avg: dict[str, float] | None = None
    pass_: bool
    warnings: int
    load_errors: int = 0


class GoldenEvalReport(BaseModel):
    """Full evaluation report for a golden-set run."""

    run_id: str
    commit: str
    golden_set_version: str
    timestamp: datetime = Field(default_factory=_utc_now_iso)
    summary: GoldenEvalSummary
    per_patent: list[EvalPatentResult] = Field(default_factory=list)
    diff_from_previous: dict[str, Any] | None = None
