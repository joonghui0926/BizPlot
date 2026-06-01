"use client"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  LayoutDashboard, Stethoscope, Target, FileText,
  User, LogOut, Bell, ChevronRight, TrendingUp
} from "lucide-react"
import { cn } from "@/lib/utils"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import type { Store } from "@/lib/types"

interface Props {
  children: React.ReactNode
  store: Store
  unreadCount?: number
}

const NAV = [
  { href: "",         icon: LayoutDashboard, label: "대시보드",  short: "홈" },
  { href: "/diagnosis", icon: Stethoscope,    label: "원인 분석", short: "진단" },
  { href: "/strategy",  icon: Target,          label: "추천 전략", short: "전략" },
  { href: "/report",    icon: FileText,        label: "상담 리포트", short: "리포트" },
  { href: "/settings",  icon: User,            label: "내 정보",   short: "내정보" },
]

export function AppShell({ children, store, unreadCount = 0 }: Props) {
  const pathname = usePathname()
  const router = useRouter()
  const base = `/dashboard/${store.id}`

  const isActive = (href: string) =>
    href === "" ? pathname === base || pathname === `${base}/` : pathname.startsWith(`${base}${href}`)

  const handleLogout = () => {
    localStorage.removeItem("token")
    router.push("/login")
  }

  return (
    <div className="min-h-screen flex bg-white">

      {/* ── Desktop Sidebar ── */}
      <aside className="hidden lg:flex flex-col w-64 xl:w-72 bg-white border-r border-slate-200/70 fixed inset-y-0 left-0 z-30">
        {/* Logo */}
        <Link href={base} className="flex items-center gap-2.5 px-5 h-16 border-b border-slate-100 flex-shrink-0 hover:opacity-80 transition-opacity">
          <div className="text-[#3253E9]"><FinPilotMark size={36} /></div>
          <span className="text-[17px] font-extrabold tracking-tight text-slate-900">BizPlot</span>
        </Link>

        {/* Store info - no box, just clean text */}
        <div className="px-5 pt-5 pb-3 border-b border-slate-100">
          <div className="text-[10.5px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">현재 사업장</div>
          <div className="text-[14px] font-extrabold text-slate-900 truncate">{store.name}</div>
          <div className="text-[11.5px] text-slate-400 mt-0.5 truncate">{store.address || store.category}</div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
          {NAV.map(item => {
            const active = isActive(item.href)
            const href = item.href === "" ? base : `${base}${item.href}`
            return (
              <Link
                key={item.href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-[13.5px] font-semibold transition-colors",
                  active
                    ? "bg-blue-600 text-white shadow-sm shadow-blue-200"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
                )}
              >
                <item.icon size={17} strokeWidth={active ? 2.5 : 2} />
                {item.label}
                {item.href === "" && unreadCount > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-3 pb-5 border-t border-slate-100 pt-3">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3.5 py-2.5 rounded-xl text-[13px] font-semibold text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
          >
            <LogOut size={16} />로그아웃
          </button>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div className="flex-1 lg:ml-64 xl:ml-72 flex flex-col min-h-screen bg-white">

        {/* Mobile Top Header */}
        <header className="lg:hidden sticky top-0 z-20 bg-white/85 backdrop-blur-xl border-b border-slate-200/60 flex items-center h-12 px-4">
          <Link href={base} className="text-[#3253E9] w-9 flex items-center">
            <FinPilotMark size={26} />
          </Link>
          <div className="flex-1 text-center text-[15px] font-extrabold tracking-tight text-slate-900">
            {NAV.find(n => isActive(n.href))?.label ?? "대시보드"}
          </div>
          <button className="relative w-9 h-9 flex items-center justify-center text-slate-400">
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-red-500 border-2 border-white" />
            )}
          </button>
        </header>

        {/* Desktop Topbar */}
        <header className="hidden lg:flex items-center justify-between h-14 px-8 bg-white border-b border-slate-200/60 sticky top-0 z-20">
          <div className="text-[14px] font-bold text-slate-400">
            {NAV.find(n => isActive(n.href))?.label ?? "대시보드"}
          </div>
          <div className="flex items-center gap-3">
            <button className="relative w-9 h-9 flex items-center justify-center rounded-xl text-slate-400 hover:bg-slate-50">
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-red-500 border-2 border-white" />
              )}
            </button>
            <div className="flex items-center gap-2 pl-2 border-l border-slate-100">
              <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white text-[13px] font-bold">
                {store.name[0]}
              </div>
              <span className="text-[13px] font-semibold text-slate-700 max-w-[120px] truncate">{store.name}</span>
            </div>
          </div>
        </header>

        {/* Page content — 흰색이 꽉 차게 (회색 여백 없음) */}
        <main className="flex-1 pb-24 lg:pb-0 bg-white">
          {children}
        </main>
      </div>

      {/* ── Mobile Bottom Tabs ── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-xl border-t border-slate-200/70 flex justify-around items-center px-1 z-40"
        style={{ paddingBottom: "max(8px, env(safe-area-inset-bottom))", paddingTop: "8px" }}>
        {NAV.map(item => {
          const active = isActive(item.href)
          const href = item.href === "" ? base : `${base}${item.href}`
          return (
            <Link
              key={item.href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-colors",
                active ? "text-blue-600" : "text-slate-400"
              )}
            >
              <item.icon size={20} strokeWidth={active ? 2.3 : 1.8} />
              <span className="text-[10px] font-semibold">{item.short}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
