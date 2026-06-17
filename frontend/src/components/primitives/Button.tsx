import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * Button — primary action primitive.
 *
 * Variants follow the spec's reserved-accent discipline:
 *  • default  = solid deep-blue (#0B3D91) CTA — the primary accent, used sparingly
 *  • glass    = frosted ghost surface (chip/secondary actions)
 *  • outline  = bordered, no fill (tertiary)
 *  • ghost    = transparent, hover-tint
 *  • danger   = destructive red (delete/irreversible only)
 * Sizes target the 40px control / 44px touch grid (--control-h / --control-touch).
 *
 * Motion: transform/opacity only (active scale). No bounce.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium",
    "rounded-md select-none disabled:pointer-events-none disabled:opacity-50",
    "transition-[transform,background-color,box-shadow] duration-[var(--dur-fast)] ease-[var(--ease-out)]",
    "focus-visible:outline-none", // ring applied via global :focus-visible in base.css
    "active:scale-[0.97]",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "bg-[var(--action-primary)] text-[var(--action-primary-contrast)] hover:bg-[var(--action-primary-hover)]",
        glass: "glass-btn text-[var(--text-primary)]",
        outline:
          "border border-[var(--border-input)] bg-transparent text-[var(--text-primary)] hover:bg-[var(--surface-subtle)]",
        ghost:
          "bg-transparent text-[var(--text-primary)] hover:bg-[var(--surface-subtle)]",
        danger:
          "bg-[var(--danger)] text-white hover:bg-[var(--danger-700)]",
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-[var(--control-h)] px-4 text-[15px]",
        lg: "h-[var(--control-touch)] px-6 text-[15px]",
        icon: "h-[var(--control-h)] w-[var(--control-h)]",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Show a spinner and disable interaction. */
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {children}
    </button>
  ),
);
Button.displayName = "Button";

export { buttonVariants };
