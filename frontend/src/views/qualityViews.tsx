/**
 * Quality-check expert views — extracted from App.tsx (M3-B').
 * ClaimDefenseView (权利要求防线) + ReviewView (审查意见).
 */
import { AlertTriangle, Search, ShieldCheck } from "@/lib/icons";
import type {
  ClaimDefenseWorksheet,
  ProjectRecord,
} from "@/api";
import {
  featureClassificationLabel,
  severityLabel,
  worksheetSourceLabel,
  worksheetStatusLabel,
} from "@/domain";

export function ClaimDefenseView({
  project,
  worksheet,
  worksheets,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  worksheet: ClaimDefenseWorksheet | null;
  worksheets: ClaimDefenseWorksheet[];
  busy: string;
  onGenerate: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>权利要求防线</h3>
          <p>{project ? "从当前草稿、交底书和已生成文本提取特征记录，标记区别特征、支撑缺口与从属兜底建议。" : "先创建项目后再生成防线工作表。"}</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!project || busy === "claim-defense"}
          onClick={onGenerate}
          type="button"
        >
          <ShieldCheck size={18} />
          <span>生成工作表</span>
        </button>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>防线建议</h3>
          <div className="flex flex-col gap-3">
            {worksheet?.defense_recommendations.map((item, index) => (
              <article className="flex gap-3 items-start p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={`${item}-${index}`}>
                <ShieldCheck size={18} />
                <div>
                  <strong>建议 {index + 1}</strong>
                  <span>{item}</span>
                </div>
              </article>
            ))}
            {!worksheet && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">生成工作表后显示防线建议。</p>}
            {worksheet && worksheet.defense_recommendations.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无防线建议。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>历史版本</h3>
          <div className="flex flex-col gap-3">
            {worksheets.map((item) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={item.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)]">{worksheetStatusLabel(item.status)}</span>
                  <span>{worksheetSourceLabel(item.source)}</span>
                  <span>{item.feature_records.length} 个特征</span>
                </div>
                <p>{item.created_at}</p>
              </article>
            ))}
            {worksheets.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无工作表历史版本。</p>}
          </div>
        </div>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>特征记录</h3>
        <div className="flex flex-col gap-3">
          {worksheet?.feature_records.map((record) => (
            <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={record.feature_id}>
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)]">{featureClassificationLabel(record.classification)}</span>
                <span>{record.claim_refs.length > 0 ? record.claim_refs.join(" / ") : "未映射权利要求"}</span>
              </div>
              <p><strong>{record.text}</strong></p>
              <p>{record.risk_tags.length > 0 ? `风险标签：${record.risk_tags.join("；")}` : "暂无风险标签"}</p>
            </article>
          ))}
          {!worksheet && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">生成工作表后显示特征记录。</p>}
          {worksheet && worksheet.feature_records.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无特征记录。</p>}
        </div>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>支撑缺口</h3>
        <div className="flex flex-col gap-3">
          {worksheet?.support_gaps.map((gap, index) => (
            <article className="flex gap-3 items-start p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={`${gap}-${index}`}>
              <AlertTriangle size={18} />
              <div>
                <strong>缺口 {index + 1}</strong>
                <span>{gap}</span>
              </div>
            </article>
          ))}
          {!worksheet && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">生成工作表后显示支撑缺口。</p>}
          {worksheet && worksheet.support_gaps.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无支撑缺口。</p>}
        </div>
      </section>
    </div>
  );
}

export function ReviewView({
  project,
  busy,
  onReview,
}: {
  project: ProjectRecord | null;
  busy: string;
  onReview: () => void;
}) {
  const findings = project?.package?.review_findings ?? [];
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>审查意见</h3>
          <p>{project?.package ? project.name : "生成申请文本后可审查。"}</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project?.package || busy === "review"} onClick={onReview} type="button">
          <Search size={18} />
          <span>审查</span>
        </button>
      </section>
      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col gap-3">
          {findings.map((finding, index) => (
            <article className={`flex items-start gap-3 p-4 border rounded-lg ${ finding.severity === "high" ? "bg-[var(--surface-inset)] border-app-danger/35" : finding.severity === "medium" ? "bg-[var(--surface-inset)] border-app-warn/35" : "bg-app-info/10 border-app-info/35" }`} key={`${finding.category}-${index}`}>
              <span>{severityLabel(finding.severity)}</span>
              <div>
                <strong>{finding.category}</strong>
                <p>{finding.message}</p>
                <p>{finding.suggestion}</p>
              </div>
            </article>
          ))}
          {findings.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无审查意见</p>}
        </div>
      </section>
    </div>
  );
}
