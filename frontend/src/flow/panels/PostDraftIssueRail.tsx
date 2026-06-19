import { type DraftReviewIssue } from "@/api";
import { Badge } from "@/components/ui/badge";

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

function groupIssues(issues: DraftReviewIssue[]) {
  const groups: Record<string, DraftReviewIssue[]> = {};
  for (const issue of issues) {
    const key = issue.status === "unanchored" ? "unanchored" : issue.kind;
    if (!groups[key]) groups[key] = [];
    groups[key].push(issue);
  }
  return groups;
}

export interface PostDraftIssueRailProps {
  issues: DraftReviewIssue[];
  selectedIssueId: string | null;
  onSelectIssue: (issue: DraftReviewIssue) => void;
}

export function PostDraftIssueRail({ issues, selectedIssueId, onSelectIssue }: PostDraftIssueRailProps) {
  const grouped = groupIssues(issues);
  const groupOrder: Array<DraftReviewIssue["kind"] | "unanchored"> = [
    "blocking",
    "hit",
    "suggestion",
    "unanchored",
  ];

  function badgeVariant(kind: string) {
    if (kind === "blocking") return "destructive";
    if (kind === "hit") return "warning";
    return "secondary";
  }

  return (
    <nav className="repair-issue-rail" aria-label="标注式修复问题导航">
      <div className="repair-issue-rail-header">
        <h4>问题列表</h4>
        <Badge variant="secondary" className="text-xs">
          {issues.length} 项
        </Badge>
      </div>
      <div className="repair-issue-scroll">
        {groupOrder.map((groupKey) => {
          const items = grouped[groupKey];
          if (!items || items.length === 0) return null;
          return (
            <div key={groupKey} className="repair-issue-group">
              <div className="repair-issue-group-label">
                <Badge variant={badgeVariant(groupKey) as "destructive" | "warning" | "secondary"} className="text-xs">
                  {groupKey === "unanchored" ? "未定位" : ISSUE_KIND_LABELS[groupKey as DraftReviewIssue["kind"]]}
                </Badge>
                <span className="repair-issue-count">{items.length}</span>
              </div>
              {items.map((issue) => (
                <button
                  key={issue.id}
                  className={`repair-issue-item ${selectedIssueId === issue.id ? "selected" : ""}`}
                  onClick={() => onSelectIssue(issue)}
                  type="button"
                >
                  <span className="repair-issue-severity" data-severity={issue.severity}>
                    {ISSUE_SEVERITY_LABELS[issue.severity]}
                  </span>
                  <span className="repair-issue-message">{issue.message}</span>
                </button>
              ))}
            </div>
          );
        })}
        {issues.length === 0 && (
          <div className="empty-panel compact">
            <strong>暂无问题</strong>
            <p>运行成稿会审后，这里会显示需要处理的问题。</p>
          </div>
        )}
      </div>
    </nav>
  );
}
