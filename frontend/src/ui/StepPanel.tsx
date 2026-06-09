import { cn } from "./cn";

type StepPanelProps = {
  stepNumber: number;
  totalSteps: number;
  title: string;
  description?: string;
  status?: "done" | "current" | "ready" | "locked" | "warning";
  riskBanner?: { message: string; variant: "warning" | "error" | "info" } | null;
  children: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
};

const statusBorder: Record<string, string> = {
  current: "border-teal-500/30",
  done: "border-emerald-500/20",
  locked: "border-slate-700/30 opacity-50",
  warning: "border-yellow-500/20",
};

const riskStyles: Record<string, string> = {
  warning: "bg-yellow-500/5 border-yellow-500/20 text-yellow-300",
  error: "bg-red-500/5 border-red-500/20 text-red-300",
  info: "bg-teal-500/5 border-teal-500/20 text-teal-300",
};

export function StepPanel({
  stepNumber,
  totalSteps,
  title,
  description,
  status = "current",
  riskBanner,
  children,
  actions,
  className,
}: StepPanelProps) {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
            Step {stepNumber} of {totalSteps}
          </span>
          {status === "done" && (
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Complete</span>
          )}
        </div>
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        {description && (
          <p className="text-sm text-slate-400">{description}</p>
        )}
      </div>

      {/* Risk Banner */}
      {riskBanner && (
        <div
          className={cn(
            "px-3 py-2 rounded-md border text-xs leading-relaxed",
            riskStyles[riskBanner.variant],
          )}
        >
          {riskBanner.message}
        </div>
      )}

      {/* Content */}
      <div
        className={cn(
          "rounded-lg border bg-slate-800/50 p-5",
          statusBorder[status] ?? "border-slate-700/30",
        )}
      >
        {children}
      </div>

      {/* Actions */}
      {actions && (
        <div className="flex items-center gap-3 flex-wrap">
          {actions}
        </div>
      )}
    </div>
  );
}
