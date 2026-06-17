import { Loader2, Sigma } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import {
  formulaMarkdownUrl,
  type AgentDoctorReport,
  type FormulaNeedAssessment,
  type FormulaRun,
  type ProjectRecord,
} from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
} from "../runtimeWidgets";

export interface FormulaPanelProps {
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
}

export function FormulaPanel({
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
}: FormulaPanelProps) {
  const required = Boolean(requirement?.required);
  const activeRun = guidedActiveRun(runs);
  const formulaBusy = busy === "formula" || Boolean(activeRun);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>核心公式</h3>
          <p>{required ? "本项目含公式型信号，需先凝练公式。" : "本项目未检测到必须凝练的公式信号。"}</p>
        </div>
        <Sigma size={24} />
      </div>
      {requirement && (
        <div className="result-meta">
          <span className={required ? "status-badge warn" : "status-badge"}>{required ? "需要公式" : "无需公式"}</span>
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
                公式说明
              </a>
            )}
          </div>
          <h4>{formulaRun.package.summary}</h4>
          <p>{formulaRun.package.formula_blocks.map((block) => `${block.id} ${block.name}`).join("；")}</p>
        </article>
      )}
      {!formulaRun && runs.length > 0 && <p className="workflow-hint">已有公式运行记录，但尚无已完成的公式。</p>}
    </section>
  );
}
