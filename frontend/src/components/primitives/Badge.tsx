import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * Badge — small status pill.
 *
 * Semantic variants map to the company palette:
 *  • success → green FILL with dark text (green is contrast-unsafe as text,
 *              per spec: use fill only) — this variant is a fill, never a text color
 *  • info / brand / warn / danger → tinted fills readable on glass
 *
 * Replaces .tag-* / .status-badge.* / .chip ad-hoc classes.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-semibold leading-none whitespace-nowrap",
  {
    variants: {
      variant: {
        neutral: "bg-[var(--surface-subtle)] text-[var(--text-muted)]",
        brand: "bg-[var(--brand-teal-50)] text-[var(--brand-teal-700)]",
        info: "bg-[var(--brand-blue-50)] text-[var(--brand-blue-700)]",
        // success is a FILL (green fails contrast as text): dark text on green bg.
        success: "bg-[var(--brand-green-100)] text-[var(--success-strong)]",
        warn: "bg-[oklch(94%_0.05_75)] text-[oklch(40%_0.10_75)]",
        danger: "bg-[oklch(92%_0.07_29)] text-[var(--danger-700)]",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
