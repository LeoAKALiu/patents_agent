import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileText,
  Gauge,
  Loader2,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Sigma,
  Upload,
  UsersRound,
  Wand2,
} from "lucide-react";

import {
  draftCompletionReportUrl,
  exportUrl,
  filingReadinessReportUrl,
  formulaMarkdownUrl,
  officialCompileReportUrl,
  officialExportUrl,
  postDraftReviewReportUrl,
  type AgentDoctorReport,
  type ClaimDefenseWorksheet,
  type DeliberationRun,
  type DisclosureRun,
  type DraftPackage,
  type DraftPackageManualUpdate,
  type DraftCompletionRun,
  type ExternalDraftIntakeRun,
  type ExternalDraftSource,
  type FilingReadinessReport,
  type FormulaNeedAssessment,
  type FormulaRun,
  type OfficialCompileRun,
  type PatentPointCandidate,
  type PostDraftReviewRun,
  type ProjectMaterial,
  type ProjectRecord,
  type RuntimeFailure,
  type RuntimeStageState,
} from "./api";
import {
  deriveGuidedFlowState,
  guidedProgressActionBlockReason,
  guidedOperationLog,
  guidedNextActionDescription,
  guidedProgressActionState,
  guidedStepStatusLabel,
  ideaPatentGoalModes,
  officialCompileActionGate,
  patentTypeOptions,
  postDraftReviewActionGate,
  qualityActionGate,
  qualitySummaryFromRuns,
  resolveGuidedViewStep,
  selectCurrentOfficialCompileRun,
  selectLatestOfficialCompileAttemptForSource,
  selectLatestMatchingPostDraftReview,
  selectLatestRepairablePostDraftReview,
  type GuidedActionGate,
  type GuidedFlowState,
  type GuidedProgressActionState,
  type GuidedStepId,
  type GuidedStepState,
  type PatentGoalMode,
  type PatentType,
  type StartChoiceId,
} from "./guidedFlow";
import {
  deliberationRunModeLabel,
  latestCompletedDeliberation,
  pipelineRunStatusLabel,
  sourceTypeLabel,
} from "./domain";
import { runtimeDisplayElapsedSeconds, useRuntimeNow } from "./runtimeDisplay";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
  type GuidedRuntimeRun,
} from "./flow/runtimeWidgets";
import {
  patentPointCandidatesFromDisclosureRun,
  evidenceStatusText,
} from "./flow/inventionSelectors";
import { GuidedScoreTile, ActionGateHint } from "./flow/parts";
import {
  DraftGenerationPanel,
  FormulaPanel,
  DeliberationPanel,
  QualityPanel,
  OfficialCompilePanel,
  PostDraftReviewPanel,
  ExportConfirmationPanel,
  IdeaIntakePanel,
  ExternalDraftIntakePanel,
  InventionPointConfirmation,
  MaterialSummary,
} from "./flow/panels";
import { Badge } from "@/components/ui/badge";


export type GuidedPatentFlowProps = {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  disclosures: DisclosureRun[];
  deliberations: DeliberationRun[];
  patentPoints: PatentPointCandidate[];
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRuns: FormulaRun[];
  officialCompileRuns: OfficialCompileRun[];
  currentSourceDraftHash: string;
  postDraftReviews: PostDraftReviewRun[];
  currentDraftHash: string;
  currentPackage: DraftPackage | null;
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
  busyElapsedSeconds?: number;
  fixedGoalMode?: PatentGoalMode;
  initialIntakeMode?: Extract<StartChoiceId, "external"> | "idea";
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
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
  disclosureResearchMode: "standard" | "free_deep_research";
  onChangeDisclosureResearchMode: (mode: "standard" | "free_deep_research") => void;
  onStartDisclosure: () => void;
  onCancelDisclosureRun: (runId: string) => void;
  onRetryDisclosureRun: (runId: string) => void;
  onSelectPatentPoint: (point: PatentPointCandidate, candidates: PatentPointCandidate[]) => void;
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
  onSaveDraftPackage: (payload: DraftPackageManualUpdate) => void;
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
  onOpenExpertTool: (
    tool: "materials" | "moat" | "deliberate" | "readiness" | "claimDefense" | "completion" | "export",
  ) => void;
};

