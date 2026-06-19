import { useEffect, useMemo, useState } from "react";

import { ClipboardCheck, Loader2, PenLine, Save, Wand2, XCircle } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import { Badge } from "@/components/ui/badge";
import {
  postDraftReviewReportUrl,
  type AgentDoctorReport,
  type DraftPackage,
  type DraftPackageManualUpdate,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import type { GuidedActionGate } from "@/guidedFlow";
import {
  ActionDock,
  InfoCard,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";
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
  currentPackage: DraftPackage | null;
  officialCompileRun: OfficialCompileRun | null;
  doctor: AgentDoctorReport | null;
  selectedProviders: string[];
  busy: string;
  busyElapsedSeconds: number;
  onStartPostDraftReview: () => void;
  onStartKimiLanguagePolish: () => void;
  onApplySafePatches: (runId: string) => void;
  onSaveDraftPackage: (payload: DraftPackageManualUpdate) => void | Promise<void>;
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
  currentPackage,
  officialCompileRun,
  doctor,
  selectedProviders,
  busy,
  busyElapsedSeconds,
  onStartPostDraftReview,
  onStartKimiLanguagePolish,
  onApplySafePatches,
  onSaveDraftPackage,
  onCancelRun,
  onRetryRun,
  onToggleProvider,
}: PostDraftReviewPanelProps) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [activeIssue, setActiveIssue] = useState("");
  const [draftEditor, setDraftEditor] = useState<DraftPackageManualUpdate | null>(() =>
    currentPackage ? editableDraftFields(currentPackage) : null,
  );
  const passed = Boolean(review?.status === "completed" && review.export_allowed);
  const blocked = Boolean(review?.status === "completed" && !review.export_allowed);
  const activeRun = guidedActiveRun(runs);
  const reviewBusy = busy === "post-draft-review" || Boolean(activeRun);
  const safePatchCount = review
    ? review.chair_result?.official_safe_patches.length
      || review.role_results.reduce((count, result) => count + result.official_safe_patches.length, 0)
    : 0;
  const applyingSafePatches = busy === "post-draft-safe-patch";
  const polishing = busy === "kimi-language-polish";
  const savingDraft = busy === "draft-save";
  const reviewIssues = useMemo(() => collectPostDraftIssues(review), [review]);

  useEffect(() => {
    if (!editorOpen) {
      setDraftEditor(currentPackage ? editableDraftFields(currentPackage) : null);
    }
  }, [currentPackage, editorOpen]);

  function openDraftEditor(issue = "") {
    if (!currentPackage) return;
    setActiveIssue(issue);
    setDraftEditor(editableDraftFields(currentPackage));
    setEditorOpen(true);
  }

  async function handleSaveDraft() {
    if (!draftEditor) return;
    await onSaveDraftPackage(draftEditor);
    setEditorOpen(false);
  }

  function updateDraftField(field: keyof DraftPackageManualUpdate, value: string) {
    setDraftEditor((current) => current ? { ...current, [field]: value } : current);
  }

  return (
    <section className="grid gap-4">
      <StatusStrip
        aria-label="成稿会审状态"
        items={[
          { label: "会审状态", value: passed ? "已通过" : blocked ? "阻止导出" : activeRun ? "运行中" : "等待会审" },
          { label: "当前成稿", value: currentDraftHash ? currentDraftHash.slice(0, 12) : "未生成" },
          { label: "正式稿", value: officialCompileRun?.official_package_hash.slice(0, 12) ?? "未编译" },
          { label: "历史记录", value: `${runs.length} 次` },
        ]}
      />

      <SettingsGroup
        title="成稿后多智能体会审"
        description="正式导出前必选。多智能体会审权利要求质量、说明书清洁度、技术硬度，再综合裁决。"
      >
        <InfoCard
          icon={<ClipboardCheck size={18} aria-hidden="true" />}
          tone={passed ? "success" : blocked ? "danger" : "warn"}
          title={passed ? "综合裁决：允许正式导出" : blocked ? "综合裁决：需要修订" : "等待成稿会审"}
          description={
            passed
              ? "当前正式稿已通过会审，可进入导出确认。"
              : blocked
                ? safePatchCount > 0
                  ? "导出已锁定。可先将会审给出的官方安全补丁写回初稿，再重新编译正式稿。"
                  : "导出已锁定，请根据阻断项修改初稿并重新编译正式稿。"
                : "选择可用智能体后启动会审，结果会绑定当前成稿和正式稿哈希。"
          }
          meta={(
            <>
              {passed ? <Badge variant="success" className="text-xs">已通过</Badge> : blocked ? <Badge variant="destructive" className="text-xs">阻止正式导出</Badge> : <Badge variant="warning" className="text-xs">等待会审</Badge>}
              {review?.draft_package_hash && <span className="hash-chip">{review.draft_package_hash.slice(0, 12)}</span>}
              {blocked && safePatchCount > 0 && <Badge variant="secondary" className="text-xs">安全补丁 {safePatchCount} 条</Badge>}
            </>
          )}
          action={blocked && review && safePatchCount > 0 ? (
            <button
              className="btn btn-primary"
              disabled={reviewBusy || applyingSafePatches}
              onClick={() => onApplySafePatches(review.id)}
              type="button"
            >
              {applyingSafePatches ? <Loader2 className="spin" size={16} /> : <ClipboardCheck size={16} />}
              <span>{applyingSafePatches ? "正在应用补丁" : "应用安全补丁到初稿"}</span>
            </button>
          ) : undefined}
        />
      <section className="post-review-workbench" aria-label="阻断修复工作台">
        <div className="post-review-issues">
          <div className="post-review-panel-heading">
            <div>
              <h4>阻断修复工作台</h4>
              <p>阻断项、命中项和改写建议集中处理；长列表只在左侧滚动。</p>
            </div>
            <Badge variant={blocked ? "destructive" : "secondary"} className="text-xs">
              {reviewIssues.length} 项
            </Badge>
          </div>
          <div className="review-issue-scroll" tabIndex={0}>
            {reviewIssues.length > 0 ? reviewIssues.map((issue, index) => (
              <article className="review-issue-card" key={`${issue.kind}-${index}-${issue.text}`}>
                <Badge variant={issue.kind === "阻断" ? "destructive" : issue.kind === "命中" ? "warning" : "secondary"} className="text-xs">
                  {issue.kind}
                </Badge>
                <p>{issue.text}</p>
                <div className="review-issue-actions">
                  <button
                    className="btn btn-secondary"
                    disabled={!currentPackage}
                    onClick={() => openDraftEditor(issue.text)}
                    type="button"
                  >
                    <PenLine size={15} />
                    <span>人工修正</span>
                  </button>
                  <button
                    className="btn btn-primary"
                    disabled={!review || safePatchCount === 0 || reviewBusy || applyingSafePatches}
                    onClick={() => review && onApplySafePatches(review.id)}
                    type="button"
                  >
                    {applyingSafePatches ? <Loader2 className="spin" size={15} /> : <Wand2 size={15} />}
                    <span>一键AI修正</span>
                  </button>
                </div>
              </article>
            )) : (
              <div className="empty-panel compact">
                <strong>暂无阻断项</strong>
                <p>运行成稿会审后，这里会显示需要处理的问题。</p>
              </div>
            )}
          </div>
        </div>
        <div className="post-review-draft">
          <div className="post-review-panel-heading">
            <div>
              <h4>当前内部初稿</h4>
              <p>在独立大窗口中查看和手动修改正文。</p>
            </div>
            <button
              className="btn btn-secondary"
              disabled={!currentPackage}
              onClick={() => openDraftEditor()}
              type="button"
            >
              <PenLine size={15} />
              <span>打开大编辑器</span>
            </button>
          </div>
          {currentPackage ? (
            <div className="draft-editor-summary">
              <strong>{currentPackage.title || "未命名初稿"}</strong>
              <p>{currentPackage.abstract || "暂无摘要。"}</p>
              <dl>
                <div><dt>权利要求书</dt><dd>{sectionLength(currentPackage.claims)} 字</dd></div>
                <div><dt>说明书</dt><dd>{sectionLength(currentPackage.description)} 字</dd></div>
                <div><dt>附图说明</dt><dd>{sectionLength(currentPackage.drawing_description)} 字</dd></div>
              </dl>
            </div>
          ) : (
            <div className="empty-panel compact">
              <strong>暂无内部初稿</strong>
              <p>请先生成初稿，再进行成稿会审修复。</p>
            </div>
          )}
        </div>
      </section>
      <AgentProviderCards
        doctor={doctor}
        role="post_review"
        selectedProviders={selectedProviders}
        disabled={!actionGate.allowed || reviewBusy}
        onToggleProvider={onToggleProvider}
      />
      <ActionGateHint gate={actionGate} />
      <ActionDock meta="会审结果必须与当前成稿哈希和正式稿哈希匹配，才会放行正式导出。润色会生成新的正式稿版本。">
        {officialCompileRun?.official_package && (
          <button
            className="btn btn-secondary"
            disabled={!actionGate.allowed || Boolean(busy)}
            onClick={onStartKimiLanguagePolish}
            title={actionGate.reason || undefined}
            type="button"
          >
            {polishing ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
            <span>{polishing ? "Kimi 润色中" : "Kimi 成稿语言润色"}</span>
          </button>
        )}
        <button
          className="btn btn-primary"
          disabled={!actionGate.allowed || reviewBusy || Boolean(busy)}
          onClick={onStartPostDraftReview}
          title={actionGate.reason || undefined}
          type="button"
        >
          {reviewBusy ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
          <span>{activeRun ? "成稿会审中" : review ? "重新成稿会审" : "启动成稿会审"}</span>
        </button>
      </ActionDock>
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "post-draft-review" || polishing} />
      <GuidedRuntimeConsole run={activeRun} label="成稿会审运行中" busy={busy} onCancel={onCancelRun} />
      <GuidedRuntimeFailures run={runs[0] ?? null} />
      <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
      {review && (
        <article className={passed ? "guided-choice selected" : "guided-choice"}>
          <div className="result-meta">
            {passed ? <Badge variant="success" className="text-xs">{pipelineRunStatusLabel(review.status)}</Badge> : <Badge variant="destructive" className="text-xs">{pipelineRunStatusLabel(review.status)}</Badge>}
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
      </SettingsGroup>
      {editorOpen && draftEditor && (
        <div className="draft-editor-overlay" role="dialog" aria-modal="true" aria-label="当前内部初稿大编辑器">
          <section className="draft-editor-dialog">
            <header className="draft-editor-header">
              <div>
                <h3>当前内部初稿</h3>
                <p>{activeIssue ? `正在处理：${activeIssue}` : "手动修订会让旧正式稿和旧成稿会审失效。"}</p>
              </div>
              <button className="icon-button" onClick={() => setEditorOpen(false)} type="button" aria-label="关闭大编辑器">
                <XCircle size={18} />
              </button>
            </header>
            <div className="draft-editor-body">
              <label className="field">
                <span>标题</span>
                <input
                  value={draftEditor.title}
                  onChange={(event) => updateDraftField("title", event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>摘要</span>
                <textarea
                  className="draft-editor-textarea compact"
                  value={draftEditor.abstract}
                  onChange={(event) => updateDraftField("abstract", event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>权利要求书</span>
                <textarea
                  className="draft-editor-textarea"
                  value={draftEditor.claims}
                  onChange={(event) => updateDraftField("claims", event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>说明书</span>
                <textarea
                  className="draft-editor-textarea tall"
                  value={draftEditor.description}
                  onChange={(event) => updateDraftField("description", event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>附图说明</span>
                <textarea
                  className="draft-editor-textarea compact"
                  value={draftEditor.drawing_description}
                  onChange={(event) => updateDraftField("drawing_description", event.currentTarget.value)}
                />
              </label>
            </div>
            <footer className="draft-editor-footer">
              <span>保存后请重新编译正式稿并重新成稿会审。</span>
              <button className="btn btn-primary" disabled={savingDraft} onClick={() => void handleSaveDraft()} type="button">
                {savingDraft ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
                <span>{savingDraft ? "正在保存" : "保存当前初稿"}</span>
              </button>
            </footer>
          </section>
        </div>
      )}
    </section>
  );
}

function editableDraftFields(packageValue: DraftPackage): DraftPackageManualUpdate {
  return {
    title: packageValue.title,
    abstract: packageValue.abstract,
    claims: packageValue.claims,
    description: packageValue.description,
    drawing_description: packageValue.drawing_description,
  };
}

function sectionLength(value: string): number {
  return value.replace(/\s+/g, "").length;
}

function collectPostDraftIssues(review: PostDraftReviewRun | null): Array<{ kind: "阻断" | "命中" | "建议"; text: string }> {
  if (!review) return [];
  const seen = new Set<string>();
  const issues: Array<{ kind: "阻断" | "命中" | "建议"; text: string }> = [];
  function add(kind: "阻断" | "命中" | "建议", text: string) {
    const normalized = text.trim();
    if (!normalized || seen.has(`${kind}:${normalized}`)) return;
    seen.add(`${kind}:${normalized}`);
    issues.push({ kind, text: normalized });
  }
  review.blocking_issues.forEach((text) => add("阻断", text));
  review.contamination_hits.forEach((text) => add("命中", text));
  review.role_results.flatMap((result) => result.rewrite_suggestions).forEach((text) => add("建议", text));
  review.chair_result?.description_rewrite_tasks.forEach((text) => add("建议", text));
  review.chair_result?.next_actions.forEach((text) => add("建议", text));
  return issues;
}
