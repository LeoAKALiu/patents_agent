import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { ClipboardCheck, FileText, Loader2, RefreshCw, Save } from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import { Badge } from "@/components/ui/badge";
import {
  postDraftReviewReportUrl,
  type AgentDoctorReport,
  type DraftPackage,
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

type DraftPackageRepairForm = Pick<
  DraftPackage,
  "title" | "abstract" | "claims" | "description" | "drawing_description"
>;

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
  onStartOfficialCompile: () => void;
  onSaveDraftPackage: (packageValue: DraftPackage) => Promise<void>;
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
  onStartOfficialCompile,
  onSaveDraftPackage,
  onCancelRun,
  onRetryRun,
  onToggleProvider,
}: PostDraftReviewPanelProps) {
  const packageValue = project?.package ?? null;
  const currentRepairForm = useMemo(() => packageToRepairForm(packageValue), [packageValue]);
  const [draftForm, setDraftForm] = useState<DraftPackageRepairForm>(() => packageToRepairForm(packageValue));
  const lastLoadedRepairFormRef = useRef(serializeRepairForm(packageToRepairForm(packageValue)));
  const lastLoadedRepairProjectIdRef = useRef(project?.id);
  const passed = Boolean(review?.status === "completed" && review.export_allowed);
  const blocked = Boolean(review?.status === "completed" && !review.export_allowed);
  const activeRun = guidedActiveRun(runs);
  const reviewBusy = busy === "post-draft-review" || Boolean(activeRun);
  const compileBusy = busy === "official-compile";
  const saveBusy = busy === "draft-package-save";
  const compileDisabled = !packageValue || compileBusy || reviewBusy || saveBusy || Boolean(activeRun) || Boolean(busy);
  const repairRun = blocked ? review : runs[0] ?? null;
  const showRepairWorkbench = Boolean(packageValue && (blocked || (!review && runs.length > 0)));
  const repairGuidance = useMemo(() => guidanceFromReview(repairRun), [repairRun]);
  const currentRepairFormKey = useMemo(() => serializeRepairForm(currentRepairForm), [currentRepairForm]);
  const draftFormKey = useMemo(() => serializeRepairForm(draftForm), [draftForm]);
  const draftDirty = useMemo(
    () => packageValue !== null && draftFormKey !== lastLoadedRepairFormRef.current,
    [draftFormKey, packageValue],
  );

  useEffect(() => {
    if (lastLoadedRepairProjectIdRef.current !== project?.id) {
      lastLoadedRepairProjectIdRef.current = project?.id;
      lastLoadedRepairFormRef.current = currentRepairFormKey;
      setDraftForm(currentRepairForm);
      return;
    }
    if (draftFormKey === currentRepairFormKey) {
      lastLoadedRepairFormRef.current = currentRepairFormKey;
      setDraftForm(currentRepairForm);
      return;
    }
    if (draftDirty && lastLoadedRepairProjectIdRef.current === project?.id) return;
    lastLoadedRepairFormRef.current = currentRepairFormKey;
    setDraftForm(currentRepairForm);
  }, [currentRepairForm, currentRepairFormKey, draftDirty, draftFormKey, project?.id]);

  function updateDraftField(field: keyof DraftPackageRepairForm, value: string) {
    setDraftForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSaveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!packageValue || !draftDirty || saveBusy) return;
    await onSaveDraftPackage({ ...packageValue, ...draftForm });
  }

  return (
    <section className="grid gap-4">
      <StatusStrip
        aria-label="成稿会审状态"
        items={[
          { label: "会审状态", value: passed ? "已通过" : blocked ? "阻止导出" : activeRun ? "运行中" : "等待会审" },
          { label: "当前成稿", value: currentDraftHash ? "已锁定" : "未生成" },
          { label: "正式稿", value: officialCompileRun?.official_package_hash ? "已生成" : "未编译" },
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
                ? "导出已锁定。下方修复工作台会汇总 Agent 阻断项，并允许直接编辑当前内部初稿。"
                : runs.length > 0
                  ? "已有历史会审记录，但当前初稿或正式稿已变化。请重新编译正式稿并会审。"
                  : "选择可用智能体后启动会审，结果会绑定当前成稿和正式稿版本。"
          }
          meta={(
            <>
              {passed ? <Badge variant="success" className="text-xs">已通过</Badge> : blocked ? <Badge variant="destructive" className="text-xs">阻止正式导出</Badge> : <Badge variant="warning" className="text-xs">等待会审</Badge>}
              {review?.draft_package_hash && <span className="tag">版本已绑定</span>}
            </>
          )}
        />

        {showRepairWorkbench && (
          <section className="post-review-repair-workbench" aria-label="阻断修复工作台">
            <div className="repair-guidance-panel">
              <div className="settings-group-header compact">
                <div>
                  <h3>阻断修复工作台</h3>
                  <p>Agent 已给出的阻断原因、改写建议和下一步动作集中在这里，旁边可直接修改当前内部初稿。</p>
                </div>
              </div>
              <div className="dense-list">
                {repairGuidance.map((item, index) => (
                  <div className="dense-item repair-guidance-item" key={`${item.kind}-${index}`}>
                    <div>
                      <span className={`tag ${item.kind === "blocking" ? "tag-danger" : item.kind === "patch" ? "tag-info" : "tag-warn"}`}>
                        {repairKindLabel(item.kind)}
                      </span>
                      <p>{item.text}</p>
                    </div>
                  </div>
                ))}
                {repairGuidance.length === 0 && (
                  <p className="workflow-hint">暂无结构化阻断建议。可打开会审报告，或直接在右侧修订初稿后重新编译。</p>
                )}
              </div>
              <ActionDock meta="建议顺序：保存初稿 → 重新编译正式稿 → 重新成稿会审。">
                <button className="btn btn-secondary" disabled={compileDisabled} onClick={onStartOfficialCompile} type="button">
                  {compileBusy ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
                  <span>{officialCompileRun ? "重新编译正式稿" : "编译正式稿"}</span>
                </button>
              </ActionDock>
            </div>

            <form className="draft-repair-editor" onSubmit={handleSaveDraft}>
              <div className="settings-group-header compact">
                <div>
                  <h3>当前内部初稿</h3>
                  <p>修改这里会更新当前工作稿版本，并让旧正式稿/旧成稿会审失效。</p>
                </div>
                <Badge variant={draftDirty ? "warning" : "secondary"} className="text-xs">
                  {draftDirty ? "有未保存修改" : "已同步"}
                </Badge>
              </div>
              <label className="field">
                <span>标题</span>
                <input value={draftForm.title} onChange={(event) => updateDraftField("title", event.target.value)} />
              </label>
              <label className="field">
                <span>摘要</span>
                <textarea value={draftForm.abstract} onChange={(event) => updateDraftField("abstract", event.target.value)} />
              </label>
              <label className="field">
                <span>权利要求书</span>
                <textarea value={draftForm.claims} onChange={(event) => updateDraftField("claims", event.target.value)} />
              </label>
              <label className="field">
                <span>说明书</span>
                <textarea value={draftForm.description} onChange={(event) => updateDraftField("description", event.target.value)} />
              </label>
              <label className="field">
                <span>附图说明</span>
                <textarea value={draftForm.drawing_description} onChange={(event) => updateDraftField("drawing_description", event.target.value)} />
              </label>
              <ActionDock meta={draftDirty ? "保存后请重新编译正式稿。" : "当前编辑器内容与工作稿一致。"}>
                <button className="btn btn-primary" disabled={!draftDirty || saveBusy || Boolean(activeRun)} type="submit">
                  {saveBusy ? <Loader2 className="spin" size={17} /> : <Save size={17} />}
                  <span>保存当前初稿</span>
                </button>
              </ActionDock>
            </form>
          </section>
        )}

        <AgentProviderCards
          doctor={doctor}
          role="post_review"
          selectedProviders={selectedProviders}
          disabled={!actionGate.allowed || reviewBusy}
          onToggleProvider={onToggleProvider}
        />
        <ActionGateHint gate={actionGate} />
        <ActionDock meta="会审结果必须与当前成稿和正式稿版本一致，才会放行正式导出。">
          <button
            className="btn btn-secondary"
            disabled={compileDisabled}
            onClick={onStartOfficialCompile}
            type="button"
          >
            {compileBusy ? <Loader2 className="spin" size={17} /> : <FileText size={17} />}
            <span>{officialCompileRun ? "重新编译正式稿" : "编译正式稿"}</span>
          </button>
          <button
            className="btn btn-primary"
            disabled={!actionGate.allowed || reviewBusy}
            onClick={onStartPostDraftReview}
            title={actionGate.reason || undefined}
            type="button"
          >
            {reviewBusy ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
            <span>{activeRun ? "成稿会审中" : review ? "重新成稿会审" : "启动成稿会审"}</span>
          </button>
        </ActionDock>
        <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "post-draft-review"} />
        <GuidedRuntimeConsole run={activeRun} label="成稿会审运行中" busy={busy} onCancel={onCancelRun} />
        <GuidedRuntimeFailures run={runs[0] ?? null} />
        <GuidedRuntimeActions run={runs[0] ?? null} disabled={Boolean(busy)} onRetry={onRetryRun} />
        {review && (
          <article className={passed ? "guided-choice selected" : "guided-choice"}>
            <div className="result-meta">
              {passed ? <Badge variant="success" className="text-xs">{pipelineRunStatusLabel(review.status)}</Badge> : <Badge variant="destructive" className="text-xs">{pipelineRunStatusLabel(review.status)}</Badge>}
              <span>{review.providers.join(" / ") || "默认三方"}</span>
              <span>会审版本已绑定</span>
              {review.official_package_hash && <span>正式稿版本已绑定</span>}
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
                导出已锁定：请在上方修复工作台处理阻断项，保存初稿后重新编译正式稿，再运行成稿会审。
              </p>
            )}
          </article>
        )}
        {!review && runs.length > 0 && (
          <p className="workflow-hint">已有成稿会审记录，但不属于当前成稿。可参考上方历史阻断建议，保存初稿后重新编译并会审。</p>
        )}
      </SettingsGroup>
    </section>
  );
}

