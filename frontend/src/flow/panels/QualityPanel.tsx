import { AlertTriangle, CheckCircle2, ClipboardList, Gauge, Info, Loader2, ShieldCheck, Wand2 } from "@/lib/icons";
import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  FilingReadinessReport,
} from "@/api";
import { qualitySummaryFromRuns, type GuidedActionGate } from "@/guidedFlow";
import { patchSafetyLabel } from "@/domain";
import { GuidedOperationConsole } from "../runtimeWidgets";
import { ActionGateHint, type ExpertToolOpener } from "../parts";
import {
  ActionDock,
  InfoCard,
  SectionHead,
  SettingsGroup,
  StatusStrip,
} from "@/ui/EnterpriseSurface";

export interface QualityPanelProps {
  actionGate: GuidedActionGate;
  filingReport: FilingReadinessReport | null;
  worksheet: ClaimDefenseWorksheet | null;
  completionRun: DraftCompletionRun | null;
  busy: string;
  busyElapsedSeconds: number;
  onRunQualityChecks: () => void;
  onImproveScore: () => void;
  onAcceptPatch: (runId: string, patchId: string) => void;
  onAcceptAllPatches: (runId: string) => void;
  onOpenExpertTool: ExpertToolOpener;
}

function severityTagClass(severity: string): string {
  if (severity === "high") return "tag tag-danger";
  if (severity === "medium") return "tag tag-warn";
  return "tag tag-info";
}

function severityTone(severity: string): "danger" | "warn" | "info" {
  if (severity === "high") return "danger";
  if (severity === "medium") return "warn";
  return "info";
}

