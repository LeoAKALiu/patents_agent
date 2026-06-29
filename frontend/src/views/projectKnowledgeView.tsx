import type { ReactNode } from "react";

import type { PriorArtCandidate, ProjectKnowledgeOverview, ProjectRecord } from "@/api";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Info,
  RefreshCw,
  Search,
  Wand2,
  XCircle,
} from "@/lib/icons";

import { QualityReportView, StatusPill } from "./widgets";

const statusLabels: Record<string, string> = {
  not_started: "未生成检索计划",
  search_plan_pending: "检索计划待确认",
  search_running: "候选检索中",
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

function formatDate(value: string): string {
  if (!value) return "未记录";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-CN", { hour12: false });
}

function candidateDecisionLabel(decision: PriorArtCandidate["user_decision"]): string {
  if (decision === "include") return "已纳入建库";
  if (decision === "exclude") return "已排除";
  return "待人工决策";
}

function recommendationLabel(action: PriorArtCandidate["recommended_action"]): string {
  if (action === "include") return "Agent 建议纳入";
  if (action === "exclude") return "Agent 建议排除";
  return "Agent 建议复核";
}

function qualityFlagCopy(flag: string, stalenessReason: string): { tone: "warning" | "info"; text: string } {
  switch (flag) {
    case "needs_search":
      return {
        tone: "warning",
        text: "尚未完成项目检索。授权判断仍然受证据门控，当前不能把 grantability 结论当成已有现有技术支撑。",
      };
    case "candidates_need_confirmation":
      return {
        tone: "info",
        text: "候选文献已生成，但还需要人工决定哪些纳入或排除，然后才能形成项目证据库。",
      };
    case "synthetic_evidence":
      return {
        tone: "warning",
        text: "建库已完成，但当前证据库仅包含 synthetic/fake 候选结果。授权判断仍然受证据门控，不能视为真实检索结论。",
      };
    case "empty_corpus":
      return {
        tone: "warning",
        text: "当前没有任何纳入建库的文献。授权判断仍然受证据门控，需要补充检索或重新筛选候选文献。",
      };
    case "stale_project_snapshot":
      return {
        tone: "warning",
        text: stalenessReason || "项目技术描述已经变化，现有证据库已过期，需要重新检索或补充检索。",
      };
    default:
      if (flag.includes("insufficient")) {
        return {
          tone: "warning",
          text: "当前证据覆盖不足。授权判断仍然受证据门控，需要补充检索后再继续使用现有技术结论。",
        };
      }
      if (flag.includes("synthetic")) {
        return {
          tone: "warning",
          text: "当前证据包含 synthetic 结果，不能把 grantability 结论视为真实现有技术支撑。",
        };
      }
      if (flag.includes("empty")) {
        return {
          tone: "warning",
          text: "当前证据库为空，授权判断仍然受证据门控。",
        };
      }
      if (flag.includes("needs_search")) {
        return {
          tone: "warning",
          text: "仍需完成检索后才能形成可依赖的项目证据库。",
        };
      }
      return {
        tone: "info",
        text: `质量信号：${flag}`,
      };
  }
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
  const latestCorpusVersion = knowledge?.latest_corpus_version ?? null;
  const includedCandidates = candidates.filter((candidate) => candidate.user_decision === "include");
  const canBuildCorpus =
    includedCandidates.length > 0 &&
    (status === "candidates_pending" || status === "needs_supplemental_search" || status === "ready");
  const qualityFlags = Array.from(new Set(state?.quality_flags ?? []));
  const guidanceCards = qualityFlags.map((flag) => ({ flag, ...qualityFlagCopy(flag, state?.staleness_reason ?? "") }));

  let primaryAction = {
    icon: Wand2,
    label: "让 Agent 生成检索计划",
    action: onGenerateKnowledgePlan,
  };

  if (status === "search_plan_pending") {
    primaryAction = {
      icon: Search,
      label: "运行候选检索",
      action: onRunKnowledgeSearch,
    };
  } else if (status === "candidates_pending") {
    primaryAction = {
      icon: Database,
      label: "确认建库",
      action: onBuildProjectCorpus,
    };
  } else if (status === "stale" || status === "needs_supplemental_search") {
    primaryAction = {
      icon: Wand2,
      label: "重新生成检索计划",
      action: onGenerateKnowledgePlan,
    };
  } else if (status === "ready") {
    primaryAction = {
      icon: Search,
      label: "重新运行最新检索计划",
      action: plan ? onRunKnowledgeSearch : onGenerateKnowledgePlan,
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
        <div className="mt-4 flex flex-col gap-3">
          {status === "failed" && (
            <p className="flex items-center gap-2 rounded-lg border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-4 py-3 text-sm text-[var(--danger)]">
              <AlertTriangle size={16} />
              本次检索或建库未成功完成。授权判断仍然受证据门控，请先修复失败原因再继续使用现有技术分析。
            </p>
          )}
          {guidanceCards.map((card) => (
            <p
              className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
                card.tone === "warning"
                  ? "border-[var(--warning,#d97706)]/30 bg-[var(--warning,#d97706)]/10 text-[var(--text-primary)]"
                  : "border-[var(--border-subtle)] bg-[var(--surface-base)] text-[var(--text-primary)]/80"
              }`}
              key={card.flag}
            >
              {card.tone === "warning" ? <AlertTriangle size={16} /> : <Info size={16} />}
              <span>{card.text}</span>
            </p>
          ))}
        </div>
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
          {canBuildCorpus && (
            <div className="mt-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm text-[var(--text-primary)]/80">
              已选 {includedCandidates.length} 篇候选文献进入建库范围，可直接确认建库。
            </div>
          )}
          {status === "stale" && includedCandidates.length > 0 && (
            <div className="mt-3 rounded-lg border border-[var(--warning,#d97706)]/30 bg-[var(--warning,#d97706)]/10 px-4 py-3 text-sm text-[var(--text-primary)]">
              当前候选来自已过期的项目快照，需要重新生成检索计划后才能再次建库。
            </div>
          )}
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
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-2 py-1">
                        {recommendationLabel(candidate.recommended_action)}
                      </span>
                      <span className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-2 py-1">
                        {candidateDecisionLabel(candidate.user_decision)}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
                      onClick={() => onCandidateDecision(candidate.id, "include")}
                      type="button"
                    >
                      <CheckCircle2 size={15} />
                      纳入建库
                    </button>
                    <button
                      className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
                      onClick={() => onCandidateDecision(candidate.id, "exclude")}
                      type="button"
                    >
                      <XCircle size={15} />
                      排除
                    </button>
                  </div>
                </div>
                <p className="mt-2 text-sm text-[var(--text-primary)]/65">{candidate.abstract}</p>
                <p className="mt-2 text-xs text-[var(--text-primary)]/55">
                  {candidate.recommendation_reason}
                </p>
              </article>
            ))}
            {candidates.length === 0 && (
              <p className="text-sm italic text-[var(--text-primary)]/50">
                运行确定性候选检索后会出现候选文献。
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3>项目证据库版本</h3>
            <p className="text-sm text-[var(--text-primary)]/65">
              这里显示当前建库结果与质量报告，方便判断 grantability 是否具备可依赖的现有技术证据。
            </p>
          </div>
          {canBuildCorpus && (
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm font-medium"
              disabled={busy.startsWith("knowledge")}
              onClick={onBuildProjectCorpus}
              type="button"
            >
              <Database size={16} />
              <span>确认建库</span>
            </button>
          )}
        </div>
        {latestCorpusVersion ? (
          <div className="mt-4 flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <StatusPill label="版本状态" value={latestCorpusVersion.status} />
              <StatusPill label="文献数" value={String(latestCorpusVersion.document_count)} />
              <StatusPill label="片段数" value={String(latestCorpusVersion.chunk_count)} />
              <StatusPill label="权利要求覆盖" value={percent(latestCorpusVersion.claim_coverage)} />
              <StatusPill label="全文覆盖" value={percent(latestCorpusVersion.fulltext_coverage)} />
            </div>
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm text-[var(--text-primary)]/80">
              <p>
                <strong>{latestCorpusVersion.name}</strong>
              </p>
              <p>建库时间：{formatDate(latestCorpusVersion.created_at)}</p>
            </div>
            <QualityReportView report={latestCorpusVersion.quality_report} />
          </div>
        ) : (
          <p className="mt-4 text-sm italic text-[var(--text-primary)]/50">
            {status === "stale"
              ? "当前项目快照已过期，需要重新生成检索计划后才能再次建库。"
              : "还没有项目证据库版本。完成候选文献决策后即可确认建库。"}
          </p>
        )}
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
