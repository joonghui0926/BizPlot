"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Eye, EyeOff, ArrowRight } from "lucide-react"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import { login, listStores, oauthLoginUrl } from "@/lib/api"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError("")
    try {
      const r = await login(email, password)
      const token = r.data.access_token
      if (!token) { setError("로그인에 실패했습니다."); return }
      localStorage.setItem("token", token)
      try {
        const stores = await listStores()
        const list = stores.data || []
        router.push(list.length > 0 ? `/dashboard/${list[0].id}` : "/onboarding")
      } catch {
        router.push("/onboarding")
      }
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.")
    } finally {
      setLoading(false)
    }
  }

  const handleSocialLogin = (provider: "google" | "kakao") => {
    window.location.href = oauthLoginUrl(provider)
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-[#EEF2FB] to-white">
      {/* Left panel - desktop only */}
      <div className="hidden lg:flex flex-col justify-between w-[440px] xl:w-[500px] bg-gradient-to-br from-blue-700 to-blue-900 p-14 flex-shrink-0">
        <div className="flex items-center gap-3">
          <FinPilotMark size={40} color="white" />
          <span className="text-xl font-extrabold text-white tracking-tight">BizPlot</span>
        </div>

        <div>
          <p className="text-white/50 text-sm font-semibold tracking-widest uppercase mb-5">소상공인 AI CFO Platform</p>
          <h2 className="text-white text-[2rem] font-extrabold leading-tight tracking-tight mb-6">
            사업 데이터로<br />금융을 먼저 준비하세요
          </h2>
          <p className="text-white/60 text-[15px] leading-relaxed mb-10">
            매출·비용·상권·날씨·리뷰를 하나로 읽어<br />
            현금흐름 위험을 사전에 감지하고<br />
            은행 상담까지 자동으로 준비합니다.
          </p>

          {/* 통계 — 박스 없이 라인으로 */}
          <div className="flex gap-0 border-t border-white/15">
            {[
              { n: "62", l: "사업 건강도" },
              { n: "17일", l: "현금 유지" },
              { n: "3가지", l: "맞춤 전략" },
              { n: "58%", l: "금융 준비도" },
            ].map((m, i) => (
              <div key={m.l} className={`flex-1 pt-5 ${i > 0 ? "border-l border-white/15 pl-4" : "pr-4"}`}>
                <div className="text-white text-2xl font-black tabular-nums">{m.n}</div>
                <div className="text-white/45 text-[11px] font-medium mt-0.5">{m.l}</div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/30 text-xs">JB금융그룹 Fin:AI Challenge · BizPlot Agent</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="text-[#3253E9]"><FinPilotMark size={40} /></div>
            <div>
              <div className="text-xl font-extrabold tracking-tight">BizPlot</div>
              <div className="text-xs text-slate-400 font-medium">소상공인 AI CFO Platform</div>
            </div>
          </div>

          <h1 className="text-2xl font-extrabold tracking-tight mb-1">로그인</h1>
          <p className="text-sm text-slate-400 mb-7">사업 상태를 분석하고 금융 전략을 시작하세요.</p>

          {/* Social login */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <button
              onClick={() => handleSocialLogin("kakao")}
              className="flex items-center justify-center gap-2 py-3 rounded-xl bg-[#FEE500] text-[#3C1E1E] font-semibold text-[13.5px] hover:bg-[#F5DC00] transition-colors"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="#3C1E1E">
                <path d="M12 3C6.48 3 2 6.48 2 10.8c0 2.76 1.8 5.19 4.5 6.6-.18.66-.65 2.4-.75 2.76-.12.42.15.42.3.3.12-.08 1.95-1.32 2.73-1.86.72.12 1.47.18 2.22.18 5.52 0 10-3.48 10-7.8S17.52 3 12 3z"/>
              </svg>
              카카오
            </button>
            <button
              onClick={() => handleSocialLogin("google")}
              className="flex items-center justify-center gap-2 py-3 rounded-xl bg-white border border-slate-200 text-slate-700 font-semibold text-[13.5px] hover:bg-slate-50 transition-colors"
            >
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </button>
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-slate-200" />
            <span className="text-xs text-slate-400 font-medium">또는 이메일로 로그인</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          {/* Email form */}
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1.5">이메일</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="example@email.com"
                required
                className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1.5">비밀번호</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="비밀번호 입력"
                  required
                  className="w-full px-4 py-3.5 pr-11 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-red-500 text-xs font-medium bg-red-50 px-3 py-2.5 rounded-xl">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />{error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2 w-full py-3.5 rounded-xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-60 hover:bg-blue-700 transition-colors"
            >
              {loading ? "로그인 중..." : <>로그인 <ArrowRight size={17} /></>}
            </button>
          </form>

          <div className="text-center mt-5">
            <span className="text-sm text-slate-400">아직 계정이 없으신가요? </span>
            <Link href="/register" className="text-sm font-bold text-blue-600 hover:text-blue-700">회원가입</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
