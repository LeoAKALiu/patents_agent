/**
 * Expert-tool views — extracted from App.tsx (M3-B').
 * ExpertToolChooser (the tool grid) + WriteView (manual draft generation).
 */
import { Wand2 } from "@/lib/icons";
import {
  expertToolGroups,
  type ExpertToolId,
} from "@/guidedFlow";
import { cn } from "@/lib/cn";
import type {
  DeliberationRun,
  DisclosureRun,
  FormulaNeedAssessment,
  FormulaRun,
  ProjectRecord,
} from "@/api";
import { DisclosureSummaryView, PackagePreview, StrategyBriefView } from "./disclosureViews";

type ToolTone = "success" | "warning" | "info" | "neutral";

const groupDescriptions: Record<string, { description: string; status: string; tone: ToolTone }> = {
  knowledge: {
    description: "语料库建设、知识库检索。证据输入类工具，结果可回写主流程。",
    status: "证据输入",
    tone: "info",
  },
  invention: {
    description: "护城河地图和候选分案点。该内容只进入内部策略稿。",
    status: "内部策略",
    tone: "warning",
  },
  strategy: {
    description: "前置材料、多智能体会审、分步撰写，辅助形成撰写策略。",
    status: "策略生成",
    tone: "info",
  },
  quality: {
    description: "提交成熟度、权利要求防线、初稿完善和审查修改。",
    status: "门禁",
    tone: "warning",
  },
  export: {
    description: "导出正式稿、内部稿和复核报告。",
    status: "文件",
    tone: "success",
  },
};

const toolStatuses: Record<ExpertToolId, { label: string; action: string; tone: ToolTone }> = {
  build: { label: "可回写", action: "打开", tone: "success" },
  corpus: { label: "检索", action: "打开", tone: "info" },
  moat: { label: "内部策略", action: "查看", tone: "warning" },
  materials: { label: "可回写", action: "编辑", tone: "success" },
  deliberate: { label: "策略生成", action: "进入", tone: "info" },
  write: { label: "高级", action: "打开", tone: "neutral" },
  readiness: { label: "门禁", action: "进入", tone: "warning" },
  claimDefense: { label: "运行", action: "打开", tone: "info" },
  completion: { label: "补强", action: "打开", tone: "info" },
  review: { label: "审查", action: "打开", tone: "info" },
  export: { label: "文件", action: "查看", tone: "success" },
};

