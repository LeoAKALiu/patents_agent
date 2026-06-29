import type { ReactNode } from "react";
import {
  ArrowRight,
  AlertTriangle,
  BookOpen,
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
  return (
    <section className="workbench-workspace" aria-labelledby="workbench-title">
      <section className="workbench-section workbench-current">
        <div>
          <p className="section-eyebrow">当前项目</p>
          <h2 id="workbench-title">工作台</h2>
          <p>{state.hasProject ? state.projectName : "先选择起步路径，创建当前项目。"}</p>
        </div>
        <span className={state.hasProject ? "workbench-project-chip" : "workbench-project-chip muted"}>
          {state.projectName}
        </span>
      </section>

      <section className="workbench-section workbench-next" aria-labelledby="workbench-next-title">
        <div className="workbench-section-heading">
          <div>
            <p className="section-eyebrow">下一步</p>
            <h3 id="workbench-next-title">{state.nextAction.label}</h3>
          </div>
          <Button
            type="button"
            onClick={() => runPrimaryAction(state, handlers, onNavigate)}
            disabled={isPrimaryActionDisabled(state)}
          >
            {primaryButtonLabel(state)}
            <ArrowRight size={16} aria-hidden="true" />
          </Button>
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
        {!state.hasProject && (
          <div className="workbench-start-grid" aria-label="起步路径">
            {v1StartChoices.map((choice) => (
              <button
                type="button"
                className="workbench-start-card"
                key={choice.id}
                onClick={() => handlers.onStartChoice(choice.id)}
              >
                <span>{choice.label}</span>
                <small>{choice.description}</small>
              </button>
            ))}
          </div>
        )}
        {startWorkspace && <div className="workbench-start-detail">{startWorkspace}</div>}
        {state.hasProject && (
          <div className="workbench-secondary-links" aria-label="常用工作区">
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
        )}
      </section>

      <section className="workbench-section" aria-labelledby="workbench-progress-title">
        <p className="section-eyebrow">流程进度</p>
        <h3 id="workbench-progress-title">流程进度</h3>
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
    </section>
  );
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
