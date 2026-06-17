/**
 * Expert-tool views — extracted from App.tsx (M3-B').
 * ExpertToolChooser (the tool grid) + WriteView (manual draft generation).
 */
import { Wand2 } from "@/lib/icons";
import {
  expertToolGroups,
  type ExpertToolId,
} from "@/guidedFlow";
import type {
  DeliberationRun,
  DisclosureRun,
  FormulaNeedAssessment,
  FormulaRun,
  ProjectRecord,
} from "@/api";
import { DisclosureSummaryView, PackagePreview, StrategyBriefView } from "./disclosureViews";

export function ExpertToolChooser({
  activeToolId,
  onSelect,
}: {
  activeToolId: ExpertToolId;
  onSelect: (id: ExpertToolId) => void;
}) {
  return (
    <section className="panel wide expert-tool-panel">
      <h3>专家工具</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {expertToolGroups.map((group) => (
          <div className="flex flex-col gap-3" key={group.id}>
            <p>{group.label}</p>
            <div className="flex flex-col gap-2">
              {group.tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <button
                    className={activeToolId === tool.id ? "flex items-center gap-3 px-4 py-3 rounded-lg bg-[var(--brand-teal-500)]/10 border border-[var(--brand-teal-500)]/30 text-[var(--action-primary)] font-semibold shadow-sm" : "flex items-center gap-3 px-4 py-3 rounded-lg bg-[var(--surface-base)] border border-[var(--border-subtle)] text-sm font-medium hover:bg-[var(--surface-raised)] transition-colors"}
                    key={tool.id}
                    onClick={() => onSelect(tool.id)}
                    type="button"
                    title={tool.description}
                  >
                    <Icon size={17} />
                    <span>{tool.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
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
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{project?.name ?? "未选择项目"}</h3>
          <p>{project?.draft_text ?? "先创建项目后再生成申请文本。"}</p>
          <p>
            {deliberation
              ? "将结合会审结论生成。"
              : "尚未完成多智能体会审，仍可直接生成。"}
          </p>
          <p>{disclosure ? "将结合前置交底书生成。" : "尚未完成前置交底书，仍可直接生成。"}</p>
          <p>{formulaRun ? "已注入核心公式。" : formulaRequirement?.required ? "核心公式未完成，暂不能生成。" : "无需核心公式。"}</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || !deliberation || !formulaReady || busy === "generate"} onClick={onGenerate} type="button">
          <Wand2 size={18} />
          <span>生成</span>
        </button>
      </section>
      <StrategyBriefView title="当前会审策略" strategy={deliberation?.strategy_brief ?? project?.package?.strategy_brief ?? null} />
      <DisclosureSummaryView packageValue={disclosure?.package ?? null} />
      <PackagePreview packageValue={project?.package ?? null} />
    </div>
  );
}
