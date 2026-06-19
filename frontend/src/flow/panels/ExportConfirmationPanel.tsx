import { Download, FileArchive, FileText, ShieldCheck } from "@/lib/icons";
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
  BoundaryCard,
  InfoCard,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";
import type { ExpertToolOpener } from "../parts";

export interface ExportConfirmationPanelProps {
  project: ProjectRecord | null;
  filingReport: FilingReadinessReport | null;
  completionRun: DraftCompletionRun | null;
  postDraftReview: PostDraftReviewRun | null;
  currentSourceDraftHash: string;
  officialCompileRun: OfficialCompileRun | null;
  onOpenExpertTool: ExpertToolOpener;
  onNavigateToPostReview?: () => void;
}

export function ExportConfirmationPanel({
  project,
  filingReport,
  completionRun,
  postDraftReview,
  currentSourceDraftHash,
  officialCompileRun,
  onOpenExpertTool,
  onNavigateToPostReview,
}: ExportConfirmationPanelProps) {
  if (!project?.package) {
    return (
      <section className="settings-group">
        <p className="empty">生成初稿后才能导出。</p>
      </section>
    );
  }
  const compileCurrent = Boolean(
    officialCompileRun?.status === "completed"
      && officialCompileRun.official_package
      && officialCompileRun.source_draft_hash === currentSourceDraftHash,
  );
  const reviewPassed = Boolean(
    postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === officialCompileRun?.source_draft_hash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
  const officialAllowed = compileCurrent && reviewPassed;
  // Lock reason depends on which gate is failing.
  const lockReason: string | null = officialAllowed
    ? null
    : !compileCurrent
      ? "请先生成正式稿。当前初稿尚未通过正式稿编译清除内部痕迹，无法导出正式提交稿。"
      : "正式稿编译已完成，但需通过成稿后多智能体会审。会审将检查权利要求质量、说明书清洁度、技术硬度和内部痕迹，通过后即可解锁正式导出。";
  const lockAction: string | null = officialAllowed
    ? null
    : !compileCurrent
      ? "run_official_compile"
      : "run_post_draft_review";

  return (
    <section className="grid gap-4">
      <StatusStrip
        aria-label="导出前状态"
        items={[
          { label: "正式稿编译", value: compileCurrent ? "已完成" : "未完成" },
          { label: "成稿会审", value: reviewPassed ? "已通过" : compileCurrent ? "等待会审" : "等待编译" },
          { label: "正式导出", value: officialAllowed ? "已解锁" : "锁定中" },
          { label: "提交成熟度", value: filingReport?.status === "high_risk" ? "高风险" : filingReport ? "已检查" : "未检查" },
        ]}
      />

      <SettingsGroup
        title="导出前确认"
        description="正式稿只在正式稿编译完成、成稿会审通过且哈希匹配后放行；导出文件仍需专业人员复核后再提交。"
      >
        {filingReport?.status === "high_risk" && (
          <div className="callout callout-warn">
            <ShieldCheck size={18} aria-hidden="true" />
            <div>
              <strong>当前提交成熟度为高风险</strong>
              <p>请先处理报告中的不利表述、内部痕迹或支撑缺口，再让专业人员复核。</p>
            </div>
          </div>
        )}
        {!officialAllowed && (
          <div className="callout callout-warn">
            <FileText size={18} aria-hidden="true" />
            <div>
              <strong>正式稿入口已锁定</strong>
              <p>{lockReason}</p>
              {lockAction === "run_post_draft_review" && onNavigateToPostReview && (
                <button
                  className="btn btn-primary"
                  onClick={onNavigateToPostReview}
                  type="button"
                  style={{ marginTop: "0.5rem" }}
                >
                  <ShieldCheck size={16} aria-hidden="true" />
                  <span>前往成稿会审</span>
                </button>
              )}
            </div>
          </div>
        )}

        <div className="boundary-grid">
          <BoundaryCard
            tone="official"
            title="正式稿"
            description={officialAllowed
              ? `已通过成稿会审，可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}`
              : compileCurrent
                ? `编译已完成，等待成稿会审通过：${officialCompileRun?.official_package_hash.slice(0, 12)}`
                : "等待正式稿编译和成稿会审通过后解锁。"}
          />
          <BoundaryCard
            tone="internal"
            title="内部稿"
            description="保留策略、风险、会审、支撑矩阵和补强建议，仅供内部复核，不作为提交稿。"
          />
          <BoundaryCard
            tone="external"
            title="导出原则"
            description="阻断项会锁定正式稿；风险说明用于解释风险来源，不替代最终人工审查。"
          />
        </div>
      </SettingsGroup>

      <SettingsGroup title="可导出文件">
      <div className="export-grid">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link export-link-primary" : "export-link disabled"}
          href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link export-link-primary" : "export-link disabled"}
          href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        <a className="export-link" href={exportUrl(project.id, "md")}>
          <Download size={18} />
          <span>内部策略稿 MD</span>
        </a>
        {filingReport && (
          <a className="export-link" href={filingReadinessReportUrl(project.id, filingReport.id)}>
            <Download size={18} />
            <span>提交成熟度报告</span>
          </a>
        )}
        {completionRun && (
          <a className="export-link" href={draftCompletionReportUrl(project.id, completionRun.id)}>
            <Download size={18} />
            <span>初稿完善报告</span>
          </a>
        )}
      </div>
      </SettingsGroup>

      <InfoCard
        icon={<FileArchive size={18} aria-hidden="true" />}
        title="专家导出工具"
        description="查看完整导出面板、桌面端原生保存和风险说明侧车文件。"
        action={(
          <button className="btn btn-secondary" onClick={() => onOpenExpertTool("export")} type="button">
            <Download size={16} aria-hidden="true" />
            <span>打开导出工具</span>
          </button>
        )}
      />
    </section>
  );
}
