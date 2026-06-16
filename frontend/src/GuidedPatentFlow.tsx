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
} from "./domain";

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

function IdeaIntakePanel({
  project,
  materials,
  externalDraftSources,
  externalDraftIntakeRuns,
  busy,
  busyElapsedSeconds,
  fixedGoalMode,
  initialIntakeMode,
  onCreateIdeaProject,
  onCreateExternalDraft,
  onUploadExternalDraft,
  onStartExternalDraftIntake,
  onConfirmExternalDraftIntake,
  onUploadMaterial,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  externalDraftSources: ExternalDraftSource[];
  externalDraftIntakeRuns: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  fixedGoalMode?: PatentGoalMode;
  initialIntakeMode?: "idea" | "external";
  onCreateIdeaProject: GuidedPatentFlowProps["onCreateIdeaProject"];
  onCreateExternalDraft: GuidedPatentFlowProps["onCreateExternalDraft"];
  onUploadExternalDraft: GuidedPatentFlowProps["onUploadExternalDraft"];
  onStartExternalDraftIntake: GuidedPatentFlowProps["onStartExternalDraftIntake"];
  onConfirmExternalDraftIntake: GuidedPatentFlowProps["onConfirmExternalDraftIntake"];
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [idea, setIdea] = useState(project?.draft_text ?? "");
  const [mode, setMode] = useState<PatentGoalMode>("stable");
  const [patentType, setPatentType] = useState<PatentType>(fixedGoalMode === "utility" ? "utility_model" : "invention");
  const [intakeMode, setIntakeMode] = useState<"idea" | "external">(initialIntakeMode ?? "idea");
  const canSubmit = Boolean(name.trim() && idea.trim() && !project);
  const effectiveMode = fixedGoalMode ?? mode;
  const effectivePatentType: PatentType = fixedGoalMode === "utility" ? "utility_model" : patentType;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await onCreateIdeaProject({ name: name.trim(), idea: idea.trim(), mode: effectiveMode, patentType: effectivePatentType });
  }

  useEffect(() => {
    setIntakeMode(initialIntakeMode ?? "idea");
  }, [initialIntakeMode]);

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>{intakeMode === "idea" ? "把你的想法写成一段话" : "导入外部专利初稿"}</h3>
          <p>
            {intakeMode === "idea"
              ? "系统会基于这段想法提炼发明点、生成专利初稿、运行质检并准备导出文件。"
              : "保存外部稿原文，解析章节，并在人工确认后转为内部工作稿。"}
          </p>
        </div>
        {intakeMode === "idea" ? <Wand2 size={24} /> : <FileText size={24} />}
      </div>
      <div className="segmented-control" role="tablist" aria-label="专利生成入口">
        <button
          aria-selected={intakeMode === "idea"}
          className={intakeMode === "idea" ? "selected" : ""}
          onClick={() => setIntakeMode("idea")}
          role="tab"
          type="button"
        >
          从想法生成
        </button>
        <button
          aria-selected={intakeMode === "external"}
          className={intakeMode === "external" ? "selected" : ""}
          onClick={() => setIntakeMode("external")}
          role="tab"
          type="button"
        >
          导入外部初稿
        </button>
      </div>
      {intakeMode === "idea" ? (
        <>
          <form className="guided-intake" onSubmit={handleSubmit}>
            <label>
              <span>项目名称</span>
              <input value={name} onChange={(event) => setName(event.target.value)} disabled={Boolean(project)} />
            </label>
            <label>
              <span>一句话想法</span>
              <textarea
                className="idea-input"
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                disabled={Boolean(project)}
                placeholder="例如：通过点云和多视角影像自动生成外立面 IFC 模型，并回链工程量清单。"
              />
            </label>
            {fixedGoalMode !== "utility" && (
              <div className="mode-grid">
                {patentTypeOptions.map((item) => (
                  <button
                    className={patentType === item.id ? "mode-card selected" : "mode-card"}
                    key={item.id}
                    onClick={() => setPatentType(item.id)}
                    type="button"
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </button>
                ))}
              </div>
            )}
            {!fixedGoalMode && (
              <div className="mode-grid">
                {ideaPatentGoalModes.map((item) => (
                  <button
                    className={mode === item.id ? "mode-card selected" : "mode-card"}
                    key={item.id}
                    onClick={() => setMode(item.id)}
                    type="button"
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </button>
                ))}
              </div>
            )}
            <button className="primary" disabled={!canSubmit || busy === "guided-create"} type="submit">
              <FileText size={17} />
              <span>{project ? "已创建想法" : "创建并继续"}</span>
            </button>
            <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-create"} />
          </form>
          {project && (
            <form className="guided-upload" onSubmit={onUploadMaterial}>
              <input
                id="project-material-file"
                name="project-material-file"
                type="file"
                accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
              />
              <button className="primary" disabled={busy === "material-upload"} type="submit">
                <Upload size={17} />
                <span>上传补充材料</span>
              </button>
              <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
            </form>
          )}
          <MaterialSummary materials={materials} />
        </>
      ) : (
        <ExternalDraftIntakePanel
          project={project}
          sources={externalDraftSources}
          runs={externalDraftIntakeRuns}
          busy={busy}
          busyElapsedSeconds={busyElapsedSeconds}
          onCreateExternalDraft={onCreateExternalDraft}
          onUploadExternalDraft={onUploadExternalDraft}
          onStartExternalDraftIntake={onStartExternalDraftIntake}
          onConfirmExternalDraftIntake={onConfirmExternalDraftIntake}
        />
      )}
    </section>
  );
}

