export type SectionType =
  | "abstract"
  | "claims"
  | "description"
  | "technical_field"
  | "background"
  | "summary"
  | "drawings"
  | "embodiments"
  | "other";

export type EvidenceStatus = "verified" | "feasible_unverified" | "needs_experiment" | "model_generated";
export type EvidenceBindingSourceType =
  | "project_material"
  | "prior_art"
  | "disclosure"
  | "patent_point"
  | "formula"
  | "draft_citation"
  | "manual";
export type EvidenceVerificationStatus =
  | "verified"
  | "retrieved"
  | "user_provided"
  | "feasible_unverified"
  | "needs_experiment"
  | "model_generated";
export type PatentPointSourceType = "user" | "model" | "imported";

export interface MoatScores {
  scope_width: number;
  designaround_difficulty: number;
  feasibility: number;
  support_strength: number;
  prior_art_distance: number;
  strategic_value: number;
}

export interface ClaimChartItem {
  prior_art_id: string;
  prior_art_title: string;
  overlapping_features: string[];
  differentiating_features: string[];
  claim_drafting_advice: string;
}

export interface PatentDocument {
  id: string;
  title: string;
  source_name: string;
  text?: string;
  sections?: Array<{ type: SectionType; heading: string; text: string; ordinal: number }>;
  metadata: Record<string, unknown>;
}

export interface PatentChunk {
  id: string;
  document_id: string;
  section_type: SectionType;
  text: string;
  ordinal: number;
  metadata: Record<string, unknown>;
}

export interface SearchResult {
  chunk: PatentChunk;
  score: number;
}

export interface ReviewFinding {
  category: string;
  severity: "low" | "medium" | "high";
  message: string;
  suggestion: string;
  evidence?: string;
}

export interface PatentStrategyBrief {
  summary: string;
  claim_strategy: string[];
  description_strategy: string[];
  risk_controls: string[];
  agent_consensus: string;
  disclosure_summary?: string | null;
  patent_point_summary?: string | null;
  prior_art_differences?: string | null;
}

export interface DraftPackage {
  title: string;
  abstract: string;
  claims: string;
  description: string;
  drawing_description: string;
  mermaid: string;
  image_prompt: string;
  review_findings: ReviewFinding[];
  citations: Array<{
    chunk_id: string;
    document_id: string;
    section_type: SectionType;
    text: string;
  }>;
  generation_logs: string[];
  deliberation_run_id?: string | null;
  strategy_brief?: PatentStrategyBrief | null;
  agent_consensus?: string | null;
  disclosure_run_id?: string | null;
  disclosure_summary?: string | null;
  patent_point_summary?: string | null;
  formula_run_id?: string | null;
  core_formula_summary?: string | null;
}

export type DraftPackageManualUpdate = Pick<
  DraftPackage,
  "title" | "abstract" | "claims" | "description" | "drawing_description"
>;

export interface RevisionLedgerRecord {
  id: string;
  project_id: string;
  revision_kind:
    | "material_merge"
    | "correction"
    | "protection_focus"
    | "post_draft_repair"
    | "official_cleanup"
    | "completion_patch";
  baseline_artifact_hash: string;
  new_artifact_hash: string;
  user_intent_summary: string;
  affected_sections: string[];
  prior_art_changed: boolean;
  protection_scope_changed: boolean;
  artifact_refs: string[];
  created_at: string;
}

export interface OfficialFigurePlanItem {
  figure_no: string;
  title: string;
  description: string;
  referenced_sections: string[];
}

export interface OfficialDraftPackage {
  title: string;
  abstract: string;
  claims: string;
  description: string;
  drawing_description: string;
  figure_plan: OfficialFigurePlanItem[];
  compile_warnings: string[];
  source_draft_hash: string;
  official_package_hash: string;
}

export interface OfficialCompileRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "blocked" | "failed";
  source_draft_hash: string;
  official_package_hash: string;
  official_package: OfficialDraftPackage | null;
  contamination_removed: Array<Record<string, string>>;
  blocked_items: Array<Record<string, string>>;
  sidecar_notes: Array<Record<string, string>>;
  logs: DeliberationLogEntry[];
  created_at: string;
  updated_at: string;
}

export type FilingReadinessStatus = "clean" | "warning" | "high_risk";
export type FilingIssueSeverity = "low" | "medium" | "high";
export type FeatureClassification =
  | "known_base"
  | "differentiator"
  | "core_combo"
  | "dependent_fallback"
  | "support_needed";

export interface FilingReadinessIssue {
  category: string;
  severity: FilingIssueSeverity;
  target: "claims" | "description" | "abstract" | "drawings" | "export";
  matched_text: string;
  message: string;
  suggestion: string;
  can_auto_clean: boolean;
}

export interface FilingReadinessReport {
  id: string;
  project_id: string;
  draft_package_hash: string;
  status: FilingReadinessStatus;
  rules_version: string;
  issues: FilingReadinessIssue[];
  created_at: string;
}

export type FeaturePlacement =
  | "independent_claim_required"
  | "dependent_claim_optional"
  | "description_only_support"
  | "should_delete";

export interface NoveltyAttack {
  feature_text: string;
  prior_art_title: string;
  prior_art_ref: string;
  citation_source: string;
  overlap_analysis: string;
  attack_strength: "strong" | "moderate" | "weak" | "none";
  evidence_quality: "verified" | "unverified" | "low";
}

export interface InventiveStepAttackCombo {
  title: string;
  primary_reference: string;
  secondary_references: string[];
  combination_rationale: string;
  attack_strength: "strong" | "moderate" | "weak";
  defense_suggestion: string;
}

export interface GrantabilityClaimChartRow {
  claim_ref: string;
  feature_text: string;
  feature_placement: FeaturePlacement;
  closest_prior_art_refs: string[];
  novelty_distinction: string;
  novelty_attack?: NoveltyAttack | null;
  inventive_step_combos: InventiveStepAttackCombo[];
  support_status: "strong" | "partial" | "weak" | "missing";
  overbreadth_risk: boolean;
  recommended_scope_adjustment: string;
}

