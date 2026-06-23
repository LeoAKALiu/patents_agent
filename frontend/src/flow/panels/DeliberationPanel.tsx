import { Loader2, UsersRound } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AgentDoctorReport, DeliberationRun } from "@/api";
import { deliberationRunModeLabel, logLevelLabel, pipelineRunStatusLabel } from "@/domain";
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
      <div className="guided-panel-actions">
        <Button className="guided-panel-action" variant="glass-soft" size="sm" onClick={() => onOpenExpertTool("deliberate")} type="button">
          <UsersRound size={16} aria-hidden="true" />
          <span>查看会审详情</span>
        </Button>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="deliberation"
        selectedProviders={selectedProviders}
        disabled={deliberationBusy}
        onToggleProvider={onToggleProvider}
      />
      <Button className="guided-primary-action" variant="glass-primary" disabled={deliberationBusy} onClick={onStartDeliberation} type="button">
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
      <DeliberationRunHistory runs={runs} />
    </section>
  );
}

function DeliberationRunHistory({ runs }: { runs: DeliberationRun[] }) {
  if (runs.length === 0) {
    return (
      <section className="guided-run-history" aria-label="会审记录与日志">
        <div className="settings-group-header">
          <h3>会审记录与日志</h3>
          <p>暂无会审记录。启动会审后会在这里显示运行事件、日志和失败原因。</p>
        </div>
      </section>
    );
  }

  return (
    <section className="guided-run-history" aria-label="会审记录与日志">
      <div className="settings-group-header">
        <h3>会审记录与日志</h3>
        <p>显示最近 {Math.min(runs.length, 5)} 轮会审的状态、事件、日志和失败原因。</p>
      </div>
      <div className="guided-run-list">
        {runs.slice(0, 5).map((run) => (
          <DeliberationRunRecord key={run.id} run={run} />
        ))}
      </div>
    </section>
  );
}

function DeliberationRunRecord({ run }: { run: DeliberationRun }) {
  const latestLogs = run.logs.slice(-4).reverse();
  const latestEvents = run.events.slice(-4).reverse();
  const latestFailures = run.failures.slice(-3);
  const latestRuntimeFailures = (run.failure_details ?? []).slice(-3);

  return (
    <article className="guided-run-record">
      <div className="guided-run-record-head">
        <div>
          <strong>run {run.id.slice(0, 10)}</strong>
          {run.retry_of && <span>重试 {run.retry_of.slice(0, 8)}</span>}
        </div>
        <div className="result-meta">
          <Badge variant={run.status === "completed" ? "success" : run.status === "failed" ? "destructive" : "secondary"} className="text-xs">
            {pipelineRunStatusLabel(run.status)}
          </Badge>
          <span>{deliberationRunModeLabel(run.run_mode)}</span>
        </div>
      </div>

      <div className="guided-run-metrics" aria-label="会审运行摘要">
        <span>{run.providers.join(" / ") || "无 provider"}</span>
        <span>{run.stage_results.length} 阶段</span>
        <span>{run.logs.length} 日志</span>
        <span>{run.failures.length + (run.failure_details?.length ?? 0)} 失败</span>
      </div>

      {latestEvents.length > 0 && (
        <div className="guided-run-events" aria-label="最近事件">
          {latestEvents.map((event, index) => (
            <span key={`${run.id}-event-${index}`}>{event}</span>
          ))}
        </div>
      )}

      <div className="guided-run-log-list" aria-label="运行日志">
        {latestLogs.length > 0 ? (
          latestLogs.map((log, index) => (
            <article className={`guided-run-log ${log.level}`} key={`${run.id}-log-${index}`}>
              <div>
                <strong>{logLevelLabel(log.level)}</strong>
                <span>{log.provider_id || "provider"} / {log.phase || "phase"}{typeof log.attempt === "number" ? ` / attempt ${log.attempt}` : ""}</span>
              </div>
              <p>{log.message || log.detail || "无日志消息"}</p>
              {log.detail && log.detail !== log.message && <pre>{log.detail}</pre>}
              {log.repair_suggestion && <p className="workflow-hint">建议：{log.repair_suggestion}</p>}
            </article>
          ))
        ) : (
          <p className="workflow-hint">暂无详细日志；最近事件会先显示在上方。</p>
        )}
      </div>

      {(latestFailures.length > 0 || latestRuntimeFailures.length > 0) && (
        <div className="guided-run-failure-list" aria-label="失败原因">
          {latestFailures.map((failure, index) => (
            <p key={`${run.id}-failure-${index}`}>
              {failure.provider_id} / {failure.phase} / {failure.reason}：{failure.message}
            </p>
          ))}
          {latestRuntimeFailures.map((failure, index) => (
            <p key={`${run.id}-runtime-failure-${index}`}>
              {failure.provider ?? "runtime"} / {failure.stage} / {failure.reason}：{failure.message}
              {failure.repair_suggestion ? ` 建议：${failure.repair_suggestion}` : ""}
            </p>
          ))}
        </div>
      )}
    </article>
  );
}