function ExternalDraftIntakePanel({
  project,
  sources,
  runs,
  busy,
  busyElapsedSeconds,
  onCreateExternalDraft,
  onUploadExternalDraft,
  onStartExternalDraftIntake,
  onConfirmExternalDraftIntake,
}: {
  project: ProjectRecord | null;
  sources: ExternalDraftSource[];
  runs: ExternalDraftIntakeRun[];
  busy: string;
  busyElapsedSeconds: number;
  onCreateExternalDraft: GuidedPatentFlowProps["onCreateExternalDraft"];
  onUploadExternalDraft: GuidedPatentFlowProps["onUploadExternalDraft"];
  onStartExternalDraftIntake: GuidedPatentFlowProps["onStartExternalDraftIntake"];
  onConfirmExternalDraftIntake: GuidedPatentFlowProps["onConfirmExternalDraftIntake"];
}) {
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("external-draft.txt");
  const [selectedUploadFileName, setSelectedUploadFileName] = useState("");
  const latestRun = runs[0] ?? null;
  const draft = latestRun?.parsed_package ?? null;
  const confirmable = Boolean(draft?.claims.trim() && draft?.description.trim());

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!project || !text.trim()) return;
    await onCreateExternalDraft({ text: text.trim(), fileName: fileName.trim() || "external-draft.txt" });
    setText("");
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedUploadFileName) return;
    await onUploadExternalDraft(event);
    setSelectedUploadFileName("");
  }

  async function handleConfirm() {
    if (!latestRun || !draft || !confirmable) return;
    await onConfirmExternalDraftIntake(latestRun.id, {
      title: draft.title,
      abstract: draft.abstract,
      claims: draft.claims,
      description: draft.description,
      drawing_description: draft.drawing_description,
    });
  }

  return (
    <section className="external-draft-panel">
      {!project && <p className="workflow-hint">请先创建或选择一个项目，再导入外部初稿。</p>}
      <form className="guided-upload" onSubmit={handleUpload}>
        <label>
          <span>文件名</span>
          <input
            id="external-draft-file"
            name="external-draft-file"
            type="file"
            accept=".docx,.txt,.md,.markdown"
            onChange={(event) => setSelectedUploadFileName(event.target.files?.[0]?.name ?? "")}
          />
        </label>
        <button className="primary" disabled={!project || !selectedUploadFileName || busy === "external-draft-upload"} type="submit">
          <Upload size={17} />
          <span>上传外部初稿</span>
        </button>
      </form>
      <form className="guided-intake" onSubmit={handleCreate}>
        <label>
          <span>粘贴稿文件名</span>
          <input value={fileName} onChange={(event) => setFileName(event.target.value)} disabled={!project} />
        </label>
        <label>
          <span>粘贴外部专利初稿</span>
          <textarea
            className="idea-input"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="粘贴发明名称、摘要、权利要求书、说明书和附图说明。"
          />
        </label>
        <button className="primary" disabled={!project || !text.trim() || busy === "external-draft-create"} type="submit">
          <FileText size={17} />
          <span>保存原始外部稿</span>
        </button>
      </form>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy.startsWith("external-draft")} />
      <div className="guided-summary-list">
        {sources.map((source) => (
          <article className="guided-summary-row external-draft-source-row" key={source.id}>
            <FileText size={18} />
            <div>
              <strong>{source.file_name}</strong>
              <span>
                {source.source_type} / {source.content_hash.slice(0, 12)}
              </span>
            </div>
            <button
              className="icon-button"
              disabled={busy === "external-draft-intake"}
              onClick={() => onStartExternalDraftIntake(source.id)}
              type="button"
            >
              解析章节
            </button>
          </article>
        ))}
        {sources.length === 0 && <p className="empty">保存外部稿后，系统会解析章节并生成内部工作稿。</p>}
      </div>
      {latestRun && (
        <article className="guided-choice selected external-draft-result">
          <div className="result-meta">
            <span className={latestRun.status === "needs_review" ? "status-badge warn" : "status-badge"}>
              {latestRun.status === "completed" ? "解析完成" : latestRun.status === "needs_review" ? "需要确认" : "解析失败"}
            </span>
            <span>{latestRun.working_draft_hash.slice(0, 12) || "无工作稿 hash"}</span>
          </div>
          <h4>{draft?.title || "外部初稿解析结果"}</h4>
          <p>{latestRun.intake_issues.map((issue) => issue.message).join("；") || "未发现导入阶段阻断问题。"}</p>
          {draft && (
            <div className="external-draft-section-preview">
              <span>权利要求：{draft.claims.trim() ? "已识别" : "缺失"}</span>
              <span>说明书：{draft.description.trim() ? "已识别" : "缺失"}</span>
            </div>
          )}
          {draft && (
            <button
              className="primary"
              disabled={!confirmable || busy === "external-draft-confirm"}
              onClick={handleConfirm}
              type="button"
            >
              <CheckCircle2 size={17} />
              <span>确认为内部工作稿</span>
            </button>
          )}
          {draft && !confirmable && <p className="workflow-hint">请补齐权利要求书和说明书后重新保存并解析。</p>}
        </article>
      )}
    </section>
  );
}