export interface GrantabilityReport {
  id: string;
  project_id: string;
  status: "high" | "medium" | "low" | "uncertain";
  overall_assessment: string;
  closest_prior_art_summary: string;
  claim_chart: GrantabilityClaimChartRow[];
  novelty_attacks: NoveltyAttack[];
  inventive_step_attacks: InventiveStepAttackCombo[];
  risk_summary: Record<string, string>;
  low_evidence_flags: string[];
  fail_closed: boolean;
  recommendation: string;
  source_ledger_citations: Array<Record<string, unknown>>;
  created_at: string;
}

export interface FeatureRecord {
  feature_id: string;
  text: string;
  classification: FeatureClassification;
  claim_refs: string[];
  description_refs: string[];
  figure_refs: string[];
  prior_art_refs: string[];
  evidence_refs: string[];
  source_refs: string[];
  support_explanation: string;
  risk_tags: string[];
}

export interface EvidenceBinding {
  evidence_id: string;
  source_type: EvidenceBindingSourceType;
  source_id: string;
  source_label: string;
  quote: string;
  confidence: number;
  verification_status: EvidenceVerificationStatus;
  internal_only: boolean;
  citable: boolean;
  metadata: Record<string, unknown>;
}

export interface ClaimDefenseWorksheet {
  id: string;
  project_id: string;
  draft_package_hash: string;
  status: "draft" | "reviewed" | "superseded";
  source: "draft" | "disclosure" | "generated_package" | "manual";
  feature_records: FeatureRecord[];
  defense_recommendations: string[];
  support_gaps: string[];
  notes: string[];
  created_at: string;
}

export interface CompletionIssue {
  id: string;
  category: string;
  severity: FilingIssueSeverity;
  target: "claim" | "description" | "drawing" | "embodiment" | "term" | "evidence" | "prior_art" | "export";
  source_refs: string[];
  message: string;
  why_it_matters: string;
  suggested_action: string;
  blocks_submission: boolean;
}

export interface CompletionTask {
  id: string;
  issue_id: string;
  task_type: string;
  priority: number;
  input_refs: string[];
  expected_output: string;
  draft_section_target: string;
  status: "open" | "proposed" | "accepted" | "rejected" | "superseded";
}

export interface ProposedPatch {
  id: string;
  task_id: string;
  target_section: string;
  patch_kind: "insert" | "replace" | "delete" | "rewrite" | "sidecar_only";
  before_text: string;
  after_text: string;
  rationale: string;
  risk_delta: string;
  evidence_refs: string[];
  can_enter_official_draft: boolean;
  status: "proposed" | "accepted" | "rejected" | "superseded";
}

export interface CompletionScoreCard {
  authorization_stability: number;
  protection_scope: number;
  support_strength: number;
  prior_art_distinction: number;
  filing_maturity: number;
  official_hygiene: number;
  overall: number;
}

export interface ClaimSupportMatrixRow {
  claim_ref: string;
  feature_text: string;
  feature_classification: FeatureClassification;
  description_refs: string[];
  figure_refs: string[];
  embodiment_refs: string[];
  formula_refs: string[];
  data_structure_refs: string[];
  pseudo_code_refs: string[];
  prior_art_refs: string[];
  evidence_refs: string[];
  source_refs: string[];
  support_explanation: string;
  missing_evidence_reason: string;
  evidence_status: EvidenceStatus;
  risk_tags: string[];
  completion_status: "supported" | "partial" | "missing";
}

export interface DraftCompletionRun {
  id: string;
  project_id: string;
  snapshot_hash: string;
  draft_package_hash: string;
  status: "completed" | "failed";
  issues: CompletionIssue[];
  tasks: CompletionTask[];
  patches: ProposedPatch[];
  support_matrix: ClaimSupportMatrixRow[];
  scorecard: CompletionScoreCard;
  scorecard_baseline?: CompletionScoreCard | null;
  notes: string[];
  created_at: string;
}

export type ExternalDraftSourceType = "pasted_text" | "markdown_file" | "docx_file";

