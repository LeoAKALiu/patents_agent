import { Gauge, Loader2, Wand2 } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  FilingReadinessReport,
} from "@/api";
import { qualitySummaryFromRuns, type GuidedActionGate } from "@/guidedFlow";
import { GuidedOperationConsole } from "../runtimeWidgets";
import { ActionGateHint, GuidedScoreTile, type ExpertToolOpener } from "../parts";

export interface QualityPanelProps {
  actionGate: GuidedActionGate;
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
  busy: string;
  busyElapsedSeconds: number;
  onRunQualityChecks: () => void;
  onImproveScore: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onOpenExpertTool: ExpertToolOpener;
}

export function QualityPanel({
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
}: QualityPanelProps) {
  const summary = qualitySummaryFromRuns({ filingReport, worksheet, completionRun });
  const actionsDisabled = !actionGate.allowed || Boolean(busy);
  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>质量检查与补强</h3>
          <p>依次运行提交成熟度、权利要求防线、初稿完善和审查意见。</p>
        </div>
        <Gauge size={24} />
      </div>
      {(filingReport || worksheet || completionRun) && (
        <p className="workflow-hint">已获得部分检查结果。可以继续补强，也可以重新运行质量检查。</p>
      )}
      <div className="button-row">
        <Button variant="glass-soft" size="icon" onClick={() => onOpenExpertTool("readiness")} type="button">
          查看提交成熟度
        </Button>
        <Button variant="glass-soft" size="icon" onClick={() => onOpenExpertTool("claimDefense")} type="button">
          查看权利要求防线
        </Button>
        <Button variant="glass-soft" size="icon" onClick={() => onOpenExpertTool("completion")} type="button">
          查看初稿完善
        </Button>
      </div>
      <ActionGateHint gate={actionGate} />
      <div className="button-row">
        <Button
          variant="glass-primary"
          disabled={actionsDisabled}
          onClick={onRunQualityChecks}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "guided-quality" ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
          <span>运行质量检查</span>
        </Button>
        <Button
          variant="glass-primary"
          disabled={actionsDisabled}
          onClick={onImproveScore}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "score-improve" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>一键提升分数</span>
        </Button>
      </div>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-quality"} />
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "score-improve"} />
      <div className="guided-score-grid">
        <GuidedScoreTile label="状态" value={summary.statusLabel} />
        <GuidedScoreTile
          label="授权稳定性"
          value={summary.authorizationStability === null ? "未评分" : `${summary.authorizationStability}/100`}
        />
        <GuidedScoreTile label="保护范围" value={summary.protectionScope === null ? "未评分" : `${summary.protectionScope}/100`} />
        <GuidedScoreTile label="提交成熟度" value={summary.filingMaturity === null ? "未评分" : `${summary.filingMaturity}/100`} />
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
            <Button variant="glass-primary" onClick={() => onAcceptPatch(completionRun.id, patch.id)} type="button">
              接受补强建议
            </Button>
          </article>
        ))}
    </section>
  );
}
