import { FormEvent, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Gauge,
  Loader2,
  ShieldCheck,
  Upload,
  Wand2,
} from "lucide-react";

import {
  draftCompletionReportUrl,
  exportUrl,
  filingReadinessReportUrl,
  officialExportUrl,
  type ClaimDefenseWorksheet,
  type DisclosureRun,
  type DraftCompletionRun,
  type FilingReadinessReport,
  type PatentPointCandidate,
  type ProjectMaterial,
  type ProjectRecord,
} from "./api";
import {
  deriveGuidedFlowState,
  patentGoalModes,
  qualitySummaryFromRuns,
  type GuidedFlowState,
  type PatentGoalMode,
} from "./guidedFlow";

export type GuidedPatentFlowProps = {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  disclosures: DisclosureRun[];
  patentPoints: PatentPointCandidate[];
  filingReports: FilingReadinessReport[];
  worksheets: ClaimDefenseWorksheet[];
  completionRuns: DraftCompletionRun[];
  busy: string;
  onCreateIdeaProject: (payload: { name: string; idea: string; mode: PatentGoalMode }) => Promise<void>;
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => void;
  onStartDisclosure: () => void;
  onSelectPatentPoint: (point: PatentPointCandidate) => void;
  onGenerateDraft: () => void;
  onRunQualityChecks: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onOpenExpertTool: (
    tool: "materials" | "moat" | "readiness" | "claimDefense" | "completion" | "export",
  ) => void;
};