export function QualityPanel({
  actionGate,
  filingReport,
  worksheet,
  completionRun,
  busy,
  busyElapsedSeconds,
  onRunQualityChecks,
  onImproveScore,
  onAcceptPatch,
  onAcceptAllPatches,
  onOpenExpertTool,
}: QualityPanelProps) {
  const summary = qualitySummaryFromRuns({ filingReport, worksheet, completionRun });
  const actionsDisabled = !actionGate.allowed || Boolean(busy);
  const hasAnyResult = Boolean(filingReport || worksheet || completionRun);
  const allProposedPatches = completionRun?.patches.filter((patch) => patch.status === "proposed") ?? [];
  const proposedPatches = allProposedPatches.slice(0, 3);
  const acceptAllDisabled = !completionRun || allProposedPatches.length === 0 || Boolean(busy);
  const evidenceRows = completionRun?.support_matrix.filter((row) => row.evidence_refs.length > 0).slice(0, 3) ?? [];
  const missingEvidenceRows = completionRun?.support_matrix.filter((row) => row.missing_evidence_reason).slice(0, 3) ?? [];

  return (
    <section className="surface-panel guided-quality-panel">
      <SectionHead
        title="质量检查与补强"
        description="依次运行提交成熟度、权利要求防线、初稿完善和审查意见。"
        actions={<Gauge size={22} />}
      />

      <StatusStrip
        aria-label="质量检查摘要"
        items={[
          { label: "状态", value: summary.statusLabel },
          { label: "授权稳定性", value: summary.authorizationStability === null ? "未评分" : `${summary.authorizationStability}/100` },
          { label: "保护范围", value: summary.protectionScope === null ? "未评分" : `${summary.protectionScope}/100` },
          { label: "提交成熟度", value: summary.filingMaturity === null ? "未评分" : `${summary.filingMaturity}/100` },
        ]}
      />

      {hasAnyResult && (
        <div className="callout callout-info">
          <span className="tag tag-info">已有结果</span>
          <div>
            <strong>可以继续补强，也可以重新运行质量检查。</strong>
            <p>当前摘要包含 {summary.issueCount} 个成熟度命中、{summary.supportGapCount} 个支撑缺口和 {summary.taskCount} 个完善任务。</p>
          </div>
        </div>
      )}

      <SettingsGroup title="检查入口" description="进入对应专家视图查看完整报告，当前面板只保留工作流必看的摘要。">
        <div className="quality-tool-grid">
          <InfoCard
            className="quality-tool-card"
            icon={<ClipboardList size={18} />}
            title="提交成熟度"
            description={filingReport ? `${summary.issueCount} 项命中` : "检查占位符、敏感表述和正式稿风险。"}
            tone={filingReport?.status === "high_risk" ? "danger" : filingReport?.status === "warning" ? "warn" : "info"}
            action={(
              <button className="btn btn-secondary" onClick={() => onOpenExpertTool("readiness")} type="button">
                查看
              </button>
            )}
          />
          <InfoCard
            className="quality-tool-card"
            icon={<ShieldCheck size={18} />}
            title="权利要求防线"
            description={worksheet ? `${worksheet.feature_records.length} 个特征，${worksheet.support_gaps.length} 个支撑缺口` : "标记区别特征、支撑缺口与从属兜底。"}
            tone={(worksheet?.support_gaps.length ?? 0) > 0 ? "warn" : "info"}
            action={(
              <button className="btn btn-secondary" onClick={() => onOpenExpertTool("claimDefense")} type="button">
                查看
              </button>
            )}
          />
          <InfoCard
            className="quality-tool-card"
            icon={<Gauge size={18} />}
            title="初稿完善"
            description={completionRun ? `${completionRun.tasks.length} 个任务，${allProposedPatches.length} 个候选补丁` : "生成补强任务和候选 patch。"}
            tone={allProposedPatches.length > 0 ? "warn" : "info"}
            action={(
              <button className="btn btn-secondary" onClick={() => onOpenExpertTool("completion")} type="button">
                查看
              </button>
            )}
          />
        </div>
      </SettingsGroup>

      <ActionGateHint gate={actionGate} />

      <ActionDock meta={actionGate.allowed ? "运行会刷新成熟度、防线和完善结果；一键提升会尝试采纳可进入工作稿的补丁。" : actionGate.reason}>
        <button
          className="btn btn-primary"
          disabled={actionsDisabled}
          onClick={onRunQualityChecks}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "guided-quality" ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
          <span>运行质量检查</span>
        </button>
        <button
          className="btn btn-secondary"
          disabled={actionsDisabled}
          onClick={onImproveScore}
          title={actionGate.reason || undefined}
          type="button"
        >
          {busy === "score-improve" ? <Loader2 className="spin" size={17} /> : <Wand2 size={17} />}
          <span>一键提升分数</span>
        </button>
        <button
          className="btn btn-secondary"
          disabled={acceptAllDisabled}
          onClick={() => {
            if (completionRun && allProposedPatches.length > 0 && !busy) {
              onAcceptAllPatches(completionRun.id);
            }
          }}
          title={allProposedPatches.length === 0 ? "暂无候选补强" : undefined}
          type="button"
        >
          {busy === "completion-accept-all" ? <Loader2 className="spin" size={17} /> : <CheckCircle2 size={17} />}
          <span>一键接受补强</span>
        </button>
      </ActionDock>

      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "guided-quality"} />
      <GuidedOperationConsole busy={busy} elapsedSeconds={busyElapsedSeconds} active={busy === "score-improve"} />

      {filingReport?.issues.length ? (
        <SettingsGroup title="风险命中" description="仅展示前 5 条工作流必看项，完整列表在提交成熟度视图中。">
          <div className="dense-list">
            {filingReport.issues.slice(0, 5).map((issue, index) => (
              <InfoCard
                icon={issue.severity === "high" ? <AlertTriangle size={18} /> : issue.severity === "medium" ? <Info size={18} /> : <CheckCircle2 size={18} />}
                title={issue.category}
                description={issue.message}
                tone={severityTone(issue.severity)}
                meta={<span className={severityTagClass(issue.severity)}>{issue.severity === "high" ? "高风险" : issue.severity === "medium" ? "中风险" : "低风险"}</span>}
                key={`${issue.category}-${index}`}
              >
                <p>{issue.suggestion}</p>
              </InfoCard>
            ))}
          </div>
        </SettingsGroup>
      ) : null}

      {completionRun && (evidenceRows.length > 0 || missingEvidenceRows.length > 0) ? (
        <SettingsGroup title="证据支持链" description="仅展示与初稿完善矩阵相关的证据编号和缺失原因。">
          <div className="dense-list">
            {evidenceRows.map((row) => (
              <InfoCard
                title={row.feature_text}
                description={row.support_explanation || "已关联证据。"}
                meta={<span className="tag tag-success">{row.evidence_refs.join(", ")}</span>}
                key={`${row.claim_ref}-${row.feature_text}-evidence`}
              >
                {row.source_refs.length ? <p>来源：{row.source_refs.join("，")}</p> : null}
              </InfoCard>
            ))}
            {missingEvidenceRows.map((row) => (
              <InfoCard
                title={row.feature_text}
                description={row.missing_evidence_reason}
                tone="warn"
                meta={<span className="tag tag-warn">待补证据</span>}
                key={`${row.claim_ref}-${row.feature_text}-missing`}
              />
            ))}
          </div>
        </SettingsGroup>
      ) : null}

      {completionRun && proposedPatches.length ? (
        <SettingsGroup
          title="候选补强"
          description={allProposedPatches.length > proposedPatches.length
            ? `仅展示前 ${proposedPatches.length} 条；一键接受会处理全部 ${allProposedPatches.length} 条候选补强。`
            : "接受后会更新评分进度；正式导出需要重新绑定后续检查。"}
        >
          <div className="dense-list">
            {proposedPatches.map((patch) => (
              <InfoCard
                title={patch.rationale}
                description={patch.risk_delta}
                meta={<span className={patch.can_enter_official_draft ? "tag tag-success" : "tag tag-warn"}>{patchSafetyLabel(patch)}</span>}
                key={patch.id}
              >
                {patch.evidence_refs.length ? <p>证据：{patch.evidence_refs.join("，")}</p> : null}
                <pre className="patch-preview">{patch.after_text}</pre>
                <button className="btn btn-primary" onClick={() => onAcceptPatch(completionRun.id, patch.id)} type="button">
                  接受补强建议
                </button>
              </InfoCard>
            ))}
          </div>
        </SettingsGroup>
      ) : null}
    </section>
  );
}
