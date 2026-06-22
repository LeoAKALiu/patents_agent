/**
 * Project + corpus + start views — extracted from App.tsx (M3-B').
 * Start screen, project picker/overview/create, and corpus import/search.
 */
import { useMemo, useState, type FormEvent } from "react";
import { CheckCircle2, FileText, Search, ShieldCheck, Trash2, Upload, Wand2 } from "@/lib/icons";
import { Badge } from "@/components/ui/badge";
import {
  v1StartChoices,
  type StartChoiceId,
} from "@/guidedFlow";
import { cn } from "@/lib/cn";
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

type ProjectFilter = "all" | "draft" | "idea" | "utility";

function formatShortProjectDate(value: string | undefined): string {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
}

function getProjectStage(project: ProjectRecord): string {
  if (project.package) return "初稿已生成";
  if (project.draft_text?.trim()) return "想法已录入";
  return "待录入";
}

function getProjectTypeLabel(project: ProjectRecord): string {
  if (project.patent_type === "utility_model") return "实用新型";
  return project.package ? "发明初稿" : "发明想法";
}

function getProjectRisk(project: ProjectRecord): { label: string; tone: "success" | "warning" | "neutral" } {
  if (!project.package) return { label: "待生成", tone: "neutral" };
  const highRiskCount = project.package.review_findings.filter((finding) => finding.severity === "high").length;
  if (highRiskCount > 0) return { label: "需复核", tone: "warning" };
  if (project.package.review_findings.length > 0) return { label: "建议补强", tone: "warning" };
  return { label: "可继续", tone: "success" };
}

function getProjectExportStatus(project: ProjectRecord): { label: string; tone: "info" | "neutral" } {
  if (project.package) return { label: "可进入导出", tone: "info" };
  return { label: "未生成初稿", tone: "neutral" };
}

function projectStatusPillClass(tone: "success" | "warning" | "info" | "neutral"): string {
  if (tone === "success") {
    return "border-[color-mix(in_oklch,var(--success),var(--border-subtle)_45%)] bg-[color-mix(in_oklch,var(--success),transparent_90%)] text-[var(--success-text)]";
  }
  if (tone === "warning") {
    return "border-[color-mix(in_oklch,var(--warn),var(--border-subtle)_42%)] bg-[color-mix(in_oklch,var(--warn),transparent_88%)] text-[var(--warn-text)]";
  }
  if (tone === "info") {
    return "border-[color-mix(in_oklch,var(--info),var(--border-subtle)_45%)] bg-[color-mix(in_oklch,var(--info),transparent_90%)] text-[var(--info)]";
  }
  return "border-[var(--border-subtle)] bg-[var(--surface-inset)] text-[var(--text-soft)]";
}

function ProjectStatusPill({
  children,
  tone,
}: {
  children: string;
  tone: "success" | "warning" | "info" | "neutral";
}) {
  return (
    <span className={cn("inline-flex min-h-6 items-center rounded-full border px-2 py-0.5 text-xs font-semibold whitespace-nowrap", projectStatusPillClass(tone))}>
      {children}
    </span>
  );
}

