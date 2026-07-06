import { type ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface StatusChip {
  label: string;
  variant?: "done" | "current" | "ready" | "locked" | "warning" | "error" | "default";
}

export interface PrimarySurfaceProps {
  id: string; // Used for data-testid="primary-surface-{id}"
  eyebrow?: string;
  title: string;
  description?: string;
  statusChips?: StatusChip[];
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function PrimarySurface({
  id,
  eyebrow = "GrantAtlas",
  title,
  description,
  statusChips = [],
  actions,
  children,
  className,
}: PrimarySurfaceProps) {
  const titleId = `primary-surface-${id}-title`;

  return (
    <section
      aria-labelledby={titleId}
      data-testid={`primary-surface-${id}`}
      className={cn("primary-surface-container", className)}
    >
      <header className="primary-surface-header">
        <div className="primary-surface-header-left">
          <div className="primary-surface-eyebrow">
            {eyebrow} <span className="primary-surface-slash">/</span> {title}
          </div>
          <div className="primary-surface-title-row">
            <p id={titleId} className="primary-surface-title">{title}</p>
            {statusChips.length > 0 && (
              <div className="primary-surface-chips" aria-label="状态指标">
                {statusChips.map((chip) => (
                  <span
                    key={`${chip.variant ?? "default"}-${chip.label}`}
                    className={cn(
                      "primary-surface-chip",
                      chip.variant ? `variant-${chip.variant}` : "variant-default",
                    )}
                  >
                    <span className="primary-surface-chip-dot" />
                    {chip.label}
                  </span>
                ))}
              </div>
            )}
          </div>
          {description && (
            <p className="primary-surface-description">{description}</p>
          )}
        </div>

        {actions && (
          <div className="primary-surface-header-actions">
            {actions}
          </div>
        )}
      </header>

      <div className="primary-surface-body">
        {children}
      </div>
    </section>
  );
}