export interface ExternalDraftSource {
  id: string;
  project_id: string;
  source_type: ExternalDraftSourceType;
  file_name: string;
  content_hash: string;
  raw_text: string;
  raw_path: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SectionConfidenceItem {
  score: number;
  source_markers: string[];
  warnings: string[];
}

export interface SectionConfidence {
  title: SectionConfidenceItem;
  abstract: SectionConfidenceItem;
  claims: SectionConfidenceItem;
  description: SectionConfidenceItem;
  drawing_description: SectionConfidenceItem;
}

export interface IntakeIssue {
  id: string;
  category:
    | "missing_section"
    | "duplicate_section"
    | "low_confidence_section"
    | "format_noise"
    | "unsupported_attachment"
    | "suspected_internal_text"
    | "malformed_claim_numbering";
  severity: FilingIssueSeverity;
  section: "title" | "abstract" | "claims" | "description" | "drawing_description" | "raw_text";
  message: string;
  suggested_action: string;
  blocks_quality_run: boolean;
}

export interface ExternalDraftIntakeRun {
  id: string;
  project_id: string;
  source_id: string;
  status: "completed" | "needs_review" | "failed";
  parser_version: string;
  source_hash: string;
  parsed_package: DraftPackage | null;
  section_confidence: SectionConfidence | null;
  intake_issues: IntakeIssue[];
  unassigned_fragments: string[];
  working_draft_hash: string;
  logs: DeliberationLogEntry[];
  created_at: string;
}

export interface ScoreImprovementResult {
  project_id: string;
  before_score: number;
  after_score: number;
  accepted_patch_ids: string[];
  before_run: DraftCompletionRun;
  after_run: DraftCompletionRun;
  logs: string[];
}

export type PatentType = "invention" | "utility_model";

export const PATENT_TYPE_INVENTION: PatentType = "invention";
export const PATENT_TYPE_UTILITY_MODEL: PatentType = "utility_model";

export interface ProjectRecord {
  id: string;
  name: string;
  draft_text: string;
  patent_type: PatentType;
  package: DraftPackage | null;
  created_at: string;
  updated_at: string;
  applicant: string;
  inventors: string;
  technical_field: string;
  background: string;
  pain_point: string;
  technical_solution: string;
  innovation: string;
  embodiments: string;
  beneficial_effects: string;
}

export interface ProjectUpdate {
  name?: string;
  draft_text?: string;
  patent_type?: PatentType;
  applicant?: string;
  inventors?: string;
  technical_field?: string;
  background?: string;
  pain_point?: string;
  technical_solution?: string;
  innovation?: string;
  embodiments?: string;
  beneficial_effects?: string;
}

export interface ProjectMaterial {
  id: string;
  project_id: string;
  file_name: string;
  path: string;
  file_type: string;
  text: string;
  status: "uploaded" | "processed" | "failed";
  warnings: string[];
  metadata: Record<string, unknown>;
}

export interface PatentPointCandidate {
  id: string;
  title: string;
  technical_problem: string;
  innovation: string;
  technical_solution: string;
  beneficial_effects: string[];
  protection_focus: string[];
  grantability_score: number;
  rationale: string;
  evidence_status: EvidenceStatus;
  source_type: PatentPointSourceType;
  feasibility_basis: string;
  support_gaps: string[];
  experiment_needed: string[];
  moat_scores: MoatScores;
  moat_rationale?: string;
  claim_chart: ClaimChartItem[];
  selected: boolean;
}

export interface PatentPointCreatePayload {
  source_candidate_id?: string | null;
  title: string;
  technical_problem: string;
  innovation: string;
  technical_solution: string;
  beneficial_effects: string[];
  protection_focus: string[];
  evidence_status: EvidenceStatus;
  source_type: PatentPointSourceType;
  feasibility_basis: string;
  support_gaps: string[];
  experiment_needed: string[];
  moat_scores: MoatScores;
  claim_chart?: ClaimChartItem[];
  selected: boolean;
  rationale: string;
}

export interface PriorArtHit {
  id: string;
  source: string;
  query: string;
  title: string;
  publication_number?: string | null;
  url: string;
  abstract?: string | null;
  relevance_summary: string;
  differentiators: string[];
}

export interface DisclosureSelfCheckFinding {
  category: string;
  severity: "low" | "medium" | "high";
  message: string;
  suggestion: string;
}

export interface RuntimeStageState {
  current_stage: string;
  provider: string;
  query: string;
  subtask: string;
  heartbeat_at: string;
  elapsed_ms: number;
  warning_count: number;
  partial_artifact_count: number;
  timeout_ms?: number | null;
  attempt?: number | null;
}

export interface RuntimeFailure {
  flow: string;
  stage: string;
  provider: string;
  reason: string;
  message: string;
  retryable: boolean;
  elapsed_ms: number;
  repair_suggestion: string;
  partial_artifact_count: number;
  created_at: string;
}

export interface ProviderDiagnostic {
  phase: string;
  available_providers: string[];
  skipped_providers: Array<{ provider: string; reason: string }>;
  active_chain: string[];
  warnings: string[];
}

export interface DisclosurePackage {
  title: string;
  summary: string;
  materials_summary: string;
  candidates: PatentPointCandidate[];
  selected_candidate_id?: string | null;
  prior_art_hits: PriorArtHit[];
  prior_art_differences: string;
  body_markdown: string;
  mermaid: string;
  image_prompt: string;
  self_check_findings: DisclosureSelfCheckFinding[];
  generation_logs: string[];
  export_warnings: string[];
  research_ledger?: Record<string, unknown>;
  provider_diagnostics?: ProviderDiagnostic[];
  research_confidence?: "none" | "low" | "medium" | "high";
}

export interface DisclosureRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "interrupted";
  trace: boolean;
  max_prior_art_results: number;
  run_dir: string;
  stage_results: Array<{ phase: string; payload: Record<string, unknown> | unknown[] }>;
  package: DisclosurePackage | null;
  failures: string[];
  events: string[];
  research_mode?: "standard" | "free_deep_research";
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  cancel_requested?: boolean;
  retry_of?: string | null;
}

export type QualityCheckState = "missing" | "stale" | "failed" | "unknown" | "current";
export type QualityCheckStates = Record<string, QualityCheckState>;

export interface ExportReadiness {
  export_allowed: boolean;
  draft_required: boolean;
  quality_required: boolean;
  official_compile_required: boolean;
  post_draft_review_required: boolean;
  next_action: "generate_draft" | "run_quality_checks" | "run_official_compile" | "run_post_draft_review" | "export_ready";
  reason: string;
  quality_done?: boolean;
  missing_quality_checks?: string[];
  stale_quality_checks?: string[];
  failed_quality_checks?: string[];
  unknown_quality_checks?: string[];
  quality_check_states?: QualityCheckStates;
  filing_readiness_report_id?: string;
  claim_defense_worksheet_id?: string;
  draft_completion_run_id?: string;
  compile_run_id?: string;
  has_compile_run?: boolean;
  compile_status?: "missing" | "queued" | "running" | "completed" | "blocked" | "failed";
  compile_blocked_items?: Array<Record<string, string>>;
  review_run_id?: string;
  official_package_hash?: string;
  current_source_draft_hash?: string;
  has_review_run?: boolean;
  review_export_allowed?: boolean;
  review_status?: "missing" | "queued" | "running" | "completed" | "failed" | "interrupted";
  review_gate_status?: "missing" | "queued" | "running" | "passed" | "needs_revision" | "blocked" | "failed" | "interrupted";
  review_blocking_issues?: string[];
}

export interface Health {
  ok: boolean;
  llm_configured: boolean;
  data_dir: string;
  model: string;
  embedding_model: string;
}

