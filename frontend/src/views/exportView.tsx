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
  type ExportReadiness,
  type OfficialCompileRun,
  type PostDraftReviewRun,
  type ProjectRecord,
  type QualityCheckStates,
} from "@/api";
import { canExportPackage } from "@/domain";
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

const QUALITY_CHECK_LABELS: Record<string, string> = {
  filing_readiness: "提交前质量检查",
  claim_defense_worksheet: "权利要求防守工作表",
  draft_completion: "成稿完整度检查",
};

function qualityCheckLabel(key: string): string {
  return QUALITY_CHECK_LABELS[key] ?? key;
}

function qualityGateDetailLines(qualityCheckStates?: QualityCheckStates): string[] {
  if (!qualityCheckStates) return [];
  const entries = Object.entries(qualityCheckStates);
  const missing = entries
    .filter(([, state]) => state === "missing")
    .map(([key]) => qualityCheckLabel(key));
  const stale = entries
    .filter(([, state]) => state === "stale")
    .map(([key]) => qualityCheckLabel(key));
  const failed = entries
    .filter(([, state]) => state === "failed")
    .map(([key]) => qualityCheckLabel(key));
  const unknown = entries
    .filter(([, state]) => state === "unknown")
    .map(([key]) => qualityCheckLabel(key));
  const lines: string[] = [];
  if (missing.length) lines.push(`缺少：${missing.join("、")}`);
  if (stale.length) lines.push(`已过期：${stale.join("、")}`);
  if (failed.length) lines.push(`失败：${failed.join("、")}`);
  if (unknown.length) lines.push(`来源未知：${unknown.join("、")}`);
  return lines;
}

type LockedGateDetail = {
  title: string;
  lines: string[];
};

function compactRecordValues(record: Record<string, string>): string {
  const preferredKeys = ["category", "code", "type", "pattern", "section", "target", "message", "reason"];
  const preferred = preferredKeys
    .map((key) => record[key])
    .filter((value): value is string => Boolean(value));
  const remaining = Object.entries(record)
    .filter(([key, value]) => !preferredKeys.includes(key) && Boolean(value))
    .map(([, value]) => value);
  return Array.from(new Set([...preferred, ...remaining])).join("；");
}

function compileGateDetailLines(
  exportReadiness: ExportReadiness | null | undefined,
  officialCompileRun: OfficialCompileRun | null,
): string[] {
  const blockedItems = exportReadiness?.compile_blocked_items?.length
    ? exportReadiness.compile_blocked_items
    : officialCompileRun?.blocked_items ?? [];
  return blockedItems
    .map(compactRecordValues)
    .filter(Boolean)
    .map((item) => `阻断项：${item}`);
}

function reviewGateStatus(
  exportReadiness: ExportReadiness | null | undefined,
  postDraftReview: PostDraftReviewRun | null,
): ExportReadiness["review_gate_status"] | undefined {
  if (exportReadiness?.review_gate_status) return exportReadiness.review_gate_status;
  if (!postDraftReview) return undefined;
  if (postDraftReview.status === "queued" || postDraftReview.status === "running") return postDraftReview.status;
  if (postDraftReview.status === "failed" || postDraftReview.status === "interrupted") return postDraftReview.status;
  if (postDraftReview.status === "completed" && postDraftReview.export_allowed) return "passed";
  return postDraftReview.chair_result?.status ?? "blocked";
}

function reviewGateDetailLines(
  exportReadiness: ExportReadiness | null | undefined,
  postDraftReview: PostDraftReviewRun | null,
): string[] {
  const issues = exportReadiness?.review_blocking_issues?.length
    ? exportReadiness.review_blocking_issues
    : postDraftReview?.blocking_issues ?? [];
  return issues.map((issue) => `阻断问题：${issue}`);
}

