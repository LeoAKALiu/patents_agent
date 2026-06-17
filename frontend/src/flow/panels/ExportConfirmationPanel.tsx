import { Download } from "@/lib/icons";
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
import type { ExpertToolOpener } from "../parts";

export interface ExportConfirmationPanelProps {
  project: ProjectRecord | null;
  filingReport: FilingReadinessReport | null;
  completionRun: DraftCompletionRun | null;
  postDraftReview: PostDraftReviewRun | null;
  currentDraftHash: string;
  officialCompileRun: OfficialCompileRun | null;
  onOpenExpertTool: ExpertToolOpener;
}

export function ExportConfirmationPanel({
  project,
  filingReport,
  completionRun,
  postDraftReview,
  currentDraftHash,
  officialCompileRun,
  onOpenExpertTool,
}: ExportConfirmationPanelProps) {
  if (!project?.package) {
    return (
      <section className="guided-panel">
        <p className="empty">生成初稿后才能导出。</p>
      </section>
    );
  }
  const officialAllowed = Boolean(
    postDraftReview?.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id,
  );

  return (
    <section className="guided-panel">
      <div className="guided-panel-heading">
        <div>
          <h3>导出前确认</h3>
          <p>正式稿只在正式稿编译完成、成稿会审通过且哈希匹配后放行；导出文件仍需专利代理师或律师复核后再提交。</p>
        </div>
        <Download size={24} />
      </div>
      {filingReport?.status === "high_risk" && <p className="workflow-hint">当前提交成熟度为高风险：请先处理报告中的不利表述、内部痕迹或支撑缺口，再让专业人员复核。</p>}
      {!officialAllowed && (
        <p className="workflow-hint">正式稿入口已锁定：请先生成正式稿，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。</p>
      )}
      <div className="export-confirmation">
        <article>
          <strong>正式稿</strong>
          <span>{officialAllowed ? `已通过成稿会审，可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}` : "等待正式稿编译和成稿会审通过后解锁。"}</span>
        </article>
        <article>
          <strong>内部稿</strong>
          <span>保留策略、风险、会审、支撑矩阵和补强建议，仅供内部复核，不作为提交稿。</span>
        </article>
        <article>
          <strong>导出原则</strong>
          <span>阻断项会锁定正式稿；风险说明用于解释风险来源，不替代最终人工审查。</span>
        </article>
      </div>
      <button className="icon-button" onClick={() => onOpenExpertTool("export")} type="button">
        查看专家导出工具
      </button>
      <div className="export-grid">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link" : "export-link disabled"}
          href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "export-link" : "export-link disabled"}
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
    </section>
  );
}
