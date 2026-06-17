import { Loader2, UsersRound } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AgentDoctorReport, DeliberationRun } from "@/api";
import { deliberationRunModeLabel } from "@/domain";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
} from "../runtimeWidgets";
import type { ExpertToolOpener } from "../parts";

export interface DeliberationPanelProps {
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
  onOpenExpertTool: ExpertToolOpener;
}

export function DeliberationPanel({
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
}: DeliberationPanelProps) {
  const activeRun = guidedActiveRun(runs);
  const deliberationBusy = busy === "deliberate" || Boolean(activeRun);
  return (
    <section className="grid gap-3.5 p-5 rounded-lg border border-app-border bg-app-surface">
      <div className="flex items-start justify-between gap-3.5">
        <div>
          <h3>多智能体会审</h3>
          <p>生成前需完成会审，用于收敛权利要求边界、说明书支撑和规避风险。</p>
        </div>
        <UsersRound size={24} />
      </div>
      <div className="button-row">
        <Button variant="glass-soft" size="icon" onClick={() => onOpenExpertTool("deliberate")} type="button">
          查看会审详情
        </Button>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="deliberation"
        selectedProviders={selectedProviders}
        disabled={deliberationBusy}
        onToggleProvider={onToggleProvider}
      />
      <Button variant="glass-primary" disabled={deliberationBusy} onClick={onStartDeliberation} type="button">
        {deliberationBusy ? <Loader2 className="spin" size={17} /> : <UsersRound size={17} />}
        <span>{activeRun ? "会审中" : deliberation ? "重新会审" : "启动多智能体会审"}</span>
      </Button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "deliberate"} />
      <GuidedRuntimeConsole run={activeRun} label="会审运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {deliberation?.strategy_brief && (
        <article className="guided-choice selected">
          <div className="result-meta">
            <Badge variant="success" className="text-xs">{deliberationRunModeLabel(deliberation.run_mode)}</Badge>
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
