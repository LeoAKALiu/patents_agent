import { Loader2, Sigma, AlertTriangle } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

function severityBadgeVariant(severity: string): "success" | "warning" | "destructive" | "secondary" {
  switch (severity) {
    case "normal":
      return "success";
    case "warning":
      return "warning";
    case "high":
    case "critical":
      return "destructive";
    default:
      return "secondary";
  }
}

function severityLabel(severity: string): string {
  switch (severity) {
    case "normal":
      return "公式质量正常";
    case "warning":
      return "公式质量偏低";
    case "high":
      return "公式质量严重不足";
    case "critical":
      return "公式质量不可用";
    default:
      return severity;
  }
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
  const pkg = formulaRun?.package;
  const isFallback = Boolean(pkg?.is_fallback);
  const qualitySeverity = pkg?.quality_severity ?? "normal";
  const hasQualityIssue = qualitySeverity === "warning" || qualitySeverity === "high" || qualitySeverity === "critical";

  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>核心公式</h3>
          <p>{required ? "本项目含公式型信号，需先凝练公式。" : "本项目未检测到必须凝练的公式信号。"}</p>
        </div>
        <Sigma size={24} />
      </div>
      {requirement && (
        <div className="result-meta">
          {required ? <Badge variant="warning" className="text-xs">需要公式</Badge> : <Badge variant="success" className="text-xs">无需公式</Badge>}
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
        <Button variant="glass-primary" disabled={!project || formulaBusy} onClick={onStartFormula} type="button">
          {formulaBusy ? <Loader2 className="spin" size={17} /> : <Sigma size={17} />}
          <span>{activeRun ? "公式凝练中" : formulaRun ? "重新凝练核心公式" : "凝练核心公式"}</span>
        </Button>
      )}
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "formula"} />
      <GuidedRuntimeConsole run={activeRun} label="核心公式运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {formulaRun?.package && (
        <article className="guided-choice selected">
          <div className="result-meta">
            <Badge variant="success" className="text-xs">{pipelineRunStatusLabel(formulaRun.status)}</Badge>
            <span>{formulaRun.package.formula_blocks.length} 个公式</span>
            {formulaRun.providers.length > 0 && <span>{formulaRun.providers.join(" / ")}</span>}
            {project && (
              <a href={formulaMarkdownUrl(project.id, formulaRun.id)} rel="noreferrer" target="_blank">
                公式说明
              </a>
            )}
            {isFallback && (
              <Badge variant="destructive" className="text-xs gap-1">
                <AlertTriangle size={11} />
                回退公式
              </Badge>
            )}
            {hasQualityIssue && !isFallback && (
              <Badge variant={severityBadgeVariant(qualitySeverity)} className="text-xs">
                {severityLabel(qualitySeverity)}
              </Badge>
            )}
          </div>
          {/* Fallback warning banner */}
          {isFallback && (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
              <p className="font-semibold flex items-center gap-1.5">
                <AlertTriangle size={14} />
                系统回退公式 — 需要人工确认
              </p>
              <p className="mt-1 text-muted-foreground">
                模型输出未能成功解析，系统生成了通用回退公式。
                {qualitySeverity === "high" && " 本项目包含矩阵/权重/优化/概率/阈值等强公式信号，回退公式不足以支撑权利要求。"}
                {qualitySeverity === "critical" && " 公式质量严重不足，请重新运行公式凝练或手工编写。"}
              </p>
              <p className="mt-1.5 text-xs text-muted-foreground">
                建议操作：检查模型配置后重新运行公式凝练，或根据项目特征手工编写核心公式。
              </p>
            </div>
          )}
          {/* Non-fallback quality warning */}
          {hasQualityIssue && !isFallback && (
            <div className="rounded-md border border-warning/40 bg-warning/5 p-3 text-sm">
              <p className="font-semibold flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-warning" />
                公式质量提示
              </p>
              <p className="mt-1 text-muted-foreground">
                {qualitySeverity === "warning" && "生成的公式可能未充分覆盖检测到的强公式信号（矩阵/权重/优化/概率/阈值），建议检查公式是否匹配项目需求。"}
                {qualitySeverity === "high" && "生成的公式未检测到与项目信号相关的关键词，可能存在偏差。"}
              </p>
            </div>
          )}
          <h4>{formulaRun.package.summary}</h4>
          <p>{formulaRun.package.formula_blocks.map((block) => `${block.id} ${block.name}`).join("；")}</p>
        </article>
      )}
      {!formulaRun && runs.length > 0 && <p className="workflow-hint">已有公式运行记录，但尚无已完成的公式。</p>}
    </section>
  );
}