export interface DesktopConfigView {
  provider: string;
  base_url: string;
  model: string;
  api_key_present: boolean;
  api_key_fingerprint: string;
  updated_at: string;
  version: number;
  api_key_source: "env" | "desktop_config" | "none";
}

export interface DesktopConfigUpdatePayload {
  provider?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  clear_api_key?: boolean;
}

export interface DesktopConfigHealthResult {
  ok: boolean;
  model: string;
  api_key_source: "env" | "desktop_config" | "none";
  latency_ms: number;
  status_code: number;
  error: string;
}

export interface AgentProviderStatus {
  id: string;
  label: string;
  command: string;
  available: boolean;
  path: string;
  required: boolean;
  model_version: string;
  roles: string[];
  installed: boolean;
  auth_status: "ready" | "not_authenticated" | "unavailable" | "timeout" | "unknown";
  diagnostic: string;
  repair_suggestion: string;
  selectable: boolean;
}

export interface AgentDoctorReport {
  status: "ready" | "degraded" | "blocked";
  run_mode: "full" | "partial" | "minimal" | "blocked";
  commands: Record<string, AgentProviderStatus>;
  active_provider_ids: string[];
  missing_required: string[];
  missing_optional: string[];
  unknown_required: string[];
}

export interface DeliberationRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "interrupted";
  providers: string[];
  participant_providers?: string[];
  run_mode: "full" | "partial" | "minimal" | "blocked";
  round_depth: string;
  trace: boolean;
  run_dir: string;
  stage_results: Array<{
    phase: string;
    provider_id: string;
    label: string;
    payload: Record<string, unknown>;
    status: "completed" | "failed" | "degraded";
  }>;
  strategy_brief: PatentStrategyBrief | null;
  failures: Array<{
    provider_id: string;
    phase: string;
    reason: string;
    message: string;
  }>;
  events: string[];
  logs: DeliberationLogEntry[];
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  cancel_requested?: boolean;
  retry_of?: string | null;
}

export interface DeliberationLogEntry {
  level: "info" | "warn" | "error";
  phase: string;
  provider_id: string;
  attempt?: number | null;
  message: string;
  detail: string;
  repair_suggestion: string;
  elapsed_ms?: number | null;
  created_at: string;
}

export interface FormulaNeedAssessment {
  required: boolean;
  signals: string[];
  reasons: string[];
}

export interface FormulaBlock {
  id: string;
  name: string;
  latex: string;
  purpose: string;
  claim_hook: string;
}

export interface FormulaVariableDefinition {
  symbol: string;
  meaning: string;
  unit: string;
}

export interface CoreFormulaPackage {
  summary: string;
  formula_blocks: FormulaBlock[];
  variable_definitions: FormulaVariableDefinition[];
  derivation_notes: string[];
  claim_hooks: string[];
  description_insert: string;
  latex_markdown: string;
  generation_logs: string[];
}

export interface FormulaRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "interrupted";
  providers: string[];
  requirement: FormulaNeedAssessment;
  package: CoreFormulaPackage | null;
  failures: string[];
  events: string[];
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  cancel_requested?: boolean;
  retry_of?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PostDraftReviewRoleResult {
  role: "claims_reviewer" | "spec_cleaner" | "technical_hardness";
  status: "passed" | "needs_revision" | "blocked";
  blocking_issues: string[];
  contamination_hits: string[];
  rewrite_suggestions: string[];
  official_safe_patches: string[];
  attorney_memo: string[];
}

export interface PostDraftReviewChairResult {
  status: "passed" | "needs_revision" | "blocked";
  export_allowed: boolean;
  blocking_issues: string[];
  contamination_hits: string[];
  claim_1_rewrite: string;
  system_claim_rewrite: string;
  abstract_rewrite: string;
  description_rewrite_tasks: string[];
  official_safe_patches: string[];
  attorney_memo: string[];
  next_actions: string[];
}

export interface PostDraftReviewRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "interrupted";
  providers: string[];
  participant_providers?: string[];
  prompt_pack_version: string;
  draft_package_hash: string;
  official_compile_run_id: string;
  official_package_hash: string;
  role_results: PostDraftReviewRoleResult[];
  chair_result: PostDraftReviewChairResult | null;
  export_allowed: boolean;
  blocking_issues: string[];
  contamination_hits: string[];
  logs: DeliberationLogEntry[];
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  cancel_requested?: boolean;
  retry_of?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PostDraftSafePatchApplyResult {
  project_id: string;
  review_run_id: string;
  applied_count: number;
  skipped_count: number;
  applied_actions: string[];
  skipped_patches: string[];
  previous_draft_hash: string;
  current_draft_hash: string;
  package: DraftPackage;
}

export interface OfficialCompileCleanupResult {
  project_id: string;
  compile_run_id: string;
  applied_count: number;
  applied_actions: string[];
  previous_draft_hash: string;
  current_draft_hash: string;
  package: DraftPackage;
}

export type DraftIssueAnchor = {
  type: "text" | "section" | "missing";
  section: "title" | "abstract" | "claims" | "description" | "drawing_description" | "unknown";
  start?: number | null;
  end?: number | null;
  snippet?: string | null;
};

export type DraftReviewIssue = {
  id: string;
  kind: "blocking" | "hit" | "suggestion";
  severity: "critical" | "high" | "medium" | "low";
  source: string;
  message: string;
  snippet?: string | null;
  target_section: DraftIssueAnchor["section"];
  anchor: DraftIssueAnchor;
  status: "open" | "fixed" | "skipped" | "stale" | "unanchored";
};

export type PostDraftRepairSession = {
  project_id: string;
  review_run_id: string;
  draft_package_hash?: string | null;
  current_draft_hash?: string | null;
  stale: boolean;
  issues: DraftReviewIssue[];
  sections: Record<string, string>;
};

export interface CorpusQualityReport {
  total_files: number;
  processed_files: number;
  imported_documents: number;
  duplicate_documents: number;
  filtered_documents: number;
  failed_documents: number;
  indexed_chunks: number;
  fulltext_extractable_rate: number;
  section_coverage: Record<string, number>;
  low_quality_documents: string[];
  failures: Array<{ file: string; reason: string }>;
}

