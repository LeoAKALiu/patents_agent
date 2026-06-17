/**
 * CorpusBuildView — extracted from App.tsx (M3-B').
 * The official-export batch corpus-building expert tool.
 */
import type { FormEvent } from "react";
import { FileArchive, FileText, Upload } from "@/lib/icons";
import type {
  CorpusImportJob,
  CorpusStats,
  CorpusVersion,
} from "@/api";
import { pipelineRunStatusLabel } from "@/domain";
import {
  StatusPill,
  QualityReportView,
  Distribution,
} from "./widgets";

export type CorpusJobForm = {
  source_type: string;
  source_name: string;
  query: string;
  domain: string;
  version_name: string;
};

function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function CorpusBuildView({
  form,
  job,
  versions,
  stats,
  busy,
  onFormChange,
  onCreateJob,
  onUploadFile,
  onRunJob,
}: {
  form: CorpusJobForm;
  job: CorpusImportJob | null;
  versions: CorpusVersion[];
  stats: CorpusStats | null;
  busy: string;
  onFormChange: (patch: Partial<CorpusJobForm>) => void;
  onCreateJob: (event: FormEvent) => void;
  onUploadFile: (event: FormEvent<HTMLFormElement>) => void;
  onRunJob: () => void;
}) {
  const report = job?.quality_report ?? versions[0]?.quality_report ?? null;
  const jobHint = !job
    ? "先创建导入任务，再上传官方导出物。"
    : job.input_paths.length === 0
      ? "任务已创建，下一步请选择 ZIP、CSV/XLSX 或全文文件并点击“上传批次文件”。"
      : job.status === "queued"
        ? "批次文件已上传，下一步点击右上角“运行导入”。"
        : job.status === "running"
          ? "导入正在运行，完成后会刷新入库、去重、过滤和失败数量。"
          : job.status === "completed"
            ? "导入已完成，可在语料统计和知识库检索中查看结果。"
            : "导入失败，请查看失败数量和质量报告。";
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>官方导出物批量建库</h3>
          <p>支持 ZIP、CSV/XLSX 元数据表和 PDF/XML/TXT/DOCX 全文配对导入；扫描版 PDF 会进入失败清单。</p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
          disabled={!job || job.input_paths.length === 0 || busy === "corpus-run"}
          onClick={onRunJob}
          type="button"
        >
          <FileArchive size={18} />
          <span>运行导入</span>
        </button>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>导入任务</h3>
          <form className="flex flex-col gap-4" onSubmit={onCreateJob}>
            <label>
              <span>来源类型</span>
              <select value={form.source_type} onChange={(event) => onFormChange({ source_type: event.target.value })}>
                <option value="cnipa_export">CNIPA 导出</option>
                <option value="local_export">地方系统导出</option>
                <option value="google_patents_export">Google Patents 导出</option>
                <option value="public_service_export">公共服务平台导出</option>
              </select>
            </label>
            <label>
              <span>来源名称</span>
              <input value={form.source_name} onChange={(event) => onFormChange({ source_name: event.target.value })} />
            </label>
            <label>
              <span>检索式 / 批次说明</span>
              <textarea
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[80px]"
                value={form.query}
                onChange={(event) => onFormChange({ query: event.target.value })}
              />
            </label>
            <label>
              <span>语料版本</span>
              <input
                value={form.version_name}
                onChange={(event) => onFormChange({ version_name: event.target.value })}
              />
            </label>
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "corpus-job"} type="submit">
              <FileText size={17} />
              <span>创建任务</span>
            </button>
          </form>

          <form className="flex flex-col gap-4 p-4 border-2 border-dashed border-[var(--border-subtle)] rounded-lg bg-[var(--surface-inset)]" onSubmit={onUploadFile}>
            {job && <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">{jobHint}</p>}
            <input
              id="corpus-batch-file"
              name="corpus-batch-file"
              type="file"
              accept=".zip,.csv,.xlsx,.xlsm,.pdf,.docx,.txt,.md,.markdown,.xml"
              disabled={!job}
            />
            <button className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors text-sm" disabled={!job || busy === "corpus-upload"} type="submit">
              <Upload size={16} />
              <span>上传</span>
            </button>
          </form>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>任务进度</h3>
          {job ? (
            <>
              <p className="text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2">{jobHint}</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatusPill label="状态" value={pipelineRunStatusLabel(job.status)} />
                <StatusPill label="版本" value={job.version_name} />
                <StatusPill label="输入批次" value={String(job.input_paths.length)} />
                <StatusPill label="已处理" value={String(job.processed_files)} />
                <StatusPill label="入库" value={String(job.imported_documents)} />
                <StatusPill label="去重" value={String(job.duplicate_documents)} />
                <StatusPill label="过滤" value={String(job.filtered_documents)} />
                <StatusPill label="失败" value={String(job.failed_documents)} />
              </div>
            </>
          ) : (
            <p className="text-sm text-[var(--text-primary)]/50 italic py-4">先创建导入任务，再上传官方导出物。</p>
          )}
          {report && <QualityReportView report={report} />}
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>语料统计</h3>
          {stats ? (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatusPill label="专利数" value={String(stats.document_count)} />
                <StatusPill label="片段数" value={String(stats.chunk_count)} />
                <StatusPill label="权利要求覆盖" value={percent(stats.section_coverage.claims)} />
                <StatusPill label="全文章节覆盖" value={percent(stats.section_coverage.embodiments)} />
              </div>
              <Distribution title="IPC 分布" values={stats.ipc_distribution} />
              <Distribution title="申请年份" values={stats.application_year_distribution} />
              <Distribution title="来源系统" values={stats.source_distribution} />
            </div>
          ) : (
            <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无统计</p>
          )}
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>语料版本</h3>
          <div className="flex flex-col gap-3">
            {versions.map((version) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={version.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span>{version.domain}</span>
                  <span>{version.document_count} 件 / {version.chunk_count} 片段</span>
                </div>
                <p><strong>{version.name}</strong></p>
                <p>{version.query || version.source_name || "未记录检索式"}</p>
              </article>
            ))}
            {versions.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无版本</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