export function GuidedPatentFlowView(props: GuidedPatentFlowProps) {
  const state = useMemo(
    () =>
      deriveGuidedFlowState({
        project: props.project,
        materials: props.materials,
        disclosures: props.disclosures,
        patentPoints: props.patentPoints,
        filingReports: props.filingReports,
        worksheets: props.worksheets,
        completionRuns: props.completionRuns,
      }),
    [
      props.project,
      props.materials,
      props.disclosures,
      props.patentPoints,
      props.filingReports,
      props.worksheets,
      props.completionRuns,
    ],
  );
  const latestDisclosure = props.disclosures.find((run) => run.status === "completed" && run.package) ?? null;
  const latestFilingReport = props.filingReports[0] ?? null;
  const latestWorksheet = props.worksheets[0] ?? null;
  const latestCompletionRun = props.completionRuns[0] ?? null;

  return (
    <div className="guided-flow">
      <WorkflowStepper state={state} />
      {state.currentStepId === "idea" && (
        <IdeaIntakePanel
          project={props.project}
          materials={props.materials}
          busy={props.busy}
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
          busy={props.busy}
          onGenerateDraft={props.onGenerateDraft}
        />
      )}
      {state.currentStepId === "quality" && (
        <QualityPanel
          filingReport={latestFilingReport}
          worksheet={latestWorksheet}
          completionRun={latestCompletionRun}
          busy={props.busy}
          onRunQualityChecks={props.onRunQualityChecks}
          onAcceptPatch={props.onAcceptPatch}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
      {state.currentStepId === "export" && (
        <ExportConfirmationPanel
          project={props.project}
          filingReport={latestFilingReport}
          completionRun={latestCompletionRun}
          onOpenExpertTool={props.onOpenExpertTool}
        />
      )}
    </div>
  );
}

function WorkflowStepper({ state }: { state: GuidedFlowState }) {
  return (
    <section className="guided-stepper">
      {state.steps.map((step, index) => (
        <article className={`guided-step ${step.status}`} key={step.id}>
          <span>{index + 1}</span>
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
  onCreateIdeaProject,
  onUploadMaterial,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  busy: string;
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
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>把你的想法写成一段话</h3>
          <p>系统会基于这段想法提炼发明点、生成专利初稿、运行质检并准备导出文件。</p>
        </div>
        <Wand2 size={24} />
      </div>
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
        <div className="mode-grid">
          {patentGoalModes.map((item) => (
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
        <button className="primary" disabled={!canSubmit || busy === "guided-create"} type="submit">
          <FileText size={17} />
          <span>{project ? "已创建想法" : "创建并继续"}</span>
        </button>
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
        </form>
      )}
      <MaterialSummary materials={materials} />
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

function InventionPointConfirmation({
  disclosure,
  materials,
  patentPoints,
  busy,
  onUploadMaterial,
  onStartDisclosure,
  onSelectPatentPoint,
  onOpenExpertTool,
}: {
  disclosure: DisclosureRun | null;
  materials: ProjectMaterial[];
  patentPoints: PatentPointCandidate[];
  busy: string;
  onUploadMaterial: GuidedPatentFlowProps["onUploadMaterial"];
  onStartDisclosure: () => void;
  onSelectPatentPoint: (point: PatentPointCandidate) => void;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const disclosureCandidates = disclosure?.package?.candidates ?? [];
  const candidates = disclosureCandidates.length ? disclosureCandidates : patentPoints;
  const needsGeneration = !disclosure || candidates.length === 0;

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
      </form>
      <MaterialSummary materials={materials} />
      {needsGeneration && (
        <button className="primary" disabled={busy === "disclosure"} onClick={onStartDisclosure} type="button">
          {busy === "disclosure" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>提炼发明点</span>
        </button>
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
            <button className="icon-button" onClick={() => onSelectPatentPoint(point)} type="button">
              选为主线
            </button>
          </article>
        ))}
        {candidates.length === 0 && <p className="empty">点击“提炼发明点”后显示候选主线。</p>}
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

function DraftGenerationPanel({
  project,
  disclosure,
  busy,
  onGenerateDraft,
}: {
  project: ProjectRecord | null;
  disclosure: DisclosureRun | null;
  busy: string;
  onGenerateDraft: () => void;
}) {
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>生成专利初稿</h3>
          <p>{disclosure ? `将使用交底书 run：${disclosure.id}` : "将使用当前想法和已确认发明点生成。"}</p>
        </div>
        <FileText size={24} />
      </div>
      <button className="primary" disabled={!project || busy === "generate"} onClick={onGenerateDraft} type="button">
        {busy === "generate" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
        <span>生成初稿</span>
      </button>
      {project?.package && <pre className="guided-preview">{project.package.claims.slice(0, 1200)}</pre>}
    </section>
  );
}

function QualityPanel({
  filingReport,
  worksheet,
  completionRun,
  busy,
  onRunQualityChecks,
  onAcceptPatch,
  onOpenExpertTool,
}: {
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
  busy: string;
  onRunQualityChecks: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  const summary = qualitySummaryFromRuns({ filingReport, worksheet, completionRun });
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
      <button className="primary" disabled={busy === "guided-quality"} onClick={onRunQualityChecks} type="button">
        {busy === "guided-quality" ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
        <span>运行质量检查</span>
      </button>
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

function ExportConfirmationPanel({
  project,
  filingReport,
  completionRun,
  onOpenExpertTool,
}: {
  project: ProjectRecord | null;
  filingReport: FilingReadinessReport | null;
  completionRun: DraftCompletionRun | null;
  onOpenExpertTool: GuidedPatentFlowProps["onOpenExpertTool"];
}) {
  if (!project?.package) {
    return (
      <section className="guided-panel">
        <p className="empty">生成初稿后才能导出。</p>
      </section>
    );
  }

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>导出前确认</h3>
          <p>这是默认流程的第二个暂停点。高风险不会阻止导出，但会保留在内部报告中。</p>
        </div>
        <Download size={24} />
      </div>
      {filingReport?.status === "high_risk" && <p className="workflow-hint">当前为高风险但允许导出。请先查看检查报告。</p>}
      <div className="export-confirmation">
        <article>
          <strong>正式稿</strong>
          <span>只包含摘要、权利要求书、说明书和附图说明。</span>
        </article>
        <article>
          <strong>内部稿</strong>
          <span>保留策略、风险、会审、支撑矩阵和补强报告。</span>
        </article>
        <article>
          <strong>导出原则</strong>
          <span>高风险会提示，但不会阻止导出。</span>
        </article>
      </div>
      <button className="icon-button" onClick={() => onOpenExpertTool("export")} type="button">
        查看专家导出工具
      </button>
      <div className="export-grid">
        <a className="export-link" href={officialExportUrl(project.id, "docx")}>
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a className="export-link" href={officialExportUrl(project.id, "md")}>
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