export interface CorpusImportJob {
  id: string;
  source_type: string;
  source_name: string;
  query: string;
  domain: string;
  version_name: string;
  status: "queued" | "running" | "completed" | "failed";
  input_paths: string[];
  total_files: number;
  processed_files: number;
  imported_documents: number;
  duplicate_documents: number;
  filtered_documents: number;
  failed_documents: number;
  errors: string[];
  quality_report: CorpusQualityReport | null;
}

export interface CorpusVersion {
  id: string;
  name: string;
  domain: string;
  source_type: string;
  source_name: string;
  query: string;
  document_count: number;
  chunk_count: number;
  quality_report: CorpusQualityReport | null;
}

export interface CorpusStats {
  version_name: string | null;
  document_count: number;
  chunk_count: number;
  document_ids: string[];
  section_coverage: Record<string, number>;
  ipc_distribution: Record<string, number>;
  application_year_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
}

export async function getHealth(): Promise<Health> {
  return request<Health>("/api/health");
}

export async function getDesktopConfig(): Promise<DesktopConfigView> {
  return request<DesktopConfigView>("/api/desktop-config");
}

export async function updateDesktopConfig(
  payload: DesktopConfigUpdatePayload,
): Promise<DesktopConfigView> {
  return request<DesktopConfigView>("/api/desktop-config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function clearDesktopConfigKey(): Promise<DesktopConfigView> {
  return request<DesktopConfigView>("/api/desktop-config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clear_api_key: true }),
  });
}

