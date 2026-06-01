"use client"
import { createContext, useContext, useRef, useState, useCallback } from "react"
import { RefreshCw, CheckCircle2 } from "lucide-react"
import { runDiagnosis, getDashboard } from "@/lib/api"

interface DiagnosisCtx {
  diagnosing: boolean
  progress: number
  stage: string
  done: boolean          // 완료 직후 "생성 완료" 표시 중
  completedTick: number  // 진단 1회 끝날 때마다 +1 → 각 페이지가 데이터 refetch
  start: (storeId: string) => void
}

const Ctx = createContext<DiagnosisCtx | null>(null)

export function useDiagnosis(): DiagnosisCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error("useDiagnosis must be used within DiagnosisProvider")
  return c
}

// 진단 파이프라인 단계별 예상 진행률 (실측 ~47s + 첫 호출 모델 콜드로드 여유)
function progressFor(elapsed: number): { pct: number; label: string } {
  const stages = [
    { until: 6,  pct: 12, label: "공공 데이터 수집 중 (상권·날씨·행사)" },
    { until: 11, pct: 22, label: "고객 리뷰 분석 중" },
    { until: 15, pct: 30, label: "사업 상태 진단 중" },
    { until: 38, pct: 66, label: "AI가 매출 하락 원인을 분석 중" },
    { until: 60, pct: 95, label: "AI가 실행 전략을 생성 중" },
  ]
  let prevUntil = 0, prevPct = 5
  for (const s of stages) {
    if (elapsed < s.until) {
      const r = (elapsed - prevUntil) / (s.until - prevUntil)
      return { pct: Math.round(prevPct + r * (s.pct - prevPct)), label: s.label }
    }
    prevUntil = s.until; prevPct = s.pct
  }
  return { pct: 95, label: "마무리 중" }
}

export function DiagnosisProvider({ children }: { children: React.ReactNode }) {
  const [diagnosing, setDiagnosing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState("")
  const [done, setDone] = useState(false)
  const [completedTick, setCompletedTick] = useState(0)
  const running = useRef(false)

  const start = useCallback(async (storeId: string) => {
    if (running.current) return  // 생성 중 재클릭/중복 트리거 차단
    running.current = true
    setDone(false)
    setDiagnosing(true)
    setProgress(5)
    setStage("진단 준비 중")

    const startedAt = Date.now()
    const timer = setInterval(() => {
      const { pct, label } = progressFor((Date.now() - startedAt) / 1000)
      setProgress(pct)
      setStage(label)
    }, 400)

    // 완료 판정 = 마지막 단계인 ActionPlan(전략)이 새로 생기는 시점
    let prevPlanId: string | null = null
    try {
      try {
        const r0 = await getDashboard(storeId)
        prevPlanId = r0.data?.latest_action_plan?.id ?? null
      } catch { /* 무시 */ }

      await runDiagnosis(storeId)

      for (let i = 0; i < 70; i++) {  // 최대 ~140초
        await new Promise(r => setTimeout(r, 2000))
        try {
          const r = await getDashboard(storeId)
          if (r.data?.latest_action_plan?.id && r.data.latest_action_plan.id !== prevPlanId) {
            break
          }
        } catch { /* 폴링 중 일시 오류 무시 */ }
      }
    } finally {
      clearInterval(timer)
      setProgress(100)
      setStage("완료!")
      setCompletedTick(t => t + 1)   // 각 페이지가 최신 데이터로 갱신
      setDiagnosing(false)
      setDone(true)
      running.current = false
      setTimeout(() => setDone(false), 2000)  // "생성 완료" 2초 노출 후 사라짐
    }
  }, [])

  return (
    <Ctx.Provider value={{ diagnosing, progress, stage, done, completedTick, start }}>
      {/* 전역 진행바 — 어떤 탭에 있어도 화면 최상단 고정 */}
      {(diagnosing || done) && (
        <div className="fixed top-0 left-0 right-0 z-[100] shadow-[0_8px_20px_-10px_rgba(37,99,235,.7)]">
          {diagnosing ? (
            <div className="bg-blue-600 text-white">
              <div className="flex items-center justify-center gap-2.5 px-5 pt-2.5 pb-2 text-[13px] font-bold">
                <RefreshCw size={15} className="animate-spin flex-shrink-0" />
                <span className="truncate">{stage || "AI가 사업 데이터를 진단하는 중"}</span>
                <span className="tabular-nums font-extrabold flex-shrink-0">{progress}%</span>
              </div>
              <div className="h-1 bg-white/25">
                <div className="h-full bg-white transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
              </div>
            </div>
          ) : (
            <div className="bg-green-600 text-white flex items-center justify-center gap-2 px-5 py-3 text-[13px] font-extrabold">
              <CheckCircle2 size={16} className="flex-shrink-0" />
              생성 완료
            </div>
          )}
        </div>
      )}
      {children}
    </Ctx.Provider>
  )
}
