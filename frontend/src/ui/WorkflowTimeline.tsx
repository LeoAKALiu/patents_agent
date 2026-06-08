import { CheckCircle2, Lock, AlertTriangle, Circle } from "lucide-react";
import type { GuidedStepState } from "../guidedFlow";

function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

type WorkflowTimelineProps = {
  steps: GuidedStepState[];
  currentStepId: string;
  onStepClick?: (stepId: string) => void;
};

export function WorkflowTimeline({ steps, currentStepId, onStepClick }: WorkflowTimelineProps) {
  return (
    <nav className="flex flex-col gap-1 px-3 py-4">
      <div className="px-3 mb-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
          Workflow
        </span>
      </div>
      {steps.map((step, idx) => {
        const isCurrent = step.id === currentStepId;
        const isDone = step.status === "done";
        const isLocked = step.status === "locked";

        return (
          <button
            key={step.id}
            onClick={() => onStepClick?.(step.id)}
            disabled={isLocked}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors w-full",
              "border-l-2",
              isCurrent && "border-teal-400 bg-teal-400/8 text-teal-300",
              isDone && !isCurrent && "border-emerald-500/60 bg-transparent text-slate-400",
              isLocked && "border-slate-700 text-slate-600 cursor-not-allowed",
              !isCurrent && !isDone && !isLocked && "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-300",
            )}
          >
            <span className="flex-shrink-0">
              {isDone ? (
                <CheckCircle2 size={16} className="text-emerald-400" />
              ) : isLocked ? (
                <Lock size={14} className="text-slate-600" />
              ) : isCurrent ? (
                <span className="block w-2.5 h-2.5 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.5)]" />
              ) : (
                <Circle size={14} className="text-slate-600" />
              )}
            </span>
            <div className="min-w-0">
              <div className={cn(
                "text-xs font-medium truncate",
                isCurrent && "text-teal-200",
                isDone && "text-slate-400",
              )}>
                {step.label}
              </div>
              <div className={cn(
                "text-[10px] leading-tight truncate mt-0.5",
                isCurrent ? "text-teal-400/70" : "text-slate-500",
              )}>
                {step.description}
              </div>
            </div>
          </button>
        );
      })}
    </nav>
  );
}