function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  return (
    <div className="guided-summary-list">
      {materials.map((material) => (
        <article className="guided-summary-row" key={material.id}>
          {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <div>
            <strong>{material.file_name}</strong>
            <span>
              {material.status === "processed"
                ? `${material.file_type} / ${material.text.length} 字`
                : material.warnings.join("；")}
            </span>
          </div>
        </article>
      ))}
      {materials.length === 0 && <p className="empty">可先不上传材料，系统会基于想法生成第一版。</p>}
    </div>
  );
}

function GuidedOperationConsole({
  busy,
  elapsedSeconds,
  active,
}: {
  busy: string;
  elapsedSeconds: number;
  active: boolean;
}) {
  const log = active ? guidedOperationLog(busy, elapsedSeconds) : null;
  if (!log) return null;
  return (
    <div className="inline-console" role="status" aria-label={log.label}>
      <div className="console-heading">
        <span>{log.label}</span>
        <span>{formatElapsedLabel(log.elapsedSeconds)}</span>
      </div>
      <pre>{log.lines.join("\n")}</pre>
    </div>
  );
}

function formatElapsedLabel(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

type GuidedRuntimeRun = {
  id: string;
  status: string;
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  events?: string[];
  providers?: string[];
  stage_results?: unknown[];
  cancel_requested?: boolean;
  retry_of?: string | null;
};

function guidedActiveRun<T extends GuidedRuntimeRun>(runs: T[]): T | null {
  return runs.find((run) => run.status === "queued" || run.status === "running") ?? null;
}

function guidedRetryableRun(run: GuidedRuntimeRun): boolean {
  return (
    run.status !== "queued"
    && run.status !== "running"
    && (run.status === "failed" || run.status === "interrupted" || Boolean(run.failure_details?.some((failure) => failure.retryable)))
  );
}

function GuidedRuntimeActions({
  run,
  disabled = false,
  onCancel,
  onRetry,
}: {
  run: GuidedRuntimeRun | null;
  disabled?: boolean;
  onCancel?: (runId: string) => void;
  onRetry?: (runId: string) => void;
}) {
  if (!run) return null;
  const active = run.status === "queued" || run.status === "running";
  const canCancel = Boolean(onCancel && active && !run.cancel_requested);
  const canRetry = Boolean(onRetry && guidedRetryableRun(run));
  if (!canCancel && !canRetry) return null;
  return (
    <div className="button-row">
      {canCancel && (
        <button className="icon-button danger" disabled={disabled} onClick={() => onCancel?.(run.id)} type="button">
          <AlertTriangle size={16} />
          <span>取消运行</span>
        </button>
      )}
      {canRetry && (
        <button className="icon-button" disabled={disabled} onClick={() => onRetry?.(run.id)} type="button">
          <RefreshCw size={16} />
          <span>重试</span>
        </button>
      )}
    </div>
  );
}

function GuidedRuntimeConsole({
  run,
  label,
  busy,
  onCancel,
}: {
  run: GuidedRuntimeRun | null;
  label: string;
  busy?: string;
  onCancel?: (runId: string) => void;
}) {
  if (!run || (run.status !== "queued" && run.status !== "running")) return null;
  const state = run.runtime_state ?? null;
  const lines = [
    `run ${run.id.slice(0, 10)} / ${pipelineRunStatusLabel(run.status)}`,
    `stage ${guidedRuntimeStageLabel(state?.current_stage)}`,
    state?.provider ? `provider ${state.provider}` : "",
    state?.subtask ? `task ${state.subtask}` : "",
    typeof state?.elapsed_ms === "number" ? `elapsed ${formatElapsedLabel(Math.floor(state.elapsed_ms / 1000))}` : "",
    typeof state?.partial_artifact_count === "number" ? `partials ${state.partial_artifact_count}` : "",
    typeof state?.warning_count === "number" ? `warnings ${state.warning_count}` : "",
    run.events?.at(-1) ? `event ${run.events.at(-1)}` : "",
  ].filter(Boolean);
  return (
    <div className="inline-console" role="status" aria-label={label}>
      <div className="console-heading">
        <span>{label}</span>
        <span>{state ? formatElapsedLabel(Math.floor(state.elapsed_ms / 1000)) : "00:00"}</span>
      </div>
      <pre>{lines.join("\n")}</pre>
      <GuidedRuntimeActions run={run} disabled={Boolean(busy)} onCancel={onCancel} />
    </div>
  );
}

function GuidedRuntimeFailures({ run }: { run: GuidedRuntimeRun | null }) {
  const failures = run?.failure_details ?? [];
  if (failures.length === 0) return null;
  return (
    <div className="guided-runtime-failures">
      {failures.slice(-2).map((failure, index) => (
        <p key={`${run?.id}-failure-${index}`}>
          {failure.reason} / {guidedRuntimeStageLabel(failure.stage)}：{failure.message}
        </p>
      ))}
    </div>
  );
}

function guidedRuntimeStageLabel(stage?: string | null): string {
  if (!stage) return "等待调度";
  if (stage === "formula_generation") return "凝练核心公式";
  if (stage === "post_draft_review") return "成稿会审";
  if (stage === "deliberation_finalize") return "会审收尾";
  if (stage === "disclosure_package") return "整理交底包";
  if (stage.startsWith("deep_research")) return "Deep Research";
  return stage.replaceAll("_", " ");
}

function InventionPointConfirmation({
  disclosure,
  disclosureRuns,
  materials,
  patentPoints,
  busy,
  busyElapsedSeconds,
  researchMode,
  onChangeResearchMode,
  onUploadMaterial,
  onStartDisclosure,
  onCancelRun,
  onRetryRun,
  onSelectPatentPoint,
  onOpenExpertTool,
}: {
  disclosure: DisclosureRun | null;
  disclosureRuns: DisclosureRun[];
  materials: ProjectMaterial[];
  patentPoints: PatentPointCandidate[];
  busy: string;
  busyElapsedSeconds: number;
  researchMode: "standard" | "free_deep_research";
  onChangeResearchMode: (mode: "standard" | "free_deep_research") => void;
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
  onStartDisclosure: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onSelectPatentPoint: GuidedPatentFlowProps["onSelectPatentPoint"];
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const activeRun = guidedActiveRun(disclosureRuns);
  const latestRun = disclosureRuns[0] ?? null;
  const activeRunCandidates = patentPointCandidatesFromDisclosureRun(activeRun);
  const latestRunCandidates = patentPointCandidatesFromDisclosureRun(latestRun);
  const disclosureCandidates = activeRunCandidates.length
    ? activeRunCandidates
    : latestRunCandidates.length
      ? latestRunCandidates
      : disclosure?.package?.candidates ?? [];
  const candidates = disclosureCandidates.length ? disclosureCandidates : patentPoints;
  const needsGeneration = (!disclosure || candidates.length === 0) && !activeRun;
  const showingPartialCandidates = Boolean(activeRun && activeRunCandidates.length > 0 && !activeRun.package);

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>确认发明点与护城河</h3>
          <p>这里是默认流程的第一个暂停点。确认主线后，系统才进入初稿生成。</p>
        </div>
        <ShieldCheck size={24} />
      </div>
      <div className="button-row">
        <button className="icon-button" onClick={() => onOpenExpertTool("materials")} type="button">
          查看前置材料详情
        </button>
        <button className="icon-button" onClick={() => onOpenExpertTool("moat")} type="button">
          查看护城河地图
        </button>
      </div>
      <form className="guided-upload" onSubmit={onUploadMaterial}>
        <input
          id="project-material-file-invention"
          name="project-material-file"
          type="file"
          accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
        />
        <button className="primary" disabled={busy === "material-upload"} type="submit">
          <Upload size={17} />
          <span>上传补充材料</span>
        </button>
        <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
      </form>
      <MaterialSummary materials={materials} />
      {needsGeneration && (
        <div className="guided-research-mode" data-testid="disclosure-research-mode">
          <label htmlFor="disclosure-research-mode-select" className="guided-research-mode-label">
            研究模式
          </label>
          <select
            id="disclosure-research-mode-select"
            value={researchMode}
            onChange={(event) =>
              onChangeResearchMode(event.target.value as "standard" | "free_deep_research")
            }
          >
            <option value="standard">标准（默认）</option>
            <option value="free_deep_research">免费 Deep Research（公开检索 + 多轮分析）</option>
          </select>
          <p className="guided-research-mode-hint">
            {researchMode === "free_deep_research"
              ? "免费 Deep Research 将在系统内执行公开专利、arXiv/OpenAlex 论文检索与多轮 LLM 分析；配置 Tavily、Exa、Semantic Scholar 等 API key 时会自动扩展检索源，未配置也会用免费公开源降级运行。它仅生成内部补充材料，不替代多智能体会审，不解锁正式稿导出。"
              : "标准模式只走常规交底书流水线；如希望系统在交底阶段做更深的公开检索调研，可切换为免费 Deep Research。"}
          </p>
        </div>
      )}
      {needsGeneration && (
        <button className="primary" disabled={busy === "disclosure"} onClick={onStartDisclosure} type="button">
          {busy === "disclosure" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>{researchMode === "free_deep_research" ? "提炼发明点（免费 Deep Research）" : "提炼发明点"}</span>
        </button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "disclosure"} />
      <GuidedRuntimeConsole run={activeRun} label="发明点提炼运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={disclosureRuns[0] ?? null} />
      <GuidedRuntimeActions run={disclosureRuns[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {showingPartialCandidates && (
        <p className="workflow-hint">
          候选发明点已返回，后台仍在整理交底包；可以先查看候选主线，完整包完成后会自动刷新。
        </p>
      )}
      <div className="guided-card-grid">
        {candidates.map((point) => (
          <article className={point.selected ? "guided-choice selected" : "guided-choice"} key={point.id}>
            <div className="result-meta">
              <span className="status-badge">{evidenceStatusText(point.evidence_status)}</span>
              <span>{point.protection_focus.join(" / ") || "方法 / 系统"}</span>
            </div>
            <h4>{point.title}</h4>
            <p>{point.innovation || point.technical_solution}</p>
            {point.support_gaps.length > 0 && <p className="workflow-hint">支撑缺口：{point.support_gaps.join("；")}</p>}
            <button className="icon-button" onClick={() => onSelectPatentPoint(point, candidates)} type="button">
              选为主线并保存后备路线
            </button>
          </article>
        ))}
        {candidates.length === 0 && <p className="empty">点击“提炼发明点”后显示候选主线。</p>}
      </div>
    </section>
  );
}

function patentPointCandidatesFromDisclosureRun(run: DisclosureRun | null): PatentPointCandidate[] {
  const packageCandidates = run?.package?.candidates ?? [];
  if (packageCandidates.length > 0) return packageCandidates;
  return patentPointCandidatesFromStageResults(run);
}

function patentPointCandidatesFromStageResults(run: DisclosureRun | null): PatentPointCandidate[] {
  const stageResults = run?.stage_results ?? [];
  for (let index = stageResults.length - 1; index >= 0; index -= 1) {
    const result = stageResults[index];
    if (result.phase !== "patent_points") continue;
    const payload = result.payload;
    if (isRecord(payload) && Array.isArray(payload.candidates)) {
      return payload.candidates.filter(isPatentPointCandidate);
    }
  }
  return [];
}

function isPatentPointCandidate(value: unknown): value is PatentPointCandidate {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.title === "string"
    && Array.isArray(value.protection_focus)
    && Array.isArray(value.support_gaps)
    && typeof value.innovation === "string"
    && typeof value.technical_solution === "string"
    && typeof value.evidence_status === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function evidenceStatusText(status: PatentPointCandidate["evidence_status"]): string {
  if (status === "verified") return "已验证";
  if (status === "needs_experiment") return "需实验";
  if (status === "feasible_unverified") return "可行未验证";
  return "模型生成";
}

function DeliberationPanel({
  deliberation,
  runs,
  doctor,
  selectedProviders,
  busy,
  busyElapsedSeconds,
  onStartDeliberation,
  onCancelRun,
  onRetryRun,
  onToggleProvider,
  onOpenExpertTool,
}: {
  deliberation: DeliberationRun | null;
  runs: DeliberationRun[];
  doctor: AgentDoctorReport | null;
  selectedProviders: string[];
  busy: string;
  busyElapsedSeconds: number;
  onStartDeliberation: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const activeRun = guidedActiveRun(runs);
  const deliberationBusy = busy === "deliberate" || Boolean(activeRun);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>多智能体会审</h3>
          <p>专利生成前必须完成会审，用于收敛权利要求边界、说明书支撑和规避风险。</p>
        </div>
        <UsersRound size={24} />
      </div>
      <div className="button-row">
        <button className="icon-button" onClick={() => onOpenExpertTool("deliberate")} type="button">
          查看会审详情
        </button>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="deliberation"
        selectedProviders={selectedProviders}
        disabled={deliberationBusy}
        onToggleProvider={onToggleProvider}
      />
      <button className="primary" disabled={deliberationBusy} onClick={onStartDeliberation} type="button">
        {deliberationBusy ? <Loader2 className="spin" size={17} /> : <UsersRound size={17} />}
        <span>{activeRun ? "会审中" : deliberation ? "重新会审" : "启动多智能体会审"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "deliberate"} />
      <GuidedRuntimeConsole run={activeRun} label="会审运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {deliberation?.strategy_brief && (
        <article className="guided-choice selected">
          <div className="result-meta">
            <span className="status-badge">{deliberationRunModeLabel(deliberation.run_mode)}</span>
            <span>{deliberation.providers.join(" / ")}</span>
          </div>
          <h4>会审共识</h4>
          <p>{deliberation.strategy_brief.agent_consensus || deliberation.strategy_brief.summary}</p>
        </article>
      )}
      {!deliberation && runs.length > 0 && <p className="workflow-hint">已有会审记录，但尚无已完成的策略结果。</p>}
    </section>
  );
}

function DraftGenerationPanel({
  project,
  disclosure,
  deliberation,
  formulaRequirement,
  formulaRun,
  busy,
  busyElapsedSeconds,
  onGenerateDraft,
}: {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  deliberation: DeliberationRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  busy: string;
  busyElapsedSeconds: number;
  onGenerateDraft: () => void;
}) {
  const formulaReady = !formulaRequirement?.required || Boolean(formulaRun?.package);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>生成专利初稿</h3>
          <p>
            {deliberation
              ? `将使用会审 run：${deliberation.id}`
              : disclosure
                ? `将使用交底书 run：${disclosure.id}`
                : "将使用当前想法和已确认发明点生成。"}
          </p>
          <p>{formulaRun ? `将注入核心公式 run：${formulaRun.id}` : formulaRequirement?.required ? "等待核心公式包。" : "本项目无需公式型凝练。"}</p>
        </div>
        <FileText size={24} />
      </div>
      <button className="primary" disabled={!project || !deliberation || !formulaReady || busy === "generate"} onClick={onGenerateDraft} type="button">
        {busy === "generate" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
        <span>生成初稿</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "generate"} />
      {project?.package && <pre className="guided-preview">{project.package.claims.slice(0, 1200)}</pre>}
    </section>
  );
}

function FormulaPanel({
  project,
  requirement,
  formulaRun,
  runs,
  doctor,
  selectedProviders,
  busy,
  busyElapsedSeconds,
  onStartFormula,
  onCancelRun,
  onRetryRun,
  onToggleProvider,
}: {
  project: ProjectRecord | null;
  requirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  runs: FormulaRun[];
  doctor: AgentDoctorReport | null;
  selectedProviders: string[];
  busy: string;
  busyElapsedSeconds: number;
  onStartFormula: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}) {
  const required = Boolean(requirement?.required);
  const activeRun = guidedActiveRun(runs);
  const formulaBusy = busy === "formula" || Boolean(activeRun);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>核心公式</h3>
          <p>{required ? "该项目包含公式型信号，需先凝练公式包。" : "当前项目未检测到必须凝练的公式型信号。"}</p>
        </div>
        <Sigma size={24} />
      </div>
      {requirement && (
        <div className="result-meta">
          <span className={required ? "status-badge warn" : "status-badge"}>{required ? "需要公式包" : "无需公式包"}</span>
          <span>{requirement.signals.join(" / ") || "无公式信号"}</span>
        </div>
      )}
      <AgentProviderCards
        doctor={doctor}
        role="formula"
        selectedProviders={selectedProviders}
        disabled={formulaBusy}
        onToggleProvider={onToggleProvider}
      />
      {required && (
        <button className="primary" disabled={!project || formulaBusy} onClick={onStartFormula} type="button">
          {formulaBusy ? <Loader2 className="spin" size={17} /> : <Sigma size={17} />}
          <span>{activeRun ? "公式凝练中" : formulaRun ? "重新凝练核心公式" : "凝练核心公式"}</span>
        </button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "formula"} />
      <GuidedRuntimeConsole run={activeRun} label="核心公式运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {formulaRun?.package && (
        <article className="guided-choice selected">
          <div className="result-meta">
            <span className="status-badge">{pipelineRunStatusLabel(formulaRun.status)}</span>
            <span>{formulaRun.package.formula_blocks.length} 个公式</span>
            {formulaRun.providers.length > 0 && <span>{formulaRun.providers.join(" / ")}</span>}
            {project && (
              <a href={formulaMarkdownUrl(project.id, formulaRun.id)} rel="noreferrer" target="_blank">
                公式 LaTeX
              </a>
            )}
          </div>
          <h4>{formulaRun.package.summary}</h4>
          <p>{formulaRun.package.formula_blocks.map((block) => `${block.id} ${block.name}`).join("；")}</p>
        </article>
      )}
      {!formulaRun && runs.length > 0 && <p className="workflow-hint">已有公式运行记录，但尚无已完成的公式包。</p>}
    </section>
  );
}

function ActionGateHint({ gate }: { gate: GuidedActionGate }) {
  if (gate.allowed || !gate.reason) {
    return null;
  }
  return <p className="workflow-hint">{gate.reason}</p>;
}

function QualityPanel({
  actionGate,
  filingReport,
  worksheet,
  completionRun,
  busy,
  busyElapsedSeconds,
  onRunQualityChecks,
  onImproveScore,
  onAcceptPatch,
  onOpenExpertTool,
}: {
  actionGate: GuidedActionGate;
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
  busy: string;
  busyElapsedSeconds: number;
  onRunQualityChecks: () => void;
  onImproveScore: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const summary = qualitySummaryFromRuns({ filingReport, worksheet, completionRun });
  const actionsDisabled = !actionGate.allowed || Boolean(busy);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>质量检查与补强</h3>
          <p>系统会运行提交成熟度、权利要求防线、初稿完善和审查意见。</p>
        </div>
        <Gauge size={24} />
      </div>
      {(filingReport || worksheet || completionRun) && (
        <p className="workflow-hint">已获得部分检查结果。可以继续补强，也可以重新运行质量检查。</p>
      )}
      <div className="button-row">
        <button className="icon-button" onClick={() => onOpenExpertTool("readiness")} type="button">
          查看提交成熟度
        </button>
        <button className="icon-button" onClick={() => onOpenExpertTool("claimDefense")} type="button">
          查看权利要求防线
        </button>
        <button className="icon-button" onClick={() => onOpenExpertTool("completion")} type="button">
          查看初稿完善
        </button>
      </div>
      <ActionGateHint gate={actionGate} />
      <div className="button-row">
        <button
          className="primary"
          disabled={actionsDisabled}
          onClick={onRunQualityChecks}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "guided-quality" ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
          <span>运行质量检查</span>
        </button>
        <button
          className="primary"
          disabled={actionsDisabled}
          onClick={onImproveScore}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "score-improve" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>一键提升分数</span>
        </button>
      </div>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-quality"} />
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "score-improve"} />
      <div className="guided-score-grid">
        <ScoreTile label="状态" value={summary.statusLabel} />
        <ScoreTile
          label="授权稳定性"
          value={summary.authorizationStability === null ? "未评分" : `${summary.authorizationStability}/100`}
        />
        <ScoreTile label="保护范围" value={summary.protectionScope === null ? "未评分" : `${summary.protectionScope}/100`} />
        <ScoreTile label="提交成熟度" value={summary.filingMaturity === null ? "未评分" : `${summary.filingMaturity}/100`} />
      </div>
      {filingReport?.issues.slice(0, 5).map((issue, index) => (
        <article className={`finding ${issue.severity}`} key={`${issue.category}-${index}`}>
          <span>{issue.severity === "high" ? "高" : issue.severity === "medium" ? "中" : "低"}</span>
          <div>
            <strong>{issue.category}</strong>
            <p>{issue.message}</p>
            <p>{issue.suggestion}</p>
          </div>
        </article>
      ))}
      {completionRun?.patches
        .filter((patch) => patch.status === "proposed")
        .slice(0, 3)
        .map((patch) => (
          <article className="guided-choice" key={patch.id}>
            <h4>{patch.rationale}</h4>
            <p>{patch.risk_delta}</p>
            <pre className="patch-preview">{patch.after_text}</pre>
            <button className="primary" onClick={() => onAcceptPatch(completionRun.id, patch.id)} type="button">
              接受补强建议
            </button>
          </article>
        ))}
    </section>
  );
}

function ScoreTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="score-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function OfficialCompilePanel({
  actionGate,
  project,
  run,
  runs,
  currentSourceDraftHash,
  busy,
  busyElapsedSeconds,
  onStartOfficialCompile,
}: {
  actionGate: GuidedActionGate;
  project: ProjectRecord | null;
  run: OfficialCompileRun | null;
  runs: OfficialCompileRun[];
  currentSourceDraftHash: string;
  busy: string;
  busyElapsedSeconds: number;
  onStartOfficialCompile: () => void;
}) {
  const completed = Boolean(run?.status === "completed" && run.official_package);
  const blocked = Boolean(run?.status === "blocked");
  const statusText = completed ? "已完成" : blocked ? "已阻断" : run?.status === "failed" ? "失败" : "等待编译";
  const statusClass = completed ? "status-badge" : blocked || run?.status === "failed" ? "status-badge danger" : "status-badge warn";

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>正式稿编译</h3>
          <p>隔离内部痕迹、支撑缺口、绘图提示和会审过程文本，生成正式申请文本专用包。</p>
        </div>
        <FileText size={24} />
      </div>
      <div className="result-meta">
        <span className={statusClass}>{statusText}</span>
        <span>源稿哈希：{currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成"}</span>
        {run?.official_package_hash && <span>正式稿哈希：{run.official_package_hash.slice(0, 12)}</span>}
      </div>
      {blocked && (
        <p className="workflow-hint workflow-hint-danger">
          当前正式稿编译已阻断，请查看编译报告并处理阻断项。
        </p>
      )}
      <ActionGateHint gate={actionGate} />
      <button
        className="primary"
        disabled={!actionGate.allowed || busy === "official-compile"}
        onClick={onStartOfficialCompile}
        title={actionGate.reason || undefined}
        type="button"
      >
        {busy === "official-compile" ? <Loader2 className="spin" size={17} /> : <FileText size={17} />}
        <span>{run ? "重新编译正式稿" : "编译正式稿"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "official-compile"} />
      {run && (
        <article className={completed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            <span className={statusClass}>{pipelineRunStatusLabel(run.status)}</span>
            <span>移除污染 {run.contamination_removed.length} 项</span>
            <span>阻断 {run.blocked_items.length} 项</span>
            {project && (
              <a href={officialCompileReportUrl(project.id, run.id)} rel="noreferrer" target="_blank">
                编译报告
              </a>
            )}
          </div>
          <h4>{completed ? "正式稿包已生成" : "正式稿未放行"}</h4>
          <p>源稿哈希：{run.source_draft_hash.slice(0, 12)}</p>
          <p>正式稿哈希：{run.official_package_hash ? run.official_package_hash.slice(0, 12) : "未生成"}</p>
          {run.blocked_items.length > 0 && (
            <p>阻断项：{run.blocked_items.map((item) => item.message || item.category || "未命名阻断项").slice(0, 3).join("；")}</p>
          )}
        </article>
      )}
      {!run && runs.length > 0 && (
        <p className="workflow-hint">已有正式稿编译记录，但不属于当前源稿。请重新编译正式稿。</p>
      )}
    </section>
  );
}

function PostDraftReviewPanel({
  actionGate,
  project,
  review,
  runs,
  currentDraftHash,
  officialCompileRun,
  doctor,
  selectedProviders,
  busy,
  busyElapsedSeconds,
  onStartPostDraftReview,
  onCancelRun,
  onRetryRun,
  onToggleProvider,
}: {
  actionGate: GuidedActionGate;
  project: ProjectRecord | null;
  review: PostDraftReviewRun | null;
  runs: PostDraftReviewRun[];
  currentDraftHash: string;
  officialCompileRun: OfficialCompileRun | null;
  doctor: AgentDoctorReport | null;
  selectedProviders: string[];
  busy: string;
  busyElapsedSeconds: number;
  onStartPostDraftReview: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}) {
  const passed = Boolean(review?.status === "completed" && review.export_allowed);
  const blocked = Boolean(review?.status === "completed" && !review.export_allowed);
  const activeRun = guidedActiveRun(runs);
  const reviewBusy = busy === "post-draft-review" || Boolean(activeRun);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>成稿后多智能体会审</h3>
          <p>正式导出前必选。内置 Prompt Pack 会审权利要求质量、说明书清污、技术硬度和主席裁决。</p>
        </div>
        <ClipboardCheck size={24} />
      </div>
      <div className="result-meta">
        <span className={passed ? "status-badge" : blocked ? "status-badge danger" : "status-badge warn"}>
          {passed ? "已通过" : blocked ? "阻止正式导出" : "等待会审"}
        </span>
        <span>{review?.prompt_pack_version ?? "post-draft-review-v1"}</span>
        <span>当前成稿哈希：{currentDraftHash ? currentDraftHash.slice(0, 12) : "未生成"}</span>
        <span>正式稿哈希：{officialCompileRun?.official_package_hash.slice(0, 12) ?? "未编译"}</span>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="post_review"
        selectedProviders={selectedProviders}
        disabled={!actionGate.allowed || reviewBusy}
        onToggleProvider={onToggleProvider}
      />
      <ActionGateHint gate={actionGate} />
      <button
        className="primary"
        disabled={!actionGate.allowed || reviewBusy}
        onClick={onStartPostDraftReview}
        title={actionGate.reason || undefined}
        type="button"
      >
        {reviewBusy ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
        <span>{activeRun ? "成稿会审中" : review ? "重新成稿会审" : "启动成稿会审"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "post-draft-review"} />
      <GuidedRuntimeConsole run={activeRun} label="成稿会审运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {review && (
        <article className={passed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            <span className={passed ? "status-badge" : "status-badge danger"}>{pipelineRunStatusLabel(review.status)}</span>
            <span>{review.providers.join(" / ") || "默认三方"}</span>
            <span>会审哈希：{review.draft_package_hash.slice(0, 12)}</span>
            {review.official_package_hash && <span>正式稿哈希：{review.official_package_hash.slice(0, 12)}</span>}
            {project && (
              <a href={postDraftReviewReportUrl(project.id, review.id)} rel="noreferrer" target="_blank">
                会审报告
              </a>
            )}
          </div>
          <h4>{passed ? "主席裁决：允许正式导出" : "主席裁决：需要修订"}</h4>
          {review.blocking_issues.length > 0 && <p>阻断项：{review.blocking_issues.slice(0, 3).join("；")}</p>}
          {review.contamination_hits.length > 0 && <p>污染命中：{review.contamination_hits.slice(0, 5).join("；")}</p>}
        </article>
      )}
      {!review && runs.length > 0 && (
        <p className="workflow-hint">已有成稿会审记录，但不属于当前成稿。请重新运行成稿会审。</p>
      )}
    </section>
  );
}

