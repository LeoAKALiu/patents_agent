import { ClipboardCheck, Loader2 } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import {
  postDraftReviewReportUrl,
  type AgentDoctorReport,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import type { GuidedActionGate } from "@/guidedFlow";
import {
  GuidedOperationConsole,
  GuidedRuntimeActions,
  GuidedRuntimeConsole,
  GuidedRuntimeFailures,
  guidedActiveRun,
} from "../runtimeWidgets";
import { ActionGateHint } from "../parts";

export interface PostDraftReviewPanelProps {
  actionGate: GuidedActionGate;
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
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
}

export function PostDraftReviewPanel({
  actionGate,
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
  onCancelRun,
  onRetryRun,
  onToggleProvider,
}: PostDraftReviewPanelProps) {
  const passed = Boolean(review?.status === "completed" && review.export_allowed);
  const blocked = Boolean(review?.status === "completed" && !review.export_allowed);
  const activeRun = guidedActiveRun(runs);
  const reviewBusy = busy === "post-draft-review" || Boolean(activeRun);
  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>成稿后多智能体会审</h3>
          <p>正式导出前必选。多智能体会审权利要求质量、说明书清洁度、技术硬度，再综合裁决。</p>
        </div>
        <ClipboardCheck size={24} />
      </div>
      <div className="result-meta">
        <span className={passed ? "status-badge" : blocked ? "status-badge danger" : "status-badge warn"}>
          {passed ? "已通过" : blocked ? "阻止正式导出" : "等待会审"}
        </span>
        <span>当前成稿：{currentDraftHash ? currentDraftHash.slice(0, 12) : "未生成"}</span>
        <span>正式稿：{officialCompileRun?.official_package_hash.slice(0, 12) ?? "未编译"}</span>
      </div>
      <AgentProviderCards
        doctor={doctor}
        role="post_review"
        selectedProviders={selectedProviders}
        disabled={!actionGate.allowed || reviewBusy}
        onToggleProvider={onToggleProvider}
      />
      <ActionGateHint gate={actionGate} />
      <button
        className="primary"
        disabled={!actionGate.allowed || reviewBusy}
        onClick={onStartPostDraftReview}
        title={actionGate.reason || undefined}
        type="button"
      >
        {reviewBusy ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
        <span>{activeRun ? "成稿会审中" : review ? "重新成稿会审" : "启动成稿会审"}</span>
      </button>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "post-draft-review"} />
      <GuidedRuntimeConsole run={activeRun} label="成稿会审运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {review && (
        <article className={passed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            <span className={passed ? "status-badge" : "status-badge danger"}>{pipelineRunStatusLabel(review.status)}</span>
            <span>{review.providers.join(" / ") || "默认三方"}</span>
            <span>会审版本：{review.draft_package_hash.slice(0, 12)}</span>
            {review.official_package_hash && <span>正式稿版本：{review.official_package_hash.slice(0, 12)}</span>}
            {project && (
              <a href={postDraftReviewReportUrl(project.id, review.id)} rel="noreferrer" target="_blank">
                会审报告
              </a>
            )}
          </div>
          <h4>{passed ? "综合裁决：允许正式导出" : "综合裁决：需要修订"}</h4>
          {review.blocking_issues.length > 0 && <p>阻断项：{review.blocking_issues.slice(0, 3).join("；")}</p>}
          {review.contamination_hits.length > 0 && <p>问题项：{review.contamination_hits.slice(0, 5).join("；")}</p>}
          {blocked && (
            <p className="workflow-hint">
              导出已锁定：请根据上方阻断项修改初稿，重新编译正式稿后再「重新成稿会审」，通过后即可导出。完整阻断项请查看会审报告。
            </p>
          )}
        </article>
      )}
      {!review && runs.length > 0 && (
        <p className="workflow-hint">已有成稿会审记录，但不属于当前成稿。请重新运行成稿会审。</p>
      )}
    </section>
  );
}
