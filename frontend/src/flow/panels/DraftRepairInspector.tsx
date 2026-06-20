import type { DraftRepairPatch, DraftReviewIssue } from "@/api";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2 as CheckCircle, Loader2, PenLine, Wand2, XCircle } from "@/lib/icons";

const ISSUE_KIND_LABELS: Record<DraftReviewIssue["kind"], string> = {
  blocking: "阻断",
  hit: "命中",
  suggestion: "建议",
};

const ISSUE_SEVERITY_LABELS: Record<DraftReviewIssue["severity"], string> = {
  critical: "严重",
  high: "高",
  medium: "中",
  low: "低",
};

const SECTION_LABELS: Record<string, string> = {
  title: "标题",
  abstract: "摘要",
  claims: "权利要求书",
  description: "说明书",
  drawing_description: "附图说明",
  unknown: "未知",
};

const PATCH_STATUS_LABELS: Record<DraftRepairPatch["status"], string> = {
  proposed: "等待应用",
  stale: "初稿已过期",
  unsafe: "不安全",
  applied: "已应用",
};

export interface DraftRepairInspectorProps {
  issue: DraftReviewIssue | null;
  sectionText: string;
  stale: boolean;
  patch: DraftRepairPatch | null;
  generating: boolean;
  applying: boolean;
  patchError: string | null;
  onGeneratePatch: () => void;
  onApplyPatch: () => void;
  onDismissPatch: () => void;
}

