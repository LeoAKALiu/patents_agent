/**
 * DeliberationReport — structured four-zone view of a multi-agent deliberation.
 *
 * Pure presentational leaf (no closure over App() state). Maps the existing
 * DeliberationRun + PatentStrategyBrief fields onto the four report zones
 * required by the UI spec:
 *   1. 综合裁决  ← strategy_brief.summary + agent_consensus (+ run status/mode)
 *   2. 阻断项    ← run.failures (provider_id / phase / reason / message)
 *   3. 问题项    ← run.stage_results with status failed | degraded
 *   4. 修改建议  ← strategy_brief.risk_controls / claim_strategy / description_strategy
 *
 * Business copy is preserved verbatim — no rewriting. Only the display
 * grouping changes.
 */
import { type ReactNode } from "react";
import { ShieldCheck, Ban, AlertCircle, Lightbulb } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion } from "@/components/ui/accordion";
import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import type { DeliberationRun } from "@/api";

type ReportSectionProps = {
  icon: ReactNode;
  title: string;
  tone: "verdict" | "blocker" | "issue" | "suggestion";
  /** When true, body collapses into an accordion on long content. */
  collapsible?: boolean;
  children: ReactNode;
  isEmpty?: boolean;
  emptyHint?: string;
};

const toneAccent: Record<ReportSectionProps["tone"], string> = {
  verdict: "text-[var(--brand-blue-500)]",
  blocker: "text-[var(--danger)]",
  issue: "text-[oklch(50%_0.12_75)]",
  suggestion: "text-[var(--brand-teal-500)]",
};

function ReportSection({
  icon,
  title,
  tone,
  collapsible = false,
  children,
  isEmpty = false,
  emptyHint = "暂无内容",
}: ReportSectionProps) {
  if (isEmpty) {
    return (
      <Card className="min-w-0">
        <CardHeader className="p-4 pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <span className={toneAccent[tone]}>{icon}</span>
            <span>{title}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <p className="italic text-[12px] text-[var(--text-soft)] m-0">{emptyHint}</p>
        </CardContent>
      </Card>
    );
  }
  if (collapsible) {
    return (
      <Card className="min-w-0">
        <CardHeader className="p-4 pb-0">
          <CardTitle className="flex items-center gap-2 text-sm">
            <span className={toneAccent[tone]}>{icon}</span>
            <span>{title}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-2">
          <Accordion type="multiple" className="w-full">
            <AccordionItem value="content" className="border-0">
              <AccordionTrigger className="text-xs py-2">展开详情</AccordionTrigger>
              <AccordionContent className="text-[13px] leading-relaxed text-[var(--text-muted)]">
                {children}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card className="min-w-0">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className={toneAccent[tone]}>{icon}</span>
          <span>{title}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0 text-[13px] leading-relaxed text-[var(--text-muted)]">
        {children}
      </CardContent>
    </Card>
  );
}

function Bullets({ items }: { items: readonly string[] }) {
  if (items.length === 0) {
    return <p className="italic text-[var(--text-soft)]">暂无。</p>;
  }
  return (
    <ul className="grid gap-1.5 m-0 p-0 list-none">
      {items.map((item, index) => (
        <li className="break-words" key={`bullet-${index}`}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export interface DeliberationReportProps {
  run: DeliberationRun | null;
  /** Loading state: show skeletons while a deliberation is in flight. */
  loading?: boolean;
}

export function DeliberationReport({ run, loading = false }: DeliberationReportProps) {
  if (loading) {
    return (
      <section className="grid gap-4">
        <Skeleton className="h-20 rounded-lg" />
        <Skeleton className="h-20 rounded-lg" />
        <Skeleton className="h-20 rounded-lg" />
        <Skeleton className="h-20 rounded-lg" />
      </section>
    );
  }

  const strategy = run?.strategy_brief ?? null;
  const verdict = strategy ? [strategy.summary, strategy.agent_consensus].filter(Boolean).join("\n\n") : "";
  const blockers = run?.failures ?? [];
  const issues = (run?.stage_results ?? []).filter(
    (stage) => stage.status === "failed" || stage.status === "degraded",
  );
  const suggestions = strategy
    ? [...strategy.risk_controls, ...strategy.claim_strategy, ...strategy.description_strategy].filter(Boolean)
    : [];

  return (
    <section className="grid gap-4 min-w-0">
      {/* 1. 综合裁决 */}
      <ReportSection
        icon={<ShieldCheck size={16} />}
        title="综合裁决"
        tone="verdict"
        isEmpty={!verdict}
        emptyHint="会审尚未生成裁决结论。"
      >
        <p className="whitespace-pre-wrap break-words m-0">{verdict}</p>
      </ReportSection>

      {/* 2. 阻断项 */}
      <ReportSection
        icon={<Ban size={16} />}
        title={`阻断项${blockers.length > 0 ? `（${blockers.length}）` : ""}`}
        tone="blocker"
        isEmpty={blockers.length === 0}
        emptyHint="无阻断项。"
      >
        <ul className="grid gap-2 m-0 p-0 list-none">
          {blockers.map((failure, index) => (
            <li
              className="grid gap-1 p-3 rounded-lg bg-[var(--surface-inset)] border border-app-danger/35 break-words"
              key={`blocker-${index}-${failure.provider_id}-${failure.phase}`}
            >
              <strong className="text-[13px] text-[var(--text-primary)]">
                {failure.provider_id} / {failure.phase} / {failure.reason}
              </strong>
              <span className="text-[12px] text-[var(--text-muted)]">{failure.message}</span>
            </li>
          ))}
        </ul>
      </ReportSection>

      {/* 3. 问题项 */}
      <ReportSection
        icon={<AlertCircle size={16} />}
        title={`问题项${issues.length > 0 ? `（${issues.length}）` : ""}`}
        tone="issue"
        isEmpty={issues.length === 0}
        emptyHint="无降级或失败阶段。"
      >
        <ul className="grid gap-2 m-0 p-0 list-none">
          {issues.map((stage, index) => (
            <li
              className="grid gap-1 p-3 rounded-lg bg-[var(--surface-inset)] border border-[var(--border-strong)] break-words"
              key={`issue-${index}-${stage.phase}-${stage.provider_id}`}
            >
              <strong className="text-[13px] text-[var(--text-primary)]">
                {stage.provider_id} / {stage.phase} / {stage.label}（{stage.status}）
              </strong>
            </li>
          ))}
        </ul>
      </ReportSection>

      {/* 4. 修改建议 */}
      <ReportSection
        icon={<Lightbulb size={16} />}
        title="修改建议"
        tone="suggestion"
        isEmpty={suggestions.length === 0}
        emptyHint="会审未产出修改建议。"
        collapsible={suggestions.length > 3}
      >
        <Bullets items={suggestions} />
      </ReportSection>
    </section>
  );
}