function lockedGateDetail({
  exportReadiness,
  officialCompileRun,
  postDraftReview,
}: {
  exportReadiness?: ExportReadiness | null;
  officialCompileRun: OfficialCompileRun | null;
  postDraftReview: PostDraftReviewRun | null;
}): LockedGateDetail | null {
  const compileStatus = exportReadiness?.compile_status ?? officialCompileRun?.status;
  if (compileStatus === "queued") {
    return {
      title: "正式稿编译排队中",
      lines: [],
    };
  }
  if (compileStatus === "running") {
    return {
      title: "正式稿编译运行中",
      lines: [],
    };
  }
  if (compileStatus === "blocked") {
    return {
      title: "正式稿编译被阻断",
      lines: compileGateDetailLines(exportReadiness, officialCompileRun),
    };
  }
  if (compileStatus === "failed") {
    return {
      title: "正式稿编译失败",
      lines: compileGateDetailLines(exportReadiness, officialCompileRun),
    };
  }
  if (compileStatus === "missing" || (exportReadiness?.official_compile_required && !officialCompileRun)) {
    return {
      title: "正式稿尚未编译",
      lines: [],
    };
  }

  const status = reviewGateStatus(exportReadiness, postDraftReview);
  if (status === "queued") return { title: "成稿会审排队中", lines: [] };
  if (status === "running") return { title: "成稿会审运行中", lines: [] };
  if (status === "needs_revision") {
    return {
      title: "成稿会审需要修复",
      lines: reviewGateDetailLines(exportReadiness, postDraftReview),
    };
  }
  if (status === "blocked") {
    return {
      title: "成稿会审阻断导出",
      lines: reviewGateDetailLines(exportReadiness, postDraftReview),
    };
  }
  if (status === "failed") return { title: "成稿会审失败", lines: [] };
  if (status === "interrupted") return { title: "成稿会审已中断", lines: [] };
  if (status === "missing" || exportReadiness?.post_draft_review_required) {
    return { title: "成稿会审未运行", lines: [] };
  }
  return null;
}

function lockedStatusLabel(
  currentQualityChecked: boolean,
  detail: LockedGateDetail | null,
): string {
  if (!currentQualityChecked) return "等待质检";
  if (!detail) return "等待会审";
  if (detail.title.includes("编译被阻断")) return "编译阻断";
  if (detail.title.includes("编译失败")) return "编译失败";
  if (detail.title.includes("编译运行") || detail.title.includes("编译排队")) return "编译中";
  if (detail.title.includes("编译")) return "等待编译";
  if (detail.title.includes("阻断")) return "会审阻断";
  if (detail.title.includes("需要修复")) return "需修复";
  if (detail.title.includes("失败")) return "会审失败";
  if (detail.title.includes("中断")) return "会审中断";
  if (detail.title.includes("运行") || detail.title.includes("排队")) return "会审中";
  return "等待会审";
}

const OFFICIAL_GATE_DEFAULT_DESCRIPTION =
  "正式稿需先完成当前初稿质量检查、生成正式稿，并通过针对当前正式稿的成稿会审；内部稿和风险说明仅供内部复核。";

