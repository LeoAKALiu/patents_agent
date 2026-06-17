import { Loader2 } from "@/lib/icons";
import { cn } from "@/lib/cn";

/**
 * Spinner — single loading indicator using the lucide Loader2 icon.
 * Replaces the inline <svg> spinners scattered in the legacy code
 * (e.g. ActionButton.tsx). Spins via the global @keyframes spin.
 *
 * prefers-reduced-motion: the spin animation is reduced to ~instant by
 * base.css's global reduce rule, but the icon remains as a static affordance.
 */
export function Spinner({
  className,
  "aria-label": label = "加载中",
}: {
  className?: string;
  "aria-label"?: string;
}) {
  return (
    <Loader2
      role="status"
      aria-label={label}
      className={cn("animate-spin", className)}
    />
  );
}
