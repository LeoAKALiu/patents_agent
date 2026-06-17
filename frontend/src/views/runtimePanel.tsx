/**
 * Runtime console cluster — extracted from App.tsx (M3-B').
 *
 * Self-contained leaf views for showing in-flight runs + busy operation logs
 * in the expert-tool views. Shared runtime shape + helpers live here so the
 * consuming views (CorpusBuildView, MoatView, …) can import them without
 * pulling App() closure scope.
 *
 * No closure over App() state — explicit props only.
 */
import { AlertTriangle, RefreshCw } from "@/lib/icons";
import type { RuntimeFailure, RuntimeStageState } from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import { runtimeDisplayElapsedMs, runtimeDisplayElapsedSeconds, useRuntimeNow } from "@/runtimeDisplay";
import { guidedOperationLog } from "@/guidedFlow";
import { OperationConsole } from "@/ui/OperationConsole";

/** Shared runtime run shape used across the expert-tool views. */
export type RuntimeAwareRun = {
  id: string;
  status: string;
  runtime_state?: RuntimeStageState | null;
  failure_details?: RuntimeFailure[];
  events?: string[];
  providers?: string[];
  stage_results?: unknown[];
  failures?: unknown[];
  logs?: unknown[];
  cancel_requested?: boolean;
  retry_of?: string | null;
};

export function isActiveRun(run: RuntimeAwareRun | null | undefined): run is RuntimeAwareRun {
  return Boolean(run && (run.status === "queued" || run.status === "running"));
}

export function latestActiveRun<T extends RuntimeAwareRun>(runs: T[]): T | null {
  return runs.find(isActiveRun) ?? null;
}

export function isRetryableRun(run: RuntimeAwareRun): boolean {
  const active = run.status === "queued" || run.status === "running";
  return (
    !active
    && (run.status === "failed" || run.status === "interrupted" || Boolean(run.failure_details?.some((failure) => failure.retryable)))
  );
}

export function runtimeStageLabel(stage?: string | null): string {
  if (!stage) return "等待调度";
  const labels: Record<string, string> = {
    queued: "等待调度",
    disclosure_scan: "扫描材料",
    patent_points: "提炼专利点",
    prior_art_terms: "规划检索词",
    prior_art_search: "检索现有技术",
    prior_art_relevance: "现有技术对比",
    disclosure_body: "生成交底正文",
    disclosure_mermaid: "生成流程图",
    disclosure_image_prompt: "生成绘图提示",
    disclosure_self_check: "交底自检",
    disclosure_package: "整理交底包",
    deep_research_plan: "Deep Research 规划",
    deep_research_evidence: "证据账本",
    deep_research_final: "研究包收尾",
    deliberation_prepare: "准备会审上下文",
    deliberation: "多智能体会审",
    deliberation_finalize: "会审收尾",
    formula_assessment: "判断公式需求",
    formula_generation: "凝练核心公式",
    post_draft_review: "成稿会审",
  };
  if (labels[stage]) return labels[stage];
  if (stage.startsWith("deep_research_queries")) return "Deep Research 检索词";
  if (stage.startsWith("deep_research_search")) return "Deep Research 检索";
  if (stage.startsWith("deep_research_synthesis")) return "Deep Research 归纳";
  if (stage.startsWith("deep_research_obviousness")) return "创造性攻击模拟";
  return stage.replaceAll("_", " ");
}

