import { cn } from "./cn";

type ScoreTileProps = {
  label: string;
  value: number | null;
  max?: number;
  className?: string;
};

export function ScoreTile({ label, value, max = 100, className }: ScoreTileProps) {
  const pct = value != null ? Math.min(value / max, 1) : 0;
  const color =
    value == null ? "bg-slate-600" :
    pct >= 0.8 ? "bg-emerald-500" :
    pct >= 0.6 ? "bg-yellow-500" :
    "bg-red-500";

  return (
    <div className={cn("flex flex-col gap-1.5 p-3 rounded-md bg-slate-800/80 border border-slate-700/50", className)}>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <span className="text-xl font-bold text-slate-100 tabular-nums">
        {value != null ? value.toFixed(1) : "—"}
      </span>
      <div className="w-full h-1 rounded-full bg-slate-700">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.round(pct * 100)}%` }}
        />
      </div>
    </div>
  );
}
