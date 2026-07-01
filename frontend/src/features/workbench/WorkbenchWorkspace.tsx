import { useState, type ReactNode } from "react";
import {
  ArrowRight,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  CircleDot,
  FileText,
  Gauge,
  Play,
  ShieldAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ProjectWorkspaceHandlers } from "@/features/projects/ProjectWorkspace";
import {
  guidedStepStatusLabel,
  v1StartChoices,
  type GuidedStepId,
  type StartChoiceId,
} from "@/guidedFlow";

import type { WorkbenchPrimaryTarget, WorkbenchState } from "./selectors";

export interface WorkbenchWorkspaceProps {
  state: WorkbenchState;
  handlers: ProjectWorkspaceHandlers;
  onNavigate: (target: WorkbenchPrimaryTarget) => void;
  startWorkspace?: ReactNode;
}

export function WorkbenchWorkspace({
  state,
  handlers,
  onNavigate,
  startWorkspace,
}: WorkbenchWorkspaceProps) {
  const [otherActionsOpen, setOtherActionsOpen] = useState(false);
  const completedPhaseCount = state.phaseGroups.filter((phase) => phase.status === "done").length;
  const currentPhase = state.phaseGroups.find((phase) => phase.status === "current")?.label ?? "待启动";
  const evidenceSatisfiedCount = state.hasProject ? Math.max(0, 4 - Math.min(state.riskSummary.issueCount, 4)) : 0;

  return (
    <section className="workbench-workspace" aria-labelledby="workbench-title">
      <div className="workbench-grid">
        <div className="workbench-left-stack">
          <section className="workbench-section workbench-mission" aria-labelledby="workbench-title">
            <div className="workbench-mission-copy">
              <p className="section-eyebrow">GrantAtlas / 权衡 · 工作台</p>
              <h2 id="workbench-title">工作台</h2>
              <p className="workbench-mission-line">
                {state.hasProject
                  ? "围绕当前项目推进生成、复核、修复和导出，把风险与证据保持在同一个可操作视图里。"
                  : "从一个明确入口开始，把技术想法、结构方案或既有稿件推进到可复核专利文稿。"}
              </p>
              <p>
                {state.hasProject
                  ? state.nextAction.description
                  : "当前没有选中项目。工作台仍保留可执行入口、流程状态和诊断队列，避免首屏只剩空白或红色告警。"}
              </p>
              {state.hasProject && (
                <div className="workbench-mission-actions">
                  <Button
                    type="button"
                    onClick={() => runPrimaryAction(state, handlers, onNavigate)}
                    disabled={isPrimaryActionDisabled(state)}
                  >
                    继续当前项目
                    <ArrowRight size={16} aria-hidden="true" />
                  </Button>
                </div>
              )}
            </div>
            <div className="workbench-mission-stats" aria-label="当前工作台摘要">
              <MissionStat
                label="当前项目"
                value={state.hasProject ? state.projectName : "—"}
                hint={state.hasProject ? "已选项目" : "等待创建或选择"}
              />
              <MissionStat
                label="工作流"
                value={`${completedPhaseCount}/${state.phaseGroups.length}`}
                hint={state.hasProject ? `当前：${currentPhase}` : "尚未启动"}
              />
              <MissionStat
                label="证据"
                value={`${evidenceSatisfiedCount}/4`}
                hint={state.hasProject ? "随复核结果更新" : "创建后展开"}
              />
              <MissionStat
                label="运行"
                value={state.runSummary.label}
                hint={state.runSummary.busy ? "后台任务执行中" : "可继续配置"}
              />
            </div>
          </section>

          <section className="workbench-section" aria-labelledby="workbench-state-title">
            <PanelHeading
              eyebrow="状态覆盖"
              title="状态覆盖"
              id="workbench-state-title"
              action={<span className="workbench-chip">当前无页面阻塞</span>}
            >
              空项目、后台加载和错误降级都保留可解释状态，不让首屏被空白或告警占满。
            </PanelHeading>
            <div className="workbench-state-band" aria-label="空、加载与错误状态">
              <StateCard
                tone="info"
                title="空项目"
                description="未选择项目时仍提供三条起步路径、证据需求和流程预览。"
              />
              <StateCard
                tone="neutral"
                title="加载队列"
                description={state.runSummary.busy ? "后台任务正在执行，主工作台仍保留当前上下文。" : "后台任务为空，创建项目后显示生成、解析和导出进度。"}
              />
              <StateCard
                tone="warn"
                title="错误降级"
                description="健康检查或门禁失败进入诊断队列，不覆盖主要工作流。"
              />
            </div>
          </section>

          <section className="workbench-section" aria-labelledby="workbench-start-title">
            <PanelHeading
              eyebrow="起步路径"
              title="选择起步方式"
              id="workbench-start-title"
              action={<span className="workbench-chip is-info">推荐先创建项目</span>}
            >
              三个入口使用同一条引导流程，但预设项目类型、材料要求和复核节奏不同。
            </PanelHeading>
            <div className="workbench-start-grid" aria-label="起步路径">
              {v1StartChoices.map((choice) => (
                <StartPathCard
                  key={choice.id}
                  choice={choice}
                  selected={!state.hasProject && choice.id === "invention"}
                  onSelect={() => handlers.onStartChoice(choice.id)}
                />
              ))}
            </div>
            {startWorkspace && <div className="workbench-start-detail">{startWorkspace}</div>}
          </section>

          <section className="workbench-section workbench-next" aria-labelledby="workbench-next-title">
            <div className="workbench-section-heading">
              <div>
                <p className="section-eyebrow">下一步</p>
                <h3 id="workbench-next-title">{state.nextAction.label}</h3>
              </div>
              {state.hasProject && (
                <Button
                  type="button"
                  onClick={() => runPrimaryAction(state, handlers, onNavigate)}
                  disabled={isPrimaryActionDisabled(state)}
                >
                  {primaryButtonLabel(state)}
                  <ArrowRight size={16} aria-hidden="true" />
                </Button>
              )}
            </div>
            <p>{state.nextAction.description}</p>
            {state.primaryActionBlockReason && (
              <div className="callout callout-warn" role="status">
                <AlertTriangle size={17} aria-hidden="true" />
                <div>
                  <strong>暂不能启动</strong>
                  <p>{state.primaryActionBlockReason}</p>
                </div>
              </div>
            )}
            {state.hasProject && (
              <details
                className="workbench-other-actions"
                onToggle={(event) => setOtherActionsOpen((event.currentTarget as HTMLDetailsElement).open)}
              >
                <summary>
                  <span>其他操作</span>
                  <ArrowRight size={14} aria-hidden="true" />
                </summary>
                <div
                  className="workbench-secondary-links"
                  aria-label="常用工作区"
                  hidden={!otherActionsOpen}
                >
                  <button type="button" onClick={() => onNavigate("documents")}>
                    <FileText size={15} aria-hidden="true" />
                    <span>文稿与修复</span>
                  </button>
                  <button type="button" onClick={() => onNavigate("knowledge")}>
                    <BookOpen size={15} aria-hidden="true" />
                    <span>知识库</span>
                  </button>
                  <button type="button" onClick={() => onNavigate("expert")}>
                    <Gauge size={15} aria-hidden="true" />
                    <span>专家工具</span>
                  </button>
                </div>
              </details>
            )}
          </section>

          <section className="workbench-section" aria-labelledby="workbench-progress-title">
            <PanelHeading
              eyebrow="流程进度"
              title="流程进度"
              id="workbench-progress-title"
              action={<span className="workbench-chip">{state.hasProject ? currentPhase : "待项目"}</span>}
            >
              步骤呈现为可进入的工作流节点，帮助你判断下一步应该配置、生成、复核还是导出。
            </PanelHeading>
            <ol className="workbench-phase-rail" aria-label="用户流程阶段">
              {state.phaseGroups.map((phase, index) => (
                <li className={`workbench-phase is-${phase.status}`} key={phase.label}>
                  <span className="workbench-phase-node">{index + 1}</span>
                  <span>{phase.label}</span>
                  <small>{phase.status === "done" ? "已完成" : phase.status === "current" ? "当前阶段" : "未解锁"}</small>
                </li>
              ))}
            </ol>
            <div className="workbench-progress-groups">
              {state.stepGroups.map((group) => (
                <div className="workbench-progress-group" key={group.label}>
                  <h4>{group.label}</h4>
                  <ol>
                    {group.steps.map((step) => (
                      <li
                        className={`workbench-step is-${step.status}`}
                        key={step.id}
                        aria-current={step.id === state.currentStepId ? "step" : undefined}
                      >
                        <span>{step.label}</span>
                        <small>{guidedStepStatusLabel(step.status)}</small>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </section>

          <section className="workbench-section" aria-labelledby="workbench-risk-title">
            <div className="workbench-section-heading">
              <div>
                <p className="section-eyebrow">风险与运行</p>
                <h3 id="workbench-risk-title">风险与运行</h3>
              </div>
              {state.riskSummary.exportLocked && <ShieldAlert size={18} aria-hidden="true" />}
            </div>
            <div className="workbench-status-grid">
              <StatusMetric label="阻断项" value={`${state.riskSummary.blockingCount} 项`} />
              <StatusMetric label="风险项" value={`${state.riskSummary.issueCount} 项`} />
              <StatusMetric label="导出状态" value={exportStateLabel(state)} />
              <StatusMetric
                label="运行状态"
                value={state.runSummary.label}
                icon={state.runSummary.busy ? <Play size={14} aria-hidden="true" /> : undefined}
              />
            </div>
          </section>

          <section className="workbench-section" aria-labelledby="workbench-queue-title">
            <PanelHeading
              eyebrow="工作队列"
              title="项目与工作队列"
              id="workbench-queue-title"
              action={<span className="workbench-chip">{state.hasProject ? "项目已选" : "0 个项目"}</span>}
            >
              空状态不留白，展示下一批可执行任务和等待数据。
            </PanelHeading>
            <div className="workbench-queue-grid">
              <div className="workbench-table" role="table" aria-label="项目队列">
                <div className="workbench-table-head" role="row">
                  <span role="columnheader">任务</span>
                  <span role="columnheader">阶段</span>
                  <span role="columnheader">状态</span>
                  <span role="columnheader">操作</span>
                </div>
                <QueueRow
                  task={state.hasProject ? state.nextAction.label : "创建第一个发明专利项目"}
                  stage={state.hasProject ? currentPhase : "入口配置"}
                  status={state.hasProject ? state.runSummary.label : "可执行"}
                  tone={state.primaryActionBlockReason ? "attention" : "ready"}
                  actionLabel={state.hasProject ? "继续" : "新建"}
                  disabled={state.hasProject && isPrimaryActionDisabled(state)}
                  onAction={() => state.hasProject
                    ? runPrimaryAction(state, handlers, onNavigate)
                    : handlers.onStartChoice("invention")}
                />
                <QueueRow
                  task={state.hasProject ? "补充或管理项目材料" : "导入技术交底书 / 原始稿件"}
                  stage="知识库"
                  status={state.hasProject ? "可维护" : "可上传"}
                  tone="ready"
                  actionLabel={state.hasProject ? "管理" : "导入"}
                  onAction={() => state.hasProject ? onNavigate("knowledge") : handlers.onStartChoice("external")}
                />
                <QueueRow
                  task="检查本机后端服务连接"
                  stage="系统"
                  status="诊断项"
                  tone="attention"
                  actionLabel="查看"
                  onAction={() => onNavigate("expert")}
                />
                <QueueRow
                  task="准备专业复核清单"
                  stage="导出前"
                  status={state.riskSummary.exportReady ? "就绪" : "待项目"}
                  tone={state.riskSummary.exportReady ? "ready" : "neutral"}
                  actionLabel="专家"
                  onAction={() => onNavigate("expert")}
                />
              </div>
              <div className="workbench-kpi-column" aria-label="运行摘要">
                <MiniKpi label="运行任务" value={state.runSummary.busy ? "1" : "0"} />
                <MiniKpi label="待确认补丁" value={state.riskSummary.blockingCount ? String(state.riskSummary.blockingCount) : "—"} />
                <MiniKpi label="导出就绪" value={state.riskSummary.exportReady ? "是" : "否"} />
              </div>
            </div>
          </section>
        </div>

        <aside className="workbench-right-stack" aria-label="运营与证据面板">
          <section className="workbench-section workbench-evidence-panel">
            <section className="workbench-right-section" aria-labelledby="workbench-review-title">
              <div className="workbench-right-title">
                <h3 id="workbench-review-title">复核摘要</h3>
                <span className="workbench-chip is-info">{state.hasProject ? currentPhase : "空项目"}</span>
              </div>
              <div className="workbench-review-card">
                <strong>{state.hasProject ? state.nextAction.label : "下一步需要建立项目卡"}</strong>
                <span>
                  {state.hasProject
                    ? state.nextAction.description
                    : "选择入口后先确认专利类型、技术主题和材料来源，证据队列会随项目自动展开。"}
                </span>
              </div>
            </section>

            <section className="workbench-right-section" aria-labelledby="workbench-evidence-title">
              <div className="workbench-right-title">
                <h3 id="workbench-evidence-title">证据矩阵</h3>
                <span className="workbench-chip">{evidenceSatisfiedCount}/4 已满足</span>
              </div>
              <div className="workbench-evidence-matrix">
                <EvidenceRow title="技术问题" detail="问题、现有方案缺陷与改进目标" status="必需" tone="info" />
                <EvidenceRow title="技术方案" detail="关键步骤、结构关系或系统模块" status="必需" tone="info" />
                <EvidenceRow
                  title="技术效果"
                  detail="需与方案逐项对应"
                  status={state.riskSummary.issueCount > 0 ? "待补" : "就绪"}
                  tone={state.riskSummary.issueCount > 0 ? "warn" : "success"}
                />
                <EvidenceRow
                  title="复核规则"
                  detail={state.hasProject ? "已绑定当前流程模板" : "创建项目后自动绑定模板"}
                  status="就绪"
                  tone="success"
                />
              </div>
            </section>

            <section className="workbench-right-section" aria-labelledby="workbench-preview-title">
              <div className="workbench-right-title">
                <h3 id="workbench-preview-title">文稿预览</h3>
                <span className="workbench-chip is-brand">{state.hasProject ? "当前草稿" : "空白模板"}</span>
              </div>
              <div className="workbench-document-preview" aria-label="文档预览占位">
                <div className="workbench-doc-page-title">
                  <span>说明书摘要</span>
                  <span>{state.riskSummary.exportReady ? "可导出" : "等待生成"}</span>
                </div>
                <div className="workbench-doc-rule">
                  <div className="workbench-doc-line is-brand" />
                  <div className="workbench-doc-line" />
                </div>
                <div className="workbench-doc-rule">
                  <div className="workbench-doc-line" />
                  <div className="workbench-doc-line is-short" />
                </div>
                <div className="workbench-doc-note">
                  <span>权利要求 / 说明书</span>
                  <strong>{state.hasProject ? exportStateLabel(state) : "等待生成"}</strong>
                </div>
              </div>
            </section>

            <section className="workbench-right-section" aria-labelledby="workbench-diagnostics-title">
              <div className="workbench-right-title">
                <h3 id="workbench-diagnostics-title">诊断队列</h3>
                <span className="workbench-chip">系统</span>
              </div>
              <div className="workbench-evidence-list">
                <div className="workbench-alert-line">
                  <AlertTriangle size={16} aria-hidden="true" />
                  <div>
                    <strong>后端诊断</strong>
                    <span>健康检查异常会保留为诊断项，不抢占主任务。</span>
                  </div>
                </div>
                <div className="workbench-evidence-item">
                  <CheckCircle2 size={15} aria-hidden="true" />
                  <div>
                    <strong>界面外壳</strong>
                    <span>工作台已加载，本机可继续配置。</span>
                  </div>
                  <span>就绪</span>
                </div>
              </div>
            </section>
          </section>
        </aside>
      </div>
    </section>
  );
}

function PanelHeading({
  eyebrow,
  title,
  id,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  id: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="workbench-section-heading">
      <div>
        <p className="section-eyebrow">{eyebrow}</p>
        <h3 id={id}>{title}</h3>
        <p>{children}</p>
      </div>
      {action}
    </div>
  );
}

function MissionStat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="workbench-mission-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      <em>{hint}</em>
    </div>
  );
}

function StateCard({
  tone,
  title,
  description,
}: {
  tone: "info" | "neutral" | "warn";
  title: string;
  description: string;
}) {
  return (
    <div className={`workbench-state-card is-${tone}`}>
      <strong>
        <WorkbenchDot tone={tone} />
        {title}
      </strong>
      <span>{description}</span>
    </div>
  );
}

const startChoiceMeta: Record<StartChoiceId, {
  index: string;
  badge: string;
  next: string;
  requirement: string;
  footnote: string;
  action: string;
  tone: "info" | "brand" | "neutral";
}> = {
  invention: {
    index: "01",
    badge: "发明专利",
    next: "想法录入 → 发明点确认",
    requirement: "技术问题、方案、效果",
    footnote: "预设 7 个字段",
    action: "进入配置",
    tone: "info",
  },
  utility: {
    index: "02",
    badge: "实用新型",
    next: "结构清单 → 附图要素",
    requirement: "部件、连接关系、结构效果",
    footnote: "预设 5 个字段",
    action: "进入配置",
    tone: "brand",
  },
  external: {
    index: "03",
    badge: "已有稿件",
    next: "章节解析 → 修复建议",
    requirement: "docx / md 初稿",
    footnote: "支持 docx / md",
    action: "选择文件",
    tone: "neutral",
  },
};

function StartPathCard({
  choice,
  selected,
  onSelect,
}: {
  choice: (typeof v1StartChoices)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  const meta = startChoiceMeta[choice.id];
  return (
    <button
      type="button"
      className={`workbench-start-card is-${meta.tone} ${selected ? "is-selected" : ""}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <span className="workbench-start-topline">
        <span className="workbench-path-index">{meta.index}</span>
        <span className={`workbench-chip is-${meta.tone}`}>{meta.badge}</span>
      </span>
      <span className="workbench-start-title">{choice.label}</span>
      <small>{choice.description}</small>
      <span className="workbench-start-meta">
        <span><strong>后续</strong> {meta.next}</span>
        <span><strong>需要</strong> {meta.requirement}</span>
      </span>
      <span className="workbench-start-action">
        <span>{meta.footnote}</span>
        <strong>{meta.action}</strong>
      </span>
    </button>
  );
}

function QueueRow({
  task,
  stage,
  status,
  tone,
  actionLabel,
  disabled,
  onAction,
}: {
  task: string;
  stage: string;
  status: string;
  tone: "ready" | "attention" | "neutral";
  actionLabel: string;
  disabled?: boolean;
  onAction: () => void;
}) {
  return (
    <div className="workbench-table-row" role="row">
      <strong role="cell">{task}</strong>
      <span role="cell">{stage}</span>
      <span className={`workbench-state-pill is-${tone}`} role="cell">{status}</span>
      <span className="workbench-action-cell" role="cell">
        <button className="workbench-row-action" type="button" disabled={disabled} onClick={onAction}>
          {actionLabel}
        </button>
      </span>
    </div>
  );
}

function MiniKpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="workbench-mini-kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EvidenceRow({
  title,
  detail,
  status,
  tone,
}: {
  title: string;
  detail: string;
  status: string;
  tone: "info" | "warn" | "success";
}) {
  return (
    <div className="workbench-evidence-row">
      <WorkbenchDot tone={tone} />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
      <span>{status}</span>
    </div>
  );
}

function WorkbenchDot({ tone }: { tone: "info" | "neutral" | "warn" | "success" }) {
  if (tone === "success") return <CheckCircle2 size={15} aria-hidden="true" />;
  if (tone === "warn") return <AlertTriangle size={15} aria-hidden="true" />;
  if (tone === "info") return <CircleDot size={15} aria-hidden="true" />;
  return <CircleDot size={15} aria-hidden="true" />;
}

function StatusMetric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
}) {
  return (
    <div className="workbench-status-metric">
      <span>{label}</span>
      <strong>
        {icon}
        {value}
      </strong>
    </div>
  );
}

function primaryButtonLabel(state: WorkbenchState): string {
  if (state.primaryTarget === "documents") return "进入文稿与修复";
  if (state.primaryTarget === "export") return "导出正式稿";
  if (state.primaryTarget === "knowledge") return "进入知识库";
  if (state.primaryTarget === "expert") return "进入专家工具";
  return state.nextAction.label;
}

function exportStateLabel(state: WorkbenchState): string {
  if (state.riskSummary.exportReady) return "可导出";
  if (state.riskSummary.exportLocked) return "导出锁定";
  return "等待生成";
}

function isPrimaryActionDisabled(state: WorkbenchState): boolean {
  if (state.primaryActionBlockReason) return true;
  return state.runSummary.busy && state.primaryTarget === "workbench-start";
}

function runPrimaryAction(
  state: WorkbenchState,
  handlers: ProjectWorkspaceHandlers,
  onNavigate: (target: WorkbenchPrimaryTarget) => void,
) {
  if (isPrimaryActionDisabled(state)) {
    return;
  }
  if (state.primaryTarget !== "workbench-start") {
    onNavigate(state.primaryTarget);
    return;
  }
  if (!state.hasProject) {
    handlers.onStartChoice("invention");
    return;
  }
  runGuidedStepAction(state.currentStepId, handlers, onNavigate);
}

function runGuidedStepAction(
  stepId: GuidedStepId,
  handlers: ProjectWorkspaceHandlers,
  onNavigate: (target: WorkbenchPrimaryTarget) => void,
) {
  if (stepId === "invention") {
    handlers.onStartDisclosure();
  } else if (stepId === "deliberation") {
    handlers.onStartDeliberation();
  } else if (stepId === "formula") {
    handlers.onStartFormula();
  } else if (stepId === "draft") {
    handlers.onGenerateDraft();
  } else if (stepId === "quality") {
    handlers.onRunQualityChecks();
  } else if (stepId === "officialCompile") {
    handlers.onStartOfficialCompile();
  } else if (stepId === "postReview") {
    handlers.onStartPostDraftReview();
  } else if (stepId === "export") {
    onNavigate("export");
  }
}
