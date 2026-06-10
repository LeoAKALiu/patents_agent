import { cn } from "./cn";

type StatusBadgeProps = {
  variant: "done" | "current" | "ready" | "locked" | "warning" | "error";
  label?: string;
  className?: string;
};

const variantStyles: Record<StatusBadgeProps["variant"], string> = {
  done: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  current: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  ready: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  locked: "bg-slate-500/5 text-slate-600 border-slate-700/20",
  warning: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
};

const variantLabels: Record<StatusBadgeProps["variant"], string> = {
  done: "已完成",
  current: "进行中",
  ready: "可查看",
  locked: "未解锁",
  warning: "警告",
  error: "错误",
};

export function StatusBadge({ variant, label, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border",
        variantStyles[variant],
        className,
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full",
          variant === "done" && "bg-emerald-400",
          variant === "current" && "bg-teal-400 shadow-[0_0_6px_rgba(45,212,191,0.5)]",
          variant === "ready" && "bg-slate-400",
          variant === "locked" && "bg-slate-600",
          variant === "warning" && "bg-yellow-400",
          variant === "error" && "bg-red-400",
        )}
      />
      {label ?? variantLabels[variant]}
    </span>
  );
}
