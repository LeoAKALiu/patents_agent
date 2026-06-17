/**
 * Filing-readiness + draft-completion views — extracted from App.tsx (M3-B').
 */
import { ClipboardList, Download, Gauge, Wand2 } from "@/lib/icons";
import {
  draftCompletionReportUrl,
  exportUrl,
  filingReadinessReportUrl,
  officialExportUrl,
  type DraftCompletionRun,
  type FilingReadinessReport,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import {
  completionCategoryLabel,
  completionPatchKindLabel,
  completionPatchStatusLabel,
  completionTaskStatusLabel,
  completionTargetLabel,
  draftSectionLabel,
  evidenceStatusLabel,
  featureClassificationLabel,
  pipelineRunStatusLabel,
  readinessStatusLabel,
  severityLabel,
} from "@/domain";

export function FilingReadinessView({
  project,
  report,
  reports,
  postDraftReview,
  officialCompileRun,
  currentDraftHash,
  currentSourceDraftHash,
  busy,
  onRun,
}: {
  project: ProjectRecord | null;
  report: FilingReadinessReport | null;
  reports: FilingReadinessReport[];
  postDraftReview: PostDraftReviewRun | null;
  officialCompileRun: OfficialCompileRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  busy: string;
  onRun: () => void;
}) {
  const canExport = Boolean(project?.package);
  const officialAllowed = Boolean(
    canExport
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
  const reportStatusClass = report?.status === "high_risk" ? "danger" : report?.status === "warning" ? "warn" : "";
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>提交成熟度</h3>
          <p>{project?.package ? "检查官方提交导出、内部策略稿和申请文本中的占位符、敏感表述与高风险命中项。" : "生成申请文本后可运行提交成熟度检查。"}</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!project?.package || busy === "filing-readiness"}
          onClick={onRun}
          type="button"
        >
          <ClipboardList size={18} />
          <span>运行检查</span>
        </button>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>导出</h3>
        {project && canExport ? (
          <div className="flex flex-col gap-4">
            {report?.status === "high_risk" && (
              <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">高风险：请先处理报告中的不利表述、内部痕迹或支撑缺口，再让专利代理师或律师复核。</p>
            )}
            {!officialAllowed && <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">正式稿入口已锁定：需先生成正式稿，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。</p>}
            {officialCompileRun?.official_package_hash && (
              <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">当前正式稿版本：{officialCompileRun.official_package_hash.slice(0, 12)}</p>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <a
                aria-disabled={!officialAllowed}
                className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
                href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
              >
                <Download size={18} />
                <span>官方 DOCX</span>
              </a>
              <a
                aria-disabled={!officialAllowed}
                className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
                href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
              >
                <Download size={18} />
                <span>官方 MD</span>
              </a>
              <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" href={exportUrl(project.id, "md")}>
                <Download size={18} />
                <span>内部策略稿</span>
              </a>
              {report && (
                <a className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" href={filingReadinessReportUrl(project.id, report.id)}>
                  <Download size={18} />
                  <span>检查报告</span>
                </a>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无可导出的申请文本。</p>
        )}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>历史检查</h3>
          <div className="flex flex-col gap-3">
            {reports.map((item) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={item.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span className={`px-2.5 py-0.5 rounded-md border ${ item.status === "high_risk" ? "bg-app-danger/10 border-app-danger/45 text-app-danger" : item.status === "warning" ? "bg-app-warn/10 border-app-warn/45 text-app-warn" : "bg-app-success/10 border-app-success/45 text-app-success" }`}>
                    {readinessStatusLabel(item.status)}
                  </span>
                  <span>{item.issues.length} 项命中</span>
                </div>
                <p>{item.created_at}</p>
                <p>{item.rules_version}</p>
              </article>
            ))}
            {reports.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无提交成熟度检查记录。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>命中项</h3>
          {report && (
            <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
              <span className={`px-2.5 py-0.5 rounded-md border ${ reportStatusClass === "danger" ? "bg-app-danger/10 border-app-danger/45 text-app-danger" : reportStatusClass === "warn" ? "bg-app-warn/10 border-app-warn/45 text-app-warn" : "bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-primary)]" }`}>{readinessStatusLabel(report.status)}</span>
              <span>{report.issues.length} 项</span>
            </div>
          )}
          <div className="flex flex-col gap-3">
            {report?.issues.map((issue, index) => (
              <article className={`flex items-start gap-3 p-4 border rounded-lg ${ issue.severity === "high" ? "bg-[var(--surface-inset)] border-app-danger/35" : issue.severity === "medium" ? "bg-[var(--surface-inset)] border-app-warn/35" : "bg-app-info/10 border-app-info/35" }`} key={`${issue.category}-${issue.target}-${index}`}>
                <span>{severityLabel(issue.severity)}</span>
                <div>
                  <strong>{issue.category} / {issue.target}</strong>
                  <p>{issue.matched_text || "未记录匹配文本"}</p>
                  <p>{issue.message}</p>
                  <p>{issue.suggestion}</p>
                </div>
              </article>
            ))}
            {!report && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">运行检查后显示命中项。</p>}
            {report && report.issues.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">最新报告没有命中项。</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

export function DraftCompletionView({
  project,
  run,
  runs,
  busy,
  onRun,
  onImprove,
  onPatch,
}: {
  project: ProjectRecord | null;
  run: DraftCompletionRun | null;
  runs: DraftCompletionRun[];
  busy: string;
  onRun: () => void;
  onImprove: () => void;
  onPatch: (runId: string, patchId: string, action: "accept" | "reject") => void;
}) {
  const scoreItems: Array<[string, number]> = run
    ? [
        ["授权稳定性", run.scorecard.authorization_stability],
        ["保护范围", run.scorecard.protection_scope],
        ["支撑强度", run.scorecard.support_strength],
        ["现有技术区分", run.scorecard.prior_art_distinction],
        ["提交成熟度", run.scorecard.filing_maturity],
        ["官方洁净度", run.scorecard.official_hygiene],
        ["整体评分", run.scorecard.overall],
      ]
    : [];
  const priorityIssues = run?.issues.filter((issue) => issue.blocks_submission || issue.severity === "high") ?? [];
  const displayedIssues = priorityIssues.length > 0 ? priorityIssues : run?.issues.slice(0, 5) ?? [];
  const patchBusy = busy === "completion" || busy.startsWith("completion-");

  function patchStatusClass(status: string): string {
    if (status === "accepted") return "";
    if (status === "rejected" || status === "superseded") return "muted";
    return "warn";
  }

  function completionStatusLabel(status: string): string {
    if (status === "supported") return "已支撑";
    if (status === "partial") return "部分支撑";
    return "缺支撑";
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>初稿完善循环</h3>
          <p>
            发现缺口、生成任务和候选补丁；补丁需人工接受后才进入完善结果。
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project?.package || Boolean(busy)}
            onClick={onRun}
            type="button"
          >
            <Gauge size={18} />
            <span>运行完善</span>
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project?.package || Boolean(busy)}
            onClick={onImprove}
            type="button"
          >
            <Wand2 size={18} />
            <span>一键提升分数</span>
          </button>
        </div>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
          <h3>评分</h3>
          {run && (
            <>
              <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)]">{pipelineRunStatusLabel(run.status)}</span>
              <span>{run.created_at}</span>
              <span>{runs.length} 次运行</span>
            </>
          )}
        </div>
        {run ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {scoreItems.map(([label, value]) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg" key={label}>
                <span>{label}</span>
                <strong>{value}/100</strong>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-primary)]/50 italic py-4">生成申请文本后可运行初稿完善循环。</p>
        )}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>高优先级问题</h3>
          <div className="flex flex-col gap-3">
            {displayedIssues.map((issue) => (
              <article className={`flex items-start gap-3 p-4 border rounded-lg ${ issue.severity === "high" ? "bg-[var(--surface-inset)] border-app-danger/35" : issue.severity === "medium" ? "bg-[var(--surface-inset)] border-app-warn/35" : "bg-app-info/10 border-app-info/35" }`} key={issue.id}>
                <span>{severityLabel(issue.severity)}</span>
                <div>
                  <strong>
                    {completionCategoryLabel(issue.category)} / {completionTargetLabel(issue.target)}
                  </strong>
                  <p>{issue.message}</p>
                  <p>{issue.why_it_matters}</p>
                  <p>{issue.suggested_action}</p>
                </div>
              </article>
            ))}
            {!run && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">运行后显示高优先级缺口。</p>}
            {run && displayedIssues.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无高优先级问题。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>完善任务</h3>
          <div className="flex flex-col gap-3">
            {run?.tasks.map((task) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={task.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)]">{completionTaskStatusLabel(task.status)}</span>
                  <span>优先级 {task.priority}</span>
                  <span>{draftSectionLabel(task.draft_section_target)}</span>
                </div>
                <p><strong>{task.task_type}</strong></p>
                <p>{task.expected_output}</p>
              </article>
            ))}
            {!run && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">运行后显示待完善任务。</p>}
            {run && run.tasks.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无完善任务。</p>}
          </div>
        </div>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>权利要求支撑矩阵</h3>
        {run && run.support_matrix.length > 0 ? (
          <div className="w-full text-sm text-left border-collapse">
            <table>
              <thead>
                <tr>
                  <th>权利要求</th>
                  <th>特征</th>
                  <th>分类</th>
                  <th>支撑状态</th>
                  <th>证据</th>
                  <th>风险</th>
                </tr>
              </thead>
              <tbody>
                {run.support_matrix.map((row, index) => (
                  <tr key={`${row.claim_ref}-${index}`}>
                    <td>{row.claim_ref || "未映射"}</td>
                    <td>{row.feature_text}</td>
                    <td>{featureClassificationLabel(row.feature_classification)}</td>
                    <td>{completionStatusLabel(row.completion_status)}</td>
                    <td>
                      {[
                        ...row.description_refs,
                        ...row.figure_refs,
                        ...row.embodiment_refs,
                        ...row.formula_refs,
                        ...row.data_structure_refs,
                        ...row.pseudo_code_refs,
                        ...row.prior_art_refs,
                      ].join("；") || evidenceStatusLabel(row.evidence_status)}
                    </td>
                    <td>{row.risk_tags.join("；") || "暂无"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-primary)]/50 italic py-4">{run ? "暂无支撑矩阵。" : "运行后显示权利要求支撑矩阵。"}</p>
        )}
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
          <h3>候选补丁</h3>
          {project && run && (
            <a className="inline-flex items-center gap-2 text-sm text-[var(--action-primary)] hover:underline font-medium" href={draftCompletionReportUrl(project.id, run.id)}>
              <Download size={17} />
              <span>报告 MD</span>
            </a>
          )}
        </div>
        <div className="flex flex-col gap-3">
          {run?.patches.map((patch) => (
            <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={patch.id}>
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                <span className={`px-2.5 py-0.5 rounded-md border ${ patchStatusClass(patch.status) === "danger" ? "bg-app-danger/10 border-app-danger/45 text-app-danger" : patchStatusClass(patch.status) === "warn" ? "bg-app-warn/10 border-app-warn/45 text-app-warn" : "bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-primary)]" }`}>{completionPatchStatusLabel(patch.status)}</span>
                <span>{completionPatchKindLabel(patch.patch_kind)}</span>
                <span>{draftSectionLabel(patch.target_section)}</span>
                <span>{patch.can_enter_official_draft ? "可进入官方稿" : "仅内部参考"}</span>
              </div>
              <p><strong>{patch.rationale}</strong></p>
              <p>{patch.risk_delta}</p>
              <pre className="p-4 bg-[var(--surface-subtle)] rounded-lg border border-[var(--border-subtle)] font-mono text-sm whitespace-pre-wrap">{patch.after_text || "无修改后文本"}</pre>
              <div className="flex items-center gap-3">
                <button
                  className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "accept")}
                  type="button"
                >
                  接受
                </button>
                <button
                  className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors text-sm"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "reject")}
                  type="button"
                  title="拒绝补丁"
                >
                  拒绝
                </button>
              </div>
            </article>
          ))}
          {!run && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">运行后显示候选补丁。</p>}
          {run && run.patches.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无候选补丁。</p>}
        </div>
      </section>
    </div>
  );
}
