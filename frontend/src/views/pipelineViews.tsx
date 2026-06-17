/**
 * Pipeline expert views — extracted from App.tsx (M3-B').
 * MoatView (护城河), DeliberationView (多智能体会审), DisclosureView (前置材料).
 */
import { useState, type FormEvent } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Upload,
  UsersRound,
} from "@/lib/icons";
import { AgentProviderCards } from "@/AgentProviderCards";
import type {
  AgentDoctorReport,
  DeliberationRun,
  DisclosureRun,
  EvidenceStatus,
  PatentPointCandidate,
  PatentPointCreatePayload,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";
import {
  agentDoctorStatusLabel,
  agentRunModeLabel,
  deliberationRunModeLabel,
  evidenceStatusLabel,
  latestCompletedDeliberation,
  logLevelLabel,
  moatScoreTotal,
  pipelineRunStatusLabel,
  sourceTypeLabel,
} from "@/domain";
import {
  RuntimeFailurePanel,
  RuntimeRunActions,
  RuntimeRunConsole,
  latestActiveRun,
  runtimeStageLabel,
} from "./runtimePanel";
import { StatusPill } from "./widgets";
import { StrategyBriefView, DisclosurePreview } from "./disclosureViews";

function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function latestCompletedDisclosure(runs: DisclosureRun[]): DisclosureRun | null {
  return runs.find((run) => run.status === "completed" && run.package) ?? null;
}

type MoatForm = {
  title: string;
  technical_problem: string;
  innovation: string;
  technical_solution: string;
  feasibility_basis: string;
  evidence_status: EvidenceStatus;
};

const defaultMoatScores = {
  scope_width: 0.6,
  designaround_difficulty: 0.6,
  feasibility: 0.5,
  support_strength: 0.2,
  prior_art_distance: 0.4,
  strategic_value: 0.7,
};

export function MoatView({
  project,
  points,
  busy,
  onCreate,
  onSelect,
  onDelete,
  onEvaluateMoat,
}: {
  project: ProjectRecord | null;
  points: PatentPointCandidate[];
  busy: string;
  onCreate: (payload: PatentPointCreatePayload) => Promise<boolean>;
  onSelect: (point: PatentPointCandidate) => Promise<void>;
  onDelete: (point: PatentPointCandidate) => Promise<void>;
  onEvaluateMoat: () => Promise<void>;
}) {
  const [form, setForm] = useState<MoatForm>({
    title: "",
    technical_problem: "",
    innovation: "",
    technical_solution: "",
    feasibility_basis: "",
    evidence_status: "feasible_unverified",
  });
  const canSubmit = Boolean(
    project
      && form.title.trim()
      && form.technical_problem.trim()
      && form.innovation.trim()
      && form.technical_solution.trim(),
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    const succeeded = await onCreate({
      title: form.title.trim(),
      technical_problem: form.technical_problem.trim(),
      innovation: form.innovation.trim(),
      technical_solution: form.technical_solution.trim(),
      beneficial_effects: [],
      protection_focus: ["方法", "系统", "介质"],
      evidence_status: form.evidence_status,
      source_type: "user",
      feasibility_basis: form.feasibility_basis.trim(),
      support_gaps: form.feasibility_basis.trim() ? [] : ["需补充可行性依据或实验记录"],
      experiment_needed: form.evidence_status === "needs_experiment" ? ["补充对比实验或工程验证记录"] : [],
      moat_scores: defaultMoatScores,
      selected: true,
      rationale: "用户指定的护城河专利点",
    });
    if (!succeeded) return;
    setForm({
      title: "",
      technical_problem: "",
      innovation: "",
      technical_solution: "",
      feasibility_basis: "",
      evidence_status: "feasible_unverified",
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>{project ? `${project.name} / 护城河专利点` : "护城河专利点"}</h3>
          <p>{project ? "把用户明确指定的可保护技术点登记成后续交底书、会审和撰写的输入。" : "先创建项目后再登记专利点。"}</p>
        </div>
        <ShieldCheck size={22} />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>新增专利点</h3>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <label>
              <span>名称 / Title</span>
              <input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>技术问题</span>
              <textarea
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[80px]"
                value={form.technical_problem}
                onChange={(event) => setForm((current) => ({ ...current, technical_problem: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>创新点</span>
              <textarea
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[80px]"
                value={form.innovation}
                onChange={(event) => setForm((current) => ({ ...current, innovation: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>技术方案</span>
              <textarea
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[80px]"
                value={form.technical_solution}
                onChange={(event) => setForm((current) => ({ ...current, technical_solution: event.target.value }))}
                disabled={!project}
                required
              />
            </label>
            <label>
              <span>可行性依据</span>
              <textarea
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]/40 min-h-[80px]"
                value={form.feasibility_basis}
                onChange={(event) => setForm((current) => ({ ...current, feasibility_basis: event.target.value }))}
                disabled={!project}
              />
            </label>
            <label>
              <span>证据状态</span>
              <select
                value={form.evidence_status}
                onChange={(event) => setForm((current) => ({ ...current, evidence_status: event.target.value as EvidenceStatus }))}
                disabled={!project}
              >
                <option value="feasible_unverified">可行未验证</option>
                <option value="verified">已验证</option>
                <option value="needs_experiment">需实验</option>
                <option value="model_generated">模型生成</option>
              </select>
            </label>
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!canSubmit || busy === "patent-point-create"} type="submit">
              <ShieldCheck size={17} />
              <span>加入护城河</span>
            </button>
          </form>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <div className="flex items-center justify-between gap-3">
            <h3>专利点列表</h3>
            <button
              className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] text-sm font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
              disabled={!points.length || busy === "patent-point-evaluate-moat"}
              onClick={() => void onEvaluateMoat()}
              type="button"
              title="调用模型对所有专利点的护城河六维打分"
            >
              <RefreshCw size={16} className={busy === "patent-point-evaluate-moat" ? "animate-spin" : ""} />
              <span>{busy === "patent-point-evaluate-moat" ? "评测中…" : "评测全部"}</span>
            </button>
          </div>
          <div className="flex flex-col gap-3">
            {points.map((point) => {
              const total = moatScoreTotal(point.moat_scores);
              return (
                <article className={point.selected ? "flex flex-col gap-2 p-4 bg-[var(--brand-teal-500)]/5 border border-[var(--brand-teal-500)]/30 rounded-lg shadow-sm ring-1 ring-[var(--brand-teal-500)]/20" : "flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm"} key={point.id}>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                    <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-primary)]">{evidenceStatusLabel(point.evidence_status)}</span>
                    <span className="px-2.5 py-0.5 rounded-md bg-[var(--surface-subtle)] border border-[var(--border-subtle)] text-[var(--text-primary)]/60">{sourceTypeLabel(point.source_type)}</span>
                    <span>{Math.round(total * 100)} 分</span>
                  </div>
                  <p><strong>{point.title}</strong></p>
                  <p>{point.innovation || point.technical_solution}</p>
                  <p className={point.support_gaps.length > 0 ? "text-sm text-[var(--text-primary)]/70 bg-[var(--surface-subtle)] px-4 py-3 rounded-lg border border-[var(--border-subtle)] flex items-center gap-2" : "text-sm text-[var(--text-primary)]/50 italic py-4"}>
                    {point.support_gaps.length > 0 ? `支撑缺口：${point.support_gaps.join("；")}` : "支撑材料暂未标记缺口。"}
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <StatusPill label="范围" value={percent(point.moat_scores.scope_width)} />
                    <StatusPill label="绕开难度" value={percent(point.moat_scores.designaround_difficulty)} />
                    <StatusPill label="可行性" value={percent(point.moat_scores.feasibility)} />
                    <StatusPill label="支撑" value={percent(point.moat_scores.support_strength)} />
                    <StatusPill label="现有技术距离" value={percent(point.moat_scores.prior_art_distance)} />
                    <StatusPill label="战略价值" value={percent(point.moat_scores.strategic_value)} />
                  </div>
                  {point.moat_rationale && (
                    <details className="text-xs text-[var(--text-primary)]/70 bg-[var(--surface-base)] px-3 py-2 rounded-lg border border-[var(--border-subtle)]">
                      <summary className="cursor-pointer select-none font-medium">评测依据</summary>
                      <p className="mt-2 whitespace-pre-wrap leading-relaxed">{point.moat_rationale}</p>
                    </details>
                  )}
                  {point.claim_chart.length > 0 && (
                    <div className="flex flex-col gap-2 mt-2 p-3 bg-[var(--surface-base)] rounded-lg text-sm border border-[var(--border-subtle)]">
                      {point.claim_chart.slice(0, 2).map((item) => (
                        <p key={item.prior_art_id}>
                          <strong>{item.prior_art_title}</strong>：{item.claim_drafting_advice}
                        </p>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-3">
                    <button
                      className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors text-sm"
                      disabled={!project || busy === "patent-point-select" || point.selected}
                      onClick={() => void onSelect(point)}
                      type="button"
                      title="设为选中"
                    >
                      <ShieldCheck size={16} />
                      <span>{point.selected ? "已选中" : "选中"}</span>
                    </button>
                    <button
                      className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors text-sm"
                      disabled={!project || busy === "patent-point-delete"}
                      onClick={() => void onDelete(point)}
                      type="button"
                      title="删除"
                    >
                      <Trash2 size={17} />
                      <span>删除</span>
                    </button>
                  </div>
                </article>
              );
            })}
            {points.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无用户指定专利点。</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

export function DeliberationView({
  project,
  doctor,
  runs,
  disclosure,
  selectedProviders,
  busy,
  onStart,
  onToggleProvider,
  onRefresh,
  onCancelRun,
  onRetryRun,
}: {
  project: ProjectRecord | null;
  doctor: AgentDoctorReport | null;
  runs: DeliberationRun[];
  disclosure: DisclosureRun | null;
  selectedProviders: string[];
  busy: string;
  onStart: (trace?: boolean) => void;
  onToggleProvider: (providerId: string, enabled: boolean) => void;
  onRefresh: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
}) {
  const latest = runs[0] ?? null;
  const completed = latestCompletedDeliberation(runs);
  const activeRun = latestActiveRun(runs);
  const deliberationBusy = busy === "deliberate" || Boolean(activeRun);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>多智能体会审</h3>
          <p>
            {project
              ? "会审会调用本机 Codex、DeepSeek、Claude，先讨论保护范围和写作策略，再注入生成流程。"
              : "先创建项目后再启动会审。"}
          </p>
          <p>{disclosure ? "将默认结合前置交底书。" : "暂无已完成交底书，会审仅基于草稿和检索片段。"}</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors" onClick={onRefresh} type="button" title="刷新会审">
            <RefreshCw size={17} />
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all"
            disabled={!project || deliberationBusy}
            onClick={() => onStart(false)}
            type="button"
          >
            <UsersRound size={18} />
            <span>{activeRun ? "会审中" : "启动会审"}</span>
          </button>
        </div>
      </section>
      <RuntimeRunConsole run={activeRun} title="多智能体会审运行中" actionDisabled={Boolean(busy)} onCancel={onCancelRun} />

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>智能体诊断</h3>
          <div className="doctor-grid">
            <StatusPill label="状态" value={agentDoctorStatusLabel(doctor?.status ?? "unknown")} />
            <StatusPill label="运行级别" value={agentRunModeLabel(doctor?.run_mode ?? "unknown")} />
          </div>
          <AgentProviderCards
            doctor={doctor}
            role="deliberation"
            selectedProviders={selectedProviders}
            disabled={deliberationBusy}
            onToggleProvider={onToggleProvider}
          />
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>会审记录</h3>
          <div className="flex flex-col gap-3">
            {runs.map((run) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={run.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span>{pipelineRunStatusLabel(run.status)}</span>
                  <span>{deliberationRunModeLabel(run.run_mode)}</span>
                  {run.runtime_state && <span>{runtimeStageLabel(run.runtime_state.current_stage)}</span>}
                  {run.retry_of && <span>重试 {run.retry_of.slice(0, 8)}</span>}
                </div>
                <p>{run.providers.join(" / ")}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span>{run.stage_results.length} 阶段</span>
                  <span>{run.failures.length} 失败</span>
                  <span>{run.logs.length} 日志</span>
                </div>
                <RuntimeFailurePanel run={run} />
                <RuntimeRunActions run={run} disabled={Boolean(busy)} onCancel={onCancelRun} onRetry={onRetryRun} />
                {run.failures.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {run.failures.map((failure) => (
                      <article className="flex items-start gap-3 p-4 bg-[var(--surface-inset)] border border-app-danger/35 rounded-lg" key={`${run.id}-${failure.phase}-${failure.provider_id}`}>
                        <span>{failure.phase}</span>
                        <div>
                          <strong>{failure.provider_id} / {failure.reason}</strong>
                          <p>{failure.message}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
                {run.logs.length > 0 && (
                  <div className="flex flex-col gap-2 font-mono text-xs mt-3 bg-[var(--surface-subtle)] p-4 rounded-lg border border-[var(--border-subtle)]">
                    {run.logs.slice(-6).map((log, index) => (
                      <article className={`log-row ${log.level}`} key={`${run.id}-log-${index}`}>
                        <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                          <span>{logLevelLabel(log.level)}</span>
                          <span>{log.phase || "阶段"}</span>
                          <span>{log.provider_id || "系统"}</span>
                          {log.attempt != null && <span>第 {log.attempt} 次尝试</span>}
                        </div>
                        <p>{log.message}</p>
                        {log.detail && <p>{log.detail}</p>}
                        {log.repair_suggestion && <p><strong>修复建议：</strong>{log.repair_suggestion}</p>}
                      </article>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {runs.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无会审记录</p>}
          </div>
        </div>
      </section>

      <StrategyBriefView
        title={completed ? "可注入会审策略" : latest ? "最近会审尚未完成" : "会审策略"}
        strategy={completed?.strategy_brief ?? null}
      />
    </div>
  );
}

export function DisclosureView({
  project,
  materials,
  runs,
  busy,
  onUpload,
  onStart,
  onRefresh,
  onCancelRun,
  onRetryRun,
}: {
  project: ProjectRecord | null;
  materials: ProjectMaterial[];
  runs: DisclosureRun[];
  busy: string;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onStart: (trace?: boolean) => void;
  onRefresh: () => void;
  onCancelRun: (runId: string) => void;
  onRetryRun: (runId: string) => void;
}) {
  const latest = runs[0] ?? null;
  const completed = latestCompletedDisclosure(runs);
  const activeRun = latestActiveRun(runs);
  const disclosureBusy = busy === "disclosure" || Boolean(activeRun);
  return (
    <div className="flex flex-col gap-4">
      <section className="flex items-center justify-between gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
        <div>
          <h3>前置材料生成</h3>
          <p>
            {project
              ? "从 draft 和补充材料挖掘专利点，检索公开现有技术，并生成可交给代理人的技术交底书。"
              : "先创建项目后再上传材料。"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--surface-subtle)] hover:bg-[var(--surface-raised)] text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] disabled:opacity-50 transition-colors" onClick={onRefresh} type="button" title="刷新前置材料">
            <RefreshCw size={17} />
          </button>
          <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || disclosureBusy} onClick={() => onStart(false)} type="button">
            <ClipboardList size={18} />
            <span>{activeRun ? "生成中" : "生成交底书"}</span>
          </button>
        </div>
      </section>
      <RuntimeRunConsole run={activeRun} title="交底书生成运行中" actionDisabled={Boolean(busy)} onCancel={onCancelRun} />

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>补充材料</h3>
          <form className="flex flex-col gap-4 p-4 border-2 border-dashed border-[var(--border-subtle)] rounded-lg bg-[var(--surface-inset)]" onSubmit={onUpload}>
            <input
              id="project-material-file"
              name="project-material-file"
              type="file"
              accept=".pdf,.docx,.pptx,.ppsx,.txt,.md,.markdown"
              disabled={!project}
            />
            <button className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-br from-[var(--action-primary)] to-[color-mix(in_oklch,var(--action-primary),black_30%)] text-[var(--action-primary-contrast)] font-medium hover:brightness-110 disabled:opacity-50 disabled:grayscale transition-all" disabled={!project || busy === "material-upload"} type="submit">
              <Upload size={17} />
              <span>上传材料</span>
            </button>
          </form>
          <div className="flex flex-col gap-3">
            {materials.map((material) => (
              <article className="flex gap-3 items-start p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={material.id}>
                {material.status === "processed" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                <div>
                  <strong>{material.file_name}</strong>
                  <span>{material.status === "processed" ? `${material.file_type} / ${material.text.length} 字` : material.warnings.join("；")}</span>
                </div>
              </article>
            ))}
            {materials.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">未上传补充材料时，系统会仅基于 draft 生成。</p>}
          </div>
        </div>

        <div className="grid gap-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-subtle)] p-6 shadow-xl backdrop-blur-xl">
          <h3>生成记录</h3>
          <div className="flex flex-col gap-3">
            {runs.map((run) => (
              <article className="flex flex-col gap-2 p-4 bg-[var(--surface-subtle)] border border-[var(--border-subtle)] rounded-lg shadow-sm" key={run.id}>
                <div className="flex items-center gap-3 text-xs text-[var(--text-primary)]/60 font-medium mb-1">
                  <span>{pipelineRunStatusLabel(run.status)}</span>
                  <span>{run.package?.prior_art_hits.length ?? 0} 条现有技术</span>
                  {run.runtime_state && <span>{runtimeStageLabel(run.runtime_state.current_stage)}</span>}
                  {run.retry_of && <span>重试 {run.retry_of.slice(0, 8)}</span>}
                </div>
                <p>{run.package?.title ?? run.events.at(-1) ?? "等待生成"}</p>
                <p>{run.events.at(-1) ?? "暂无事件"}</p>
                <RuntimeFailurePanel run={run} />
                <RuntimeRunActions run={run} disabled={Boolean(busy)} onCancel={onCancelRun} onRetry={onRetryRun} />
              </article>
            ))}
            {runs.length === 0 && <p className="text-sm text-[var(--text-primary)]/50 italic py-4">暂无交底书生成记录。</p>}
          </div>
        </div>
      </section>

      <DisclosurePreview project={project} run={completed ?? latest} />
    </div>
  );
}
