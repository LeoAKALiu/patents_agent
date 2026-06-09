import { Loader2 } from "lucide-react";

type OperationConsoleProps = {
  label: string;
  lines: string[];
  elapsedSeconds?: number;
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function OperationConsole({ label, lines, elapsedSeconds = 0 }: OperationConsoleProps) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/80 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-teal-400">
          <Loader2 size={14} className="animate-spin" />
          {label}
        </div>
        <span className="text-[10px] text-slate-500 tabular-nums font-mono">
          {formatElapsed(elapsedSeconds)}
        </span>
      </div>
      <pre className="text-[11px] leading-relaxed text-slate-400 font-mono whitespace-pre-wrap m-0 max-h-48 overflow-y-auto">
        {lines.join("\n")}
      </pre>
    </div>
  );
}
