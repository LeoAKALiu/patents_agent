/**
 * Filing-readiness + draft-completion views — extracted from App.tsx (M3-B').
 */
import { safeProjectName } from "@/lib/filename";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  Gauge,
  Info,
  LockKeyhole,
  Wand2,
} from "@/lib/icons";
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
import {
  ActionDock,
  InfoCard,
  SectionHead,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";

function EmptyMessage({ children }: { children: string }) {
  return <p className="empty">{children}</p>;
}

function readinessTagClass(status: string): string {
  if (status === "high_risk") return "tag tag-danger";
  if (status === "warning") return "tag tag-warn";
  if (status === "clean") return "tag tag-success";
  return "tag";
}

function readinessTone(status: string): "danger" | "warn" | "success" {
  if (status === "high_risk") return "danger";
  if (status === "warning") return "warn";
  return "success";
}

function severityTagClass(severity: string): string {
  if (severity === "high") return "tag tag-danger";
  if (severity === "medium") return "tag tag-warn";
  return "tag tag-info";
}

function severityTone(severity: string): "danger" | "warn" | "info" {
  if (severity === "high") return "danger";
  if (severity === "medium") return "warn";
  return "info";
}

function scoreTone(value: number): "success" | "info" | "warn" | "danger" {
  if (value >= 80) return "success";
  if (value >= 70) return "info";
  if (value >= 60) return "warn";
  return "danger";
}

function scoreLabel(value: number): string {
  if (value >= 80) return "稳健";
  if (value >= 70) return "可继续";
  if (value >= 60) return "建议补强";
  return "需处理";
}

function scoreWidth(value: number): string {
  return `${Math.max(0, Math.min(100, value))}%`;
}

function patchStatusTone(status: string): "success" | "warn" | "danger" | "default" {
  if (status === "accepted") return "success";
  if (status === "proposed") return "warn";
  if (status === "rejected" || status === "superseded") return "danger";
  return "default";
}

function patchStatusTagClass(status: string): string {
  const tone = patchStatusTone(status);
  if (tone === "success") return "tag tag-success";
  if (tone === "warn") return "tag tag-warn";
  if (tone === "danger") return "tag tag-danger";
  return "tag";
}

function completionStatusLabel(status: string): string {
  if (status === "supported") return "已支撑";
  if (status === "partial") return "部分支撑";
  return "缺支撑";
}

function completionStatusTagClass(status: string): string {
  if (status === "supported") return "tag tag-success";
  if (status === "partial") return "tag tag-warn";
  return "tag tag-danger";
}

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
  const projectName = safeProjectName(project?.name);
  const officialAllowed = Boolean(
    canExport
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
  const highIssues = report?.issues.filter((issue) => issue.severity === "high").length ?? 0;
  const mediumIssues = report?.issues.filter((issue) => issue.severity === "medium").length ?? 0;
  const officialHash = officialCompileRun?.official_package_hash;

  return (
    <div className="grid gap-4">
      <StatusStrip
        aria-label="提交成熟度状态"
        items={[
          { label: "提交成熟度", value: report ? readinessStatusLabel(report.status) : "未检查" },
          { label: "命中项", value: report ? `${report.issues.length} 项` : "等待运行" },
          { label: "正式稿入口", value: officialAllowed ? "可导出" : "已锁定" },
          { label: "正式稿版本", value: officialHash ? officialHash.slice(0, 12) : "未绑定" },
        ]}
      />

      <SectionHead
        title="提交成熟度"
        description={project?.package ? "检查官方提交导出、内部工作稿和申请文本中的占位符、敏感表述与高风险命中项。" : "生成申请文本后可运行提交成熟度检查。"}
        actions={(
          <button
            className="btn btn-primary"
            disabled={!project?.package || busy === "filing-readiness"}
            onClick={onRun}
            type="button"
          >
            <ClipboardList size={18} />
            <span>运行检查</span>
          </button>
        )}
      />

      <SettingsGroup title="导出门禁" description="正式提交稿、内部工作稿与检查报告分离展示，避免把内部材料混进正式稿。">
        {project && canExport ? (
          <div className="grid gap-3">
            {report?.status === "high_risk" && (
              <div className="callout callout-warn">
                <span className="tag tag-warn">高风险</span>
                <div>
                  <strong>高风险但可继续复核</strong>
                  <p>请先处理报告中的不利表述、内部痕迹或支撑缺口，再让专利代理师或律师复核。</p>
                </div>
              </div>
            )}
            {!officialAllowed && (
              <div className="callout callout-danger">
                <span className="tag tag-danger">导出阻断</span>
                <div>
                  <strong>正式稿入口已锁定</strong>
                  <p>需先生成正式稿，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。</p>
                </div>
              </div>
            )}
            {officialHash && (
              <div className="callout callout-success">
                <span className="tag tag-success">版本绑定</span>
                <div>
                  <strong>当前正式稿版本</strong>
                  <p className="hash-chip">{officialHash.slice(0, 12)}</p>
                </div>
              </div>
            )}

            <div className="quality-export-grid">
              <InfoCard
                icon={officialAllowed ? <CheckCircle2 size={18} /> : <LockKeyhole size={18} />}
                title="官方 DOCX"
                description="正式提交候选包，必须绑定成稿会审结果。"
                tone={officialAllowed ? "success" : "danger"}
                meta={<span className={officialAllowed ? "tag tag-success" : "tag tag-danger"}>{officialAllowed ? "可下载" : "已锁定"}</span>}
                action={(
                  <a
                    aria-disabled={!officialAllowed}
                    className={officialAllowed ? "btn btn-primary" : "btn btn-secondary is-disabled"}
                    download={`${projectName}-正式提交稿.docx`}
                    href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
                  >
                    <Download size={18} />
                    <span>下载</span>
                  </a>
                )}
              />
              <InfoCard
                icon={officialAllowed ? <FileText size={18} /> : <LockKeyhole size={18} />}
                title="官方 MD"
                description="正式提交稿 Markdown，用于最终复核。"
                tone={officialAllowed ? "success" : "danger"}
                meta={<span className={officialAllowed ? "tag tag-success" : "tag tag-danger"}>{officialAllowed ? "可下载" : "已锁定"}</span>}
                action={(
                  <a
                    aria-disabled={!officialAllowed}
                    className={officialAllowed ? "btn btn-secondary" : "btn btn-secondary is-disabled"}
                    download={`${projectName}-正式提交稿.md`}
                    href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
                  >
                    <Download size={18} />
                    <span>下载</span>
                  </a>
                )}
              />
              <InfoCard
                icon={<Info size={18} />}
                title="内部工作稿"
                description="仅供内部复核，可能含护城河、风险说明和策略备注。"
                tone="info"
                meta={<span className="tag tag-info">内部材料</span>}
                action={(
                  <a className="btn btn-secondary" download={`${projectName}.md`} href={exportUrl(project.id, "md")}>
                    <Download size={18} />
                    <span>下载</span>
                  </a>
                )}
              />
              {report && (
                <InfoCard
                  icon={<ClipboardList size={18} />}
                  title="检查报告"
                  description={`${report.issues.length} 项命中，规则版本 ${report.rules_version}`}
                  tone={readinessTone(report.status)}
                  meta={<span className={readinessTagClass(report.status)}>{readinessStatusLabel(report.status)}</span>}
                  action={(
                    <a className="btn btn-secondary" download={`${projectName}-提交成熟度报告.md`} href={filingReadinessReportUrl(project.id, report.id)}>
                      <Download size={18} />
                      <span>下载</span>
                    </a>
                  )}
                />
              )}
            </div>
          </div>
        ) : (
          <EmptyMessage>暂无可导出的申请文本。</EmptyMessage>
        )}
      </SettingsGroup>

      <div className="quality-split-grid">
        <SettingsGroup title="历史检查" description="保留每次成熟度检查的状态、命中数和规则版本。">
          <div className="dense-list">
            {reports.map((item) => (
              <InfoCard
                title={item.created_at}
                description={item.rules_version}
                tone={readinessTone(item.status)}
                meta={(
                  <>
                    <span className={readinessTagClass(item.status)}>{readinessStatusLabel(item.status)}</span>
                    <span className="tag">{item.issues.length} 项命中</span>
                  </>
                )}
                key={item.id}
              />
            ))}
            {reports.length === 0 && <EmptyMessage>暂无提交成熟度检查记录。</EmptyMessage>}
          </div>
        </SettingsGroup>

        <SettingsGroup title="命中项" description="高/中/低风险分层展示，正式稿风险和导出阻断会明确标注。">
          {report && (
            <div className="settings-group-header compact">
              <p>
                <span className={readinessTagClass(report.status)}>{readinessStatusLabel(report.status)}</span>
                <span className="tag">{report.issues.length} 项</span>
                <span className="tag tag-danger">高 {highIssues}</span>
                <span className="tag tag-warn">中 {mediumIssues}</span>
              </p>
            </div>
          )}
          <div className="dense-list">
            {report?.issues.map((issue, index) => (
              <InfoCard
                icon={issue.severity === "high" ? <AlertTriangle size={18} /> : <Info size={18} />}
                title={`${issue.category} / ${issue.target}`}
                description={issue.message}
                tone={severityTone(issue.severity)}
                meta={(
                  <>
                    <span className={severityTagClass(issue.severity)}>{severityLabel(issue.severity)}</span>
                    <span className="tag">{issue.can_auto_clean ? "可自动清理" : "需人工复核"}</span>
                    <span className="tag tag-info">{issue.matched_text || "未记录匹配文本"}</span>
                  </>
                )}
                key={`${issue.category}-${issue.target}-${index}`}
              >
                <p>{issue.suggestion}</p>
              </InfoCard>
            ))}
            {!report && <EmptyMessage>运行检查后显示命中项。</EmptyMessage>}
            {report && report.issues.length === 0 && <EmptyMessage>最新报告没有命中项。</EmptyMessage>}
          </div>
        </SettingsGroup>
      </div>

      <ActionDock meta={officialAllowed ? "正式稿已绑定当前成稿会审，可进入下载确认。" : "正式导出需要当前正式稿与成稿会审 hash 匹配。"}>
        <button
          className="btn btn-primary"
          disabled={!project?.package || busy === "filing-readiness"}
          onClick={onRun}
          type="button"
        >
          <ClipboardList size={18} />
          <span>重新运行检查</span>
        </button>
      </ActionDock>
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
  const blockingIssueCount = run?.issues.filter((issue) => issue.blocks_submission).length ?? 0;
  const proposedPatchCount = run?.patches.filter((patch) => patch.status === "proposed").length ?? 0;
  const patchBusy = busy === "completion" || busy.startsWith("completion-");
  const projectName = safeProjectName(project?.name);

  return (
    <div className="grid gap-4">
      <StatusStrip
        aria-label="初稿完善状态"
        items={[
          { label: "运行状态", value: run ? pipelineRunStatusLabel(run.status) : "未运行" },
          { label: "整体评分", value: run ? `${run.scorecard.overall}/100` : "未评分" },
          { label: "阻断问题", value: `${blockingIssueCount} 项` },
          { label: "候选补丁", value: `${proposedPatchCount} 个待确认` },
        ]}
      />

      <SectionHead
        title="初稿完善循环"
        description="发现缺口、生成任务和候选补丁；补丁需人工接受后才进入完善结果。"
        actions={(
          <div className="button-row quality-actions">
            <button
              className="btn btn-primary"
              disabled={!project?.package || Boolean(busy)}
              onClick={onRun}
              type="button"
            >
              <Gauge size={18} />
              <span>运行完善</span>
            </button>
            <button
              className="btn btn-secondary"
              disabled={!project?.package || Boolean(busy)}
              onClick={onImprove}
              type="button"
            >
              <Wand2 size={18} />
              <span>一键提升分数</span>
            </button>
          </div>
        )}
      />

      <SettingsGroup
        title="评分"
        description={run ? `${pipelineRunStatusLabel(run.status)} · ${run.created_at} · ${runs.length} 次运行` : "生成申请文本后可运行初稿完善循环。"}
      >
        {run ? (
          <div className="quality-score-grid">
            {scoreItems.map(([label, value]) => {
              const tone = scoreTone(value);
              return (
                <InfoCard
                  icon={tone === "success" ? <CheckCircle2 size={18} /> : tone === "danger" ? <AlertTriangle size={18} /> : <Gauge size={18} />}
                  title={label}
                  description={scoreLabel(value)}
                  tone={tone}
                  action={(
                    <div className="score quality-score">
                      <div className="score-top">
                        <span className={`tag tag-${tone === "danger" ? "danger" : tone === "warn" ? "warn" : tone === "success" ? "success" : "info"}`}>{value}/100</span>
                      </div>
                      <div className={`bar ${tone}`}>
                        <span style={{ width: scoreWidth(value) }} />
                      </div>
                    </div>
                  )}
                  key={label}
                />
              );
            })}
          </div>
        ) : (
          <EmptyMessage>生成申请文本后可运行初稿完善循环。</EmptyMessage>
        )}
      </SettingsGroup>

      <div className="quality-split-grid">
        <SettingsGroup title="高优先级问题" description="优先展示阻断提交或高风险问题。">
          <div className="dense-list">
            {displayedIssues.map((issue) => (
              <InfoCard
                icon={issue.blocks_submission || issue.severity === "high" ? <AlertTriangle size={18} /> : <Info size={18} />}
                title={`${completionCategoryLabel(issue.category)} / ${completionTargetLabel(issue.target)}`}
                description={issue.message}
                tone={issue.blocks_submission ? "danger" : severityTone(issue.severity)}
                meta={(
                  <>
                    <span className={severityTagClass(issue.severity)}>{severityLabel(issue.severity)}</span>
                    {issue.blocks_submission && <span className="tag tag-danger">阻断提交</span>}
                    {issue.source_refs.length > 0 && <span className="tag tag-info">{issue.source_refs.join(" / ")}</span>}
                  </>
                )}
                key={issue.id}
              >
                <p>{issue.why_it_matters}</p>
                <p>{issue.suggested_action}</p>
              </InfoCard>
            ))}
            {!run && <EmptyMessage>运行后显示高优先级缺口。</EmptyMessage>}
            {run && displayedIssues.length === 0 && <EmptyMessage>暂无高优先级问题。</EmptyMessage>}
          </div>
        </SettingsGroup>

        <SettingsGroup title="完善任务" description="任务状态、优先级和目标章节保持在同一行内。">
          <div className="dense-list">
            {run?.tasks.map((task) => (
              <InfoCard
                title={task.task_type}
                description={task.expected_output}
                meta={(
                  <>
                    <span className="tag">{completionTaskStatusLabel(task.status)}</span>
                    <span className="tag tag-info">优先级 {task.priority}</span>
                    <span className="tag">{draftSectionLabel(task.draft_section_target)}</span>
                  </>
                )}
                key={task.id}
              />
            ))}
            {!run && <EmptyMessage>运行后显示待完善任务。</EmptyMessage>}
            {run && run.tasks.length === 0 && <EmptyMessage>暂无完善任务。</EmptyMessage>}
          </div>
        </SettingsGroup>
      </div>

      <SettingsGroup title="权利要求支撑矩阵" description="矩阵在小屏幕内局部滚动，长特征和风险标签会换行。">
        {run && run.support_matrix.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
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
                    <td><span className={completionStatusTagClass(row.completion_status)}>{completionStatusLabel(row.completion_status)}</span></td>
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
          <EmptyMessage>{run ? "暂无支撑矩阵。" : "运行后显示权利要求支撑矩阵。"}</EmptyMessage>
        )}
      </SettingsGroup>

      <SettingsGroup
        title="候选补丁"
        description="采纳会进入完善结果；不能进入正式稿的补丁会明确标识为仅内部参考。"
      >
        {project && run && (
          <a className="btn btn-secondary quality-inline-action" download={`${projectName}-初稿完善报告.md`} href={draftCompletionReportUrl(project.id, run.id)}>
            <Download size={17} />
            <span>报告 MD</span>
          </a>
        )}
        <div className="dense-list">
          {run?.patches.map((patch) => (
            <InfoCard
              title={patch.rationale}
              description={patch.risk_delta}
              tone={patchStatusTone(patch.status) === "default" ? "default" : patchStatusTone(patch.status)}
              meta={(
                <>
                  <span className={patchStatusTagClass(patch.status)}>{completionPatchStatusLabel(patch.status)}</span>
                  <span className="tag tag-info">{completionPatchKindLabel(patch.patch_kind)}</span>
                  <span className="tag">{draftSectionLabel(patch.target_section)}</span>
                  <span className={patch.can_enter_official_draft ? "tag tag-success" : "tag tag-warn"}>
                    {patch.can_enter_official_draft ? "可进入官方稿" : "仅内部参考"}
                  </span>
                </>
              )}
              key={patch.id}
            >
              <pre className="patch-preview">{patch.after_text || "无修改后文本"}</pre>
              <div className="action-dock quality-card-dock">
                <button
                  className="btn btn-primary"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "accept")}
                  type="button"
                >
                  接受
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={patch.status !== "proposed" || patchBusy}
                  onClick={() => onPatch(run.id, patch.id, "reject")}
                  type="button"
                  title="拒绝补丁"
                >
                  拒绝
                </button>
              </div>
            </InfoCard>
          ))}
          {!run && <EmptyMessage>运行后显示候选补丁。</EmptyMessage>}
          {run && run.patches.length === 0 && <EmptyMessage>暂无候选补丁。</EmptyMessage>}
        </div>
      </SettingsGroup>

      <ActionDock meta={run ? `当前运行 ${run.id}，${proposedPatchCount} 个补丁待确认。` : "运行完善后可采纳补丁或继续提升分数。"}>
        <button
          className="btn btn-primary"
          disabled={!project?.package || Boolean(busy)}
          onClick={onRun}
          type="button"
        >
          <Gauge size={18} />
          <span>运行完善</span>
        </button>
        <button
          className="btn btn-secondary"
          disabled={!project?.package || Boolean(busy)}
          onClick={onImprove}
          type="button"
        >
          <Wand2 size={18} />
          <span>一键提升分数</span>
        </button>
      </ActionDock>
    </div>
  );
}
