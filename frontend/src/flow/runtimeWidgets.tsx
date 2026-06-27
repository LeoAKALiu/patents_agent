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
import { runtimeDisplayElapsedSeconds, runtimeFailureCopy, useRuntimeNow } from "@/runtimeDisplay";
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
  if (stage === "disclosure_scan") return "发明点提炼";
  if (stage === "project_material_scan") return "材料梳理";
  if (stage === "formula_generation") return "凝练核心公式";
  if (stage === "post_draft_review") return "成稿会审";
  if (stage === "deliberation_finalize") return "会审收尾";
  if (stage === "disclosure_package") return "整理交底包";
  if (stage.startsWith("deep_research")) return "Deep Research";
  return stage.replaceAll("_", " ");
}

export function guidedRuntimeSubtaskLabel(subtask?: string | null): string {
  if (!subtask) return "";
  if (subtask === "project/material scan") return "项目与材料分析";
  if (subtask.includes("disclosure")) return "发明点提炼";
  if (subtask.includes("material")) return "材料分析";
  if (subtask === "post_draft_claims_reviewer" || subtask === "post-draft claims review") return "权利要求复核";
  if (subtask === "post_draft_spec_cleaner" || subtask === "post-draft specification cleanup") return "说明书清洁度复核";
  if (subtask === "post_draft_technical_hardness" || subtask === "post-draft technical hardness review") return "技术硬度复核";
  if (subtask === "post_draft_chair_synthesis" || subtask === "post-draft chair synthesis") return "会审主席综合";
  if (subtask.includes("post_draft")) return "成稿会审";
  return "运行中";
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
        <Button
          className="guided-runtime-action"
          variant="destructive"
          size="sm"
          disabled={disabled}
          onClick={() => onCancel?.(run.id)}
          type="button"
        >
          <AlertTriangle size={16} />
          <span>取消运行</span>
        </Button>
      )}
      {canRetry && (
        <Button
          className="guided-runtime-action"
          variant="glass-soft"
          size="sm"
          disabled={disabled}
          onClick={() => onRetry?.(run.id)}
          type="button"
        >
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
  const latestEvent = run.events?.at(-1);
  const lines = [
    `运行 ${pipelineRunStatusLabel(run.status)}`,
    `阶段 ${guidedRuntimeStageLabel(state?.current_stage)}`,
    state?.provider ? "服务 模型服务" : "",
    state?.subtask ? `任务 ${guidedRuntimeSubtaskLabel(state.subtask)}` : "",
    state ? `耗时 ${formatElapsedLabel(elapsedSeconds)}` : "",
    typeof state?.partial_artifact_count === "number" ? `中间结果 ${state.partial_artifact_count}` : "",
    typeof state?.warning_count === "number" ? `提示 ${state.warning_count}` : "",
    latestEvent ? `事件 ${runtimeEventLabel(latestEvent)}` : "",
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

function runtimeEventLabel(event: string): string {
  if (event === "cancel requested") return "正在取消";
  if (event === "run cancelled") return "已取消";
  if (event === "run started") return "已开始";
  return "状态已更新";
}

/** Last-two failure detail lines for a run. */
export function GuidedRuntimeFailures({ run }: { run: GuidedRuntimeRun | null }) {
  const failures = run?.failure_details ?? [];
  if (failures.length === 0) return null;
  return (
    <div className="guided-runtime-failures">
      {failures.slice(-2).map((failure, index) => {
        const copy = runtimeFailureCopy(failure);
        const detail = copy.detail
          ?? [
            failure.reason,
            guidedRuntimeStageLabel(failure.stage),
            failure.provider ? agentProviderRuntimeLabel(failure.provider) : "",
            failure.message,
            failure.repair_suggestion,
          ].filter(Boolean).join(" / ");
        if (copy.tone === "info") {
          return (
            <div className="callout callout-info" key={`${run?.id}-failure-${index}`}>
              <div>
                <strong>{copy.title}</strong>
                <p>{copy.message}</p>
                {detail && (
                  <details>
                    <summary>诊断详情</summary>
                    <code>{detail}</code>
                  </details>
                )}
              </div>
            </div>
          );
        }
        return (
          <div key={`${run?.id}-failure-${index}`}>
            <p>{copy.title}：{copy.message}</p>
            {detail && (
              <details>
                <summary>诊断详情</summary>
                <code>{detail}</code>
              </details>
            )}
          </div>
        );
      })}
    </div>
  );
}