export function GuidedPatentFlowView(props: GuidedPatentFlowProps) {
  const state = useMemo(
    () =>
      deriveGuidedFlowState({
        project: props.project,
        materials: props.materials,
        disclosures: props.disclosures,
        deliberations: props.deliberations,
        patentPoints: props.patentPoints,
        formulaRequirement: props.formulaRequirement,
        formulaRuns: props.formulaRuns,
        filingReports: props.filingReports,
        worksheets: props.worksheets,
        completionRuns: props.completionRuns,
        externalDraftSources: props.externalDraftSources,
        externalDraftIntakeRuns: props.externalDraftIntakeRuns,
        officialCompileRuns: props.officialCompileRuns,
        currentSourceDraftHash: props.currentSourceDraftHash,
        postDraftReviews: props.postDraftReviews,
      }),
    [
      props.project,
      props.materials,
      props.disclosures,
      props.deliberations,
      props.patentPoints,
      props.formulaRequirement,
      props.formulaRuns,
      props.filingReports,
      props.worksheets,
      props.completionRuns,
      props.externalDraftSources,
      props.externalDraftIntakeRuns,
      props.officialCompileRuns,
      props.currentSourceDraftHash,
      props.postDraftReviews,
    ],
  );
  const latestDisclosure = props.disclosures.find((run) => run.status === "completed" && run.package) ?? null;
  const latestDeliberation = latestCompletedDeliberation(props.deliberations);
  const latestFormulaRun = props.formulaRuns.find((run) => run.status === "completed" && run.package) ?? null;
  const latestFilingReport = props.filingReports[0] ?? null;
  const latestWorksheet = props.worksheets[0] ?? null;
  const latestCompletionRun = props.completionRuns[0] ?? null;
  const latestOfficialCompileRun = selectCurrentOfficialCompileRun(
    props.officialCompileRuns,
    props.currentSourceDraftHash,
  );
  const displayOfficialCompileRun = latestOfficialCompileRun
    ?? selectLatestOfficialCompileAttemptForSource(props.officialCompileRuns, props.currentSourceDraftHash);
  const latestMatchingPostDraftReview = selectLatestMatchingPostDraftReview(
    props.postDraftReviews,
    latestOfficialCompileRun,
  );
  const latestRepairablePostDraftReview = selectLatestRepairablePostDraftReview(
    props.postDraftReviews,
    props.currentSourceDraftHash,
  );
  const [manualViewStepId, setManualViewStepId] = useState<GuidedStepId | null>(null);

  useEffect(() => {
    setManualViewStepId(null);
  }, [state.currentStepId]);

  const displayedStepId = resolveGuidedViewStep(
    state.currentStepId,
    manualViewStepId,
    state.steps,
    props.initialIntakeMode,
    state.hasCompletedExternalDraftIntake || state.draftReady,
  );
  const completedStepCount = state.steps.filter((step) => step.status === "done").length;
  const progressActionBlockReason = guidedProgressActionBlockReason({
    currentStepId: state.currentStepId,
    selectedDeliberationProviders: props.selectedDeliberationProviders,
  });
  const progressAction = guidedProgressActionState({
    busy: props.busy,
    currentStepId: state.currentStepId,
    displayedStepId,
    actionBlockReason: progressActionBlockReason,
  });

  function handleNextAction(): void {
    if (progressAction.disabled) {
      return;
    }
    if (progressAction.kind === "return") {
      setManualViewStepId(null);
      return;
    }
    setManualViewStepId(null);
    if (state.currentStepId === "invention") {
      props.onStartDisclosure();
    } else if (state.currentStepId === "deliberation") {
      props.onStartDeliberation();
    } else if (state.currentStepId === "formula") {
      props.onStartFormula();
    } else if (state.currentStepId === "draft") {
      props.onGenerateDraft();
    } else if (state.currentStepId === "quality") {
      props.onRunQualityChecks();
    } else if (state.currentStepId === "officialCompile") {
      props.onStartOfficialCompile();
    } else if (state.currentStepId === "postReview") {
      props.onStartPostDraftReview();
    } else if (state.currentStepId === "export") {
      props.onOpenExpertTool("export");
    }
  }

  return (
    <div className="guided-flow">
      <WorkflowStepper
        displayedStepId={displayedStepId}
        onSelectStep={setManualViewStepId}
        state={state}
      />
      <GuidedProgressBanner
        action={progressAction}
        busy={props.busy}
        completedStepCount={completedStepCount}
        currentStepId={state.currentStepId}
        displayedStepId={displayedStepId}
        onNext={handleNextAction}
        totalStepCount={state.steps.length}
      />
      {displayedStepId === "idea" && (
        <IdeaIntakePanel
          project={props.project}
          materials={props.materials}
          externalDraftSources={props.externalDraftSources}
          externalDraftIntakeRuns={props.externalDraftIntakeRuns}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          fixedGoalMode={props.fixedGoalMode}
          initialIntakeMode={props.initialIntakeMode}
          onCreateIdeaProject={props.onCreateIdeaProject}
          onCreateExternalDraft={props.onCreateExternalDraft}
          onUploadExternalDraft={props.onUploadExternalDraft}
          onStartExternalDraftIntake={props.onStartExternalDraftIntake}
          onConfirmExternalDraftIntake={props.onConfirmExternalDraftIntake}
          onUploadMaterial={props.onUploadMaterial}
        />
      )}
      {displayedStepId === "invention" && (
        <InventionPointConfirmation
          project={props.project}
          disclosure={latestDisclosure}
          disclosureRuns={props.disclosures}
          materials={props.materials}
          patentPoints={props.patentPoints}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          researchMode={props.disclosureResearchMode}
          onChangeResearchMode={props.onChangeDisclosureResearchMode}
          onUploadMaterial={props.onUploadMaterial}
          onStartDisclosure={props.onStartDisclosure}
          onCancelRun={props.onCancelDisclosureRun}
          onRetryRun={props.onRetryDisclosureRun}
          onSelectPatentPoint={props.onSelectPatentPoint}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {displayedStepId === "draft" && (
        <DraftGenerationPanel
          project={props.project}
          disclosure={latestDisclosure}
          deliberation={latestDeliberation}
          formulaRequirement={props.formulaRequirement}
          formulaRun={latestFormulaRun}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onGenerateDraft={props.onGenerateDraft}
        />
      )}
      {displayedStepId === "deliberation" && (
        <DeliberationPanel
          deliberation={latestDeliberation}
          runs={props.deliberations}
          doctor={props.agentDoctor}
          selectedProviders={props.selectedDeliberationProviders}
          participantProviders={props.selectedDeliberationParticipantProviders}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartDeliberation={props.onStartDeliberation}
          onCancelRun={props.onCancelDeliberationRun}
          onRetryRun={props.onRetryDeliberationRun}
          onToggleProvider={props.onToggleDeliberationProvider}
          onToggleParticipantProvider={props.onToggleDeliberationParticipantProvider}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {displayedStepId === "formula" && (
        <FormulaPanel
          project={props.project}
          requirement={props.formulaRequirement}
          formulaRun={latestFormulaRun}
          runs={props.formulaRuns}
          doctor={props.agentDoctor}
          selectedProviders={props.selectedFormulaProviders}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartFormula={props.onStartFormula}
          onCancelRun={props.onCancelFormulaRun}
          onRetryRun={props.onRetryFormulaRun}
          onToggleProvider={props.onToggleFormulaProvider}
        />
      )}
      {displayedStepId === "quality" && (
        <QualityPanel
          actionGate={qualityActionGate(state, state.currentStepId, displayedStepId)}
          filingReport={latestFilingReport}
          worksheet={latestWorksheet}
          completionRun={latestCompletionRun}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onRunQualityChecks={props.onRunQualityChecks}
          onImproveScore={props.onImproveScore}
          onAcceptPatch={props.onAcceptPatch}
          onAcceptAllPatches={props.onAcceptAllPatches}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {displayedStepId === "officialCompile" && (
        <OfficialCompilePanel
          actionGate={officialCompileActionGate(state, state.currentStepId, displayedStepId)}
          project={props.project}
          run={displayOfficialCompileRun}
          runs={props.officialCompileRuns}
          currentSourceDraftHash={props.currentSourceDraftHash}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartOfficialCompile={props.onStartOfficialCompile}
          onApplyCleanup={props.onApplyOfficialCompileCleanup}
        />
      )}
      {displayedStepId === "postReview" && (
        <PostDraftReviewPanel
          actionGate={postDraftReviewActionGate(state, state.currentStepId, displayedStepId)}
          project={props.project}
          review={latestMatchingPostDraftReview}
          repairReview={latestRepairablePostDraftReview}
          runs={props.postDraftReviews}
          currentDraftHash={props.currentDraftHash}
          currentPackage={props.currentPackage}
          officialCompileRun={latestOfficialCompileRun}
          doctor={props.agentDoctor}
          selectedProviders={props.selectedDeliberationProviders}
          participantProviders={props.selectedDeliberationParticipantProviders}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartPostDraftReview={props.onStartPostDraftReview}
          onStartKimiLanguagePolish={props.onStartKimiLanguagePolish}
          onApplySafePatches={props.onApplyPostDraftSafePatches}
          onSaveDraftPackage={props.onSaveDraftPackage}
          onCancelRun={props.onCancelPostDraftReviewRun}
          onRetryRun={props.onRetryPostDraftReviewRun}
          onToggleProvider={props.onToggleDeliberationProvider}
          onToggleParticipantProvider={props.onToggleDeliberationParticipantProvider}
        />
      )}
      {displayedStepId === "export" && (
        <ExportConfirmationPanel
          project={props.project}
          filingReport={latestFilingReport}
          completionRun={latestCompletionRun}
          postDraftReview={latestMatchingPostDraftReview}
          currentSourceDraftHash={props.currentSourceDraftHash}
          officialCompileRun={latestOfficialCompileRun}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
    </div>
  );
}

function GuidedProgressBanner({
  action,
  busy,
  completedStepCount,
  currentStepId,
  displayedStepId,
  onNext,
  totalStepCount,
}: {
  action: GuidedProgressActionState;
  busy: string;
  completedStepCount: number;
  currentStepId: GuidedStepId;
  displayedStepId: GuidedStepId;
  onNext: () => void;
  totalStepCount: number;
}) {
  const percent = Math.round((completedStepCount / totalStepCount) * 100);
  const actionIsFormOnly = action.disabled && currentStepId === "idea" && displayedStepId === currentStepId;
  return (
    <section className="guided-progress-banner" aria-label="流程进度和下一步">
      <div className="guided-progress-copy">
        <Badge variant="success" className="text-xs">{completedStepCount}/{totalStepCount} 已完成</Badge>
        <div>
          <h3>当前进度：{percent}%</h3>
          <p>{guidedNextActionDescription(currentStepId)}</p>
        </div>
      </div>
      <div className="guided-progress-meter" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>
      <span
        className="guided-progress-action-wrap"
        title={action.title}
      >
        <button
          aria-label={action.label}
          className="btn btn-primary"
          disabled={action.disabled}
          onClick={onNext}
          title={action.title}
          type="button"
        >
          {busy ? <Loader2 className="spin" size={17} /> : action.kind === "return" ? <RefreshCw size={17} /> : <PlayCircle size={17} />}
          <span>{action.label}</span>
        </button>
      </span>
      {actionIsFormOnly && (
        <div className="callout guided-progress-callout">
          <AlertTriangle size={17} aria-hidden="true" />
          <div>
            <strong>等待首 Mile 输入</strong>
            <p>请在下方表单中填写项目名称和技术方案，或返回三选一选择导入已有稿件。</p>
          </div>
        </div>
      )}
    </section>
  );
}

function WorkflowStepper({
  state,
  displayedStepId,
  onSelectStep,
}: {
  state: GuidedFlowState;
  displayedStepId: GuidedStepId;
  onSelectStep: (stepId: GuidedStepId) => void;
}) {
  return (
    <nav aria-label="专利生成流程" className="guided-stepper">
      {state.steps.map((step, index) => (
        <StepNavButton
          displayedStepId={displayedStepId}
          index={index}
          key={step.id}
          onSelectStep={onSelectStep}
          step={step}
        />
      ))}
    </nav>
  );
}

function StepNavButton({
  step,
  index,
  displayedStepId,
  onSelectStep,
}: {
  step: GuidedStepState;
  index: number;
  displayedStepId: GuidedStepId;
  onSelectStep: (stepId: GuidedStepId) => void;
}) {
  const locked = step.status === "locked";
  const isDisplayed = displayedStepId === step.id;
  const className = [
    "guided-step",
    step.status,
    isDisplayed ? "viewing" : "",
    step.status === "current" ? "workflow-current" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      aria-current={isDisplayed ? "step" : undefined}
      aria-disabled={locked || undefined}
      className={className}
      disabled={locked}
      onClick={() => onSelectStep(step.id)}
      title={locked ? "请先完成前置步骤" : step.description}
      type="button"
    >
      <span aria-hidden="true">{index + 1}</span>
      <div>
        <strong>{step.label}</strong>
        <p>{step.description}</p>
        <span className="guided-step-status">{guidedStepStatusLabel(step.status)}</span>
      </div>
    </button>
  );
}
