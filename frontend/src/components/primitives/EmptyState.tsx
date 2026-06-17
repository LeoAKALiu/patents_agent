import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * EmptyState — teaching empty surface (not just "nothing here").
 * Per spec copy contract: a heading + body that points to the next action,
 * plus an optional action node (usually a <Button>).
 */
export interface EmptyStateProps {
  icon?: ReactNode;
  heading: string;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  heading,
  body,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
    >
      {icon && <div className="text-[var(--text-soft)]">{icon}</div>}
      <h3 className="text-[var(--fs-heading)] font-semibold text-[var(--text-primary)]">
        {heading}
      </h3>
      {body && (
        <p className="max-w-md text-[var(--fs-body)] text-[var(--text-muted)]">
          {body}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
