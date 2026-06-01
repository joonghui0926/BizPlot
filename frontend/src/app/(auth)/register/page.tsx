"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Eye, EyeOff, ArrowRight, CheckCircle2 } from "lucide-react"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import { register } from "@/lib/api"

export default function RegisterPage() {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const pwStrength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 6) { setError("비밀번호는 6자 이상이어야 합니다."); return }
    setLoading(true); setError("")
    try {
      const r = await register(email, password, name)
      localStorage.setItem("token", r.data.access_token)
      router.push("/onboarding")
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(detail === "Email already registered" ? "이미 가입된 이메일입니다." : "회원가입에 실패했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-[#EEF2FB] to-white">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-[440px] xl:w-[500px] bg-gradient-to-br from-blue-700 to-blue-900 p-14 flex-shrink-0">
        <div className="flex items-center gap-3">
          <FinPilotMark size={40} color="white" />
          <span className="text-xl font-extrabold text-white tracking-tight">BizPlot</span>
        </div>

        <div>
          <p className="text-white/50 text-sm font-semibold tracking-widest uppercase mb-5">무료로 시작하기</p>
          <h2 className="text-white text-[2rem] font-extrabold leading-tight tracking-tight mb-6">
            지역 소상공인을 위한<br />AI CFO 플랫폼
          </h2>

          {/* 기능 목록 — 박스 없이 라인 구분 */}
          <div className="border-t border-white/15">
            {[
              { n: "01", t: "매출·비용·상권·날씨 데이터를 한 번에" },
              { n: "02", t: "현금흐름 위험을 사전에 감지" },
              { n: "03", t: "맞춤 운영·마케팅·금융 전략 제안" },
              { n: "04", t: "은행 상담 준비 리포트 자동 생성" },
            ].map(item => (
              <div key={item.n} className="flex items-start gap-4 py-4 border-b border-white/10">
                <span className="text-white/30 text-[11px] font-bold tabular-nums mt-0.5 flex-shrink-0">{item.n}</span>
                <span className="text-white/80 text-[14px] font-medium leading-snug">{item.t}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/30 text-xs">JB금융그룹 Fin:AI Challenge · BizPlot Agent</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-2.5 mb-8 lg:hidden">
            <div className="text-[#3253E9]"><FinPilotMark size={40} /></div>
            <div>
              <div className="text-xl font-extrabold tracking-tight">BizPlot</div>
              <div className="text-xs text-slate-400 font-medium">소상공인 AI CFO Platform</div>
            </div>
          </div>

          <h1 className="text-2xl font-extrabold tracking-tight mb-1">회원가입</h1>
          <p className="text-sm text-slate-400 mb-7">무료로 시작하고 사업 상태를 바로 진단해 보세요.</p>

          {/* Social buttons */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <button
              onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_URL?.replace("/api","")}/auth/kakao`}
              className="flex items-center justify-center gap-2 py-3 rounded-xl bg-[#FEE500] text-[#3C1E1E] font-semibold text-[13.5px] hover:bg-[#F5DC00] transition-colors"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="#3C1E1E">
                <path d="M12 3C6.48 3 2 6.48 2 10.8c0 2.76 1.8 5.19 4.5 6.6-.18.66-.65 2.4-.75 2.76-.12.42.15.42.3.3.12-.08 1.95-1.32 2.73-1.86.72.12 1.47.18 2.22.18 5.52 0 10-3.48 10-7.8S17.52 3 12 3z"/>
              </svg>
              카카오
            </button>
            <button
              onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_URL?.replace("/api","")}/auth/google`}
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
            <span className="text-xs text-slate-400 font-medium">또는 이메일로 가입</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1.5">이름</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="홍길동" required
                className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1.5">이메일</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="example@email.com" required
                className="w-full px-4 py-3.5 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1.5">비밀번호</label>
              <div className="relative">
                <input type={showPw ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="6자 이상" required minLength={6}
                  className="w-full px-4 py-3.5 pr-11 rounded-xl border border-slate-200 text-[14px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <button type="button" onClick={() => setShowPw(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {password.length > 0 && (
                <div className="flex gap-1 mt-1.5">
                  {[1,2,3].map(i => (
                    <div key={i} className={`flex-1 h-1 rounded-full ${pwStrength >= i ? (pwStrength === 1 ? "bg-red-400" : pwStrength === 2 ? "bg-amber-400" : "bg-green-500") : "bg-slate-200"}`} />
                  ))}
                  <span className="text-[10.5px] text-slate-400 ml-1">
                    {pwStrength === 1 ? "약함" : pwStrength === 2 ? "보통" : "강함"}
                  </span>
                </div>
              )}
            </div>
            {error && (
              <div className="flex items-center gap-2 text-red-500 text-xs font-medium bg-red-50 px-3 py-2.5 rounded-xl">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0" />{error}
              </div>
            )}
            <button type="submit" disabled={loading}
              className="flex items-center justify-center gap-2 w-full py-3.5 rounded-xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-60 hover:bg-blue-700 transition-colors">
              {loading ? "가입 중..." : <>시작하기 <ArrowRight size={17} /></>}
            </button>
          </form>

          <div className="text-center mt-5">
            <span className="text-sm text-slate-400">이미 계정이 있으신가요? </span>
            <Link href="/login" className="text-sm font-bold text-blue-600 hover:text-blue-700">로그인</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
