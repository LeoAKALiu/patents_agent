import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes, ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "@/lib/icons";
import { cn } from "@/lib/cn";

/**
 * Banner — full-width contextual message (notice / callout / workflow-hint).
 * Replaces .notice / .callout / .callout-warn/danger/success / .workflow-hint-danger.
 *
 * Tone drives both the icon and the tinted fill. Success tone uses the
 * darkened green text token (bright green #1DBF73 fails contrast on light).
 */
const bannerVariants = cva(
  "flex items-start gap-3 rounded-lg px-4 py-3 text-[15px] leading-[var(--lh-body)]",
  {
    variants: {
      tone: {
        info: "bg-[var(--brand-blue-50)] text-[var(--text-primary)]",
        success:
          "bg-[var(--brand-green-50)] text-[var(--text-primary)]",
        warn: "bg-[oklch(94%_0.05_75)] text-[var(--text-primary)]",
        danger: "bg-[oklch(92%_0.07_29)] text-[var(--text-primary)]",
        neutral: "bg-[var(--surface-subtle)] text-[var(--text-primary)]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

const toneIcon: Record<NonNullable<BannerProps["tone"]>, ReactNode> = {
  info: <Info className="mt-0.5 shrink-0 text-[var(--brand-blue-500)]" size={18} />,
  success: (
    <CheckCircle2 className="mt-0.5 shrink-0 text-[var(--success-strong)]" size={18} />
  ),
  warn: <AlertTriangle className="mt-0.5 shrink-0 text-[oklch(50%_0.12_75)]" size={18} />,
  danger: <XCircle className="mt-0.5 shrink-0 text-[var(--danger)]" size={18} />,
  neutral: null,
};

export interface BannerProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof bannerVariants> {
  tone?: "info" | "success" | "warn" | "danger" | "neutral";
  /** Hide the leading icon (defaults to one matching the tone). */
  hideIcon?: boolean;
}

export function Banner({
  className,
  tone = "neutral",
  hideIcon,
  children,
  ...props
}: BannerProps) {
  return (
    <div role="note" className={cn(bannerVariants({ tone }), className)} {...props}>
      {!hideIcon && toneIcon[tone]}
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export { bannerVariants };
