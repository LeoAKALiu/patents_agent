import type { DraftReviewIssue } from "@/api";

const SECTION_LABELS: Record<string, string> = {
  title: "标题",
  abstract: "摘要",
  claims: "权利要求书",
  description: "说明书",
  drawing_description: "附图说明",
};

export interface AnnotatedDraftSectionProps {
  sectionKey: string;
  label: string;
  value: string;
  selected: boolean;
  anchorIssue: DraftReviewIssue | null;
  patchActivity?: "applying" | "applied" | null;
  onChange: (value: string) => void;
}

export function AnnotatedDraftSection({
  sectionKey,
  label,
  value,
  selected,
  anchorIssue,
  patchActivity,
  onChange,
}: AnnotatedDraftSectionProps) {
  const hasTextAnchor = anchorIssue?.anchor.type === "text";
  const isMissing = anchorIssue?.anchor.type === "missing";
  const cappedValue = value || "";

  return (
    <label className={`annotated-draft-section ${selected ? "selected" : ""}`}>
      <span className="annotated-draft-section-label">
        {label}
        {anchorIssue && (
          <span
            className={`annotated-draft-section-badge ${
              hasTextAnchor
                ? "badge-text-anchor"
                : isMissing
                  ? "badge-missing"
                  : "badge-section"
            }`}
          >
            {hasTextAnchor ? "文本定位" : isMissing ? "未定位" : "段落定位"}
          </span>
        )}
      </span>
      <textarea
        className={`draft-editor-textarea ${
          patchActivity === "applying"
            ? "patch-applying"
            : patchActivity === "applied"
              ? "patch-applied"
              : ""
        }`}
        value={cappedValue}
        onChange={(event) => onChange(event.currentTarget.value)}
        aria-label={label}
        rows={sectionKey === "description" ? 8 : sectionKey === "claims" ? 6 : sectionKey === "drawing_description" ? 3 : 2}
      />
      {patchActivity && (
        <p className="annotated-draft-patch-status" aria-live="polite">
          正文状态：{patchActivity === "applying" ? "正在应用" : "已写回"} AI 修正到{label}
        </p>
      )}
      {anchorIssue?.snippet && (
        <p className="annotated-draft-snippet" aria-live="polite">
          片段：{anchorIssue.snippet}
        </p>
      )}
    </label>
  );
}

export { SECTION_LABELS };