export async function checkDesktopConfigHealth(): Promise<DesktopConfigHealthResult> {
  return request<DesktopConfigHealthResult>("/api/desktop-config/health", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function getAgentDoctor(): Promise<AgentDoctorReport> {
  return request<AgentDoctorReport>("/api/agents/doctor");
}

export async function listCorpus(): Promise<PatentDocument[]> {
  const data = await request<{ documents: PatentDocument[] }>("/api/corpus");
  return data.documents;
}

export async function createCorpusJob(payload: {
  source_type: string;
  source_name: string;
  query: string;
  domain: string;
  version_name: string;
}): Promise<CorpusImportJob> {
  return request<CorpusImportJob>("/api/corpus/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadCorpusJobFile(jobId: string, file: File): Promise<{ job: CorpusImportJob; file_count: number }> {
  const form = new FormData();
  form.append("file", file);
  return request<{ job: CorpusImportJob; file_count: number }>(`/api/corpus/jobs/${jobId}/files`, {
    method: "POST",
    body: form,
  });
}

export async function runCorpusJob(jobId: string): Promise<CorpusImportJob> {
  return request<CorpusImportJob>(`/api/corpus/jobs/${jobId}/run`, { method: "POST" });
}

export async function getCorpusJob(jobId: string): Promise<CorpusImportJob> {
  return request<CorpusImportJob>(`/api/corpus/jobs/${jobId}`);
}

export async function listCorpusVersions(): Promise<CorpusVersion[]> {
  const data = await request<{ versions: CorpusVersion[] }>("/api/corpus/versions");
  return data.versions;
}

export async function getCorpusStats(version?: string): Promise<CorpusStats> {
  const params = new URLSearchParams();
  if (version) params.set("version", version);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<CorpusStats>(`/api/corpus/stats${suffix}`);
}

export async function getCorpusDocument(documentId: string): Promise<PatentDocument> {
  return request<PatentDocument>(`/api/corpus/documents/${documentId}`);
}

export async function importPatent(file: File): Promise<{ document: PatentDocument; chunks_count: number }> {
  const form = new FormData();
  form.append("file", file);
  return request<{ document: PatentDocument; chunks_count: number }>("/api/corpus/import", { method: "POST", body: form });
}

export async function searchCorpus(q: string, sectionType: SectionType | "", version?: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q });
  if (sectionType) params.set("section_type", sectionType);
  if (version) params.set("version", version);
  const data = await request<{ results: SearchResult[] }>(`/api/corpus/search?${params.toString()}`);
  return data.results;
}

export async function listProjects(): Promise<ProjectRecord[]> {
  const data = await request<{ projects: ProjectRecord[] }>("/api/projects");
  return data.projects;
}

export async function createProject(
  name: string,
  draftText: string,
  patentType: PatentType = PATENT_TYPE_INVENTION,
  metadata?: Partial<ProjectUpdate>,
): Promise<ProjectRecord> {
  const body: Record<string, unknown> = {
    name,
    draft_text: draftText,
    patent_type: patentType,
  };
  if (metadata) {
    for (const [key, value] of Object.entries(metadata)) {
      if (value !== undefined && value !== "") {
        body[key] = value;
      }
    }
  }
  return request<ProjectRecord>("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function updateProject(
  projectId: string,
  updates: ProjectUpdate,
): Promise<ProjectRecord> {
  return request<ProjectRecord>(`/api/projects/${projectId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}

export async function deleteProject(projectId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}`, { method: "DELETE" });
}

export async function uploadProjectMaterial(projectId: string, file: File): Promise<ProjectMaterial> {
  const form = new FormData();
  form.append("file", file);
  try {
    return await request<ProjectMaterial>(
      `/api/projects/${projectId}/materials`,
      { method: "POST", body: form },
      { fetchFailureMessage: "无法读取该文件，请检查文件权限或重新选择可读文件。" },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const uploadDetail = message.match(/返回 (?:415|422)：(.+)$/);
    if (uploadDetail?.[1]) {
      throw new Error(`材料上传失败：${uploadDetail[1]}`);
    }
    throw err;
  }
}

export async function listProjectMaterials(projectId: string): Promise<ProjectMaterial[]> {
  const data = await request<{ materials: ProjectMaterial[] }>(`/api/projects/${projectId}/materials`);
  return data.materials;
}

export async function createExternalDraftSource(
  projectId: string,
  payload: { source_type: ExternalDraftSourceType; text: string; file_name?: string; file_content?: string },
): Promise<ExternalDraftSource> {
  return request<ExternalDraftSource>(`/api/projects/${projectId}/external-drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadExternalDraftSource(projectId: string, file: File): Promise<ExternalDraftSource> {
  const form = new FormData();
  form.append("file", file);
  return request<ExternalDraftSource>(`/api/projects/${projectId}/external-drafts/upload`, {
    method: "POST",
    body: form,
  });
}

export async function listExternalDraftSources(projectId: string): Promise<ExternalDraftSource[]> {
  const data = await request<{ sources: ExternalDraftSource[] }>(`/api/projects/${projectId}/external-drafts`);
  return data.sources;
}

export async function startExternalDraftIntakeRun(
  projectId: string,
  sourceId: string,
): Promise<ExternalDraftIntakeRun> {
  return request<ExternalDraftIntakeRun>(`/api/projects/${projectId}/external-drafts/${sourceId}/intake-runs`, {
    method: "POST",
  });
}

export async function listExternalDraftIntakeRuns(
  projectId: string,
  sourceId: string,
): Promise<ExternalDraftIntakeRun[]> {
  const data = await request<{ runs: ExternalDraftIntakeRun[] }>(
    `/api/projects/${projectId}/external-drafts/${sourceId}/intake-runs`,
  );
  return data.runs;
}

export async function confirmExternalDraftIntakeRun(
  projectId: string,
  runId: string,
  payload: Pick<DraftPackage, "title" | "abstract" | "claims" | "description" | "drawing_description">,
): Promise<ExternalDraftIntakeRun> {
  return request<ExternalDraftIntakeRun>(`/api/projects/${projectId}/external-draft-intake-runs/${runId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function externalDraftReviewBundleReportUrl(projectId: string): string {
  return `/api/projects/${projectId}/external-draft-review-bundle/report.md`;
}

export async function listProjectPatentPoints(projectId: string): Promise<PatentPointCandidate[]> {
  const data = await request<{ points: PatentPointCandidate[] }>(`/api/projects/${projectId}/patent-points`);
  return data.points;
}

export async function createProjectPatentPoint(
  projectId: string,
  payload: PatentPointCreatePayload,
): Promise<PatentPointCandidate> {
  return request<PatentPointCandidate>(`/api/projects/${projectId}/patent-points`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateProjectPatentPoint(
  projectId: string,
  pointId: string,
  payload: Partial<PatentPointCreatePayload>,
): Promise<PatentPointCandidate> {
  return request<PatentPointCandidate>(`/api/projects/${projectId}/patent-points/${pointId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteProjectPatentPoint(projectId: string, pointId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/projects/${projectId}/patent-points/${pointId}`, { method: "DELETE" });
}

export async function evaluateProjectPatentPointMoat(
  projectId: string,
  pointId: string,
): Promise<PatentPointCandidate> {
  return request<PatentPointCandidate>(
    `/api/projects/${projectId}/patent-points/${pointId}/evaluate-moat`,
    { method: "POST" },
  );
}

export type DisclosureResearchMode = "standard" | "free_deep_research";

export async function startProjectDisclosure(
  projectId: string,
  trace = false,
  researchMode: DisclosureResearchMode = "standard",
): Promise<DisclosureRun> {
  return request<DisclosureRun>(`/api/projects/${projectId}/disclosures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace, max_prior_art_results: 8, research_mode: researchMode }),
  });
}

export async function listProjectDisclosures(projectId: string): Promise<DisclosureRun[]> {
  const data = await request<{ runs: DisclosureRun[] }>(`/api/projects/${projectId}/disclosures`);
  return data.runs;
}

export async function cancelProjectDisclosure(projectId: string, runId: string): Promise<DisclosureRun> {
  return request<DisclosureRun>(`/api/projects/${projectId}/disclosures/${runId}/cancel`, { method: "POST" });
}

export async function retryProjectDisclosure(projectId: string, runId: string): Promise<DisclosureRun> {
  return request<DisclosureRun>(`/api/projects/${projectId}/disclosures/${runId}/retry`, { method: "POST" });
}

export async function generateProject(projectId: string, deliberationRunId?: string | null, formulaRunId?: string | null): Promise<DraftPackage> {
  return request<DraftPackage>(`/api/projects/${projectId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deliberation_run_id: deliberationRunId ?? null, formula_run_id: formulaRunId ?? null }),
  });
}

export async function reviewProject(projectId: string): Promise<DraftPackage> {
  return request<DraftPackage>(`/api/projects/${projectId}/review`, { method: "POST" });
}

export async function updateProjectDraftPackage(
  projectId: string,
  payload: DraftPackageManualUpdate,
): Promise<DraftPackage> {
  return request<DraftPackage>(`/api/projects/${projectId}/draft-package`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function createFilingReadinessReport(projectId: string): Promise<FilingReadinessReport> {
  return request<FilingReadinessReport>(`/api/projects/${projectId}/filing-readiness`, { method: "POST" });
}

export async function listFilingReadinessReports(
  projectId: string,
): Promise<{ reports: FilingReadinessReport[]; current_source_draft_hash: string }> {
  return request<{ reports: FilingReadinessReport[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/filing-readiness`,
  );
}

export function filingReadinessReportUrl(projectId: string, reportId: string): string {
  return `/api/projects/${projectId}/filing-readiness/${reportId}/export.md`;
}

export async function createGrantabilityReport(projectId: string): Promise<GrantabilityReport> {
  return request<GrantabilityReport>(`/api/projects/${projectId}/grantability-reports`, { method: "POST" });
}

export async function listGrantabilityReports(
  projectId: string,
): Promise<{ reports: GrantabilityReport[]; current_source_draft_hash: string }> {
  return request<{ reports: GrantabilityReport[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/grantability-reports`,
  );
}

export async function getGrantabilityReport(projectId: string, reportId: string): Promise<GrantabilityReport> {
  return request<GrantabilityReport>(`/api/projects/${projectId}/grantability-reports/${reportId}`);
}

export function grantabilityReportUrl(projectId: string, reportId: string): string {
  return `/api/projects/${projectId}/grantability-reports/${reportId}/export.md`;
}

export async function createClaimDefenseWorksheet(projectId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets`, { method: "POST" });
}

export async function listClaimDefenseWorksheets(
  projectId: string,
): Promise<{ worksheets: ClaimDefenseWorksheet[]; current_source_draft_hash: string }> {
  return request<{ worksheets: ClaimDefenseWorksheet[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/claim-defense-worksheets`,
  );
}

export async function getClaimDefenseWorksheet(projectId: string, worksheetId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets/${worksheetId}`);
}

export async function createDraftCompletionRun(projectId: string): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs`, { method: "POST" });
}

export async function listDraftCompletionRuns(
  projectId: string,
): Promise<{ runs: DraftCompletionRun[]; current_source_draft_hash: string }> {
  return request<{ runs: DraftCompletionRun[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/completion-runs`,
  );
}

export function draftCompletionReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/completion-runs/${runId}/report.md`;
}

export async function generateCompletionPatches(projectId: string, runId: string): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/generate`, {
    method: "POST",
  });
}

export async function acceptCompletionPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/${patchId}/accept`, {
    method: "POST",
  });
}

export async function acceptAllCompletionPatches(projectId: string, runId: string): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/accept-all`, {
    method: "POST",
  });
}

export async function rejectCompletionPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/${patchId}/reject`, {
    method: "POST",
  });
}

export async function improveProjectScore(
  projectId: string,
  payload: { max_rounds?: number; target_score?: number } = {},
): Promise<ScoreImprovementResult> {
  return request<ScoreImprovementResult>(`/api/projects/${projectId}/score-improvement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function clearProjectLlmCache(projectId: string): Promise<{ deleted: number }> {
  return request<{ deleted: number }>(`/api/projects/${projectId}/llm-cache/clear`, { method: "POST" });
}

export async function listProjectDeliberations(projectId: string): Promise<DeliberationRun[]> {
  const data = await request<{ runs: DeliberationRun[] }>(`/api/projects/${projectId}/deliberations`);
  return data.runs;
}

export async function cancelProjectDeliberation(projectId: string, runId: string): Promise<DeliberationRun> {
  return request<DeliberationRun>(`/api/projects/${projectId}/deliberations/${runId}/cancel`, { method: "POST" });
}

export async function retryProjectDeliberation(projectId: string, runId: string): Promise<DeliberationRun> {
  return request<DeliberationRun>(`/api/projects/${projectId}/deliberations/${runId}/retry`, { method: "POST" });
}

export async function getFormulaRequirement(projectId: string): Promise<FormulaNeedAssessment> {
  return request<FormulaNeedAssessment>(`/api/projects/${projectId}/formula-requirement`);
}

export async function startFormulaRun(projectId: string, providers?: string[]): Promise<FormulaRun> {
  return request<FormulaRun>(`/api/projects/${projectId}/formula-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ providers: providers ?? null }),
  });
}

export async function listFormulaRuns(projectId: string): Promise<FormulaRun[]> {
  const data = await request<{ runs: FormulaRun[] }>(`/api/projects/${projectId}/formula-runs`);
  return data.runs;
}

export async function cancelFormulaRun(projectId: string, runId: string): Promise<FormulaRun> {
  return request<FormulaRun>(`/api/projects/${projectId}/formula-runs/${runId}/cancel`, { method: "POST" });
}

export async function retryFormulaRun(projectId: string, runId: string): Promise<FormulaRun> {
  return request<FormulaRun>(`/api/projects/${projectId}/formula-runs/${runId}/retry`, { method: "POST" });
}

export function formulaMarkdownUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/formula-runs/${runId}/latex.md`;
}

export async function getExportReadiness(projectId: string): Promise<ExportReadiness> {
  return request<ExportReadiness>(`/api/projects/${projectId}/export-readiness`);
}

export async function startOfficialCompileRun(projectId: string): Promise<OfficialCompileRun> {
  return request<OfficialCompileRun>(`/api/projects/${projectId}/official-compile-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function startKimiOfficialLanguagePolish(projectId: string, runId: string): Promise<OfficialCompileRun> {
  return request<OfficialCompileRun>(`/api/projects/${projectId}/official-compile-runs/${runId}/kimi-language-polish`, {
    method: "POST",
  });
}

export async function listOfficialCompileRuns(
  projectId: string,
): Promise<{ runs: OfficialCompileRun[]; current_source_draft_hash: string }> {
  return request<{ runs: OfficialCompileRun[]; current_source_draft_hash: string }>(
    `/api/projects/${projectId}/official-compile-runs`,
  );
}

export function officialCompileReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/official-compile-runs/${runId}/report.md`;
}

export async function applyOfficialCompileCleanup(
  projectId: string,
  runId: string,
): Promise<OfficialCompileCleanupResult> {
  return request<OfficialCompileCleanupResult>(
    `/api/projects/${projectId}/official-compile-runs/${runId}/apply-cleanup`,
    { method: "POST" },
  );
}

export async function listRevisionLedger(projectId: string): Promise<RevisionLedgerRecord[]> {
  return request<RevisionLedgerRecord[]>(`/api/projects/${projectId}/revision-ledger`);
}

export async function startPostDraftReview(
  projectId: string,
  providers?: string[],
  participantProviders?: string[],
): Promise<PostDraftReviewRun> {
  return request<PostDraftReviewRun>(`/api/projects/${projectId}/post-draft-reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ providers: providers ?? null, participant_providers: participantProviders ?? null }),
  });
}

