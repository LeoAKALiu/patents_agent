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

export interface FeatureRecord {
  feature_id: string;
  text: string;
  classification: FeatureClassification;
  claim_refs: string[];
  description_refs: string[];
  figure_refs: string[];
  prior_art_refs: string[];
  risk_tags: string[];
}

export interface ClaimDefenseWorksheet {
  id: string;
  project_id: string;
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
  evidence_status: EvidenceStatus;
  risk_tags: string[];
  completion_status: "supported" | "partial" | "missing";
}

export interface DraftCompletionRun {
  id: string;
  project_id: string;
  snapshot_hash: string;
  status: "completed" | "failed";
  issues: CompletionIssue[];
  tasks: CompletionTask[];
  patches: ProposedPatch[];
  support_matrix: ClaimSupportMatrixRow[];
  scorecard: CompletionScoreCard;
  notes: string[];
  created_at: string;
}

export interface ProjectRecord {
  id: string;
  name: string;
  draft_text: string;
  package: DraftPackage | null;
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
  claim_chart: ClaimChartItem[];
  selected: boolean;
}

export interface PatentPointCreatePayload {
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
}

export interface Health {
  ok: boolean;
  llm_configured: boolean;
  data_dir: string;
  model: string;
  embedding_model: string;
}

export interface AgentProviderStatus {
  id: string;
  label: string;
  command: string;
  available: boolean;
  path: string;
  required: boolean;
}

export interface AgentDoctorReport {
  status: "ready" | "degraded" | "blocked";
  run_mode: "full" | "partial" | "minimal" | "blocked";
  commands: Record<string, AgentProviderStatus>;
  active_provider_ids: string[];
  missing_required: string[];
  missing_optional: string[];
}

export interface DeliberationRun {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "interrupted";
  providers: string[];
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
}

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
  const response = await fetch(`/api/corpus/jobs/${jobId}/files`, { method: "POST", body: form });
  return parseResponse(response);
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
  const response = await fetch("/api/corpus/import", { method: "POST", body: form });
  return parseResponse(response);
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

export async function createProject(name: string, draftText: string): Promise<ProjectRecord> {
  return request<ProjectRecord>("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, draft_text: draftText }),
  });
}

export async function uploadProjectMaterial(projectId: string, file: File): Promise<ProjectMaterial> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`/api/projects/${projectId}/materials`, { method: "POST", body: form });
  return parseResponse(response);
}

export async function listProjectMaterials(projectId: string): Promise<ProjectMaterial[]> {
  const data = await request<{ materials: ProjectMaterial[] }>(`/api/projects/${projectId}/materials`);
  return data.materials;
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

export async function startProjectDisclosure(projectId: string, trace = false): Promise<DisclosureRun> {
  return request<DisclosureRun>(`/api/projects/${projectId}/disclosures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace, max_prior_art_results: 8 }),
  });
}

export async function listProjectDisclosures(projectId: string): Promise<DisclosureRun[]> {
  const data = await request<{ runs: DisclosureRun[] }>(`/api/projects/${projectId}/disclosures`);
  return data.runs;
}

export async function generateProject(projectId: string, deliberationRunId?: string | null): Promise<DraftPackage> {
  return request<DraftPackage>(`/api/projects/${projectId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deliberation_run_id: deliberationRunId ?? null }),
  });
}

export async function reviewProject(projectId: string): Promise<DraftPackage> {
  return request<DraftPackage>(`/api/projects/${projectId}/review`, { method: "POST" });
}

export async function createFilingReadinessReport(projectId: string): Promise<FilingReadinessReport> {
  return request<FilingReadinessReport>(`/api/projects/${projectId}/filing-readiness`, { method: "POST" });
}

export async function listFilingReadinessReports(projectId: string): Promise<FilingReadinessReport[]> {
  const data = await request<{ reports: FilingReadinessReport[] }>(`/api/projects/${projectId}/filing-readiness`);
  return data.reports;
}

export function filingReadinessReportUrl(projectId: string, reportId: string): string {
  return `/api/projects/${projectId}/filing-readiness/${reportId}/export.md`;
}

export async function createClaimDefenseWorksheet(projectId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets`, { method: "POST" });
}

export async function listClaimDefenseWorksheets(projectId: string): Promise<ClaimDefenseWorksheet[]> {
  const data = await request<{ worksheets: ClaimDefenseWorksheet[] }>(
    `/api/projects/${projectId}/claim-defense-worksheets`,
  );
  return data.worksheets;
}

export async function getClaimDefenseWorksheet(projectId: string, worksheetId: string): Promise<ClaimDefenseWorksheet> {
  return request<ClaimDefenseWorksheet>(`/api/projects/${projectId}/claim-defense-worksheets/${worksheetId}`);
}

export async function createDraftCompletionRun(projectId: string): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs`, { method: "POST" });
}

export async function listDraftCompletionRuns(projectId: string): Promise<DraftCompletionRun[]> {
  const data = await request<{ runs: DraftCompletionRun[] }>(`/api/projects/${projectId}/completion-runs`);
  return data.runs;
}

export function draftCompletionReportUrl(projectId: string, runId: string): string {
  return `/api/projects/${projectId}/completion-runs/${runId}/report.md`;
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

export async function rejectCompletionPatch(
  projectId: string,
  runId: string,
  patchId: string,
): Promise<DraftCompletionRun> {
  return request<DraftCompletionRun>(`/api/projects/${projectId}/completion-runs/${runId}/patches/${patchId}/reject`, {
    method: "POST",
  });
}

export async function listProjectDeliberations(projectId: string): Promise<DeliberationRun[]> {
  const data = await request<{ runs: DeliberationRun[] }>(`/api/projects/${projectId}/deliberations`);
  return data.runs;
}

export async function startProjectDeliberation(projectId: string, trace = false): Promise<DeliberationRun> {
  return request<DeliberationRun>(`/api/projects/${projectId}/deliberations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace, round_depth: "converged_two_round" }),
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
  kind: "docx" | "md" | "mmd" | "prompt",
): string {
  if (kind === "docx") return `/api/projects/${projectId}/disclosures/${runId}/export.docx`;
  if (kind === "md") return `/api/projects/${projectId}/disclosures/${runId}/export.md`;
  if (kind === "mmd") return `/api/projects/${projectId}/disclosures/${runId}/diagram.mmd`;
  return `/api/projects/${projectId}/disclosures/${runId}/image-prompt.md`;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
