import type { DraftReviewIssue } from "@/api";
import { Badge } from "@/components/ui/badge";
import { PenLine, Wand2 } from "@/lib/icons";

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

export interface DraftRepairInspectorProps {
  issue: DraftReviewIssue | null;
  stale: boolean;
}

export function DraftRepairInspector({ issue, stale }: DraftRepairInspectorProps) {
  if (!issue) {
    return (
      <aside className="repair-inspector" aria-label="标注式修复详情面板">
        <div className="repair-inspector-header">
          <h4>问题详情</h4>
        </div>
        <div className="empty-panel compact">
          <strong>未选择问题</strong>
          <p>从左侧问题列表中选择一个，查看详情和操作。</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="repair-inspector" aria-label="标注式修复详情面板">
      <div className="repair-inspector-header">
        <h4>问题详情</h4>
        <Badge variant={issue.kind === "blocking" ? "destructive" : issue.kind === "hit" ? "warning" : "secondary"} className="text-xs">
          {ISSUE_KIND_LABELS[issue.kind]}
        </Badge>
      </div>
      <div className="repair-inspector-body">
        <div className="repair-inspector-field">
          <span className="repair-inspector-label">严重程度</span>
          <span className="repair-inspector-value" data-severity={issue.severity}>
            {ISSUE_SEVERITY_LABELS[issue.severity]}
          </span>
        </div>
        <div className="repair-inspector-field">
          <span className="repair-inspector-label">目标段落</span>
          <span className="repair-inspector-value">
            {SECTION_LABELS[issue.target_section] || issue.target_section}
          </span>
        </div>
        <div className="repair-inspector-field">
          <span className="repair-inspector-label">定位方式</span>
          <span className="repair-inspector-value">
            {issue.anchor.type === "text"
              ? "文本匹配"
              : issue.anchor.type === "section"
                ? "段落推断"
                : "未定位"}
          </span>
        </div>
        <div className="repair-inspector-message">
          <span className="repair-inspector-label">问题描述</span>
          <p>{issue.message}</p>
        </div>
        {issue.snippet && (
          <div className="repair-inspector-message">
            <span className="repair-inspector-label">匹配片段</span>
            <p className="repair-inspector-snippet">{issue.snippet}</p>
          </div>
        )}
        {stale && (
          <div className="callout callout-warn">
            <div>
              <strong>初稿已变更</strong>
              <p>当前初稿与生成此修复会话时的初稿不同。AI 修正功能已被禁用，请使用人工修正。</p>
            </div>
          </div>
        )}
      </div>
      <div className="repair-inspector-actions">
        <button className="btn btn-secondary" type="button" title="在中间正文区直接修改对应段落">
          <PenLine size={15} />
          <span>人工修正</span>
        </button>
        <button className="btn btn-primary" type="button" disabled title={stale ? "初稿已变更，AI 修正不可用" : "AI 修正将在后续版本中实现"}>
          <Wand2 size={15} />
          <span>生成 AI 修正</span>
        </button>
      </div>
    </aside>
  );
}