function toolPillClass(tone: ToolTone): string {
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

function ToolPill({ children, tone }: { children: string; tone: ToolTone }) {
  return (
    <span className={cn("inline-flex min-h-6 items-center rounded-full border px-2 py-0.5 text-xs font-semibold whitespace-nowrap", toolPillClass(tone))}>
      {children}
    </span>
  );
}

export function ExpertToolChooser({
  activeToolId,
  onSelect,
}: {
  activeToolId: ExpertToolId;
  onSelect: (id: ExpertToolId) => void;
}) {
  const activeTool = expertToolGroups.flatMap((group) => group.tools).find((tool) => tool.id === activeToolId);
  const toolCount = expertToolGroups.reduce((count, group) => count + group.tools.length, 0);

  return (
    <section className="grid gap-4" aria-label="专家工具中心">
      <div className="status-strip" aria-label="专家工具摘要">
        <div className="status-tile">
          <span>当前工具</span>
          <strong>{activeTool?.label ?? "未选择"}</strong>
        </div>
        <div className="status-tile">
          <span>工具分组</span>
          <strong>{expertToolGroups.length} 组</strong>
        </div>
        <div className="status-tile">
          <span>可用入口</span>
          <strong>{toolCount} 个</strong>
        </div>
        <div className="status-tile">
          <span>默认流程</span>
          <strong>不受影响</strong>
        </div>
      </div>

      <div className="grid gap-6 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4 shadow-sm md:p-5">
        {expertToolGroups.map((group) => (
          <section className="grid gap-3" id={`expert-${group.id}`} key={group.id}>
            <header className="flex flex-col gap-2 border-b border-[var(--border-subtle)] pb-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="m-0 font-[var(--font-display)] text-base font-semibold text-[var(--text-primary)]">{group.label}</h3>
                <p className="m-0 mt-1 text-sm leading-6 text-[var(--text-muted)]">
                  {groupDescriptions[group.id]?.description ?? "高级工具入口。"}
                </p>
              </div>
              <ToolPill tone={groupDescriptions[group.id]?.tone ?? "neutral"}>{groupDescriptions[group.id]?.status ?? "工具"}</ToolPill>
            </header>

            <div className="grid gap-2">
              {group.tools.map((tool) => {
                const Icon = tool.icon;
                const isActive = activeToolId === tool.id;
                const status = toolStatuses[tool.id];
                return (
                  <button
                    aria-pressed={isActive}
                    className={cn(
                      "grid min-h-[76px] w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-lg border p-3 text-left transition-colors sm:grid-cols-[auto_minmax(0,1fr)_auto]",
                      isActive
                        ? "border-[color-mix(in_oklch,var(--action-primary),var(--border-subtle)_38%)] bg-[color-mix(in_oklch,var(--action-primary),transparent_94%)] shadow-[inset_3px_0_0_var(--action-primary)]"
                        : "border-[var(--border-subtle)] bg-[var(--surface-subtle)] hover:bg-[var(--surface-inset)]",
                    )}
                    key={tool.id}
                    onClick={() => onSelect(tool.id)}
                    type="button"
                    title={tool.description}
                  >
                    <span
                      className={cn(
                        "grid size-10 place-items-center rounded-md border",
                        isActive
                          ? "border-[color-mix(in_oklch,var(--action-primary),var(--border-subtle)_45%)] bg-[color-mix(in_oklch,var(--action-primary),transparent_88%)] text-[var(--action-primary)]"
                          : "border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)]",
                      )}
                    >
                      <Icon size={18} aria-hidden="true" />
                    </span>
                    <span className="min-w-0">
                      <strong className="block truncate text-sm font-semibold text-[var(--text-primary)]">{tool.label}</strong>
                      <span className="mt-1 block text-sm leading-5 text-[var(--text-muted)]">{tool.description}</span>
                    </span>
                    <span className="col-span-2 flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3 sm:col-span-1 sm:justify-end sm:border-t-0 sm:pt-0">
                      <ToolPill tone={isActive ? "success" : status.tone}>{isActive ? "当前" : status.label}</ToolPill>
                      <span
                        className={cn(
                          "inline-flex min-h-9 items-center rounded-md border px-3 text-xs font-semibold",
                          isActive
                            ? "border-[color-mix(in_oklch,var(--action-primary),transparent_66%)] bg-[var(--surface-inset)] text-[var(--action-primary)]"
                            : "border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)]",
                        )}
                      >
                        {isActive ? "已打开" : status.action}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

export function WriteView({
  project,
  deliberation,
  disclosure,
  formulaRequirement,
  formulaRun,
  busy,
  onGenerate,
}: {
  project: ProjectRecord | null;
  deliberation: DeliberationRun | null;
  disclosure: DisclosureRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  formulaRun: FormulaRun | null;
  busy: string;
  onGenerate: () => void;
}) {
  const formulaReady = !formulaRequirement?.required || Boolean(formulaRun?.package);
  const canGenerate = Boolean(project && deliberation && formulaReady && busy !== "generate");
  return (
    <div className="flex flex-col gap-4">
      <section className="surface-panel grid gap-4 p-5">
        <div>
          <h3>{project?.name ?? "未选择项目"}</h3>
          <p>{project?.draft_text ?? "先创建项目后再生成申请文本。"}</p>
        </div>
        <div className="status-strip" aria-label="生成申请文本前置条件">
          <div className="status-tile">
            <span>项目</span>
            <strong>{project ? "已选择" : "未选择"}</strong>
          </div>
          <div className="status-tile">
            <span>会审策略</span>
            <strong>{deliberation ? "已完成" : "未完成"}</strong>
          </div>
          <div className="status-tile">
            <span>前置交底</span>
            <strong>{disclosure ? "已生成" : "未生成"}</strong>
          </div>
          <div className="status-tile">
            <span>核心公式</span>
            <strong>{formulaRun ? "已注入" : formulaRequirement?.required ? "未完成" : "不需要"}</strong>
          </div>
        </div>
        <div className="action-dock">
          <span className="meta">{canGenerate ? "将结合会审策略、交底材料和核心公式生成申请文本。" : "需先选择项目、完成会审策略，并满足核心公式要求。"}</span>
          <button className="btn btn-primary" disabled={!canGenerate} onClick={onGenerate} type="button">
            <Wand2 size={18} />
            <span>生成</span>
          </button>
        </div>
      </section>
      <StrategyBriefView title="当前会审策略" strategy={deliberation?.strategy_brief ?? project?.package?.strategy_brief ?? null} />
      <DisclosureSummaryView packageValue={disclosure?.package ?? null} />
      <PackagePreview packageValue={project?.package ?? null} />
    </div>
  );
}
