import * as React from "react"
import { cn } from "@/lib/cn"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Glass surface tier: "soft" (ghost/chips), default (panels/cards), "strong" (chrome) */
  variant?: "soft" | "default" | "strong"
  interactive?: boolean
}

const glassVariants = {
  soft: "bg-white/5 backdrop-blur-[8px] border border-white/10 shadow-none",
  default: "bg-white/[0.60] backdrop-blur-[16px] border border-white/[0.55] shadow-[inset_0_0_0_1px_rgba(15,40,60,0.06),0_4px_24px_rgba(11,61,145,0.08)]",
  strong: "bg-white/[0.72] backdrop-blur-[28px] saturate-[1.4] border border-white/[0.55] shadow-[inset_0_0_0_1px_rgba(15,40,60,0.06),0_12px_40px_rgba(11,61,145,0.12)]",
}

export function GlassCard({
  variant = "default",
  interactive = false,
  className,
  children,
  ...props
}: GlassCardProps) {
  return (
    <Card
      className={cn(
        glassVariants[variant],
        interactive && "cursor-pointer transition-transform duration-200 hover:translate-y-[-2px] hover:shadow-[inset_0_0_0_1px_rgba(15,40,60,0.06),0_12px_40px_rgba(11,61,145,0.12)] active:translate-y-0 active:duration-[120ms]",
        className
      )}
      {...props}
    >
      {children}
    </Card>
  )
}

export { CardHeader, CardTitle, CardDescription, CardContent, CardFooter }
