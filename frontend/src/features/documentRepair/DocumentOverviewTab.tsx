import { AlertTriangle, ArrowRight, CheckCircle2, FileText, LockKeyhole } from "lucide-react";

import { Button } from "@/components/ui/button";

import type {
  DocumentRepairState,
  DocumentRepairTabId,
  DraftStatusCardState,
  GateNode,
  IssueSummaryRow,
} from "./selectors";

export interface DocumentOverviewTabProps {
  state: DocumentRepairState;
  onPrimaryAction: () => void;
  onOpenTab: (tab: DocumentRepairTabId) => void;
}

function primaryActionHint(state: DocumentRepairState): string {
  if (state.primaryAction.targetSection === "workbench") {
    return "该操作会回到工作台，由主流程启动对应 Agent 门禁。";
  }
  if (state.primaryAction.targetSection === "export") {
    return "导出门禁已放行，可以进入导出工作区保存正式提交稿。";
  }
  if (state.primaryAction.targetTab === "annotated") {
    return "该操作会打开标注修复，按问题定位到正文并生成安全补丁。";
  }
  if (state.primaryAction.targetTab === "issues") {
    return "该操作会打开问题队列，先处理阻断项再重新验证。";
  }
  return "该操作只影响当前文稿工作区，不会启动新的 Agent 运行。";
}

function shouldShowDraftCardAction(card: DraftStatusCardState, state: DocumentRepairState): boolean {
  if (card.tone === "internal" && state.primaryAction.targetSection === "workbench") {
    return false;
  }
  return true;
}

export function DocumentOverviewTab({
  state,
  onPrimaryAction,
  onOpenTab,
}: DocumentOverviewTabProps) {
  return (
    <div className="document-overview">
      <section className="document-overview-hero" aria-labelledby="document-overview-title">
        <div>
          <p className="section-eyebrow">总览</p>
          <h2 id="document-overview-title">{state.topConclusion}</h2>
          <p>{state.issueSummary.explanation}</p>
          <p className="document-action-hint">{primaryActionHint(state)}</p>
        </div>
        <Button type="button" onClick={onPrimaryAction}>
          {state.primaryAction.label}
          <ArrowRight size={16} aria-hidden="true" />
        </Button>
      </section>

      <section className="document-panel" aria-labelledby="document-gates-title">
        <div className="document-panel-heading">
          <div>
            <p className="section-eyebrow">门禁链路</p>
            <h3 id="document-gates-title">内部初稿到导出</h3>
          </div>
        </div>
        <ol className="document-gate-chain">
          {Object.values(state.gates).map((gate) => (
            <GateNodeView gate={gate} key={gate.id} />
          ))}
        </ol>
      </section>

      <section className="document-draft-grid" aria-label="文稿状态">
        <DraftStatusCard
          card={state.internalDraft}
          onAction={() => onOpenTab("edit")}
          showAction={shouldShowDraftCardAction(state.internalDraft, state)}
        />
        <DraftStatusCard card={state.officialDraft} onAction={() => onOpenTab("versions")} />
      </section>

      <section className="document-panel" aria-labelledby="document-issues-title">
        <div className="document-panel-heading">
          <div>
            <p className="section-eyebrow">问题</p>
            <h3 id="document-issues-title">问题摘要</h3>
          </div>
          <button type="button" className="document-link-button" onClick={() => onOpenTab("issues")}>
            查看全部
          </button>
        </div>
        <div className="document-issue-metrics">
          <IssueMetric label="阻断" value={state.issueSummary.blocking} />
          <IssueMetric label="风险" value={state.issueSummary.risk} />
          <IssueMetric label="建议" value={state.issueSummary.suggestion} />
          <IssueMetric label="已处理" value={state.issueSummary.resolved} />
        </div>
        {state.issueSummary.topIssues.length > 0 ? (
          <div className="document-issue-list">
            {state.issueSummary.topIssues.map((issue) => (
              <IssueRow issue={issue} key={issue.id} onLocate={() => onOpenTab("annotated")} />
            ))}
          </div>
        ) : (
          <p className="document-empty-copy">当前没有需要展示的阻断或风险项。</p>
        )}
      </section>

      <section className="document-panel" aria-labelledby="document-recent-title">
        <div className="document-panel-heading">
          <div>
            <p className="section-eyebrow">记录</p>
            <h3 id="document-recent-title">最近记录</h3>
          </div>
        </div>
        <div className="document-record-list">
          {state.recentRecords.map((record) => (
            <div className="document-record" key={record.label}>
              <span>{record.label}</span>
              <strong>{record.value}</strong>
              <small>{record.detail}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function GateNodeView({ gate }: { gate: GateNode }) {
  return (
    <li className="document-gate-node">
      <span className={`document-gate-icon is-${gate.state}`}>
        {gate.state === "可导出" || gate.state === "当前有效" || gate.state === "可编辑" ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : gate.state === "导出锁定" || gate.state === "需要修复" ? (
          <LockKeyhole size={16} aria-hidden="true" />
        ) : (
          <AlertTriangle size={16} aria-hidden="true" />
        )}
      </span>
      <span>
        <strong>{gate.label}</strong>
        <small>{gate.state}</small>
      </span>
      <p>{gate.detail}</p>
    </li>
  );
}

function DraftStatusCard({
  card,
  onAction,
  showAction = true,
}: {
  card: DraftStatusCardState;
  onAction: () => void;
  showAction?: boolean;
}) {
  return (
    <article className={`document-draft-card is-${card.tone}`}>
      <div className="document-draft-card-heading">
        <div>
          <span className="document-draft-kind">{card.subtitle}</span>
          <h3>{card.tone === "internal" ? "内部初稿" : "正式稿"}</h3>
        </div>
        <span className="document-state-pill">{card.state}</span>
      </div>
      <p className="document-draft-title">
        <FileText size={15} aria-hidden="true" />
        <span>{card.title}</span>
      </p>
      <div className="document-draft-metrics">
        {card.metrics.map((metric) => (
          <div key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </div>
      <ul>
        {card.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      {showAction ? (
        <button type="button" className="document-secondary-action" onClick={onAction}>
          {card.actionLabel}
        </button>
      ) : null}
    </article>
  );
}

function IssueMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="document-issue-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IssueRow({
  issue,
  onLocate,
}: {
  issue: IssueSummaryRow;
  onLocate: () => void;
}) {
  return (
    <div className="document-issue-row">
      <span className={`document-issue-level is-${issue.level}`}>{issue.level}</span>
      <span className="document-issue-section">{issue.section}</span>
      <strong>{issue.title}</strong>
      <button type="button" onClick={onLocate}>
        定位
      </button>
    </div>
  );
}
