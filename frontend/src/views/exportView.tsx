/**
 * ExportView — extracted from App.tsx (M3-B').
 * The expert export tool: official/internal/sidecar export + native save +
 * contamination warning + last-export success card.
 */
import { AlertTriangle, CheckCircle2, Download, FileArchive, FileText } from "@/lib/icons";
import {
  exportUrl,
  officialExportUrl,
  type DraftPackage,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
} from "@/api";
import { canExportPackage } from "@/domain";
import {
  findOfficialContaminationMarkers,
  formatBytes,
} from "@/lib/officialContamination";
import { PackagePreview } from "./disclosureViews";

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
  const officialAllowed = Boolean(
    enabled
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === currentDraftHash
      && postDraftReview.draft_package_hash === currentSourceDraftHash
      && postDraftReview.official_compile_run_id === officialCompileRun?.id
      && postDraftReview.official_package_hash === officialCompileRun?.official_package_hash,
  );
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
  return (
    <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>导出文件</h3>
      <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">
        {officialAllowed
          ? `正式稿已由成稿会审解锁：${officialCompileRun?.official_package_hash.slice(0, 12)}`
          : "正式稿需先生成，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。"}
      </p>
      {contaminationMatches.length > 0 && (
        <div
          className="flex flex-col gap-2 px-4 py-3 rounded-lg border border-app-warn/60 bg-app-warn/10 text-app-warn"
          role="alert"
          data-testid="official-contamination-warning"
        >
          <p className="flex items-center gap-2 font-medium">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>检测到正式稿仍包含 {contaminationMatches.length} 处内部痕迹</span>
          </p>
          <p className="text-sm text-app-warn/80">
            请重新运行正式稿编译并通过成稿会审后再导出；下方涉及的章节与模式仅作提示，不会自动从已生成的官方稿中删除。
          </p>
          <ul className="text-xs font-mono list-disc pl-6 text-app-warn/80">
            {contaminationMatches.slice(0, 8).map((entry, index) => (
              <li key={`${entry.section}-${entry.pattern}-${index}`}>
                {entry.section}: 命中 “{entry.pattern}”
              </li>
            ))}
            {contaminationMatches.length > 8 && (
              <li>其余 {contaminationMatches.length - 8} 处已省略…</li>
            )}
          </ul>
        </div>
      )}
      {lastExport && lastExportMatchesHash && (
        <div
          className="flex flex-col gap-2 px-4 py-3 rounded-lg border border-app-success/50 bg-app-success/10 text-app-success"
          data-testid="export-success-card"
        >
          <p className="flex items-center gap-2 font-medium">
            <CheckCircle2 size={18} aria-hidden="true" />
            <span>已导出{lastExport.format === "sidecar" ? "正式稿编译报告" : lastExport.format === "docx" ? "官方 DOCX" : "官方 Markdown"}</span>
          </p>
          <p className="text-sm font-mono break-all text-app-success/90">
            {lastExport.filePath}（{formatBytes(lastExport.byteCount)}）
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[var(--action-primary)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 transition-all disabled:opacity-50"
              disabled={!desktopDialogsAvailable}
              onClick={onOpenExportFolder}
              type="button"
            >
              <FileArchive size={16} aria-hidden="true" />
              <span>在系统文件管理器中打开</span>
            </button>
            <a
              aria-disabled={!lastExportDownloadHref}
              className={lastExportDownloadHref ? "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-medium hover:bg-white transition-colors" : "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
              href={lastExportDownloadHref}
            >
              <Download size={16} aria-hidden="true" />
              <span>再次下载</span>
            </a>
          </div>
          {!desktopDialogsAvailable && (
            <p className="text-xs text-app-success/70">
              “在系统文件管理器中打开”仅在桌面端原生对话框可用时启用。
            </p>
          )}
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
          href={officialAllowed && project ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
          href={officialAllowed && project ? officialExportUrl(project.id, "md") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 MD</span>
        </a>
        {desktopDialogsAvailable && officialCompileRun?.status === "completed" && (
          <>
            <button
              aria-disabled={!officialAllowed}
              className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--action-primary)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
              disabled={!officialAllowed}
              onClick={() => onNativeExport("docx")}
              type="button"
            >
              <FileText size={18} />
              <span>原生保存 DOCX…</span>
            </button>
            <button
              aria-disabled={!officialAllowed}
              className={officialAllowed ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--action-primary)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
              disabled={!officialAllowed}
              onClick={() => onNativeExport("md")}
              type="button"
            >
              <FileText size={18} />
              <span>原生保存 Markdown…</span>
            </button>
            <button
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors"
              onClick={() => onNativeExport("sidecar")}
              type="button"
            >
              <FileText size={18} />
              <span>导出风险说明…</span>
            </button>
          </>
        )}
        {[
          ["docx", "DOCX"],
          ["md", "Markdown"],
          ["mmd", "Mermaid"],
          ["prompt", "绘图提示词"],
        ].map(([kind, label]) => (
          <a
            aria-disabled={!enabled}
            className={enabled ? "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] shadow-sm hover:bg-white text-[var(--text-primary)] font-medium transition-colors" : "inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/40 font-medium cursor-not-allowed"}
            href={enabled && project ? exportUrl(project.id, kind as "docx" | "md" | "mmd" | "prompt") : undefined}
            key={kind}
          >
            <Download size={18} />
            <span>{label}</span>
          </a>
        ))}
      </div>
      <PackagePreview packageValue={packageValue} compact />
    </section>
  );
}
