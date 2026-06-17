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

import { AgentProviderCards } from "./AgentProviderCards";
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
  guidedOperationLog,
  guidedNextActionDescription,
  guidedNextActionLabel,
  guidedStepStatusLabel,
  ideaPatentGoalModes,
  officialCompileActionGate,
  patentTypeOptions,
  postDraftReviewActionGate,
  qualityActionGate,
  qualitySummaryFromRuns,
  resolveGuidedViewStep,
  selectCurrentOfficialCompileRun,
  selectLatestMatchingPostDraftReview,
  type GuidedActionGate,
  type GuidedFlowState,
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
  agentDoctor: AgentDoctorReport | null;
  selectedDeliberationProviders: string[];
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
  onCreateIdeaProject: (payload: { name: string; idea: string; mode: PatentGoalMode; patentType: PatentType }) => Promise<void>;
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
  onStartPostDraftReview: () => void;
  onCancelPostDraftReviewRun: (runId: string) => void;
  onRetryPostDraftReviewRun: (runId: string) => void;
  onToggleDeliberationProvider: (providerId: string, enabled: boolean) => void;
  onToggleFormulaProvider: (providerId: string, enabled: boolean) => void;
  onGenerateDraft: () => void;
  onRunQualityChecks: () => void;
  onImproveScore: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
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
  const latestMatchingPostDraftReview = selectLatestMatchingPostDraftReview(
    props.postDraftReviews,
    latestOfficialCompileRun,
  );
  const [manualViewStepId, setManualViewStepId] = useState<GuidedStepId | null>(null);

  useEffect(() => {
    setManualViewStepId(null);
  }, [state.currentStepId]);

  const displayedStepId = resolveGuidedViewStep(state.currentStepId, manualViewStepId, state.steps);
  const completedStepCount = state.steps.filter((step) => step.status === "done").length;

  function handleNextAction(): void {
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
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartDeliberation={props.onStartDeliberation}
          onCancelRun={props.onCancelDeliberationRun}
          onRetryRun={props.onRetryDeliberationRun}
          onToggleProvider={props.onToggleDeliberationProvider}
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
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {displayedStepId === "officialCompile" && (
        <OfficialCompilePanel
          actionGate={officialCompileActionGate(state, state.currentStepId, displayedStepId)}
          project={props.project}
          run={latestOfficialCompileRun}
          runs={props.officialCompileRuns}
          currentSourceDraftHash={props.currentSourceDraftHash}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartOfficialCompile={props.onStartOfficialCompile}
        />
      )}
      {displayedStepId === "postReview" && (
        <PostDraftReviewPanel
          actionGate={postDraftReviewActionGate(state, state.currentStepId, displayedStepId)}
          project={props.project}
          review={latestMatchingPostDraftReview}
          runs={props.postDraftReviews}
          currentDraftHash={props.currentDraftHash}
          officialCompileRun={latestOfficialCompileRun}
          doctor={props.agentDoctor}
          selectedProviders={props.selectedDeliberationProviders}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartPostDraftReview={props.onStartPostDraftReview}
          onCancelRun={props.onCancelPostDraftReviewRun}
          onRetryRun={props.onRetryPostDraftReviewRun}
          onToggleProvider={props.onToggleDeliberationProvider}
        />
      )}
      {displayedStepId === "export" && (
        <ExportConfirmationPanel
          project={props.project}
          filingReport={latestFilingReport}
          completionRun={latestCompletionRun}
          postDraftReview={latestMatchingPostDraftReview}
          currentDraftHash={props.currentDraftHash}
          officialCompileRun={latestOfficialCompileRun}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
    </div>
  );
}

function GuidedProgressBanner({
  busy,
  completedStepCount,
  currentStepId,
  displayedStepId,
  onNext,
  totalStepCount,
}: {
  busy: string;
  completedStepCount: number;
  currentStepId: GuidedStepId;
  displayedStepId: GuidedStepId;
  onNext: () => void;
  totalStepCount: number;
}) {
  const percent = Math.round((completedStepCount / totalStepCount) * 100);
  const isBrowsingPastStep = displayedStepId !== currentStepId;
  const actionIsFormOnly = currentStepId === "idea";
  return (
    <section className="guided-progress-banner" aria-label="流程进度和下一步">
      <div className="guided-progress-copy">
        <span className="status-badge">{completedStepCount}/{totalStepCount} 已完成</span>
        <div>
          <h3>当前进度：{percent}%</h3>
          <p>{guidedNextActionDescription(currentStepId)}</p>
        </div>
      </div>
      <div className="guided-progress-meter" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>
      <button
        className="primary"
        disabled={Boolean(busy) || actionIsFormOnly}
        onClick={onNext}
        type="button"
      >
        {busy ? <Loader2 className="spin" size={17} /> : <PlayCircle size={17} />}
        <span>{isBrowsingPastStep ? "回到当前步骤" : guidedNextActionLabel(currentStepId)}</span>
      </button>
      {actionIsFormOnly && (
        <p className="workflow-hint">请在下方表单中填写项目名称和技术方案，或返回三选一选择导入已有稿件。</p>
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