export function ExportView({
  project,
  packageValue,
  postDraftReview,
  officialCompileRun,
  exportReadiness,
  currentDraftHash,
  currentSourceDraftHash,
  currentQualityChecked,
  qualityCheckStates,
  lastExport,
  onNativeExport,
  onOpenExportFolder,
  desktopDialogsAvailable,
}: {
  project: ProjectRecord | null;
  packageValue: DraftPackage | null;
  postDraftReview: PostDraftReviewRun | null;
  officialCompileRun: OfficialCompileRun | null;
  exportReadiness?: ExportReadiness | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  currentQualityChecked: boolean;
  qualityCheckStates?: QualityCheckStates;
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
      && currentQualityChecked
      && officialCompileRun?.status === "completed"
      && officialCompileRun.official_package
      && officialCompileRun.source_draft_hash === currentSourceDraftHash
      && postDraftReview?.status === "completed"
      && postDraftReview.export_allowed
      && postDraftReview.draft_package_hash === officialCompileRun.source_draft_hash
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
  const qualityGateLines = qualityGateDetailLines(qualityCheckStates);
  const showQualityGateDetails = !officialAllowed && !currentQualityChecked && qualityGateLines.length > 0;
  const gateDetail = officialAllowed || showQualityGateDetails
    ? null
    : lockedGateDetail({ exportReadiness, officialCompileRun, postDraftReview });
  const lockedGateLines = showQualityGateDetails ? qualityGateLines : gateDetail?.lines ?? [];
  const lockedGateTitle = showQualityGateDetails ? "质量检查未完成" : gateDetail?.title ?? "正式稿入口已锁定";
  return (
    <section className="col-span-full grid gap-5">
      <StatusStrip
        aria-label="导出状态"
        items={[
          { label: "正式稿状态", value: officialAllowed ? "已解锁" : lockedStatusLabel(currentQualityChecked, gateDetail) },
          { label: "源稿哈希", value: currentSourceDraftHash ? currentSourceDraftHash.slice(0, 12) : "未生成" },
          { label: "正式稿哈希", value: officialCompileRun?.official_package_hash?.slice(0, 12) ?? "未编译" },
          { label: "最近导出", value: lastExport && lastExportMatchesHash ? lastExport.format.toUpperCase() : "无有效导出" },
        ]}
      />

      <SettingsGroup
        title="导出边界"
        description="正式提交稿、内部复核材料和风险说明与追溯使用不同容器，避免内部会审内容进入可提交文件。"
      >
        <div className="boundary-grid">
          <BoundaryCard
            tone="official"
            title="正式提交稿"
            description="只包含清污后的权利要求、说明书和摘要；必须由质量检查、正式稿编译和成稿会审共同解锁。"
          />
          <BoundaryCard
            tone="internal"
            title="内部复核材料"
            description="保留会审结论、护城河、支撑缺口和补强建议，仅供内部复核，不作为提交稿。"
          />
          <BoundaryCard
            tone="external"
            title="风险说明与追溯"
            description="解释导出阻断、清污命中和版本哈希来源，帮助人工复核，不替代专利代理师或律师意见。"
          />
        </div>
      </SettingsGroup>

      <SettingsGroup title="正式提交稿" description="正式稿导出受门禁控制，只呈现可提交给代理师或提交系统的文件形态。">
        <InfoCard
          icon={<FileText size={18} aria-hidden="true" />}
          tone={officialAllowed ? "success" : "warn"}
          title={officialAllowed ? "正式稿已通过质量检查和成稿会审" : lockedGateTitle}
          description={
            officialAllowed
              ? `当前正式稿可导出：${officialCompileRun?.official_package_hash.slice(0, 12)}`
              : lockedGateLines.length > 0
                ? (
                    <>
                      <span>{OFFICIAL_GATE_DEFAULT_DESCRIPTION}</span>
                      {lockedGateLines.map((line) => (
                        <span key={line}>
                          <br />
                          {line}
                        </span>
                      ))}
                    </>
                  )
                : OFFICIAL_GATE_DEFAULT_DESCRIPTION
          }
          meta={<span className={officialAllowed ? "tag tag-success" : "tag tag-warn"}>{officialAllowed ? "可导出" : "需处理"}</span>}
        />
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
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <a
          aria-disabled={!officialAllowed}
          className={exportLinkClass(officialAllowed, true)}
          href={officialAllowed && project ? officialExportUrl(project.id, "docx") : undefined}
        >
          <Download size={18} />
          <span>正式提交稿 DOCX</span>
        </a>
        <a
          aria-disabled={!officialAllowed}
          className={exportLinkClass(officialAllowed, true)}
          href={officialAllowed && project ? officialExportUrl(project.id, "md") : undefined}
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
          </>
        )}
      </div>
      </SettingsGroup>

      <SettingsGroup
        title="内部复核材料"
        description="内部材料始终带有策略语境，请勿直接作为正式提交稿。"
      >
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[
          ["docx", "DOCX"],
          ["md", "Markdown"],
          ["mmd", "Mermaid"],
          ["prompt", "绘图提示词"],
        ].map(([kind, label]) => (
          <a
            aria-disabled={!enabled}
            className={exportLinkClass(enabled)}
            href={enabled && project ? exportUrl(project.id, kind as "docx" | "md" | "mmd" | "prompt") : undefined}
            key={kind}
          >
            <Download size={18} />
            <span>{label}</span>
          </a>
        ))}
      </div>
      </SettingsGroup>

      <SettingsGroup title="风险说明与追溯" description="用于人工复核导出内容、阻断原因和追溯信息，正式提交前仍需专业人员确认。">
      {desktopDialogsAvailable && officialCompileRun?.status === "completed" && (
        <div className="workspace-action-row">
          <button
            className="export-link"
            onClick={() => onNativeExport("sidecar")}
            type="button"
          >
            <FileText size={18} />
            <span>导出风险说明…</span>
          </button>
        </div>
      )}
      <div className="report-preview-pane">
        <PackagePreview packageValue={packageValue} compact />
      </div>
      </SettingsGroup>
    </section>
  );
}
