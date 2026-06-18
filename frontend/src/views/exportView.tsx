/**
 * ExportView — extracted from App.tsx (M3-B').
 * The expert export tool: official/internal/sidecar export + native save +
 * contamination warning + last-export success card.
 */
import { safeProjectName } from "@/lib/filename";
import { AlertTriangle, ArrowRight, CheckCircle2, Download, FileArchive, FileText } from "@/lib/icons";
import {
  exportUrl,
  officialExportUrl,
  type DraftPackage,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import { canExportPackage, deriveExportReadiness } from "@/domain";
import {
  findOfficialContaminationMarkers,
  formatBytes,
} from "@/lib/officialContamination";
import {
  ActionDock,
  BoundaryCard,
  InfoCard,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";
import { PackagePreview } from "./disclosureViews";

function exportLinkClass(enabled: boolean, primary = false): string {
  if (!enabled) return "export-link disabled";
  return primary ? "export-link export-link-primary" : "export-link";
}

export function ExportView({
  project,
  packageValue,
  postDraftReview,
  officialCompileRun,
  currentDraftHash,
  currentSourceDraftHash,
  lastExport,
  onNativeExport,
  onOpenExportFolder,
  desktopDialogsAvailable,
}: {
  project: ProjectRecord | null;
  packageValue: DraftPackage | null;
  postDraftReview: PostDraftReviewRun | null;
  officialCompileRun: OfficialCompileRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  lastExport: {
    format: "docx" | "md" | "sidecar";
    filePath: string;
    byteCount: number;
    officialPackageHash?: string;
  } | null;
  onNativeExport: (format: "docx" | "md" | "sidecar") => void;
  onOpenExportFolder: () => void;
  desktopDialogsAvailable: boolean;
}) {
  const enabled = canExportPackage(packageValue);
  const projectName = safeProjectName(project?.name);

  // Derive the export gate state from existing props (mirrors backend
  // compute_official_export_readiness without a network round-trip).
  const readiness = deriveExportReadiness({
    hasPackage: enabled,
    officialCompileCompleted: Boolean(
      officialCompileRun?.status === "completed" && officialCompileRun.official_package,
    ),
    officialCompilePresent: Boolean(officialCompileRun),
    postDraftReviewCompleted: Boolean(postDraftReview?.status === "completed"),
    postDraftReviewBlocked:
      Boolean(postDraftReview?.status === "completed" && !postDraftReview.export_allowed),
    postDraftReviewPresent: Boolean(postDraftReview),
  });

  // Keep the existing officialAllowed check for backward compat — it gates
  // the actual download hrefs and is stricter than readiness.ready because
  // it also verifies hash matches between compile run and review.
  const officialAllowed = Boolean(
    enabled
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );

  const gateStatusLabel = (function () {
    if (officialAllowed) return "已解锁 — 可导出";
    if (readiness.reason === "draft_required") return "未生成初稿";
    if (readiness.reason === "official_compile_required") return "等待正式稿编译";
    if (readiness.reason === "post_draft_review_required") return "需要成稿会审";
    if (readiness.reason === "post_draft_review_blocked") return "成稿会审已阻断";
    return "等待会审";
  })();

  const gateTitle = (function () {
    if (officialAllowed) return "正式稿已通过成稿会审";
    if (readiness.reason === "post_draft_review_required")
      return "正式稿已编译 — 需完成成稿会审";
    if (readiness.reason === "post_draft_review_blocked")
      return "成稿会审已阻断 — 需修订后重新会审";
    if (readiness.reason === "official_compile_required") return "正式稿入口已锁定";
    if (readiness.reason === "draft_required") return "正式稿入口已锁定";
    return "正式稿入口已锁定";
  })();

  const gateDescription = (function () {
    if (officialAllowed)
      return `当前正式稿可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}`;
    return readiness.detail;
  })();

  // PR7 (issue #21): scan the official package text for residual internal
  // markers (log lines, prompt fragments, review memos, mermaid fences, etc.).
  // The backend already strips these at compile time and the gate refuses to
  // run, but a defensive warning in the UI lets the user double-check before
  // they hand the file to their attorney / 国知局.
  const officialPackage = officialCompileRun?.official_package ?? null;
  const contaminationMatches = officialPackage
    ? findOfficialContaminationMarkers(officialPackage)
    : [];
  const lastExportMatchesHash = Boolean(
    lastExport?.officialPackageHash &&
    lastExport.officialPackageHash === officialCompileRun?.official_package_hash,
  );
  const lastExportDownloadHref = project && lastExport
    ? lastExport.format === "sidecar"
      ? officialCompileRun?.id
        ? `/api/projects/${project.id}/official-compile-runs/${officialCompileRun.id}/report.md`
        : undefined
      : officialExportUrl(project.id, lastExport.format === "docx" ? "docx" : "md")
    : undefined;
  const lastExportDownloadName = lastExport
    ? lastExport.format === "sidecar"
      ? `${projectName}-正式稿编译报告.md`
      : lastExport.format === "docx"
        ? `${projectName}-正式提交稿.docx`
        : `${projectName}-正式提交稿.md`
    : undefined;
  const filenames: Record<"docx" | "md" | "mmd" | "prompt", string> = {
    docx: `${projectName}.docx`,
    md: `${projectName}.md`,
    mmd: `${projectName}.mmd`,
    prompt: `${projectName}-绘图提示词.md`,
  };
  return (
    <section className="col-span-full grid gap-5">
      <StatusStrip
        aria-label="导出状态"
        items={[
          { label: "正式稿状态", value: gateStatusLabel },
          { label: "源稿哈希", value: currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成" },
          { label: "正式稿哈希", value: officialCompileRun?.official_package_hash?.slice(0, 12) ?? "未编译" },
          { label: "最近导出", value: lastExport && lastExportMatchesHash ? lastExport.format.toUpperCase() : "无有效导出" },
        ]}
      />

      <SettingsGroup
        title="导出边界"
        description="正式提交稿、内部工作稿和风险说明使用不同容器，避免内部会审内容进入可提交文件。"
      >
        <div className="boundary-grid">
          <BoundaryCard
            tone="official"
            title="正式提交稿"
            description="只包含清污后的权利要求、说明书和摘要；必须由正式稿编译和成稿会审共同解锁。"
          />
          <BoundaryCard
            tone="internal"
            title="内部工作稿"
            description="保留会审结论、护城河、支撑缺口和补强建议，仅供内部复核，不作为提交稿。"
          />
          <BoundaryCard
            tone="external"
            title="风险说明"
            description="解释导出阻断、清污命中和版本哈希来源，帮助人工复核，不替代专利代理师或律师意见。"
          />
        </div>
      </SettingsGroup>

      <SettingsGroup title="正式稿门禁">
        <InfoCard
          icon={<FileText size={18} aria-hidden="true" />}
          tone={officialAllowed ? "success" : "warn"}
          title={gateTitle}
          description={gateDescription}
          meta={<span className={officialAllowed ? "tag tag-success" : "tag tag-warn"}>{officialAllowed ? "可导出" : "需处理"}</span>}
          data-testid="official-export-gate-card"
        />
      {readiness.reason === "post_draft_review_required" && (
        <div
          className="callout callout-action"
          role="alert"
          data-testid="official-export-cta-review-required"
        >
          <ArrowRight size={18} aria-hidden="true" />
          <div>
            <strong>下一步：运行成稿会审</strong>
            <p>正式稿已编译完成，但导出前必须通过成稿后多智能体会审。请在流程中进入「成稿会审」步骤运行，通过后即可导出正式提交稿。</p>
          </div>
        </div>
      )}
      {readiness.reason === "post_draft_review_blocked" && (
        <div
          className="callout callout-danger"
          role="alert"
          data-testid="official-export-cta-review-blocked"
        >
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>成稿会审已阻断，需要修订</strong>
            <p>请查看会审报告中的阻断项，修改初稿后重新编译正式稿，再运行成稿会审。通过后即可导出正式提交稿。</p>
          </div>
        </div>
      )}
      {readiness.reason === "official_compile_required" && (
        <div
          className="callout callout-warn"
          role="alert"
          data-testid="official-export-cta-compile-required"
        >
          <ArrowRight size={18} aria-hidden="true" />
          <div>
            <strong>需要先编译正式稿</strong>
            <p>正式导出前需要先生成正式稿。请在流程中进入「正式稿编译」步骤运行，编译通过后再完成成稿会审即可导出。</p>
          </div>
        </div>
      )}
      {readiness.reason === "draft_required" && (
        <div
          className="callout callout-warn"
          role="alert"
          data-testid="official-export-cta-draft-required"
        >
          <ArrowRight size={18} aria-hidden="true" />
          <div>
            <strong>需要先生成专利初稿</strong>
            <p>正式导出前需要先完成初稿生成，再经过正式稿编译和成稿会审。请先在流程中生成初稿。</p>
          </div>
        </div>
      )}
      {contaminationMatches.length > 0 && (
        <div
          className="callout callout-warn"
          role="alert"
          data-testid="official-contamination-warning"
        >
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>检测到正式稿仍包含 {contaminationMatches.length} 处内部痕迹</strong>
            <p>请重新运行正式稿编译并通过成稿会审后再导出；下方涉及的章节与模式仅作提示，不会自动从已生成的官方稿中删除。</p>
            <ul className="mt-2 list-disc pl-5 font-mono text-xs text-[var(--warn-text)]">
              {contaminationMatches.slice(0, 8).map((entry, index) => (
                <li key={`${entry.section}-${entry.pattern}-${index}`}>
                  {entry.section}: 命中 “{entry.pattern}”
                </li>
              ))}
              {contaminationMatches.length > 8 && (
                <li>其余 {contaminationMatches.length - 8} 处已省略...</li>
              )}
            </ul>
          </div>
        </div>
      )}
      {lastExport && lastExportMatchesHash && (
        <InfoCard
          icon={<CheckCircle2 size={18} aria-hidden="true" />}
          tone="success"
          title={`已导出${lastExport.format === "sidecar" ? "正式稿编译报告" : lastExport.format === "docx" ? "官方 DOCX" : "官方 Markdown"}`}
          description={`${lastExport.filePath}（${formatBytes(lastExport.byteCount)}）`}
          meta={<span className="tag tag-success">哈希匹配</span>}
          action={(
            <div className="button-row">
              <button
                className="btn btn-primary"
                disabled={!desktopDialogsAvailable}
                onClick={onOpenExportFolder}
                type="button"
              >
                <FileArchive size={16} aria-hidden="true" />
                <span>打开文件夹</span>
              </button>
              <a
                aria-disabled={!lastExportDownloadHref}
                className={lastExportDownloadHref ? "btn btn-secondary" : "btn btn-secondary is-disabled"}
                download={lastExportDownloadName}
                href={lastExportDownloadHref}
              >
                <Download size={16} aria-hidden="true" />
                <span>再次下载</span>
              </a>
            </div>
          )}
          data-testid="export-success-card"
        >
          {!desktopDialogsAvailable && (
            <p>
              “在系统文件管理器中打开”仅在桌面端原生对话框可用时启用。
            </p>
          )}
        </InfoCard>
      )}
      </SettingsGroup>

      <SettingsGroup
        title="导出文件"
        description="正式提交稿受门禁控制；内部工作稿始终带有策略语境，不可作为正式提交稿。"
      >
      <div
        className="grid grid-cols-2 sm:grid-cols-3 gap-4"
        aria-label="正式提交稿导出"
        data-testid="official-export-grid"
      >
        <a
          aria-disabled={!officialAllowed}
          className={exportLinkClass(officialAllowed, true)}
          download={`${projectName}-正式提交稿.docx`}
          href={officialAllowed && project ? officialExportUrl(project.id, "docx") : undefined}
          data-testid="official-export-docx"
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={exportLinkClass(officialAllowed, true)}
          download={`${projectName}-正式提交稿.md`}
          href={officialAllowed && project ? officialExportUrl(project.id, "md") : undefined}
          data-testid="official-export-md"
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        {desktopDialogsAvailable && officialCompileRun?.status === "completed" && (
          <>
            <button
              aria-disabled={!officialAllowed}
              className={exportLinkClass(officialAllowed, true)}
              disabled={!officialAllowed}
              onClick={() => onNativeExport("docx")}
              type="button"
            >
              <FileText size={18} />
              <span>原生保存 DOCX…</span>
            </button>
            <button
              aria-disabled={!officialAllowed}
              className={exportLinkClass(officialAllowed, true)}
              disabled={!officialAllowed}
              onClick={() => onNativeExport("md")}
              type="button"
            >
              <FileText size={18} />
              <span>原生保存 Markdown…</span>
            </button>
            <button
              className="export-link"
              onClick={() => onNativeExport("sidecar")}
              type="button"
            >
              <FileText size={18} />
              <span>导出风险说明…</span>
            </button>
          </>
        )}
      </div>

      <div className="callout callout-warn" data-testid="internal-export-notice">
        <AlertTriangle size={18} aria-hidden="true" />
        <div>
          <strong>以下为内部工作稿</strong>
          <p>
            内部工作稿未经过正式稿清污与成稿会审，可能包含策略备注、护城河、支撑缺口或绘图素材，仅供内部复核，不可作为正式提交稿。
          </p>
        </div>
      </div>
      <div
        className="grid grid-cols-2 sm:grid-cols-3 gap-4"
        aria-label="内部工作稿导出"
        data-testid="internal-export-grid"
      >
        {([
          ["docx", "DOCX"],
          ["md", "Markdown"],
          ["mmd", "Mermaid"],
          ["prompt", "绘图提示词"],
        ] as Array<[keyof typeof filenames, string]>).map(([kind, label]) => (
          <a
            aria-disabled={!enabled}
            className={exportLinkClass(enabled)}
            download={filenames[kind]}
            href={enabled && project ? exportUrl(project.id, kind) : undefined}
            key={kind}
            data-testid={`internal-export-${kind}`}
          >
            <Download size={18} />
            <span>内部工作稿 {label}</span>
          </a>
        ))}
      </div>
      </SettingsGroup>

      <SettingsGroup title="包内容预览" description="用于人工复核导出内容，正式提交前仍需专业人员确认。">
      <PackagePreview packageValue={packageValue} compact />
      </SettingsGroup>
    </section>
  );
}
