import { useMemo, useState } from "react";

import type { DocumentIssueInboxRow, DocumentIssueInboxState } from "./selectors";

type IssueFilter = "all" | "blocking";

export interface DocumentIssuesTabProps {
  inbox: DocumentIssueInboxState;
  onOpenAnnotated: () => void;
}

export function DocumentIssuesTab({ inbox, onOpenAnnotated }: DocumentIssuesTabProps) {
  const [filter, setFilter] = useState<IssueFilter>("all");
  const rows = useMemo(
    () => filter === "blocking" ? inbox.rows.filter((row) => row.kind === "阻断") : inbox.rows,
    [filter, inbox.rows],
  );

  return (
    <section className="document-panel document-issues" aria-labelledby="document-issues-tab-title">
      <div className="document-panel-heading">
        <div>
          <p className="section-eyebrow">问题</p>
          <h3 id="document-issues-tab-title">问题队列</h3>
        </div>
        <div className="document-filter-actions" aria-label="问题筛选">
          <button
            type="button"
            className={filter === "all" ? "is-active" : ""}
            onClick={() => setFilter("all")}
          >
            全部
          </button>
          <button
            type="button"
            className={filter === "blocking" ? "is-active" : ""}
            onClick={() => setFilter("blocking")}
          >
            只看阻断
          </button>
        </div>
      </div>

      <p className="document-empty-copy">
        当前共 {inbox.rows.length} 项，阻断 {inbox.blockingCount} 项，风险 {inbox.riskCount} 项，其他 {inbox.suggestionCount} 项。
      </p>

      {rows.length > 0 ? (
        <div className="document-issues-table-wrap">
          <table className="document-issues-table">
            <thead>
              <tr>
                <th scope="col">类型</th>
                <th scope="col">来源</th>
                <th scope="col">章节</th>
                <th scope="col">内容</th>
                <th scope="col">状态</th>
                <th scope="col">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <IssueTableRow row={row} onOpenAnnotated={onOpenAnnotated} key={row.id} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="document-empty-copy">当前筛选下没有问题。</p>
      )}
    </section>
  );
}

function IssueTableRow({
  row,
  onOpenAnnotated,
}: {
  row: DocumentIssueInboxRow;
  onOpenAnnotated: () => void;
}) {
  return (
    <tr>
      <td>
        <span className={`document-issue-level is-${row.kind}`}>{row.kind}</span>
        <span className="document-issue-severity">{row.severity}</span>
      </td>
      <td>{row.source}</td>
      <td>{row.section}</td>
      <td>
        <strong>{row.message}</strong>
      </td>
      <td>
        <code>{row.state}</code>
      </td>
      <td>
        <button type="button" className="document-link-button" onClick={onOpenAnnotated}>
          定位修复
        </button>
      </td>
    </tr>
  );
}
