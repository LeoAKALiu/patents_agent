import { useState, type ReactNode } from "react";

import type {
  CnipaQueryPack,
  PriorArtCandidate,
  ProjectKnowledgeImportLedger,
  ProjectKnowledgeOverview,
  ProjectRecord,
} from "@/api";
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

const corpusVersionStatusLabels: Record<string, string> = {
  building: "建库中",
  ready: "已就绪",
  needs_supplemental_search: "需要补充检索",
  failed: "失败",
  superseded: "已替代",
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

function joinQueries(queries: string[]): string {
  return queries.join("\n\n");
}

function skippedCount(ledger: ProjectKnowledgeImportLedger): number | null {
  if (typeof ledger.row_count !== "number" || typeof ledger.parsed_count !== "number") return null;
  const delta = ledger.row_count - ledger.parsed_count;
  return delta >= 0 ? delta : null;
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

function sourceLabel(source: string): string {
  if (source === "cnipa_official_export") return "CNIPA 官方导出";
  if (source === "cnipa_authorized_api") return "CNIPA 授权 API";
  if (source === "cnipa_epub") return "CNIPA legacy helper";
  if (source === "wipo_patentscope") return "WIPO Patentscope";
  if (source === "google_patents") return "Google Patents";
  return source;
}

function normalizePlanWarning(warning: string): string {
  if (warning.includes("CNIPA_EPUB_SEARCH_SCRIPT")) {
    return "CNIPA helper 当前未配置。普通导入路径请改用 CNIPA 官方导出检索包，不需要额外环境变量。";
  }
  return warning;
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
    case "non_patent_source":
      return {
        tone: "warning",
        text: "当前纳入项包含非专利来源，不能作为项目现有技术库就绪依据；请改用专利检索来源或重新筛选候选文献。",
      };
    case "cnipa_export_missing_provenance":
      return {
        tone: "warning",
        text: "部分 CNIPA 官方导出候选缺少原始导出链路，暂不能作为完整官方证据；请重新导出并保留来源字段后再导入。",
      };
    case "cnipa_export_metadata_only":
      return {
        tone: "warning",
        text: "当前 CNIPA 官方导出仅含题录元数据，缺少可支撑复核的正文证据；请补充包含摘要或全文字段的官方导出。",
      };
    case "cnipa_export_missing_claims":
      return {
        tone: "warning",
        text: "当前 CNIPA 官方导出缺少权利要求内容，无法满足正式的权利要求覆盖复核；请补充包含权利要求的官方导出。",
      };
    case "cnipa_export_partial_fulltext":
      return {
        tone: "warning",
        text: "当前 CNIPA 官方导出只有部分全文，现有技术证据仍不完整；请补充更完整的官方导出结果。",
      };
    case "cnipa_export_parse_warnings":
      return {
        tone: "info",
        text: "CNIPA 官方导入时出现解析提醒，建议复核导入结果，但这不单独等同于覆盖率门控失败。",
      };
    case "no_hits":
      return {
        tone: "warning",
        text: "本次检索没有形成候选文献。请检查 Google Patents 网络/证书状态，或直接改走 CNIPA 官方导出导入路径；在证据库就绪前不要依赖授权前景判断。",
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
  cnipaQueryPack,
  importLedgers,
  onGenerateKnowledgePlan,
  onRunKnowledgeSearch,
  onCandidateDecision,
  onBuildProjectCorpus,
  onImportCnipaExport,
  advancedFallback,
}: {
  selectedProject: ProjectRecord | null;
  knowledge: ProjectKnowledgeOverview | null;
  busy: string;
  cnipaQueryPack?: CnipaQueryPack | null;
  importLedgers?: ProjectKnowledgeImportLedger[];
  onGenerateKnowledgePlan: () => void;
  onRunKnowledgeSearch: () => void;
  onCandidateDecision: (
    candidateId: string,
    decision: PriorArtCandidate["user_decision"],
  ) => void;
  onBuildProjectCorpus: () => void;
  onImportCnipaExport?: (file: File) => void;
  advancedFallback?: ReactNode;
}) {
  const [copyFeedback, setCopyFeedback] = useState("");

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
  const planWarnings = (plan?.warnings ?? []).map(normalizePlanWarning);
  const intent = knowledge?.latest_intent ?? null;
  const state = knowledge?.state;
  const latestCorpusVersion = knowledge?.latest_corpus_version ?? null;
  const cnipaStrategyQueries = cnipaQueryPack?.strategies?.flatMap((strategy) => strategy.queries) ?? [];
  const includedCandidates = candidates.filter((candidate) => candidate.user_decision === "include");
  const hasReadonlyCandidates =
    status === "stale" || status === "not_started" || status === "search_running" || status === "failed";
  const canDecideCandidates = !hasReadonlyCandidates;
  const canBuildCorpus =
    includedCandidates.length > 0 && canDecideCandidates;
  const qualityFlags = Array.from(new Set(state?.quality_flags ?? []));
  const guidanceCards = qualityFlags.map((flag) => ({ flag, ...qualityFlagCopy(flag, state?.staleness_reason ?? "") }));
  const handleCopyCnipaQuery = async (queries: string[]) => {
    const cnipaQueryText = joinQueries(queries);
    if (!cnipaQueryText) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(cnipaQueryText);
        setCopyFeedback("已复制检索式。");
        return;
      }
    } catch {
      // Fall through to manual-copy guidance below.
    }
    setCopyFeedback("当前环境不支持自动复制，请手动复制下方检索式。");
  };

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
  const primaryActionDisabled = busy.startsWith("knowledge") || (status === "candidates_pending" && !canBuildCorpus);

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
            disabled={primaryActionDisabled}
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

      {plan && (
        <section className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h3>CNIPA 官方导出</h3>
              <p className="text-sm text-[var(--text-primary)]/65">
                Agent 已生成 CNIPA 检索包。请在 CNIPA 官方系统执行检索并导出 CSV/XLSX/ZIP，再导入为真实中文专利候选。
              </p>
            </div>
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                const file = new FormData(event.currentTarget).get("file");
                if (file instanceof File && file.size > 0) onImportCnipaExport?.(file);
                event.currentTarget.reset();
              }}
            >
              <input accept=".csv,.xlsx,.zip" className="text-sm" name="file" type="file" />
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm font-medium"
                disabled={busy.startsWith("knowledge") || !onImportCnipaExport}
                type="submit"
              >
                <Database size={16} />
                <span>导入 CNIPA 官方导出物</span>
              </button>
            </form>
          </div>
          {cnipaQueryPack?.strategies?.length ? (
            <div className="mt-4 grid gap-3">
              <button
                className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-medium"
                onClick={() => void handleCopyCnipaQuery(cnipaStrategyQueries)}
                type="button"
              >
                <RefreshCw size={14} />
                <span>复制 CNIPA 检索式</span>
              </button>
              {cnipaQueryPack.strategies.map((strategy) => (
                <article
                  className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-3"
                  key={strategy.strategy_group_id}
                >
                  <p className="font-semibold">{strategy.label}</p>
                  <p className="text-sm text-[var(--text-primary)]/65">{strategy.purpose}</p>
                  <div className="mt-2 flex flex-col gap-2">
                    <button
                      className="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-medium"
                      onClick={() => void handleCopyCnipaQuery(strategy.queries)}
                      type="button"
                    >
                      <RefreshCw size={14} />
                      <span>复制该策略检索式</span>
                    </button>
                    <p className="text-xs text-[var(--text-primary)]/70">{strategy.queries.join(" / ")}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
          {copyFeedback ? (
            <p className="mt-3 text-xs text-[var(--text-primary)]/65">{copyFeedback}</p>
          ) : null}
          {importLedgers?.length ? (
            <div className="mt-4 flex flex-col gap-3">
              {importLedgers.map((ledger) => {
                const derivedSkippedCount = skippedCount(ledger);
                return (
                  <article
                    className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] p-3 text-sm"
                    key={ledger.id}
                  >
                    <div className="flex flex-col gap-1">
                      <p className="font-medium">导入文件：{ledger.source_file_name}</p>
                      <p className="text-xs text-[var(--text-primary)]/60">
                        导入时间：{formatDate(ledger.created_at)}
                      </p>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
                      <StatusPill label="原始行数" value={String(ledger.row_count ?? 0)} />
                      <StatusPill label="解析候选" value={String(ledger.parsed_count ?? 0)} />
                      <StatusPill
                        label="跳过/重复"
                        value={derivedSkippedCount === null ? "未记录" : String(derivedSkippedCount)}
                      />
                      <StatusPill label="失败行数" value={String(ledger.failures?.length ?? 0)} />
                    </div>
                    {ledger.warnings?.length ? (
                      <div className="mt-3 rounded-lg border border-[var(--warning,#d97706)]/30 bg-[var(--warning,#d97706)]/10 px-3 py-2">
                        <p className="text-xs font-medium">导入提醒</p>
                        <ul className="mt-1 list-disc pl-5 text-xs text-[var(--text-primary)]/75">
                          {ledger.warnings.map((warning, index) => (
                            <li key={`${ledger.id}-warning-${index}`}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {ledger.failures?.length ? (
                      <div className="mt-3 rounded-lg border border-[var(--danger)]/25 bg-[var(--danger)]/8 px-3 py-2">
                        <p className="text-xs font-medium">失败明细</p>
                        <div className="mt-2 flex flex-col gap-2">
                          {ledger.failures.map((failure, index) => (
                            <div
                              className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-3 py-2 text-xs"
                              key={`${ledger.id}-failure-${index}`}
                            >
                              <p>
                                {failure.source_file_name} 第 {failure.row_number} 行
                              </p>
                              <p className="text-[var(--text-primary)]/70">
                                {failure.code} · {failure.message}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ) : null}
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-6">
          <h3>Agent 检索计划</h3>
          {intent ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-[var(--text-primary)]/70">
                {intent.technical_means || intent.technical_object}
              </p>
              {planWarnings.length > 0 && (
                <div className="rounded-lg border border-[var(--warning,#d97706)]/30 bg-[var(--warning,#d97706)]/10 px-4 py-3 text-sm text-[var(--text-primary)]">
                  <div className="flex flex-col gap-2">
                    {planWarnings.map((warning) => (
                      <p className="flex items-start gap-2" key={warning}>
                        <AlertTriangle className="mt-0.5 shrink-0" size={15} />
                        <span>{warning}</span>
                      </p>
                    ))}
                  </div>
                </div>
              )}
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
          {hasReadonlyCandidates && candidates.length > 0 && (
            <div className="mt-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm text-[var(--text-primary)]/80">
              {status === "stale"
                ? "这些候选属于旧的项目快照，当前只能只读查看。请先重新生成检索计划，再对新候选执行纳入或排除。"
                : "当前状态下候选文献仅供只读查看。请先完成新的检索计划或重新生成候选文献，再继续纳入或排除。"}
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
                      {candidate.publication_number || "未记录公开号"} · {sourceLabel(candidate.source)}
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
                  {canDecideCandidates ? (
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
                  ) : (
                    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-3 py-2 text-xs text-[var(--text-primary)]/60">
                      {status === "stale" ? "候选已过期，请重新生成检索计划。" : "当前为只读候选，待生成新结果后再决策。"}
                    </div>
                  )}
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
              <StatusPill
                label="版本状态"
                value={corpusVersionStatusLabels[latestCorpusVersion.status] ?? latestCorpusVersion.status}
              />
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