export function StartChoiceScreen({ onSelect }: { onSelect: (choice: StartChoiceId) => void }) {
  const iconForChoice: Record<StartChoiceId, typeof Wand2> = {
    invention: Wand2,
    utility: ShieldCheck,
    external: Upload,
  };
  const choiceMeta: Record<StartChoiceId, { status: string; next: string; tone: "accent" | "info" | "success" | "warn" }> = {
    invention: {
      status: "发明专利",
      next: "想法录入后进入发明点确认",
      tone: "accent",
    },
    utility: {
      status: "实用新型",
      next: "结构方案优先，跳过发明专属重步骤",
      tone: "success",
    },
    external: {
      status: "已有稿件",
      next: "先选择项目，再解析章节并确认工作稿",
      tone: "warn",
    },
  };

  return (
    <section className="start-choice-screen" aria-label="v1.1.0 默认入口">
      <div className="section-head">
        <div>
          <h2>开始撰写</h2>
          <p>选择本次工作的起点。专家工具仍在二级导航中，默认路径只保留普通用户最常用的三种入口。</p>
        </div>
        <Badge variant="success" className="self-start text-xs">v1.1.0</Badge>
      </div>

      <div className="status-strip" aria-label="起步摘要">
        <div className="status-tile">
          <span>默认工作区</span>
          <strong>专利生成</strong>
        </div>
        <div className="status-tile">
          <span>入口数量</span>
          <strong>{v1StartChoices.length} 条路径</strong>
        </div>
        <div className="status-tile">
          <span>项目状态</span>
          <strong>待创建</strong>
        </div>
        <div className="status-tile">
          <span>专业复核</span>
          <strong>提交前必需</strong>
        </div>
      </div>

      <div className="settings-group">
        <div className="settings-group-header">
          <h3>选择起步方式</h3>
          <p>每张配置卡都会进入同一条 guided flow，只是预设项目类型、录入方式和后续节奏不同。</p>
        </div>
        <div className="start-choice-list">
          {v1StartChoices.map((choice) => {
            const Icon = iconForChoice[choice.id];
            const meta = choiceMeta[choice.id];
            const pillTone = choice.id === "utility" ? "success" : choice.id === "external" ? "warning" : "info";
            return (
              <button
                className="info-card start-choice-config-card start-choice-row"
                key={choice.id}
                onClick={() => onSelect(choice.id)}
                type="button"
              >
                <div className={cn("info-card-icon", meta.tone)}>
                  <Icon size={18} aria-hidden="true" />
                </div>
                <div className="info-card-body">
                  <strong>{choice.label}</strong>
                  <p>{choice.description}</p>
                  <div className="info-card-meta">
                    <ProjectStatusPill tone={pillTone}>{meta.status}</ProjectStatusPill>
                    <span>{meta.next}</span>
                  </div>
                </div>
                <span className="btn-primary start-choice-action">
                  <CheckCircle2 size={16} aria-hidden="true" />
                  <span>选择</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="callout">
        <ShieldCheck size={18} aria-hidden="true" />
        <div>
          <strong>正式提交前请专业复核</strong>
          <p>PatentAgent 生成内容仅为专利撰写辅助材料，不替代专利代理师、律师或正式法律意见。</p>
        </div>
      </div>
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
  const [activeFilter, setActiveFilter] = useState<ProjectFilter>("all");
  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;
  const draftCount = projects.filter((project) => project.package).length;
  const utilityCount = projects.filter((project) => project.patent_type === "utility_model").length;
  const ideaCount = projects.length - draftCount;
  const latestUpdate = projects
    .map((project) => project.updated_at)
    .filter(Boolean)
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];

  const filterOptions: Array<{ id: ProjectFilter; label: string; count: number }> = [
    { id: "all", label: "全部项目", count: projects.length },
    { id: "draft", label: "已有初稿", count: draftCount },
    { id: "idea", label: "仅有想法", count: ideaCount },
    { id: "utility", label: "实用新型", count: utilityCount },
  ];

  const visibleProjects = useMemo(
    () =>
      projects.filter((project) => {
        if (activeFilter === "draft") return Boolean(project.package);
        if (activeFilter === "idea") return !project.package;
        if (activeFilter === "utility") return project.patent_type === "utility_model";
        return true;
      }),
    [activeFilter, projects],
  );

  return (
    <section className="col-span-full grid gap-4">
      <div className="status-strip" aria-label="项目摘要">
        <div className="status-tile">
          <span>全部项目</span>
          <strong>{projects.length}</strong>
        </div>
        <div className="status-tile">
          <span>已有初稿</span>
          <strong>{draftCount}</strong>
        </div>
        <div className="status-tile">
          <span>当前项目</span>
          <strong title={selectedProject?.name ?? "未选择"}>{selectedProject?.name ?? "未选择"}</strong>
        </div>
        <div className="status-tile">
          <span>最近更新</span>
          <strong>{formatShortProjectDate(latestUpdate)}</strong>
        </div>
      </div>

      <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] shadow-sm">
        <header className="flex flex-col gap-4 border-b border-[var(--border-subtle)] px-4 py-4 md:flex-row md:items-start md:justify-between md:px-5">
          <div className="min-w-0">
            <h3 className="m-0 font-[var(--font-display)] text-lg font-semibold text-[var(--text-primary)]">项目列表</h3>
            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              选择历史项目后，可以继续生成、质检或导出；删除操作仍使用原有确认流程。
            </p>
          </div>
          <div className="flex flex-wrap gap-2" aria-label="项目筛选">
            {filterOptions.map((option) => (
              <button
                aria-pressed={activeFilter === option.id}
                className={cn(
                  "inline-flex min-h-9 items-center gap-2 rounded-md border px-3 text-xs font-semibold transition-colors",
                  activeFilter === option.id
                    ? "border-[color-mix(in_oklch,var(--action-primary),var(--border-subtle)_45%)] bg-[color-mix(in_oklch,var(--action-primary),transparent_90%)] text-[var(--action-primary)]"
                    : "border-[var(--border-subtle)] bg-[var(--surface-subtle)] text-[var(--text-muted)] hover:bg-[var(--surface-inset)] hover:text-[var(--text-primary)]",
                )}
                key={option.id}
                onClick={() => setActiveFilter(option.id)}
                type="button"
              >
                <span>{option.label}</span>
                <span className="font-mono text-[11px]">{option.count}</span>
              </button>
            ))}
          </div>
        </header>

        <div className="hidden md:block overflow-x-auto">
          <table className="w-full min-w-[840px] border-collapse text-sm">
            <thead className="bg-[var(--surface-subtle)] text-left text-xs font-semibold text-[var(--text-muted)]">
              <tr>
                <th className="px-4 py-3">项目</th>
                <th className="px-4 py-3 whitespace-nowrap">当前步骤</th>
                <th className="px-4 py-3 whitespace-nowrap">风险状态</th>
                <th className="px-4 py-3 whitespace-nowrap">导出状态</th>
                <th className="px-4 py-3 whitespace-nowrap">更新时间</th>
                <th className="px-4 py-3 text-right whitespace-nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              {visibleProjects.map((project) => {
                const metadata = project as ProjectRecord & ProjectMetadata;
                const isSelected = project.id === selectedProjectId;
                const risk = getProjectRisk(project);
                const exportStatus = getProjectExportStatus(project);
                return (
                  <tr
                    className={cn(
                      "border-t border-[var(--border-subtle)] align-top transition-colors",
                      isSelected
                        ? "bg-[color-mix(in_oklch,var(--action-primary),transparent_94%)]"
                        : "hover:bg-[var(--surface-subtle)]",
                    )}
                    key={project.id}
                  >
                    <td className="px-4 py-4">
                      <div className="min-w-0">
                        <strong className="block max-w-[320px] truncate text-[var(--text-primary)]" title={project.name}>
                          {project.name}
                        </strong>
                        <span className="mt-1 block text-xs text-[var(--text-muted)]">
                          {getProjectTypeLabel(project)} · <span className="font-mono">{project.id.slice(0, 8)}</span>
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-[var(--text-muted)] whitespace-nowrap">{getProjectStage(project)}</td>
                    <td className="px-4 py-4">
                      <ProjectStatusPill tone={risk.tone}>{risk.label}</ProjectStatusPill>
                    </td>
                    <td className="px-4 py-4">
                      <ProjectStatusPill tone={exportStatus.tone}>{exportStatus.label}</ProjectStatusPill>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <span className="block font-mono text-xs text-[var(--text-primary)] whitespace-nowrap">
                        {formatShortProjectDate(metadata.updated_at)}
                      </span>
                      <span className="mt-1 block text-xs text-[var(--text-soft)] whitespace-nowrap">
                        创建 {formatShortProjectDate(metadata.created_at)}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-1.5 whitespace-nowrap">
                        <button
                          className={cn(
                            "inline-flex min-h-9 min-w-[72px] items-center justify-center gap-1.5 rounded-md border px-2 text-xs font-semibold whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-55",
                            isSelected
                              ? "border-[color-mix(in_oklch,var(--action-primary),transparent_66%)] bg-[var(--surface-inset)] text-[var(--action-primary)]"
                              : "border-[color-mix(in_oklch,var(--action-primary),transparent_60%)] bg-[var(--action-primary)] text-[var(--action-primary-contrast)] hover:bg-[var(--action-primary-hover)]",
                          )}
                          disabled={isSelected}
                          onClick={() => onSelect(project.id)}
                          type="button"
                        >
                          <CheckCircle2 size={16} aria-hidden="true" />
                          <span>{isSelected ? "当前项目" : "选择"}</span>
                        </button>
                        <button
                          className="inline-flex min-h-9 min-w-[68px] items-center justify-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-subtle)] px-2 text-xs font-semibold text-[var(--danger)] whitespace-nowrap transition-colors hover:border-[color-mix(in_oklch,var(--danger),transparent_74%)] hover:bg-[var(--surface-inset)] disabled:cursor-not-allowed disabled:opacity-55"
                          disabled={busy === "project-delete"}
                          onClick={() => onDelete(project)}
                          type="button"
                          title="删除项目"
                        >
                          <Trash2 size={16} aria-hidden="true" />
                          <span>删除</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="grid gap-3 p-4 md:hidden">
          {visibleProjects.map((project) => {
            const metadata = project as ProjectRecord & ProjectMetadata;
            const isSelected = project.id === selectedProjectId;
            const risk = getProjectRisk(project);
            const exportStatus = getProjectExportStatus(project);
            return (
              <article
                className={cn(
                  "grid gap-4 rounded-lg border bg-[var(--surface-subtle)] p-4",
                  isSelected
                    ? "border-[color-mix(in_oklch,var(--action-primary),var(--border-subtle)_42%)] shadow-[inset_3px_0_0_var(--action-primary)]"
                    : "border-[var(--border-subtle)]",
                )}
                key={project.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <strong className="block truncate text-[var(--text-primary)]" title={project.name}>
                      {project.name}
                    </strong>
                    <span className="mt-1 block text-xs text-[var(--text-muted)]">
                      {getProjectTypeLabel(project)} · <span className="font-mono">{project.id.slice(0, 8)}</span>
                    </span>
                  </div>
                  <ProjectStatusPill tone={risk.tone}>{risk.label}</ProjectStatusPill>
                </div>

                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-xs font-semibold text-[var(--text-soft)]">当前步骤</dt>
                    <dd className="m-0 mt-1 text-[var(--text-primary)]">{getProjectStage(project)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-[var(--text-soft)]">导出状态</dt>
                    <dd className="m-0 mt-1">
                      <ProjectStatusPill tone={exportStatus.tone}>{exportStatus.label}</ProjectStatusPill>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-[var(--text-soft)]">创建</dt>
                    <dd className="m-0 mt-1 font-mono text-xs text-[var(--text-primary)]">{formatProjectDate(metadata.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-[var(--text-soft)]">更新</dt>
                    <dd className="m-0 mt-1 font-mono text-xs text-[var(--text-primary)]">{formatProjectDate(metadata.updated_at)}</dd>
                  </div>
                </dl>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    className={cn(
                      "inline-flex min-h-11 items-center justify-center gap-2 rounded-md border px-3 text-sm font-semibold whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-55",
                      isSelected
                        ? "border-[color-mix(in_oklch,var(--action-primary),transparent_66%)] bg-[var(--surface-inset)] text-[var(--action-primary)]"
                        : "border-[color-mix(in_oklch,var(--action-primary),transparent_60%)] bg-[var(--action-primary)] text-[var(--action-primary-contrast)]",
                    )}
                    disabled={isSelected}
                    onClick={() => onSelect(project.id)}
                    type="button"
                  >
                    <CheckCircle2 size={17} aria-hidden="true" />
                    <span>{isSelected ? "当前项目" : "选择项目"}</span>
                  </button>
                  <button
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 text-sm font-semibold text-[var(--danger)] whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-55"
                    disabled={busy === "project-delete"}
                    onClick={() => onDelete(project)}
                    type="button"
                  >
                    <Trash2 size={17} aria-hidden="true" />
                    <span>删除项目</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        {visibleProjects.length === 0 && (
          <div className="border-t border-[var(--border-subtle)] px-5 py-10 text-center text-sm text-[var(--text-muted)]">
            {projects.length === 0 ? "暂无项目。进入“专利生成”输入想法即可创建。" : "当前筛选下暂无项目。"}
          </div>
        )}
      </section>
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
      <section className="surface-panel grid gap-4 p-5">
        <div className="settings-group-header">
          <h3>语料导入</h3>
          <p>导入历史专利文件，作为检索语料和证据输入。</p>
        </div>
        <form className="info-card" onSubmit={onImport}>
          <div className="info-card-icon info">
            <Upload size={17} />
          </div>
          <div className="info-card-body">
            <strong>导入专利文件</strong>
            <p>支持 PDF、DOCX、TXT、Markdown。</p>
            <input id="patent-file" name="patent-file" type="file" accept=".pdf,.docx,.txt,.md,.markdown" />
          </div>
          <button className="btn btn-primary" disabled={busy === "import"} type="submit" title="导入专利文件">
            <Upload size={17} />
            <span>导入</span>
          </button>
        </form>
        <div className="dense-list">
          {documents.map((document) => (
            <article className="info-card" key={document.id}>
              <div className="info-card-icon">
                <FileText size={18} />
              </div>
              <div className="info-card-body">
                <strong>{document.title}</strong>
                <p>{document.source_name}</p>
              </div>
            </article>
          ))}
          {documents.length === 0 && (
            <div className="callout">
              <FileText size={18} />
              <div>
                <strong>暂无语料</strong>
                <p>导入文件后可在右侧检索片段。</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="surface-panel grid gap-4 p-5">
        <div className="settings-group-header">
          <h3>片段检索</h3>
          <p>按章节过滤语料片段，用于发明点和说明书支撑。</p>
        </div>
        <form className="info-card corpus-search-card" onSubmit={onSearch}>
          <div className="info-card-body">
            <strong>检索条件</strong>
            <div className="guided-field-grid">
              <label className="field">
                <span>关键词</span>
                <input value={searchText} onChange={(event) => onSearchText(event.target.value)} />
              </label>
              <label className="field">
                <span>章节</span>
                <select value={searchSection} onChange={(event) => onSearchSection(event.target.value as SectionType | "")}>
                  {sectionOptions.map((option) => (
                    <option key={option.value || "all"} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
          <button className="btn btn-secondary btn-icon" disabled={busy === "search"} type="submit" title="检索">
            <Search size={17} />
          </button>
        </form>
        <div className="dense-list">
          {searchResults.map((result) => (
            <article className="info-card info-card-no-icon" key={result.chunk.id}>
              <div className="info-card-body">
                <div className="meta-row">
                  <span className="tag tag-info">{result.chunk.section_type}</span>
                  <span className="hash-chip">{result.score.toFixed(3)}</span>
                </div>
                <p>{result.chunk.text}</p>
              </div>
            </article>
          ))}
          {searchResults.length === 0 && (
            <div className="callout">
              <Search size={18} />
              <div>
                <strong>暂无检索结果</strong>
                <p>输入关键词并选择章节后开始检索。</p>
              </div>
            </div>
          )}
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
    <section className="settings-group create-project-view col-span-full">
      <div className="section-head">
        <div>
          <h2>技术交底</h2>
          <p>用于旧入口的手动项目创建。填写项目名称和技术方案后，会进入现有项目工作台。</p>
        </div>
      </div>
      <div className="status-strip" aria-label="创建项目摘要">
        <div className="status-tile">
          <span>项目名称</span>
          <strong>{projectName.trim() || "待填写"}</strong>
        </div>
        <div className="status-tile">
          <span>交底内容</span>
          <strong>{draftText.trim() ? `${draftText.trim().length} 字` : "待录入"}</strong>
        </div>
        <div className="status-tile">
          <span>创建状态</span>
          <strong>{busy === "create" ? "创建中" : "可编辑"}</strong>
        </div>
        <div className="status-tile">
          <span>下一步</span>
          <strong>项目工作台</strong>
        </div>
      </div>
      <form className="settings-group" onSubmit={onSubmit}>
        <div className="info-card create-project-field">
          <div className="info-card-icon accent">
            <FileText size={18} aria-hidden="true" />
          </div>
          <div className="info-card-body">
            <label className="field">
              <span>项目名称</span>
              <input value={projectName} onChange={(event) => onProjectName(event.target.value)} />
            </label>
          </div>
        </div>
        <div className="info-card create-project-field">
          <div className="info-card-icon info">
            <Wand2 size={18} aria-hidden="true" />
          </div>
          <div className="info-card-body">
            <label className="field">
              <span>Draft</span>
              <textarea
                className="idea-input"
                value={draftText}
                onChange={(event) => onDraftText(event.target.value)}
                placeholder="粘贴技术方案、实施方式、效果或已有交底片段。"
              />
            </label>
          </div>
        </div>
        <div className="callout">
          <ShieldCheck size={18} aria-hidden="true" />
          <div>
            <strong>建议优先使用“开始撰写”</strong>
            <p>guided flow 会自动补齐发明点确认、质量检查和正式导出边界；这个入口保留给已有交底文本的快速建项。</p>
          </div>
        </div>
        <div className="action-dock">
          <span className="meta">创建后会自动选择该项目，并跳转到材料/语料工具。</span>
          <button className="btn-primary" disabled={busy === "create"} type="submit" title="创建项目">
            <FileText size={17} aria-hidden="true" />
            <span>创建</span>
          </button>
        </div>
      </form>
    </section>
  );
}
