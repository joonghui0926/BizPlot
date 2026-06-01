import { cn } from "@/lib/utils"

type Variant = "default" | "ok" | "warn" | "risk" | "blue" | "outline"

interface BadgeProps {
  children: React.ReactNode
  variant?: Variant
  className?: string
}

const variants: Record<Variant, string> = {
  default: "bg-slate-100 text-slate-700",
  ok: "bg-emerald-50 text-emerald-700 border border-emerald-100",
  warn: "bg-amber-50 text-amber-700 border border-amber-100",
  risk: "bg-red-50 text-red-700 border border-red-100",
  blue: "bg-blue-50 text-blue-700 border border-blue-100",
  outline: "bg-white text-slate-600 border border-slate-200",
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-semibold whitespace-nowrap",
      variants[variant],
      className
    )}>
      {children}
    </span>
  )
}