export function formatRuntimeMs(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/** Busy operation log block (status + lines). */
export function BusyOperationConsole({ log }: { log: ReturnType<typeof guidedOperationLog> }) {
  if (!log) return null;
  return (
    <div className="bg-[var(--surface-inset)] text-[var(--action-primary-contrast)]/90 p-4 rounded-lg font-mono text-xs overflow-auto max-h-32 mt-2 w-full" role="status" aria-label={log.label}>
      <pre>{log.lines.join("\n")}</pre>
    </div>
  );
}

/** Cancel/retry row for an in-flight or retryable run. */
export function RuntimeRunActions({
  run,
  disabled = false,
  onCancel,
  onRetry,
}: {
  run: RuntimeAwareRun;
  disabled?: boolean;
  onCancel?: (runId: string) => void;
  onRetry?: (runId: string) => void;
}) {
  const canCancel = Boolean(onCancel && isActiveRun(run) && !run.cancel_requested);
  const canRetry = Boolean(onRetry && isRetryableRun(run));
  if (!canCancel && !canRetry) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      {canCancel && (
        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-950/40 hover:bg-red-900/50 text-red-100 border border-red-500/30 disabled:opacity-50 px-3 py-2 text-sm transition-colors"
          disabled={disabled}
          onClick={() => onCancel?.(run.id)}
          title="请求取消当前运行"
          type="button"
        >
          <AlertTriangle size={15} />
          <span>取消运行</span>
        </button>
      )}
      {canRetry && (
        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--surface-inset)] hover:bg-[var(--surface-subtle)] text-[var(--text-primary)] border border-[var(--border-strong)] disabled:opacity-50 px-3 py-2 text-sm transition-colors"
          disabled={disabled}
          onClick={() => onRetry?.(run.id)}
          title="按相同输入重试该运行"
          type="button"
        >
          <RefreshCw size={15} />
          <span>重试</span>
        </button>
      )}
    </div>
  );
}

/** Live runtime console for a single run. */
export function RuntimeRunConsole({
  run,
  title,
  actionDisabled,
  onCancel,
}: {
  run: RuntimeAwareRun | null;
  title: string;
  actionDisabled?: boolean;
  onCancel?: (runId: string) => void;
}) {
  const active = isActiveRun(run);
  const now = useRuntimeNow(active);
  if (!run || !active) return null;
  const state = run.runtime_state ?? null;
  const elapsedMs = runtimeDisplayElapsedMs(state, now);
  const elapsedSeconds = runtimeDisplayElapsedSeconds(state, now);
  const lines = [
    `run ${run.id.slice(0, 10)} / ${pipelineRunStatusLabel(run.status)}`,
    `stage ${runtimeStageLabel(state?.current_stage)}`,
    state?.provider ? `provider ${state.provider}` : "",
    state?.subtask ? `task ${state.subtask}` : "",
    state?.query ? `query ${state.query}` : "",
    state ? `elapsed ${formatRuntimeMs(elapsedMs)}` : "",
    typeof state?.partial_artifact_count === "number" ? `partials ${state.partial_artifact_count}` : "",
    typeof state?.warning_count === "number" ? `warnings ${state.warning_count}` : "",
    state?.timeout_ms ? `stage timeout ${formatRuntimeMs(state.timeout_ms)}` : "",
    run.events?.at(-1) ? `event ${run.events.at(-1)}` : "",
  ].filter(Boolean);
  return (
    <div className="grid gap-2">
      <OperationConsole label={title} lines={lines} elapsedSeconds={elapsedSeconds} />
      <RuntimeRunActions run={run} disabled={actionDisabled} onCancel={onCancel} />
    </div>
  );
}

/** Last-three failure detail articles for a run. */
export function RuntimeFailurePanel({ run }: { run: RuntimeAwareRun | null }) {
  const failures = run?.failure_details ?? [];
  if (!run || failures.length === 0) return null;
  return (
    <div className="grid gap-2">
      {failures.slice(-3).map((failure, index) => (
        <article className="rounded-lg border border-red-500/30 bg-red-950/20 p-3 text-sm" key={`${run.id}-runtime-failure-${index}`}>
          <div className="flex flex-wrap items-center gap-2 text-xs text-red-200/80">
            <span>{failure.reason}</span>
            <span>{runtimeStageLabel(failure.stage)}</span>
            {failure.provider && <span>{failure.provider}</span>}
            <span>{formatRuntimeMs(failure.elapsed_ms)}</span>
          </div>
          <p className="mt-1 text-[var(--text-primary)]">{failure.message}</p>
          {failure.repair_suggestion && <p className="mt-1 text-[var(--text-soft)]">{failure.repair_suggestion}</p>}
        </article>
      ))}
    </div>
  );
}