function packageToRepairForm(packageValue: DraftPackage | null): DraftPackageRepairForm {
  return {
    title: packageValue?.title ?? "",
    abstract: packageValue?.abstract ?? "",
    claims: packageValue?.claims ?? "",
    description: packageValue?.description ?? "",
    drawing_description: packageValue?.drawing_description ?? "",
  };
}

function serializeRepairForm(form: DraftPackageRepairForm): string {
  return JSON.stringify(form);
}

function guidanceFromReview(run: PostDraftReviewRun | null): Array<{ kind: "blocking" | "issue" | "rewrite" | "patch"; text: string }> {
  if (!run) return [];
  const items: Array<{ kind: "blocking" | "issue" | "rewrite" | "patch"; text: string }> = [];
  items.push(...run.blocking_issues.map((text) => ({ kind: "blocking" as const, text })));
  items.push(...run.contamination_hits.map((text) => ({ kind: "issue" as const, text })));
  for (const result of run.role_results) {
    items.push(...result.blocking_issues.map((text) => ({ kind: "blocking" as const, text: `${roleLabel(result.role)}：${text}` })));
    items.push(...result.rewrite_suggestions.map((text) => ({ kind: "rewrite" as const, text: `${roleLabel(result.role)}：${text}` })));
    items.push(...result.official_safe_patches.map((text) => ({ kind: "patch" as const, text: `${roleLabel(result.role)}：${text}` })));
  }
  const chair = run.chair_result;
  if (chair) {
    if (chair.claim_1_rewrite) items.push({ kind: "rewrite", text: `主席建议权利要求1：${chair.claim_1_rewrite}` });
    if (chair.system_claim_rewrite) items.push({ kind: "rewrite", text: `主席建议系统权利要求：${chair.system_claim_rewrite}` });
    if (chair.abstract_rewrite) items.push({ kind: "rewrite", text: `主席建议摘要：${chair.abstract_rewrite}` });
    items.push(...chair.description_rewrite_tasks.map((text) => ({ kind: "rewrite" as const, text: `说明书任务：${text}` })));
    items.push(...chair.official_safe_patches.map((text) => ({ kind: "patch" as const, text: `官方安全补丁建议：${text}` })));
    items.push(...chair.next_actions.map((text) => ({ kind: "rewrite" as const, text: `下一步：${text}` })));
  }
  return dedupeGuidance(items);
}

function dedupeGuidance<T extends { text: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  const deduped: T[] = [];
  for (const item of items) {
    const key = item.text.trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    deduped.push(item);
  }
  return deduped;
}

function repairKindLabel(kind: "blocking" | "issue" | "rewrite" | "patch"): string {
  if (kind === "blocking") return "阻断";
  if (kind === "issue") return "命中";
  if (kind === "patch") return "补丁建议";
  return "改写建议";
}

function roleLabel(role: string): string {
  if (role === "claims_reviewer") return "权利要求审查";
  if (role === "spec_cleaner") return "说明书清洁";
  if (role === "technical_hardness") return "技术硬度";
  return role;
}
