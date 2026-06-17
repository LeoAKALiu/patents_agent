/**
 * Guided-flow runtime widgets — extracted from GuidedPatentFlow.tsx (M4).
 *
 * Self-contained leaf components shared across step panels: the operation
 * console (busy spinner + elapsed), the per-run runtime console, and the
 * cancel/retry action row + failure list. Plus their pure helpers (elapsed
 * formatting, stage/provider labels, active/retryable run selectors) and the
 * shared GuidedRuntimeRun shape.
 *
 * No closure over GuidedPatentFlowView props — explicit props only.
 */
import { AlertTriangle, RefreshCw } from "@/lib/icons";
import { Button } from "@/components/ui/button";
import type { RuntimeFailure, RuntimeStageState } from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import { runtimeDisplayElapsedSeconds, useRuntimeNow } from "@/runtimeDisplay";
import { guidedOperationLog } from "@/guidedFlow";

export type GuidedRuntimeRun = {
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

/** The in-flight run (queued/running), if any. */
export function guidedActiveRun<T extends GuidedRuntimeRun>(runs: T[]): T | null {
  return runs.find((run) => run.status === "queued" || run.status === "running") ?? null;
}

/** A run is retryable when it's terminal-failed or has a retryable failure detail. */
export function guidedRetryableRun(run: GuidedRuntimeRun): boolean {
  return (
    run.status !== "queued"
    && run.status !== "running"
    && (run.status === "failed"
      || run.status === "interrupted"
      || Boolean(run.failure_details?.some((failure) => failure.retryable)))
  );
}

/** mm:ss elapsed label. */
export function formatElapsedLabel(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

/** zh-CN label for a runtime stage id. */
export function guidedRuntimeStageLabel(stage?: string | null): string {
  if (!stage) return "等待调度";
  if (stage === "formula_generation") return "凝练核心公式";
  if (stage === "post_draft_review") return "成稿会审";
  if (stage === "deliberation_finalize") return "会审收尾";
  if (stage === "disclosure_package") return "整理交底包";
  if (stage.startsWith("deep_research")) return "Deep Research";
  return stage.replaceAll("_", " ");
}

/** Display name for an agent provider id. */
export function agentProviderRuntimeLabel(providerId: string): string {
  if (providerId === "codex") return "Codex";
  if (providerId === "deepseek") return "DeepSeek";
  if (providerId === "claude") return "Claude";
  if (providerId === "kimicode") return "KimiCode";
  if (providerId === "mimo") return "Mimo";
  return providerId;
}

/** Inline operation console shown while a guided operation is in flight. */
export function GuidedOperationConsole({
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

/** Cancel/retry row for an in-flight or retryable run. */
export function GuidedRuntimeActions({
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
        <Button variant="destructive" size="icon" disabled={disabled} onClick={() => onCancel?.(run.id)} type="button">
          <AlertTriangle size={16} />
          <span>取消运行</span>
        </Button>
      )}
      {canRetry && (
        <Button variant="glass-soft" size="icon" disabled={disabled} onClick={() => onRetry?.(run.id)} type="button">
          <RefreshCw size={16} />
          <span>重试</span>
        </Button>
      )}
    </div>
  );
}

/** Live runtime console for a single run (stage/provider/elapsed/events). */
export function GuidedRuntimeConsole({
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
  const active = Boolean(run && (run.status === "queued" || run.status === "running"));
  const now = useRuntimeNow(active);
  if (!run || !active) return null;
  const state = run.runtime_state ?? null;
  const elapsedSeconds = runtimeDisplayElapsedSeconds(state, now);
  const lines = [
    `run ${run.id.slice(0, 10)} / ${pipelineRunStatusLabel(run.status)}`,
    `stage ${guidedRuntimeStageLabel(state?.current_stage)}`,
    state?.provider ? `provider ${state.provider}` : "",
    state?.subtask ? `task ${state.subtask}` : "",
    state ? `elapsed ${formatElapsedLabel(elapsedSeconds)}` : "",
    typeof state?.partial_artifact_count === "number" ? `partials ${state.partial_artifact_count}` : "",
    typeof state?.warning_count === "number" ? `warnings ${state.warning_count}` : "",
    run.events?.at(-1) ? `event ${run.events.at(-1)}` : "",
  ].filter(Boolean);
  return (
    <div className="inline-console" role="status" aria-label={label}>
      <div className="console-heading">
        <span>{label}</span>
        <span>{formatElapsedLabel(elapsedSeconds)}</span>
      </div>
      <pre>{lines.join("\n")}</pre>
      <GuidedRuntimeActions run={run} disabled={Boolean(busy)} onCancel={onCancel} />
    </div>
  );
}

/** Last-two failure detail lines for a run. */
export function GuidedRuntimeFailures({ run }: { run: GuidedRuntimeRun | null }) {
  const failures = run?.failure_details ?? [];
  if (failures.length === 0) return null;
  return (
    <div className="guided-runtime-failures">
      {failures.slice(-2).map((failure, index) => {
        const provider = failure.provider ? ` / ${agentProviderRuntimeLabel(failure.provider)}` : "";
        return (
          <p key={`${run?.id}-failure-${index}`}>
            {failure.reason} / {guidedRuntimeStageLabel(failure.stage)}{provider}：{failure.message}
            {failure.repair_suggestion ? ` 建议：${failure.repair_suggestion}` : ""}
          </p>
        );
      })}
    </div>
  );
}
