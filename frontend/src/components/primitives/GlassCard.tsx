import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * GlassCard — the default container for panels / cards.
 *
 * Replaces the 7 ad-hoc card variants (choice-card, project-card, mode-card,
 * boundary-card, score-card, agent-card, start-choice-card) with one token-driven
 * glass surface. Glass elevation (blur + soft shadow) is the separator — not
 * hard borders (spec: reserve borders for inputs and thin dividers only).
 *
 * Props:
 *  • tier: "soft" | "default" | "strong" — maps to .glass-* frost tiers
 *  • interactive: hover lift (translateY, transform-only)
 *  • selected: accent-blue ring (reserved list)
 */
export interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  tier?: "soft" | "default" | "strong";
  interactive?: boolean;
  selected?: boolean;
}

const tierClass: Record<NonNullable<GlassCardProps["tier"]>, string> = {
  soft: "glass-soft",
  default: "glass",
  strong: "glass-strong",
};

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, tier = "default", interactive, selected, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        tierClass[tier],
        interactive && "is-interactive",
        selected && "is-selected",
        className,
      )}
      {...props}
    />
  ),
);
GlassCard.displayName = "GlassCard";