export async function listPostDraftReviews(projectId: string): Promise<{ runs: PostDraftReviewRun[]; current_draft_hash: string }> {
  return request<{ runs: PostDraftReviewRun[]; current_draft_hash: string }>(`/api/projects/${projectId}/post-draft-reviews`);
}

export async function applyPostDraftSafePatches(
  projectId: string,
  runId: string,
): Promise<PostDraftSafePatchApplyResult> {
  return request<PostDraftSafePatchApplyResult>(
    `/api/projects/${projectId}/post-draft-reviews/${runId}/apply-safe-patches`,
    { method: "POST" },
  );
}

export async function getPostDraftRepairSession(
  projectId: string,
  runId: string,
): Promise<PostDraftRepairSession> {
  return request<PostDraftRepairSession>(
    `/api/projects/${projectId}/post-draft-reviews/${runId}/repair-session`,
  );
}

export type DraftRepairPatch = {
  id: string;
  issue_id: string;
  project_id: string;
  review_run_id: string;
  status: "proposed" | "stale" | "unsafe" | "applied";
  target_section: "title" | "abstract" | "claims" | "description" | "drawing_description";
  original: string;
  patched: string;
  diff_summary: string;
  risk_notes: string[];
  draft_package_hash: string;
};

export async function createDraftRepairPatch(
  projectId: string,
  runId: string,
  payload: {
    issue_id: string;
    draft_package_hash: string;
    target_section: DraftRepairPatch["target_section"];
    selected_text?: string | null;
    nearby_context?: string | null;
  },
): Promise<DraftRepairPatch> {
  return request<DraftRepairPatch>(
    `/api/projects/${projectId}/post-draft-reviews/${runId}/repair-patches`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function applyDraftRepairPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<{ package: DraftPackage; current_draft_hash: string }> {
  return request<{ package: DraftPackage; current_draft_hash: string }>(
    `/api/projects/${projectId}/post-draft-reviews/${runId}/repair-patches/${patchId}/apply`,
    { method: "POST" },
  );
}

export async function cancelPostDraftReview(projectId: string, runId: string): Promise<PostDraftReviewRun> {
  return request<PostDraftReviewRun>(`/api/projects/${projectId}/post-draft-reviews/${runId}/cancel`, { method: "POST" });
}

export async function retryPostDraftReview(projectId: string, runId: string): Promise<PostDraftReviewRun> {
  return request<PostDraftReviewRun>(`/api/projects/${projectId}/post-draft-reviews/${runId}/retry`, { method: "POST" });
}

export function postDraftReviewReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/post-draft-reviews/${runId}/report.md`;
}

export async function startProjectDeliberation(
  projectId: string,
  trace = false,
  providers?: string[],
  participantProviders?: string[],
): Promise<DeliberationRun> {
  return request<DeliberationRun>(`/api/projects/${projectId}/deliberations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trace,
      round_depth: "converged_two_round",
      providers: providers ?? null,
      participant_providers: participantProviders ?? null,
    }),
  });
}

