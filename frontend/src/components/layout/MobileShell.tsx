"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, Stethoscope, Target, FileText, User
} from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  children: React.ReactNode
  storeId?: string
}

const tabs = [
  { href: "", icon: LayoutDashboard, label: "홈" },
  { href: "/diagnosis", icon: Stethoscope, label: "진단" },
  { href: "/strategy", icon: Target, label: "전략" },
  { href: "/report", icon: FileText, label: "리포트" },
  { href: "/settings", icon: User, label: "내정보" },
]

export function MobileShell({ children, storeId }: Props) {
  const pathname = usePathname()
  const base = storeId ? `/dashboard/${storeId}` : "/dashboard"

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex flex-col max-w-lg mx-auto relative">
      <main className="flex-1 overflow-y-auto pb-20">
        {children}
      </main>
      <nav className="fixed bottom-0 left-0 right-0 max-w-lg mx-auto bg-white border-t border-slate-100 flex justify-around items-center px-2 py-2 pb-safe z-50">
        {tabs.map((tab) => {
          const href = tab.href === "" ? base : `${base}${tab.href}`
          const isActive = tab.href === ""
            ? pathname === base || pathname === `${base}/`
            : pathname.startsWith(`${base}${tab.href}`)
          return (
            <Link
              key={tab.href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-colors",
                isActive ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
              )}
            >
              <tab.icon size={21} strokeWidth={isActive ? 2.2 : 1.8} />
              <span className="text-[10.5px] font-semibold">{tab.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
