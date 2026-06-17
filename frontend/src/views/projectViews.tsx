/**
 * Project + corpus + start views — extracted from App.tsx (M3-B').
 * Start screen, project picker/overview/create, and corpus import/search.
 */
import type { FormEvent } from "react";
import { CheckCircle2, FileText, Search, ShieldCheck, Trash2, Upload, Wand2 } from "@/lib/icons";
import {
  v1StartChoices,
  type StartChoiceId,
} from "@/guidedFlow";
import type {
  PatentDocument,
  ProjectRecord,
  SearchResult,
  SectionType,
} from "@/api";

/** Corpus search-section dropdown options. */
const sectionOptions: Array<{ value: SectionType | ""; label: string }> = [
  { value: "", label: "全部章节" },
  { value: "claims", label: "权利要求书" },
  { value: "abstract", label: "摘要" },
  { value: "summary", label: "发明内容" },
  { value: "embodiments", label: "具体实施方式" },
  { value: "drawings", label: "附图说明" },
];

/** zh-CN locale-formatted project date. */
function formatProjectDate(value: string | undefined): string {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type ProjectMetadata = {
  created_at?: string;
  updated_at?: string;
};

export function StartChoiceScreen({ onSelect }: { onSelect: (choice: StartChoiceId) => void }) {
  const iconForChoice: Record<StartChoiceId, typeof Wand2> = {
    invention: Wand2,
    utility: ShieldCheck,
    external: Upload,
  };
  return (
    <section className="start-choice-screen" aria-label="v1.1.0 默认入口">
      <div className="start-choice-copy">
        <span className="status-badge">v1.1.0</span>
        <h3>请选择本次工作的起点</h3>
        <p>普通用户只需要先选一种路径；专家工具已移到二级导航，仍可随时打开。</p>
      </div>
      <div className="start-choice-grid">
        {v1StartChoices.map((choice) => {
          const Icon = iconForChoice[choice.id];
          return (
            <button
              className="start-choice-card"
              key={choice.id}
              onClick={() => onSelect(choice.id)}
              type="button"
            >
              <Icon size={24} aria-hidden="true" />
              <strong>{choice.label}</strong>
              <span>{choice.description}</span>
            </button>
          );
        })}
      </div>
      <p className="workflow-hint">
        PatentAgent 生成内容仅为专利撰写辅助材料，不替代专利代理师、律师或正式法律意见；正式提交前请由专业人员复核。
      </p>
    </section>
  );
}

export function ProjectSelect({
  projects,
  selectedProjectId,
  onChange,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onChange: (id: string) => void;
}) {
  return (
    <label className="flex flex-col md:flex-row items-start md:items-center gap-3">
      <span>当前项目</span>
      <select value={selectedProjectId} onChange={(event) => onChange(event.target.value)}>
        <option value="">{projects.length === 0 ? "暂无项目" : "新建项目"}</option>
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ProjectsOverview({
  projects,
  selectedProjectId,
  onSelect,
  onDelete,
  busy,
}: {
  projects: ProjectRecord[];
  selectedProjectId: string;
  onSelect: (id: string) => void;
  onDelete: (project: ProjectRecord) => void;
  busy: string;
}) {
  return (
    <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>项目</h3>
      <p className="section-copy">选择历史项目后，可以继续生成、质检或导出。</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => {
          const metadata = project as ProjectRecord & ProjectMetadata;
          const isSelected = project.id === selectedProjectId;
          return (
            <article className={isSelected ? "flex flex-col gap-4 p-5 bg-[var(--surface-raised)] border border-[var(--brand-teal-500)]/30 rounded-lg shadow-[0_8px_30px_var(--glass-shadow-high)] ring-1 ring-[var(--brand-teal-500)]/20" : "flex flex-col gap-4 p-5 bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-lg shadow-sm hover:shadow-md transition-shadow"} key={project.id}>
              <div>
                <strong>{project.name}</strong>
                <span>{project.package ? "已有初稿" : "仅有想法"}</span>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt>创建</dt>
                  <dd>{formatProjectDate(metadata.created_at)}</dd>
                </div>
                <div>
                  <dt>更新</dt>
                  <dd>{formatProjectDate(metadata.updated_at)}</dd>
                </div>
              </dl>
              <div className="project-actions mt-4 pt-4 border-t border-[var(--border-subtle)]">
                <button
                  className={isSelected ? "project-action-btn project-action-btn-current" : "project-action-btn project-action-btn-primary"}
                  disabled={isSelected}
                  onClick={() => onSelect(project.id)}
                  type="button"
                >
                  <CheckCircle2 size={17} />
                  <span>{isSelected ? "当前项目" : "选择项目"}</span>
                </button>
                <button
                  className="project-action-btn project-action-btn-danger"
                  disabled={busy === "project-delete"}
                  onClick={() => onDelete(project)}
                  type="button"
                  title="删除项目"
                >
                  <Trash2 size={17} />
                  <span>删除项目</span>
                </button>
              </div>
            </article>
          );
        })}
        {projects.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无项目。进入“专利生成”输入想法即可创建。</p>}
      </div>
    </section>
  );
}

export function CorpusView({
  documents,
  searchText,
  searchSection,
  searchResults,
  busy,
  onImport,
  onSearch,
  onSearchText,
  onSearchSection,
}: {
  documents: PatentDocument[];
  searchText: string;
  searchSection: SectionType | "";
  searchResults: SearchResult[];
  busy: string;
  onImport: (event: FormEvent<HTMLFormElement>) => void;
  onSearch: (event: FormEvent) => void;
  onSearchText: (value: string) => void;
  onSearchSection: (value: SectionType | "") => void;
}) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>语料导入</h3>
        <form className="flex flex-col gap-4" onSubmit={onImport}>
          <input id="patent-file" name="patent-file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" />
          <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "import"} type="submit" title="导入专利文件">
            <Upload size={17} />
            <span>导入</span>
          </button>
        </form>
        <div className="flex flex-col gap-3">
          {documents.map((document) => (
            <article className="flex gap-3 items-start p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={document.id}>
              <FileText size={18} />
              <div>
                <strong>{document.title}</strong>
                <span>{document.source_name}</span>
              </div>
            </article>
          ))}
          {documents.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无语料</p>}
        </div>
      </section>

      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>片段检索</h3>
        <form className="flex items-center gap-3" onSubmit={onSearch}>
          <input value={searchText} onChange={(event) => onSearchText(event.target.value)} />
          <select value={searchSection} onChange={(event) => onSearchSection(event.target.value as SectionType | "")}>
            {sectionOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors" disabled={busy === "search"} type="submit" title="检索">
            <Search size={17} />
          </button>
        </form>
        <div className="results">
          {searchResults.map((result) => (
            <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={result.chunk.id}>
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                <span>{result.chunk.section_type}</span>
                <span>{result.score.toFixed(3)}</span>
              </div>
              <p>{result.chunk.text}</p>
            </article>
          ))}
          {searchResults.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无检索结果</p>}
        </div>
      </section>
    </div>
  );
}

export function CreateProjectView({
  projectName,
  draftText,
  busy,
  onProjectName,
  onDraftText,
  onSubmit,
}: {
  projectName: string;
  draftText: string;
  busy: string;
  onProjectName: (value: string) => void;
  onDraftText: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl col-span-full">
      <h3>技术交底</h3>
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <label>
          <span>项目名称</span>
          <input value={projectName} onChange={(event) => onProjectName(event.target.value)} />
        </label>
        <label>
          <span>Draft</span>
          <textarea
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-5 py-4 focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[200px]"
            value={draftText}
            onChange={(event) => onDraftText(event.target.value)}
          />
        </label>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={busy === "create"} type="submit" title="创建项目">
          <FileText size={17} />
          <span>创建</span>
        </button>
      </form>
    </section>
  );
}
