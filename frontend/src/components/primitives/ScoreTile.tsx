import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * ScoreTile — labelled value + progress indicator.
 *
 * Replaces both the dead ui/ScoreTile.tsx AND the local ScoreTile shadow
 * defined inline in GuidedPatentFlow.tsx:1480. The bar fill is semantic:
 * high/ready → green fill (#1DBF73, used as fill per spec — safe); otherwise
 * brand teal. Never colours text with the bright green.
 */
export interface ScoreTileProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string;
  /** 0–100 progress for the bar; omit to hide the bar. */
  progress?: number;
  /** Treat as a passing state → green bar fill. */
  passing?: boolean;
}

export function ScoreTile({
  label,
  value,
  progress,
  passing,
  className,
  ...props
}: ScoreTileProps) {
  const showBar = typeof progress === "number";
  return (
    <div
      className={cn("glass-soft rounded-md p-3 flex flex-col gap-1", className)}
      {...props}
    >
      <span className="text-[13px] font-semibold text-[var(--text-muted)]">
        {label}
      </span>
      <span className="font-mono text-[18px] font-semibold text-[var(--text-primary)]">
        {value}
      </span>
      {showBar && (
        <div
          className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-inset)]"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
        >
          <div
            className="h-full rounded-full transition-[width] duration-[var(--dur-normal)] ease-[var(--ease-out)]"
            style={{
              width: `${Math.max(0, Math.min(100, progress!))}%`,
              background: passing ? "var(--success)" : "var(--brand-teal-500)",
            }}
          />
        </div>
      )}
    </div>
  );
}
