/**
 * Disclosure / strategy / package preview views — extracted from App.tsx (M3-B').
 *
 * Pure leaf views that render disclosure packages, strategy briefs, and draft
 * packages via PreviewBlock. No closure over App() state.
 */
import { Download } from "@/lib/icons";
import {
  disclosureExportUrl,
  type DisclosurePackage,
  type DisclosureRun,
  type DraftPackage,
  type PatentStrategyBrief,
  type ProjectRecord,
} from "@/api";
import { PreviewBlock } from "./widgets";

function researchConfidenceLabel(value: DisclosurePackage["research_confidence"]): string {
  if (value === "high") return "高";
  if (value === "medium") return "中";
  if (value === "low") return "低";
  if (value === "none") return "无";
  return "未记录";
}

function dedupeStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

export function DisclosurePreview({
  project,
  run,
}: {
  project: ProjectRecord | null;
  run: DisclosureRun | null;
}) {
  const packageValue = run?.package ?? null;
  if (!run) {
    return <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl"><p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无前置材料结果。</p></section>;
  }
  if (!packageValue) {
    return (
      <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <h3>{run.status === "completed" ? "交底书" : "生成中"}</h3>
        <p className="text-sm text-[var(--text-primary)]/50 italic py-4">{run.events.at(-1) ?? "等待后台任务更新。"}</p>
      </section>
    );
  }
  const selected = packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id)
    ?? packageValue.candidates[0]
    ?? null;
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{packageValue.title}</h3>
          <p>{packageValue.summary}</p>
        </div>
        <div className="flex items-center gap-3">
          {project && (
            <>
              <a className="inline-flex items-center gap-2 text-sm text-[var(--action-primary)] hover:underline font-medium" href={disclosureExportUrl(project.id, run.id, "docx")}>
                <Download size={17} />
                <span>DOCX</span>
              </a>
              <a className="inline-flex items-center gap-2 text-sm text-[var(--action-primary)] hover:underline font-medium" href={disclosureExportUrl(project.id, run.id, "md")}>
                <Download size={17} />
                <span>MD</span>
              </a>
            </>
          )}
        </div>
      </section>
      <DisclosureSourceStatus packageValue={packageValue} />

      <section className="flex flex-col gap-6">
        {selected && <PreviewBlock title="推荐专利点" text={`${selected.title}\n${selected.innovation}\n${selected.rationale}`} />}
        <PreviewBlock title="公开现有技术差异" text={packageValue.prior_art_differences} />
        <PreviewBlock
          title="公开现有技术"
          text={packageValue.prior_art_hits.map((hit) => `${hit.source} ${hit.title}\n${hit.url}\n${hit.relevance_summary}`).join("\n\n") || "暂无。"}
        />
        <PreviewBlock
          title="自检结果"
          text={packageValue.self_check_findings.map((finding) => `[${finding.severity}] ${finding.category}: ${finding.message}`).join("\n") || "暂无。"}
        />
        <PreviewBlock title="技术交底书" text={packageValue.body_markdown} />
        <PreviewBlock title="Mermaid" text={packageValue.mermaid} />
      </section>
    </div>
  );
}

export function DisclosureSourceStatus({ packageValue }: { packageValue: DisclosurePackage }) {
  const diagnostics = packageValue.provider_diagnostics ?? [];
  const activeChain = diagnostics.flatMap((item) => item.active_chain ?? []);
  const skipped = diagnostics.flatMap((item) => item.skipped_providers ?? []);
  const warnings = diagnostics.flatMap((item) => item.warnings ?? []);
  return (
    <section className="grid gap-3 border border-[var(--border-strong)] rounded-lg bg-[var(--surface-inset)] p-4">
      <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-soft)] font-medium">
        <span>研究置信度：{researchConfidenceLabel(packageValue.research_confidence)}</span>
        <span>检索链：{dedupeStrings(activeChain).join(" / ") || "未记录"}</span>
        <span>现有技术：{packageValue.prior_art_hits.length} 条</span>
      </div>
      {(skipped.length > 0 || warnings.length > 0) && (
        <div className="grid gap-2 text-sm text-[var(--text-muted)]">
          {skipped.slice(0, 4).map((item) => (
            <p key={`${item.provider}-${item.reason}`}>{item.provider} 跳过：{item.reason}</p>
          ))}
          {warnings.slice(0, 3).map((warning, index) => <p key={`provider-warning-${index}`}>告警：{warning}</p>)}
        </div>
      )}
    </section>
  );
}

export function DisclosureSummaryView({ packageValue }: { packageValue: DisclosurePackage | null }) {
  return (
    <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
      <h3>当前前置交底书</h3>
      {packageValue ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <PreviewBlock title="摘要" text={packageValue.summary} />
          <PreviewBlock
            title="推荐专利点"
            text={(packageValue.candidates.find((candidate) => candidate.id === packageValue.selected_candidate_id) ?? packageValue.candidates[0])?.title ?? "暂无"}
          />
          <PreviewBlock title="现有技术差异" text={packageValue.prior_art_differences} />
        </div>
      ) : (
        <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无已完成前置交底书。</p>
      )}
    </section>
  );
}

export function StrategyBriefView({
  title,
  strategy,
}: {
  title: string;
  strategy: PatentStrategyBrief | null;
}) {
  return (
    <section className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
      <h3>{title}</h3>
      {strategy ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <PreviewBlock title="摘要" text={strategy.summary} />
          <PreviewBlock title="权利要求策略" text={strategy.claim_strategy.join("\n")} />
          <PreviewBlock title="说明书策略" text={strategy.description_strategy.join("\n")} />
          <PreviewBlock title="风险控制" text={strategy.risk_controls.join("\n")} />
          <PreviewBlock title="智能体共识" text={strategy.agent_consensus} />
        </div>
      ) : (
        <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无可注入策略</p>
      )}
    </section>
  );
}

export function PackagePreview({
  packageValue,
  compact = false,
}: {
  packageValue: DraftPackage | null;
  compact?: boolean;
}) {
  if (!packageValue) {
    return <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无申请文本</p>;
  }
  return (
    <section className={compact ? "flex flex-col gap-4 text-sm" : "flex flex-col gap-6"}>
      <PreviewBlock title="摘要" text={packageValue.abstract} />
      <PreviewBlock title="权利要求书" text={packageValue.claims} />
      {!compact && <PreviewBlock title="说明书" text={packageValue.description} />}
      {!compact && <PreviewBlock title="附图说明" text={packageValue.drawing_description} />}
      <PreviewBlock title="Mermaid流程图" text={packageValue.mermaid} />
      <PreviewBlock title="绘图提示词" text={packageValue.image_prompt} />
      {packageValue.strategy_brief && <PreviewBlock title="多智能体会审策略" text={packageValue.strategy_brief.summary} />}
    </section>
  );
}