export function exportUrl(projectId: string, kind: "docx" | "md" | "mmd" | "prompt"): string {
  if (kind === "docx") return `/api/projects/${projectId}/export.docx`;
  if (kind === "md") return `/api/projects/${projectId}/export.md`;
  if (kind === "mmd") return `/api/projects/${projectId}/diagram.mmd`;
  return `/api/projects/${projectId}/image-prompt.md`;
}

export function officialExportUrl(projectId: string, kind: "docx" | "md"): string {
  return kind === "docx" ? `/api/projects/${projectId}/official-export.docx` : `/api/projects/${projectId}/official-export.md`;
}

export function disclosureExportUrl(
  projectId: string,
  runId: string,
  kind: "docx" | "md" | "mmd" | "prompt" | "sidecar",
): string {
  if (kind === "docx") return `/api/projects/${projectId}/disclosures/${runId}/export.docx`;
  if (kind === "md") return `/api/projects/${projectId}/disclosures/${runId}/export.md`;
  if (kind === "sidecar") return `/api/projects/${projectId}/disclosures/${runId}/sidecar.md`;
  if (kind === "mmd") return `/api/projects/${projectId}/disclosures/${runId}/diagram.mmd`;
  return `/api/projects/${projectId}/disclosures/${runId}/image-prompt.md`;
}

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

type TauriGlobal = {
  __TAURI__?: {
    core?: {
      invoke?: TauriInvoke;
    };
  };
};

let tauriBackendBaseUrlPromise: Promise<string | null> | null = null;

function getTauriInvoke(): TauriInvoke | null {
  const maybeWindow = globalThis as typeof globalThis & TauriGlobal;
  return maybeWindow.__TAURI__?.core?.invoke ?? null;
}

async function getTauriBackendBaseUrl(): Promise<string | null> {
  const invoke = getTauriInvoke();
  if (!invoke) return null;
  if (!tauriBackendBaseUrlPromise) {
    tauriBackendBaseUrlPromise = invoke<string>("get_backend_base_url")
      .then((baseUrl: string) => baseUrl.replace(/\/+$/, ""))
      .catch(() => null);
  }
  return tauriBackendBaseUrlPromise;
}

async function resolveApiUrl(url: string): Promise<string> {
  if (!url.startsWith("/api/")) return url;
  const backendBaseUrl = await getTauriBackendBaseUrl();
  return backendBaseUrl ? `${backendBaseUrl}${url}` : url;
}

async function request<T>(url: string, init?: RequestInit, options?: { fetchFailureMessage?: string }): Promise<T> {
  const method = init?.method ?? "GET";
  const resolvedUrl = await resolveApiUrl(url);
  let response: Response;
  try {
    response = await fetch(resolvedUrl, init);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (options?.fetchFailureMessage) {
      throw new Error(options.fetchFailureMessage);
    }
    throw new Error(`${method} ${url} 请求失败：${message}`);
  }
  return parseResponse<T>(response, url, method);
}

async function parseResponse<T>(response: Response, url: string, method: string): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const contentType = response.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        detail = data.detail ?? detail;
      } else {
        detail = await response.text();
      }
    } catch {
      detail = response.statusText;
    }
    throw new Error(`${method} ${url} 返回 ${response.status}：${detail}`);
  }
  return response.json() as Promise<T>;
}
