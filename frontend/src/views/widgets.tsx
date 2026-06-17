/**
 * Pure presentational widgets extracted from App.tsx (M3 batch A — safe
 * mechanical extraction). These have NO closure over App() state/effects:
 * narrow, explicit props only. Stateful views (those reading the ~60
 * useState hooks / loadX handlers) stay in App.tsx until the AppStore
 * reducer (batch B) lands, because extracting them first would force
 * massive prop-drilling.
 *
 * Test contract note: AppRefreshEffect.test.ts asserts raw-source strings
 * inside App.tsx (refreshDisclosureRunUntilSettled, loadPatentPoints) —
 * those stateful handlers MUST remain in App.tsx, so they are not moved
 * here. Only pure leaf components are extracted.
 */
import { AlertTriangle, BarChart3 } from "@/lib/icons";
import type { CorpusImportJob } from "@/api";

/** Small label/value stat tile. Reusable inside expert-tool views. */
export function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 p-3 bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-lg text-sm">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/** Local percent helper — kept co-located with its only consumer. */
function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

/** Corpus quality report block — depends only on StatusPill + the report. */
export function QualityReportView({ report }: { report: CorpusImportJob["quality_report"] }) {
  if (!report) return null;
  return (
    <div className="flex flex-col gap-4 mt-6 p-6 rounded-lg bg-[var(--surface-inset)]/50 border border-app-danger/35">
      <h4>质量报告</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatusPill label="可抽取率" value={percent(report.fulltext_extractable_rate)} />
        <StatusPill label="索引片段" value={String(report.indexed_chunks)} />
        <StatusPill label="低质量样本" value={String(report.low_quality_documents.length)} />
        <StatusPill label="错误数" value={String(report.failures.length)} />
      </div>
      {report.failures.length > 0 && (
        <div className="flex flex-col gap-3">
          {report.failures.slice(0, 6).map((failure) => (
            <article className="flex gap-3 items-start p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={`${failure.file}-${failure.reason}`}>
              <AlertTriangle size={18} />
              <div>
                <strong>{failure.file}</strong>
                <span>{failure.reason}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

/** Key/value frequency distribution chips. */
export function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values).slice(0, 8);
  return (
    <div className="flex flex-col gap-3 mt-4 p-5 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)]">
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
        <BarChart3 size={16} />
        <strong>{title}</strong>
      </div>
      {entries.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {entries.map(([key, value]) => (
            <span className="px-3 py-1 rounded-lg bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-primary)]" key={key}>{key}: {value}</span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无数据</p>
      )}
    </div>
  );
}

/** Titled <pre> text block for previews / strategy briefs / packages. */
export function PreviewBlock({ title, text }: { title: string; text: string }) {
  return (
    <article className="p-6 bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded-lg shadow-sm">
      <h4>{title}</h4>
      <pre>{text}</pre>
    </article>
  );
}
