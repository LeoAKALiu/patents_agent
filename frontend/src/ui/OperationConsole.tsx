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
  const [summaryLine, ...detailLines] = lines;
  return (
    <div className="operation-console motion-reveal" role="status" aria-label={label}>
      <div className="operation-console-heading">
        <div>
          <Loader2 size={14} className="animate-spin" />
          {label}
        </div>
        <span>{formatElapsed(elapsedSeconds)}</span>
      </div>
      {summaryLine && <p className="operation-console-summary">{summaryLine}</p>}
      {detailLines.length > 0 && (
        <details className="operation-console-details">
          <summary>技术详情</summary>
          <pre>{detailLines.join("\n")}</pre>
        </details>
      )}
    </div>
  );
}