function ExportConfirmationPanel({
  project,
  filingReport,
  completionRun,
  postDraftReview,
  currentDraftHash,
  officialCompileRun,
  onOpenExpertTool,
}: {
  project: ProjectRecord | null;
  filingReport: FilingReadinessReport | null;
  completionRun: DraftCompletionRun | null;
  postDraftReview: PostDraftReviewRun | null;
  currentDraftHash: string;
  officialCompileRun: OfficialCompileRun | null;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  if (!project?.package) {
    return (
      <section className="guided-panel">
        <p className="empty">生成初稿后才能导出。</p>
      </section>
    );
  }
  const officialAllowed = Boolean(
    postDraftReview?.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id,
  );

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>导出前确认</h3>
          <p>正式稿只在正式稿编译完成、成稿会审通过且哈希匹配后放行；导出文件仍需专利代理师或律师复核后再提交。</p>
        </div>
        <Download size={24} />
      </div>
      {filingReport?.status === "high_risk" && <p className="workflow-hint">当前提交成熟度为高风险：请先处理报告中的不利表述、内部痕迹或支撑缺口，再让专业人员复核。</p>}
      {!officialAllowed && (
        <p className="workflow-hint">正式稿入口已锁定：请先完成正式稿编译，并通过匹配当前正式稿哈希的成稿会审；内部稿和侧车报告仅供内部复核。</p>
      )}
      <div className="export-confirmation">
        <article>
          <strong>正式稿</strong>
          <span>{officialAllowed ? `已通过成稿会审，可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}` : "等待正式稿编译和成稿会审通过后解锁。"}</span>
        </article>
        <article>
          <strong>内部稿</strong>
          <span>保留策略、风险、会审、支撑矩阵和补强建议，仅供内部复核，不作为提交稿。</span>
        </article>
        <article>
          <strong>导出原则</strong>
          <span>阻断项会锁定正式稿；侧车报告用于解释风险来源，不替代最终人工审查。</span>
        </article>
      </div>
      <button className="icon-button" onClick={() => onOpenExpertTool("export")} type="button">
        查看专家导出工具
      </button>
      <div className="export-grid">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link" : "export-link disabled"}
          href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link" : "export-link disabled"}
          href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        <a className="export-link" href={exportUrl(project.id, "md")}>
          <Download size={18} />
          <span>内部策略稿 MD</span>
        </a>
        {filingReport && (
          <a className="export-link" href={filingReadinessReportUrl(project.id, filingReport.id)}>
            <Download size={18} />
            <span>提交成熟度报告</span>
          </a>
        )}
        {completionRun && (
          <a className="export-link" href={draftCompletionReportUrl(project.id, completionRun.id)}>
            <Download size={18} />
            <span>初稿完善报告</span>
          </a>
        )}
      </div>
    </section>
  );
}
