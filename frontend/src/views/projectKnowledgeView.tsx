import type { ReactNode } from "react";

import type { PriorArtCandidate, ProjectKnowledgeOverview, ProjectRecord } from "@/api";
import { AlertTriangle, CheckCircle2, Database, RefreshCw, Search, Wand2 } from "@/lib/icons";

import { StatusPill } from "./widgets";

const statusLabels: Record<string, string> = {
  not_started: "未生成检索计划",
  search_plan_pending: "检索计划待确认",
  search_running: "官方源检索中",
  candidates_pending: "候选文献待确认",
  corpus_building: "语料库建库中",
  ready: "语料库就绪",
  needs_supplemental_search: "需要补充检索",
  stale: "语料库过期",
  failed: "检索失败",
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function ProjectKnowledgeView({
  selectedProject,
  knowledge,
  busy,
  onGenerateKnowledgePlan,
  onRunKnowledgeSearch,
  onCandidateDecision,
  onBuildProjectCorpus,
  advancedFallback,
}: {
  selectedProject: ProjectRecord | null;
  knowledge: ProjectKnowledgeOverview | null;
  busy: string;
  onGenerateKnowledgePlan: () => void;
  onRunKnowledgeSearch: () => void;
  onCandidateDecision: (
    candidateId: string,
    decision: PriorArtCandidate["user_decision"],
  ) => void;
  onBuildProjectCorpus: () => void;
  advancedFallback?: ReactNode;
}) {
  if (!selectedProject) {
    return (
      <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
        <h3>项目现有技术库</h3>
        <p className="text-sm text-[var(--text-primary)]/60">
          请先创建或选择项目，Agent 会根据项目题目和一句话介绍生成检索计划。
        </p>
      </section>
    );
  }

  const status = knowledge?.state.status ?? "not_started";
  const candidates = knowledge?.candidates ?? [];
  const plan = knowledge?.latest_plan ?? null;
  const intent = knowledge?.latest_intent ?? null;
  const state = knowledge?.state;

  let primaryAction = {
    icon: Wand2,
    label: "让 Agent 生成检索计划",
    action: onGenerateKnowledgePlan,
  };

  if (status === "search_plan_pending") {
    primaryAction = {
      icon: Search,
      label: "开始官方源检索",
      action: onRunKnowledgeSearch,
    };
  } else if (status === "candidates_pending") {
    primaryAction = {
      icon: Database,
      label: "确认建库",
      action: onBuildProjectCorpus,
    };
  } else if (status === "ready" || status === "needs_supplemental_search" || status === "stale") {
    primaryAction = {
      icon: Search,
      label: "补充检索",
      action: onGenerateKnowledgePlan,
    };
  }

  const PrimaryIcon = primaryAction.icon;

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3>项目现有技术库</h3>
            <p className="text-sm text-[var(--text-primary)]/65">
              Agent 根据项目题目和一句话介绍生成检索计划、候选文献池和项目语料库。
            </p>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] px-5 py-2.5 font-medium text-[var(--action-primary-contrast)] disabled:opacity-50"
            disabled={busy.startsWith("knowledge")}
            onClick={primaryAction.action}
            type="button"
          >
            <PrimaryIcon size={17} />
            <span>{primaryAction.label}</span>
          </button>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">
          <StatusPill label="知识状态" value={statusLabels[status] ?? status} />
          <StatusPill label="候选文献" value={String(state?.candidate_count ?? candidates.length)} />
          <StatusPill label="入库文献" value={String(state?.document_count ?? 0)} />
          <StatusPill label="权利要求覆盖" value={percent(state?.claim_coverage ?? 0)} />
          <StatusPill label="全文覆盖" value={percent(state?.fulltext_coverage ?? 0)} />
        </div>
        {status === "stale" && (
          <p className="mt-4 flex items-center gap-2 text-sm text-[var(--danger)]">
            <AlertTriangle size={16} />
            {state?.staleness_reason || "项目技术方案已变化，需要补充检索。"}
          </p>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
          <h3>Agent 检索计划</h3>
          {intent ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-[var(--text-primary)]/70">
                {intent.technical_means || intent.technical_object}
              </p>
              <div className="flex flex-wrap gap-2">
                {intent.keywords_zh.map((keyword) => (
                  <span className="tag" key={keyword}>
                    {keyword}
                  </span>
                ))}
              </div>
              {plan?.strategy_groups.map((group) => (
                <article
                  className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-4"
                  key={group.id}
                >
                  <p className="font-semibold">{group.label}</p>
                  <p className="text-sm text-[var(--text-primary)]/65">{group.purpose}</p>
                  <p className="mt-2 text-xs text-[var(--text-primary)]/55">
                    {group.queries.join(" / ")}
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm italic text-[var(--text-primary)]/50">还没有检索计划。</p>
          )}
        </div>

        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
          <h3>候选文献池</h3>
          <div className="flex flex-col gap-3">
            {candidates.map((candidate) => (
              <article
                className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-4"
                key={candidate.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{candidate.title}</p>
                    <p className="text-xs text-[var(--text-primary)]/55">
                      {candidate.publication_number || "未记录公开号"} · {candidate.source}
                    </p>
                  </div>
                  <button
                    className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
                    onClick={() => onCandidateDecision(candidate.id, "include")}
                    type="button"
                  >
                    <CheckCircle2 size={15} />
                    入库
                  </button>
                </div>
                <p className="mt-2 text-sm text-[var(--text-primary)]/65">{candidate.abstract}</p>
                <p className="mt-2 text-xs text-[var(--text-primary)]/55">
                  {candidate.recommendation_reason}
                </p>
              </article>
            ))}
            {candidates.length === 0 && (
              <p className="text-sm italic text-[var(--text-primary)]/50">
                运行官方源检索后会出现候选文献。
              </p>
            )}
          </div>
        </div>
      </section>

      {advancedFallback && (
        <details className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
          <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)]">
            <span className="inline-flex items-center gap-2">
              <RefreshCw size={16} />
              从本地文件补充语料
            </span>
          </summary>
          <div className="mt-4">{advancedFallback}</div>
        </details>
      )}
    </div>
  );
}
