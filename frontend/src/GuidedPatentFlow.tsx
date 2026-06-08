import { FormEvent, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileText,
  Gauge,
  Loader2,
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
  type FilingReadinessReport,
  type FormulaNeedAssessment,
  type FormulaRun,
  type OfficialCompileRun,
  type PatentPointCandidate,
  type PostDraftReviewRun,
  type ProjectMaterial,
  type ProjectRecord,
} from "./api";
import {
  deriveGuidedFlowState,
  guidedOperationLog,
  patentGoalModes,
  qualitySummaryFromRuns,
  selectCurrentOfficialCompileRun,
  selectLatestMatchingPostDraftReview,
  type GuidedFlowState,
  type PatentGoalMode,
} from "./guidedFlow";
import { latestCompletedDeliberation } from "./domain";

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
  busy: string;
  busyElapsedSeconds?: number;
  onCreateIdeaProject: (payload: { name: string; idea: string; mode: PatentGoalMode }) => Promise<void>;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
  onStartDisclosure: () => void;
  onSelectPatentPoint: (point: PatentPointCandidate, candidates: PatentPointCandidate[]) => void;
  onStartDeliberation: () => void;
  onStartFormula: () => void;
  onStartOfficialCompile: () => void;
  onStartPostDraftReview: () => void;
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

  return (
    <div className="max-w-[1200px] mx-auto w-full flex flex-col gap-8 pb-24">
      <WorkflowStepper state={state} />
      {state.currentStepId === "idea" && (
        <IdeaIntakePanel
          project={props.project}
          materials={props.materials}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onCreateIdeaProject={props.onCreateIdeaProject}
          onUploadMaterial={props.onUploadMaterial}
        />
      )}
      {state.currentStepId === "invention" && (
        <InventionPointConfirmation
          disclosure={latestDisclosure}
          materials={props.materials}
          patentPoints={props.patentPoints}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onUploadMaterial={props.onUploadMaterial}
          onStartDisclosure={props.onStartDisclosure}
          onSelectPatentPoint={props.onSelectPatentPoint}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {state.currentStepId === "draft" && (
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
      {state.currentStepId === "deliberation" && (
        <DeliberationPanel
          deliberation={latestDeliberation}
          runs={props.deliberations}
          doctor={props.agentDoctor}
          selectedProviders={props.selectedDeliberationProviders}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartDeliberation={props.onStartDeliberation}
          onToggleProvider={props.onToggleDeliberationProvider}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {state.currentStepId === "formula" && (
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
          onToggleProvider={props.onToggleFormulaProvider}
        />
      )}
      {state.currentStepId === "quality" && (
        <QualityPanel
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
      {state.currentStepId === "officialCompile" && (
        <OfficialCompilePanel
          project={props.project}
          run={latestOfficialCompileRun}
          runs={props.officialCompileRuns}
          currentSourceDraftHash={props.currentSourceDraftHash}
          busy={props.busy}
          busyElapsedSeconds={props.busyElapsedSeconds ?? 0}
          onStartOfficialCompile={props.onStartOfficialCompile}
        />
      )}
      {state.currentStepId === "postReview" && (
        <PostDraftReviewPanel
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
          onToggleProvider={props.onToggleDeliberationProvider}
        />
      )}
      {state.currentStepId === "export" && (
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

function WorkflowStepper({ state }: { state: GuidedFlowState }) {
  return (
    <section className="grid grid-cols-5 gap-3">
      {state.steps.map((step, index) => (
        <article className={`flex gap-3 min-h-[94px] rounded-2xl p-3.5 backdrop-blur-md saturate-110 ${step.status === 'current' ? 'border border-[#267a78]/40 bg-white/90 shadow-[0_0_0_3px_rgba(38,122,120,0.12),0_16px_50px_rgba(31,52,54,0.12)]' : 'border border-white/70 bg-white/50 shadow-lg'}`} key={step.id}>
          <span className={step.status === "done" ? "bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white flex items-center justify-center w-6 h-6 rounded-full text-sm font-bold" : "flex items-center justify-center w-6 h-6 rounded-full bg-white/60 text-[#142424] text-sm font-bold"}>{index + 1}</span>
          <div>
            <strong>{step.label}</strong>
            <p>{step.description}</p>
          </div>
        </article>
      ))}
    </section>
  );
}

function IdeaIntakePanel({
  project,
  materials,
  busy,
  busyElapsedSeconds,
  onCreateIdeaProject,
  onUploadMaterial,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  busy: string;
  busyElapsedSeconds: number;
  onCreateIdeaProject: GuidedPatentFlowProps["onCreateIdeaProject"];
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
}) {
  const [name, setName] = useState(project?.name ?? "");
  const [idea, setIdea] = useState(project?.draft_text ?? "");
  const [mode, setMode] = useState<PatentGoalMode>("stable");
  const canSubmit = Boolean(name.trim() && idea.trim() && !project);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    await onCreateIdeaProject({ name: name.trim(), idea: idea.trim(), mode });
  }

  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>把你的想法写成一段话</h3>
          <p>系统会基于这段想法提炼发明点、生成专利初稿、运行质检并准备导出文件。</p>
        </div>
        <Wand2 size={24} />
      </div>
      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        <label>
          <span>项目名称</span>
          <input value={name} onChange={(event) => setName(event.target.value)} disabled={Boolean(project)} />
        </label>
        <label>
          <span>一句话想法</span>
          <textarea
            className="w-full rounded-2xl border border-white/60 bg-white/50 px-5 py-4 focus:outline-none focus:ring-2 focus:ring-[#267a78]/40 min-h-[160px] text-lg"
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            disabled={Boolean(project)}
            placeholder="例如：通过点云和多视角影像自动生成外立面 IFC 模型，并回链工程量清单。"
          />
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {patentGoalModes.map((item) => (
            <button
              className={mode === item.id ? "flex flex-col gap-2 p-5 bg-white/90 border border-[#267a78]/40 rounded-2xl shadow-[0_4px_20px_rgba(38,122,120,0.08)] ring-1 ring-[#267a78]/20" : "flex flex-col gap-2 p-5 bg-white/40 border border-white/50 rounded-2xl cursor-pointer hover:bg-white/60 transition-colors"}
              key={item.id}
              onClick={() => setMode(item.id)}
              type="button"
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!canSubmit || busy === "guided-create"} type="submit">
          <FileText size={17} />
          <span>{project ? "已创建想法" : "创建并继续"}</span>
        </button>
        <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-create"} />
      </form>
      {project && (
        <form className="flex items-center gap-4 p-4 border-2 border-dashed border-white/60 rounded-2xl bg-white/30" onSubmit={onUploadMaterial}>
          <input
            id="project-material-file"
            name="project-material-file"
            type="file"
            accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
          />
          <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "material-upload"} type="submit">
            <Upload size={17} />
            <span>上传补充材料</span>
          </button>
          <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
        </form>
      )}
      <MaterialSummary materials={materials} />
    </section>
  );
}

function MaterialSummary({ materials }: { materials: ProjectMaterial[] }) {
  return (
    <div className="flex flex-col gap-3">
      {materials.map((material) => (
        <article className="flex items-start gap-3 p-4 bg-white/40 border border-white/50 rounded-2xl" key={material.id}>
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
      {materials.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">可先不上传材料，系统会基于想法生成第一版。</p>}
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
    <div className="bg-[#112a2d] text-white/90 rounded-2xl overflow-hidden shadow-lg border border-white/10" role="status" aria-label={log.label}>
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10 text-xs font-mono text-white/60">
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

function InventionPointConfirmation({
  disclosure,
  materials,
  patentPoints,
  busy,
  busyElapsedSeconds,
  onUploadMaterial,
  onStartDisclosure,
  onSelectPatentPoint,
  onOpenExpertTool,
}: {
  disclosure: DisclosureRun | null;
  materials: ProjectMaterial[];
  patentPoints: PatentPointCandidate[];
  busy: string;
  busyElapsedSeconds: number;
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
  onStartDisclosure: () => void;
  onSelectPatentPoint: GuidedPatentFlowProps["onSelectPatentPoint"];
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const disclosureCandidates = disclosure?.package?.candidates ?? [];
  const candidates = disclosureCandidates.length ? disclosureCandidates : patentPoints;
  const needsGeneration = !disclosure || candidates.length === 0;

  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>确认发明点与护城河</h3>
          <p>这里是默认流程的第一个暂停点。确认主线后，系统才进入初稿生成。</p>
        </div>
        <ShieldCheck size={24} />
      </div>
      <div className="flex items-center gap-3">
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("materials")} type="button">
          查看前置材料详情
        </button>
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("moat")} type="button">
          查看护城河地图
        </button>
      </div>
      <form className="flex items-center gap-4 p-4 border-2 border-dashed border-white/60 rounded-2xl bg-white/30" onSubmit={onUploadMaterial}>
        <input
          id="project-material-file-invention"
          name="project-material-file"
          type="file"
          accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
        />
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "material-upload"} type="submit">
          <Upload size={17} />
          <span>上传补充材料</span>
        </button>
        <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "material-upload"} />
      </form>
      <MaterialSummary materials={materials} />
      {needsGeneration && (
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "disclosure"} onClick={onStartDisclosure} type="button">
          {busy === "disclosure" ? <Loader2 className="animate-spin" size={17} /> : <Wand2 size={17} />}
          <span>提炼发明点</span>
        </button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "disclosure"} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {candidates.map((point) => (
          <article className={point.selected ? "flex flex-col gap-3 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20" : "flex flex-col gap-3 p-5 bg-white/50 border border-white/60 rounded-3xl shadow-sm"} key={point.id}>
            <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
              <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{evidenceStatusText(point.evidence_status)}</span>
              <span>{point.protection_focus.join(" / ") || "方法 / 系统"}</span>
            </div>
            <h4>{point.title}</h4>
            <p>{point.innovation || point.technical_solution}</p>
            {point.support_gaps.length > 0 && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">支撑缺口：{point.support_gaps.join("；")}</p>}
            <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onSelectPatentPoint(point, candidates)} type="button">
              选为主线并保存后备路线
            </button>
          </article>
        ))}
        {candidates.length === 0 && <p className="text-sm text-[#142424]/50 italic py-4">点击“提炼发明点”后显示候选主线。</p>}
      </div>
    </section>
  );
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
  onToggleProvider: (providerId: string, enabled: boolean) => void;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>多 Agent 会审</h3>
          <p>专利生成前必须完成会审，用于收敛权利要求边界、说明书支撑和规避风险。</p>
        </div>
        <UsersRound size={24} />
      </div>
      <div className="flex items-center gap-3">
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("deliberate")} type="button">
          查看会审详情
        </button>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="deliberation"
        selectedProviders={selectedProviders}
        disabled={busy === "deliberate"}
        onToggleProvider={onToggleProvider}
      />
      <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "deliberate"} onClick={onStartDeliberation} type="button">
        {busy === "deliberate" ? <Loader2 className="animate-spin" size={17} /> : <UsersRound size={17} />}
        <span>{deliberation ? "重新会审" : "启动多 Agent 会审"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "deliberate"} />
      {deliberation?.strategy_brief && (
        <article className="flex flex-col gap-3 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20">
          <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
            <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{deliberation.run_mode}</span>
            <span>{deliberation.providers.join(" / ")}</span>
          </div>
          <h4>会审共识</h4>
          <p>{deliberation.strategy_brief.agent_consensus || deliberation.strategy_brief.summary}</p>
        </article>
      )}
      {!deliberation && runs.length > 0 && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">已有会审运行，但尚无 completed 策略结果。</p>}
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
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
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
      <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || !deliberation || !formulaReady || busy === "generate"} onClick={onGenerateDraft} type="button">
        {busy === "generate" ? <Loader2 className="animate-spin" size={17} /> : <Wand2 size={17} />}
        <span>生成初稿</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "generate"} />
      {project?.package && <pre className="p-6 bg-white/40 border border-white/50 rounded-3xl font-mono text-sm leading-relaxed overflow-auto max-h-[500px]">{project.package.claims.slice(0, 1200)}</pre>}
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
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}) {
  const required = Boolean(requirement?.required);
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>核心公式</h3>
          <p>{required ? "该项目包含公式型信号，需先凝练公式包。" : "当前项目未检测到必须凝练的公式型信号。"}</p>
        </div>
        <Sigma size={24} />
      </div>
      {requirement && (
        <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
          <span className={required ? "px-2.5 py-0.5 rounded-md bg-amber-100 border border-amber-200 text-amber-700" : "px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]"}>{required ? "需要公式包" : "无需公式包"}</span>
          <span>{requirement.signals.join(" / ") || "无公式信号"}</span>
        </div>
      )}
      <AgentProviderCards
        doctor={doctor}
        role="formula"
        selectedProviders={selectedProviders}
        disabled={busy === "formula"}
        onToggleProvider={onToggleProvider}
      />
      {required && (
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || busy === "formula"} onClick={onStartFormula} type="button">
          {busy === "formula" ? <Loader2 className="animate-spin" size={17} /> : <Sigma size={17} />}
          <span>{formulaRun ? "重新凝练核心公式" : "凝练核心公式"}</span>
        </button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "formula"} />
      {formulaRun?.package && (
        <article className="flex flex-col gap-3 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20">
          <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
            <span className="px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]">{formulaRun.status}</span>
            <span>{formulaRun.package.formula_blocks.length} 个公式</span>
            {formulaRun.providers.length > 0 && <span>{formulaRun.providers.join(" / ")}</span>}
            {project && (
              <a href={formulaMarkdownUrl(project.id, formulaRun.id)} rel="noreferrer" target="_blank">
                LaTeX
              </a>
            )}
          </div>
          <h4>{formulaRun.package.summary}</h4>
          <p>{formulaRun.package.formula_blocks.map((block) => `${block.id} ${block.name}`).join("；")}</p>
        </article>
      )}
      {!formulaRun && runs.length > 0 && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">已有公式运行，但尚无 completed 公式包。</p>}
    </section>
  );
}

function QualityPanel({
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
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>质量检查与补强</h3>
          <p>系统会运行提交成熟度、权利要求防线、初稿完善和审查意见。</p>
        </div>
        <Gauge size={24} />
      </div>
      {(filingReport || worksheet || completionRun) && (
        <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">已获得部分检查结果。可以继续补强，也可以重新运行质量检查。</p>
      )}
      <div className="flex items-center gap-3">
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("readiness")} type="button">
          查看提交成熟度
        </button>
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("claimDefense")} type="button">
          查看权利要求防线
        </button>
        <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("completion")} type="button">
          查看初稿完善
        </button>
      </div>
      <div className="flex items-center gap-3">
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={Boolean(busy)} onClick={onRunQualityChecks} type="button">
          {busy === "guided-quality" ? <Loader2 className="animate-spin" size={17} /> : <Gauge size={17} />}
          <span>运行质量检查</span>
        </button>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={Boolean(busy)} onClick={onImproveScore} type="button">
          {busy === "score-improve" ? <Loader2 className="animate-spin" size={17} /> : <Wand2 size={17} />}
          <span>一键提升分数</span>
        </button>
      </div>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-quality"} />
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "score-improve"} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ScoreTile label="状态" value={summary.statusLabel} />
        <ScoreTile
          label="授权稳定性"
          value={summary.authorizationStability === null ? "未评分" : `${summary.authorizationStability}/100`}
        />
        <ScoreTile label="保护范围" value={summary.protectionScope === null ? "未评分" : `${summary.protectionScope}/100`} />
        <ScoreTile label="提交成熟度" value={summary.filingMaturity === null ? "未评分" : `${summary.filingMaturity}/100`} />
      </div>
      {filingReport?.issues.slice(0, 5).map((issue, index) => (
        <article className={`flex items-start gap-3 p-4 border rounded-2xl ${ issue.severity === "high" ? "bg-red-50 border-red-100" : issue.severity === "medium" ? "bg-amber-50 border-amber-100" : "bg-blue-50 border-blue-100" }`} key={`${issue.category}-${index}`}>
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
          <article className="flex flex-col gap-3 p-5 bg-white/50 border border-white/60 rounded-3xl shadow-sm" key={patch.id}>
            <h4>{patch.rationale}</h4>
            <p>{patch.risk_delta}</p>
            <pre className="p-4 bg-white/40 rounded-xl border border-white/50 font-mono text-sm whitespace-pre-wrap">{patch.after_text}</pre>
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" onClick={() => onAcceptPatch(completionRun.id, patch.id)} type="button">
              接受补强建议
            </button>
          </article>
        ))}
    </section>
  );
}

function ScoreTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="flex flex-col gap-2 p-4 bg-white/60 border border-white/70 rounded-2xl">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function OfficialCompilePanel({
  project,
  run,
  runs,
  currentSourceDraftHash,
  busy,
  busyElapsedSeconds,
  onStartOfficialCompile,
}: {
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
  const statusClass = completed ? "px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]" : blocked || run?.status === "failed" ? "px-2.5 py-0.5 rounded-md bg-red-100 border border-red-200 text-red-700" : "px-2.5 py-0.5 rounded-md bg-amber-100 border border-amber-200 text-amber-700";

  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>正式稿编译</h3>
          <p>隔离内部痕迹、support gaps、绘图提示和会审过程文本，生成正式申请文本专用包。</p>
        </div>
        <FileText size={24} />
      </div>
      <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
        <span className={statusClass}>{statusText}</span>
        <span>source hash：{currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成"}</span>
        {run?.official_package_hash && <span>official hash：{run.official_package_hash.slice(0, 12)}</span>}
      </div>
      <button
        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
        disabled={!project?.package || busy === "official-compile"}
        onClick={onStartOfficialCompile}
        type="button"
      >
        {busy === "official-compile" ? <Loader2 className="animate-spin" size={17} /> : <FileText size={17} />}
        <span>{run ? "重新编译正式稿" : "编译正式稿"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "official-compile"} />
      {run && (
        <article className={completed ? "flex flex-col gap-3 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20" : "flex flex-col gap-3 p-5 bg-white/50 border border-white/60 rounded-3xl shadow-sm"}>
          <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
            <span className={statusClass}>{run.status}</span>
            <span>移除污染 {run.contamination_removed.length} 项</span>
            <span>阻断 {run.blocked_items.length} 项</span>
            {project && (
              <a href={officialCompileReportUrl(project.id, run.id)} rel="noreferrer" target="_blank">
                编译报告
              </a>
            )}
          </div>
          <h4>{completed ? "正式稿包已生成" : "正式稿未放行"}</h4>
          <p>source hash：{run.source_draft_hash.slice(0, 12)}</p>
          <p>official hash：{run.official_package_hash ? run.official_package_hash.slice(0, 12) : "未生成"}</p>
          {run.blocked_items.length > 0 && (
            <p>阻断项：{run.blocked_items.map((item) => item.message || item.category || "未命名阻断项").slice(0, 3).join("；")}</p>
          )}
        </article>
      )}
      {!run && runs.length > 0 && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">已有正式稿编译记录，但未匹配当前 source hash。</p>}
    </section>
  );
}

function PostDraftReviewPanel({
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
  onToggleProvider,
}: {
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
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}) {
  const passed = Boolean(review?.status === "completed" && review.export_allowed);
  const blocked = Boolean(review?.status === "completed" && !review.export_allowed);
  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>成稿后多 Agent 会审</h3>
          <p>正式导出前必选。内置 Prompt Pack 会审权利要求质量、说明书清污、技术硬度和主席裁决。</p>
        </div>
        <ClipboardCheck size={24} />
      </div>
      <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
        <span className={passed ? "px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]" : blocked ? "px-2.5 py-0.5 rounded-md bg-red-100 border border-red-200 text-red-700" : "px-2.5 py-0.5 rounded-md bg-amber-100 border border-amber-200 text-amber-700"}>
          {passed ? "已通过" : blocked ? "阻止正式导出" : "等待会审"}
        </span>
        <span>{review?.prompt_pack_version ?? "post-draft-review-v1"}</span>
        <span>当前 hash：{currentDraftHash ? currentDraftHash.slice(0, 12) : "未生成"}</span>
        <span>official hash：{officialCompileRun?.official_package_hash.slice(0, 12) ?? "未编译"}</span>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="post_review"
        selectedProviders={selectedProviders}
        disabled={busy === "post-draft-review"}
        onToggleProvider={onToggleProvider}
      />
      <button
        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-gradient-to-br from-[#267a78] to-[#165b5d] text-white font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
        disabled={!project?.package || busy === "post-draft-review"}
        onClick={onStartPostDraftReview}
        type="button"
      >
        {busy === "post-draft-review" ? <Loader2 className="animate-spin" size={17} /> : <ClipboardCheck size={17} />}
        <span>{review ? "重新成稿会审" : "启动成稿会审"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "post-draft-review"} />
      {review && (
        <article className={passed ? "flex flex-col gap-3 p-5 bg-white/90 border border-[#267a78]/30 rounded-3xl shadow-[0_8px_30px_rgba(38,122,120,0.12)] ring-1 ring-[#267a78]/20" : "flex flex-col gap-3 p-5 bg-white/50 border border-white/60 rounded-3xl shadow-sm"}>
          <div className="flex items-center gap-3 text-xs text-[#142424]/60 font-medium mb-1">
            <span className={passed ? "px-2.5 py-0.5 rounded-md bg-white/80 border border-white text-[#142424]" : "px-2.5 py-0.5 rounded-md bg-red-100 border border-red-200 text-red-700"}>{review.status}</span>
            <span>{review.providers.join(" / ") || "默认三方"}</span>
            <span>review hash：{review.draft_package_hash.slice(0, 12)}</span>
            {review.official_package_hash && <span>official hash：{review.official_package_hash.slice(0, 12)}</span>}
            {project && (
              <a href={postDraftReviewReportUrl(project.id, review.id)} rel="noreferrer" target="_blank">
                会审报告
              </a>
            )}
          </div>
          <h4>{passed ? "主席裁决：允许正式导出" : "主席裁决：需要修订"}</h4>
          {review.blocking_issues.length > 0 && <p>Blocking：{review.blocking_issues.slice(0, 3).join("；")}</p>}
          {review.contamination_hits.length > 0 && <p>污染命中：{review.contamination_hits.slice(0, 5).join("；")}</p>}
        </article>
      )}
      {!review && runs.length > 0 && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">已有成稿会审记录，但未匹配当前成稿 hash。</p>}
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
      <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
        <p className="text-sm text-[#142424]/50 italic py-4">生成初稿后才能导出。</p>
      </section>
    );
  }
  const officialAllowed = Boolean(
    postDraftReview?.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id,
  );

  return (
    <section className="grid gap-4 border border-white/70 rounded-[34px] bg-white/60 p-6 shadow-xl backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 mb-2">
        <div>
          <h3>导出前确认</h3>
          <p>这是默认流程的第二个暂停点。正式稿只在成稿会审通过且匹配当前成稿 hash 后放行。</p>
        </div>
        <Download size={24} />
      </div>
      {filingReport?.status === "high_risk" && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">当前提交成熟度为高风险，请结合成稿会审报告处理。</p>}
      {!officialAllowed && <p className="text-sm text-[#142424]/70 bg-white/40 px-4 py-3 rounded-xl border border-white/50 flex items-center gap-2">正式稿入口已锁定：需要通过匹配当前正式稿编译 hash 的成稿会审。</p>}
      <div className="p-6 bg-[#267a78]/5 border border-[#267a78]/20 rounded-2xl flex flex-col gap-4">
        <article>
          <strong>正式稿</strong>
          <span>{officialAllowed ? `已通过成稿会审，可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}` : "等待正式稿编译和成稿会审通过后解锁。"}</span>
        </article>
        <article>
          <strong>内部稿</strong>
          <span>保留策略、风险、会审、支撑矩阵和补强报告。</span>
        </article>
        <article>
          <strong>导出原则</strong>
          <span>blocking issue 阻止正式稿；内部稿和报告不受阻止。</span>
        </article>
      </div>
      <button className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/60 hover:bg-white/90 text-[#142424] shadow-sm border border-white/50 disabled:opacity-50 transition-colors" onClick={() => onOpenExpertTool("export")} type="button">
        查看专家导出工具
      </button>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
          href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/40 border border-white/50 text-[#142424]/40 font-medium cursor-not-allowed"}
          href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" href={exportUrl(project.id, "md")}>
          <Download size={18} />
          <span>内部策略稿 MD</span>
        </a>
        {filingReport && (
          <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" href={filingReadinessReportUrl(project.id, filingReport.id)}>
            <Download size={18} />
            <span>提交成熟度报告</span>
          </a>
        )}
        {completionRun && (
          <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white/80 border border-white shadow-sm hover:bg-white text-[#142424] font-medium transition-colors" href={draftCompletionReportUrl(project.id, completionRun.id)}>
            <Download size={18} />
            <span>初稿完善报告</span>
          </a>
        )}
      </div>
    </section>
  );
}