export function DraftRepairInspector({
  issue,
  sectionText,
  stale,
  patch,
  generating,
  applying,
  patchError,
  onGeneratePatch,
  onApplyPatch,
  onDismissPatch,
}: DraftRepairInspectorProps) {
  if (!issue) {
    return (
      <aside className="repair-inspector" aria-label="标注式修复详情面板">
        <div className="repair-inspector-header">
          <h4>修复面板</h4>
        </div>
        <div className="empty-panel compact">
          <strong>未选择问题</strong>
          <p>从左侧问题列表中选择一个，查看详情和操作。</p>
        </div>
      </aside>
    );
  }

  const targetPatchable = issue.target_section !== "unknown";
  const canGenerate = !stale && !generating && targetPatchable;
  const generateDisabled = !canGenerate;
  const anchorModeLabel = anchorModeText(issue.anchor.type);
  const anchorSnippet = issue.anchor.snippet ?? issue.snippet ?? issue.message;
  const anchorContext = buildAnchorContext(issue, sectionText);

  const canApply = patch && patch.status === "proposed" && !applying;
  const applyDisabledReason: string | null = !patch
    ? null
    : patch.status === "unsafe"
      ? "补丁被标记为不安全，无法应用。请手动清理源文本后重新生成。"
      : patch.status === "stale"
        ? "初稿已变更，补丁已过期。请重新打开修复会话。"
        : patch.status === "applied"
          ? "补丁已应用。"
          : null;

  return (
    <aside className="repair-inspector" aria-label="标注式修复详情面板">
      <div className="repair-inspector-header">
        <h4>修复面板</h4>
        <Badge
          variant={
            issue.kind === "blocking"
              ? "destructive"
              : issue.kind === "hit"
                ? "warning"
                : "secondary"
          }
          className="text-xs"
        >
          {ISSUE_KIND_LABELS[issue.kind]}
        </Badge>
      </div>
      <div className="repair-inspector-body">
        <section className="repair-inspector-summary" aria-label="当前问题摘要">
          <div className="repair-inspector-chip-row">
            <span className="repair-inspector-chip" data-severity={issue.severity}>
              {ISSUE_SEVERITY_LABELS[issue.severity]}
            </span>
            <span className="repair-inspector-chip">
              {SECTION_LABELS[issue.target_section] || issue.target_section}
            </span>
            <span className="repair-inspector-chip">{anchorModeLabel}</span>
          </div>
          <p className="repair-inspector-summary-text">{issue.message}</p>
        </section>

        <section className="repair-anchor-card" aria-label="问题定位上下文">
          <div className="repair-anchor-card-header">
            <span>命中文本</span>
            <span>
              {SECTION_LABELS[issue.anchor.section] ||
                SECTION_LABELS[issue.target_section] ||
                issue.target_section}
            </span>
          </div>
          <p className="repair-anchor-snippet">
            {anchorSnippet || "未找到可直接匹配的文本片段"}
          </p>
          {anchorContext && (
            <p className="repair-anchor-context">
              {anchorContext.before && <span>{anchorContext.before}</span>}
              <mark>{anchorContext.match}</mark>
              {anchorContext.after && <span>{anchorContext.after}</span>}
            </p>
          )}
        </section>

        {!patch && (
          <RepairActions
            patch={patch}
            applying={applying}
            generating={generating}
            generateDisabled={generateDisabled}
            stale={stale}
            targetPatchable={targetPatchable}
            canApply={canApply}
            applyDisabledReason={applyDisabledReason}
            onApplyPatch={onApplyPatch}
            onDismissPatch={onDismissPatch}
            onGeneratePatch={onGeneratePatch}
          />
        )}

        {stale && (
          <div className="callout callout-warn">
            <div>
              <strong>初稿已变更</strong>
              <p>
                当前初稿与生成此修复会话时的初稿不同。AI
                修正功能已被禁用，请使用人工修正。
              </p>
            </div>
          </div>
        )}

        {patchError && (
          <div className="callout callout-error">
            <div>
              <strong>生成失败</strong>
              <p>{patchError}</p>
            </div>
          </div>
        )}

        {patch && (
          <div className="repair-patch-preview">
            <div className="repair-inspector-field">
              <span className="repair-inspector-label">补丁状态</span>
              <span className="repair-patch-status" data-status={patch.status}>
                {PATCH_STATUS_LABELS[patch.status] || patch.status}
              </span>
            </div>
            <div className="repair-inspector-message">
              <span className="repair-inspector-label">变更摘要</span>
              <p>{patch.diff_summary}</p>
            </div>
            <div className="repair-inspector-message">
              <span className="repair-inspector-label">原始文本</span>
              <p className="repair-inspector-snippet repair-patch-original">
                {patch.original}
              </p>
            </div>
            <div className="repair-inspector-message">
              <span className="repair-inspector-label">修正后文本</span>
              <p className="repair-inspector-snippet repair-patch-patched">
                {patch.patched}
              </p>
            </div>
            {patch.risk_notes.length > 0 && (
              <div className="repair-inspector-message">
                <span className="repair-inspector-label">风险提示</span>
                <ul className="repair-patch-risks">
                  {patch.risk_notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {patch && (
          <RepairActions
            patch={patch}
            applying={applying}
            generating={generating}
            generateDisabled={generateDisabled}
            stale={stale}
            targetPatchable={targetPatchable}
            canApply={canApply}
            applyDisabledReason={applyDisabledReason}
            onApplyPatch={onApplyPatch}
            onDismissPatch={onDismissPatch}
            onGeneratePatch={onGeneratePatch}
          />
        )}

        {patch && patch.status === "applied" && (
          <div className="callout callout-success">
            <div>
              <strong>
                <CheckCircle size={14} /> 已写回当前初稿
              </strong>
              <p>已写回当前初稿，请重新编译正式稿并重新成稿会审。</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

interface RepairActionsProps {
  patch: DraftRepairPatch | null;
  applying: boolean;
  generating: boolean;
  generateDisabled: boolean;
  stale: boolean;
  targetPatchable: boolean;
  canApply: boolean | null;
  applyDisabledReason: string | null;
  onGeneratePatch: () => void;
  onApplyPatch: () => void;
  onDismissPatch: () => void;
}

function RepairActions({
  patch,
  applying,
  generating,
  generateDisabled,
  stale,
  targetPatchable,
  canApply,
  applyDisabledReason,
  onGeneratePatch,
  onApplyPatch,
  onDismissPatch,
}: RepairActionsProps) {
  return (
    <div className="repair-inspector-actions">
      <button
        className="btn btn-secondary"
        type="button"
        title="在中间正文区直接修改对应段落"
      >
        <PenLine size={15} />
        <span>人工修正</span>
      </button>
      {patch ? (
        <>
          <button
            className="btn btn-primary"
            type="button"
            disabled={!canApply || applying}
            onClick={onApplyPatch}
            title={applyDisabledReason ?? "将 AI 修正写回当前初稿"}
          >
            {applying ? (
              <Loader2 className="spin" size={15} />
            ) : (
              <CheckCircle size={15} />
            )}
            <span>{applying ? "正在应用" : "应用 AI 修正"}</span>
          </button>
          <button
            className="btn btn-ghost repair-inspector-dismiss"
            type="button"
            onClick={onDismissPatch}
            disabled={applying}
            title="放弃当前生成的补丁"
            aria-label="放弃当前生成的补丁"
          >
            <XCircle size={14} />
          </button>
        </>
      ) : (
        <button
          className="btn btn-primary"
          type="button"
          disabled={generateDisabled}
          onClick={onGeneratePatch}
          title={
            stale
              ? "初稿已变更，AI 修正不可用"
              : !targetPatchable
                ? "该问题未定位到可修正段落，请人工修正"
                : generating
                  ? "正在生成 AI 修正"
                  : "为此问题生成 AI 修正补丁"
          }
        >
          {generating ? (
            <Loader2 className="spin" size={15} />
          ) : (
            <Wand2 size={15} />
          )}
          <span>{generating ? "正在生成" : "生成 AI 修正"}</span>
        </button>
      )}
    </div>
  );
}

function anchorModeText(anchorType: DraftReviewIssue["anchor"]["type"]): string {
  if (anchorType === "text") return "文本匹配";
  if (anchorType === "section") return "段落推断";
  return "未定位";
}

function buildAnchorContext(
  issue: DraftReviewIssue,
  sectionText: string,
): { before: string; match: string; after: string } | null {
  const anchorStart = issue.anchor.start;
  const anchorEnd = issue.anchor.end;
  if (
    issue.anchor.type !== "text" ||
    typeof anchorStart !== "number" ||
    typeof anchorEnd !== "number" ||
    !sectionText
  ) {
    return null;
  }

  const start = Math.max(0, anchorStart);
  const end = Math.min(sectionText.length, anchorEnd);
  if (start >= end) return null;

  const contextSize = 34;
  return {
    before: sectionText.slice(Math.max(0, start - contextSize), start),
    match: sectionText.slice(start, end),
    after: sectionText.slice(end, Math.min(sectionText.length, end + contextSize)),
  };
}
