import { Download, FileArchive, FileText, ShieldCheck, ArrowRight } from "@/lib/icons";
import { safeProjectName } from "@/lib/filename";
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
import { canExportPackage, deriveExportReadiness } from "@/domain";
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
      <section className="settings-group">
        <p className="empty">生成初稿后才能导出。</p>
      </section>
    );
  }
  const projectName = safeProjectName(project?.name);
  const officialAllowed = Boolean(
    postDraftReview?.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id,
  );

  // Derive the export gate state (mirrors backend compute_official_export_readiness).
  const readiness = deriveExportReadiness({
    hasPackage: canExportPackage(project.package),
    officialCompileCompleted: Boolean(
      officialCompileRun?.status === "completed" && officialCompileRun.official_package,
    ),
    officialCompilePresent: Boolean(officialCompileRun),
    postDraftReviewCompleted: Boolean(postDraftReview?.status === "completed"),
    postDraftReviewBlocked:
      Boolean(postDraftReview?.status === "completed" && !postDraftReview.export_allowed),
    postDraftReviewPresent: Boolean(postDraftReview),
  });

  const gateStatusLabel = (function () {
    if (officialAllowed) return "已解锁";
    if (readiness.reason === "post_draft_review_required") return "需要成稿会审";
    if (readiness.reason === "post_draft_review_blocked") return "已阻断";
    if (readiness.reason === "official_compile_required") return "等待编译";
    return "锁定中";
  })();

  const gateTitle = (function () {
    if (officialAllowed) return "正式稿：已通过成稿会审";
    if (readiness.reason === "post_draft_review_required")
      return "正式稿：需完成成稿会审";
    if (readiness.reason === "post_draft_review_blocked")
      return "正式稿：会审已阻断";
    return "正式稿：锁定中";
  })();

  return (
    <section className="grid gap-4">
      <StatusStrip
        aria-label="导出前状态"
        items={[
          { label: "正式稿", value: gateStatusLabel },
          { label: "提交成熟度", value: filingReport?.status === "high_risk" ? "高风险" : filingReport ? "已检查" : "未检查" },
          { label: "初稿完善", value: completionRun ? "有报告" : "无报告" },
          { label: "当前哈希", value: currentDraftHash ? currentDraftHash.slice(0, 12) : "未生成" },
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
        {!officialAllowed && readiness.reason === "post_draft_review_required" && (
          <div className="callout callout-action" data-testid="export-confirm-cta-review-required">
            <ArrowRight size={18} aria-hidden="true" />
            <div>
              <strong>正式稿已编译 — 需完成成稿会审</strong>
              <p>正式导出前必须通过成稿后多智能体会审。请前往「成稿会审」步骤运行，通过后即可导出正式提交稿。</p>
            </div>
          </div>
        )}
        {!officialAllowed && readiness.reason === "post_draft_review_blocked" && (
          <div className="callout callout-danger" data-testid="export-confirm-cta-review-blocked">
            <ShieldCheck size={18} aria-hidden="true" />
            <div>
              <strong>成稿会审已阻断</strong>
              <p>请查看会审报告中的阻断项，修改初稿后重新编译正式稿，再运行成稿会审。</p>
            </div>
          </div>
        )}
        {!officialAllowed && readiness.reason === "official_compile_required" && (
          <div className="callout callout-warn" data-testid="export-confirm-cta-compile-required">
            <ArrowRight size={18} aria-hidden="true" />
            <div>
              <strong>正式稿入口已锁定</strong>
              <p>需要先运行正式稿编译，再通过成稿会审后才能导出。请前往「正式稿编译」步骤操作。</p>
            </div>
          </div>
        )}
        {!officialAllowed && readiness.reason === "draft_required" && (
          <div className="callout callout-warn">
            <FileText size={18} aria-hidden="true" />
            <div>
              <strong>正式稿入口已锁定</strong>
              <p>请先生成专利初稿。完成初稿后再经过正式稿编译和成稿会审即可导出。</p>
            </div>
          </div>
        )}
        {!officialAllowed && readiness.reason !== "post_draft_review_required" && readiness.reason !== "post_draft_review_blocked" && readiness.reason !== "official_compile_required" && readiness.reason !== "draft_required" && (
          <div className="callout callout-warn">
            <FileText size={18} aria-hidden="true" />
            <div>
              <strong>正式稿入口已锁定</strong>
              <p>请先生成正式稿，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。</p>
            </div>
          </div>
        )}

        <div className="boundary-grid">
          <BoundaryCard
            tone="official"
            title={gateTitle}
            description={officialAllowed ? `已通过成稿会审，可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}` : readiness.detail}
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
            download={`${projectName}-正式提交稿.docx`}
            href={officialAllowed ? officialExportUrl(project.id, "docx") : undefined}
          >
            <Download size={18} />
            <span>正式提交稿 DOCX</span>
          </a>
          <a
            aria-disabled={!officialAllowed}
            className={officialAllowed ? "export-link export-link-primary" : "export-link disabled"}
            download={`${projectName}-正式提交稿.md`}
            href={officialAllowed ? officialExportUrl(project.id, "md") : undefined}
          >
            <Download size={18} />
            <span>正式提交稿 MD</span>
          </a>
          <a
            className="export-link"
            download={`${projectName}.md`}
            href={exportUrl(project.id, "md")}
            data-testid="internal-export-md"
          >
            <Download size={18} />
            <span>内部工作稿 MD</span>
          </a>
          {filingReport && (
            <a
              className="export-link"
              download={`${projectName}-提交成熟度报告.md`}
              href={filingReadinessReportUrl(project.id, filingReport.id)}
            >
              <Download size={18} />
              <span>提交成熟度报告</span>
            </a>
          )}
          {completionRun && (
            <a
              className="export-link"
              download={`${projectName}-初稿完善报告.md`}
              href={draftCompletionReportUrl(project.id, completionRun.id)}
            >
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
