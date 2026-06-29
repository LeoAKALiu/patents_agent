import type { FormEvent } from "react";

import {
  ProjectSelect,
  ProjectsOverview,
  StartChoiceScreen,
  type ProjectListLoadStatus,
} from "@/views/projectViews";
import { GuidedPatentFlowView } from "@/GuidedPatentFlow";

import type {
  AgentDoctorReport,
  ClaimDefenseWorksheet,
  DeliberationRun,
  DisclosureRun,
  DraftCompletionRun,
  ExternalDraftIntakeRun,
  ExternalDraftSource,
  FilingReadinessReport,
  FormulaNeedAssessment,
  FormulaRun,
  OfficialCompileRun,
  PatentPointCandidate,
  PatentType,
  PostDraftReviewRun,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";
import type { PatentGoalMode, StartChoiceId } from "@/guidedFlow";

/**
 * State slice consumed by the "project" workspace: start choice, project
 * overview, and the guided patent flow. The workspace is presentational
 * — handlers are passed in from App.tsx.
 */
export interface ProjectWorkspaceState {
  startChoice: StartChoiceId | null;
  selectedProject: ProjectRecord | null;
  projects: ProjectRecord[];
  projectMaterials: ProjectMaterial[];
  disclosureRuns: DisclosureRun[];
  deliberationRuns: DeliberationRun[];
  visiblePatentPoints: PatentPointCandidate[];
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRuns: FormulaRun[];
  officialCompileRuns: OfficialCompileRun[];
  currentSourceDraftHash: string;
  postDraftReviews: PostDraftReviewRun[];
  currentDraftHash: string;
  currentPackage: ProjectRecord["package"];
  agentDoctor: AgentDoctorReport | null;
  selectedDeliberationProviders: string[];
  selectedDeliberationParticipantProviders: string[];
  selectedFormulaProviders: string[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
  externalDraftSources: ExternalDraftSource[];
  externalDraftIntakeRuns: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  disclosureResearchMode: "standard" | "free_deep_research";
}

export interface ProjectWorkspaceHandlers {
  onStartChoice: (choice: StartChoiceId) => void;
  onSelectProjectId: (projectId: string) => void;
  onDeleteProject: (project: ProjectRecord) => void;
  onCreateIdeaProject: (payload: {
    name: string;
    idea: string;
    mode: PatentGoalMode;
    patentType: PatentType;
    applicant?: string;
    inventors?: string;
    technical_field?: string;
    background?: string;
    pain_point?: string;
    technical_solution?: string;
    innovation?: string;
    embodiments?: string;
    beneficial_effects?: string;
  }) => Promise<void>;
  onCreateExternalDraft: (payload: { text: string; fileName: string }) => Promise<void>;
  onUploadExternalDraft: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onStartExternalDraftIntake: (sourceId: string) => Promise<void>;
  onConfirmExternalDraftIntake: (
    runId: string,
    payload: {
      title: string;
      abstract: string;
      claims: string;
      description: string;
      drawing_description: string;
    },
  ) => Promise<void>;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onChangeDisclosureResearchMode: (mode: "standard" | "free_deep_research") => void;
  onStartDisclosure: () => void;
  onCancelDisclosureRun: (runId: string) => void;
  onRetryDisclosureRun: (runId: string) => void;
  onSelectPatentPoint: (
    point: PatentPointCandidate,
    candidates: PatentPointCandidate[],
  ) => void;
  onStartDeliberation: () => void;
  onCancelDeliberationRun: (runId: string) => void;
  onRetryDeliberationRun: (runId: string) => void;
  onStartFormula: () => void;
  onCancelFormulaRun: (runId: string) => void;
  onRetryFormulaRun: (runId: string) => void;
  onStartOfficialCompile: () => void;
  onStartKimiLanguagePolish: () => void;
  onStartPostDraftReview: () => void;
  onApplyOfficialCompileCleanup: (runId: string) => void;
  onApplyPostDraftSafePatches: (runId: string) => void;
  onSaveDraftPackage: (payload: {
    title: string;
    abstract: string;
    claims: string;
    description: string;
    drawing_description: string;
  }) => void;
  onDraftRepairPatchApplied?: (issueId?: string) => void | Promise<void>;
  onCancelPostDraftReviewRun: (runId: string) => void;
  onRetryPostDraftReviewRun: (runId: string) => void;
  onToggleDeliberationProvider: (providerId: string, enabled: boolean) => void;
  onToggleDeliberationParticipantProvider: (providerId: string, enabled: boolean) => void;
  onToggleFormulaProvider: (providerId: string, enabled: boolean) => void;
  onGenerateDraft: () => void;
  onRunQualityChecks: () => void;
  onImproveScore: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onAcceptAllPatches: (runId: string) => void;
  onOpenExpertTool: (tool: string) => void;
}

export interface ProjectWorkspaceProps {
  /** Which main section is active; the workspace routes to the right view. */
  section: "generate" | "utility" | "projects";
  state: ProjectWorkspaceState;
  handlers: ProjectWorkspaceHandlers;
  loadStatus?: ProjectListLoadStatus;
  /**
   * Optional override for the fixed goal mode (utility vs invention). Set when
   * the user picked the "实用新型" start choice.
   */
  fixedGoalMode?: PatentGoalMode;
  /** Optional intake hint for the guided flow. */
  initialIntakeMode?: "idea" | "external";
}

/**
 * Decide which project sub-view to render based on the active
 * main section and the current state of the start-choice / selected-project
 * pair. This is the routing decision that App.tsx previously inlined.
 */
function pickProjectVariant(
  section: "generate" | "utility" | "projects",
  hasSelectedProject: boolean,
  hasStartChoice: boolean,
): "projects-overview" | "start-choice" | "guided" {
  if (section === "projects") return "projects-overview";
  if (!hasSelectedProject && !hasStartChoice) return "start-choice";
  return "guided";
}

/**
 * Renders the start-choice screen, project overview, or guided patent flow.
 * App.tsx routes to this component for the
 * "generate" / "utility" / "projects" sections.
 */
export function ProjectWorkspace({
  section,
  state,
  handlers,
  loadStatus = "idle",
  fixedGoalMode,
  initialIntakeMode,
}: ProjectWorkspaceProps) {
  const variant = pickProjectVariant(
    section,
    Boolean(state.selectedProject),
    Boolean(state.startChoice),
  );
  if (variant === "projects-overview") {
    return (
      <ProjectsOverview
        projects={state.projects}
        selectedProjectId={state.selectedProject?.id ?? ""}
        loadStatus={loadStatus}
        onSelect={handlers.onSelectProjectId}
        onDelete={(project) => void handlers.onDeleteProject(project)}
        busy={state.busy}
      />
    );
  }
  if (variant === "start-choice") {
    return <StartChoiceScreen onSelect={handlers.onStartChoice} />;
  }
  return (
    <GuidedPatentFlowView
      project={state.selectedProject}
      materials={state.projectMaterials}
      disclosures={state.disclosureRuns}
      deliberations={state.deliberationRuns}
      patentPoints={state.visiblePatentPoints}
      formulaRequirement={state.formulaRequirement}
      formulaRuns={state.formulaRuns}
      officialCompileRuns={state.officialCompileRuns}
      currentSourceDraftHash={state.currentSourceDraftHash}
      postDraftReviews={state.postDraftReviews}
      currentDraftHash={state.currentDraftHash}
      currentPackage={state.currentPackage}
      agentDoctor={state.agentDoctor}
      selectedDeliberationProviders={state.selectedDeliberationProviders}
      selectedDeliberationParticipantProviders={state.selectedDeliberationParticipantProviders}
      selectedFormulaProviders={state.selectedFormulaProviders}
      filingReports={state.filingReports}
      worksheets={state.worksheets}
      completionRuns={state.completionRuns}
      externalDraftSources={state.externalDraftSources}
      externalDraftIntakeRuns={state.externalDraftIntakeRuns}
      busy={state.busy}
      busyElapsedSeconds={state.busyElapsedSeconds}
      fixedGoalMode={fixedGoalMode}
      initialIntakeMode={initialIntakeMode}
      onCreateIdeaProject={handlers.onCreateIdeaProject}
      onCreateExternalDraft={handlers.onCreateExternalDraft}
      onUploadExternalDraft={handlers.onUploadExternalDraft}
      onStartExternalDraftIntake={handlers.onStartExternalDraftIntake}
      onConfirmExternalDraftIntake={handlers.onConfirmExternalDraftIntake}
      onUploadMaterial={handlers.onUploadMaterial}
      disclosureResearchMode={state.disclosureResearchMode}
      onChangeDisclosureResearchMode={handlers.onChangeDisclosureResearchMode}
      onStartDisclosure={handlers.onStartDisclosure}
      onCancelDisclosureRun={handlers.onCancelDisclosureRun}
      onRetryDisclosureRun={handlers.onRetryDisclosureRun}
      onSelectPatentPoint={handlers.onSelectPatentPoint}
      onStartDeliberation={handlers.onStartDeliberation}
      onCancelDeliberationRun={handlers.onCancelDeliberationRun}
      onRetryDeliberationRun={handlers.onRetryDeliberationRun}
      onStartFormula={handlers.onStartFormula}
      onCancelFormulaRun={handlers.onCancelFormulaRun}
      onRetryFormulaRun={handlers.onRetryFormulaRun}
      onStartOfficialCompile={handlers.onStartOfficialCompile}
      onStartKimiLanguagePolish={handlers.onStartKimiLanguagePolish}
      onStartPostDraftReview={handlers.onStartPostDraftReview}
      onApplyOfficialCompileCleanup={handlers.onApplyOfficialCompileCleanup}
      onApplyPostDraftSafePatches={handlers.onApplyPostDraftSafePatches}
      onSaveDraftPackage={handlers.onSaveDraftPackage}
      onCancelPostDraftReviewRun={handlers.onCancelPostDraftReviewRun}
      onRetryPostDraftReviewRun={handlers.onRetryPostDraftReviewRun}
      onToggleDeliberationProvider={handlers.onToggleDeliberationProvider}
      onToggleDeliberationParticipantProvider={handlers.onToggleDeliberationParticipantProvider}
      onToggleFormulaProvider={handlers.onToggleFormulaProvider}
      onGenerateDraft={handlers.onGenerateDraft}
      onRunQualityChecks={handlers.onRunQualityChecks}
      onImproveScore={handlers.onImproveScore}
      onAcceptPatch={handlers.onAcceptPatch}
      onAcceptAllPatches={handlers.onAcceptAllPatches}
      onOpenExpertTool={handlers.onOpenExpertTool}
    />
  );
}

/**
 * Project selector slot used in the topbar. Lives here because the project
 * feature owns the "selected project" concept that everything else keys off.
 */
export function ProjectSelectorSlot({
  projects,
  selectedProjectId,
  loadStatus = "idle",
  onSelect,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  loadStatus?: ProjectListLoadStatus;
  onSelect: (id: string) => void;
}) {
  return <ProjectSelect projects={projects} selectedProjectId={selectedProjectId} loadStatus={loadStatus} onChange={onSelect} />;
}
