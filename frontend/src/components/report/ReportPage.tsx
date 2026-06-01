"use client"
import { useEffect, useState } from "react"
import {
  FileText, Download, CheckCircle2, AlertCircle,
  Building, TrendingDown, Shield, List,
  BarChart3, Target, Loader2, ArrowRight, FileDown, Share2
} from "lucide-react"
import { getDashboard, createReport, getReport } from "@/lib/api"
import type { Dashboard, Store as StoreType } from "@/lib/types"
import { HealthGauge } from "@/components/ui/HealthGauge"
import { FinPilotMark } from "@/components/ui/FinPilotLogo"
import { AppShell } from "@/components/layout/AppShell"
import { downloadWithAuth } from "@/lib/utils"

interface Props { store: StoreType }

export function ReportPage({ store }: Props) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)
  const [reportStatus, setReportStatus] = useState<"idle" | "creating" | "pending" | "done" | "failed">("idle")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard(store.id).then(r => setData(r.data)).finally(() => setLoading(false))
  }, [store.id])

  const [downloading, setDownloading] = useState(false)

  // 한 번 클릭 → 생성 → 완료되면 자동 다운로드
  const handleCreateReport = async () => {
    setReportStatus("creating")
    try {
      const r = await createReport(store.id)
      const id = r.data.id
      setReportId(id)
      setReportStatus("pending")
      const ok = await pollReport(id)
      if (ok) {
        setReportStatus("done")
        await downloadPdfById(id)   // 생성 완료 즉시 다운로드
      } else {
        setReportStatus("failed")
      }
    } catch {
      setReportStatus("failed")
    }
  }

  const pollReport = async (id: string): Promise<boolean> => {
    for (let i = 0; i < 40; i++) {
      await new Promise(r => setTimeout(r, 2000))
      try {
        const r = await getReport(id)
        if (r.data.status === "done") return true
        if (r.data.status === "failed") return false
      } catch { return false }
    }
    return false
  }

  const downloadPdfById = async (id: string) => {
    setDownloading(true)
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
      await downloadWithAuth(`${apiBase}/stores/reports/${id}/download`, `bizplot_${store.name}.pdf`)
    } catch {
      alert("PDF 다운로드에 실패했습니다. 다시 시도해 주세요.")
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadPdf = () => reportId && downloadPdfById(reportId)

  const handleDownloadCsv = async () => {
    setDownloading(true)
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
      await downloadWithAuth(`${apiBase}/stores/${store.id}/export?format=csv`, `bizplot_${store.name}.csv`)
    } catch (e) {
      alert("CSV 다운로드에 실패했습니다. 다시 시도해 주세요.")
    } finally {
      setDownloading(false)
    }
  }

  const state = data?.state
  const diagnosis = data?.latest_diagnosis
  const plan = data?.latest_action_plan
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

  const tocItems = [
    { icon: <BarChart3 size={14} />, title: "1. 사업 상태 요약" },
    { icon: <TrendingDown size={14} />, title: "2. 매출 하락 원인 분석" },
    { icon: <Target size={14} />, title: "3. 권장 실행 전략" },
    { icon: <Building size={14} />, title: "4. 금융 준비 방향" },
    { icon: <List size={14} />, title: "5. 상담 시 확인 질문 목록" },
  ]

  const questions = [
    "단기 운전자금 대출 가능 한도 및 금리 조건은?",
    "소상공인 경영안정 정책자금 신청 자격은?",
    "현금흐름 개선을 위한 분할상환·유예 옵션은?",
    "지역화폐 가맹 시 추가 마케팅 지원이 있나요?",
    "사업 데이터를 기반으로 상담 받을 수 있나요?",
  ]

  return (
    <AppShell store={store}>
      {loading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 size={28} className="text-blue-500 animate-spin" />
        </div>
      )}

      {/* ──────────────────────────────────────────
          MOBILE LAYOUT  (lg:hidden)
      ────────────────────────────────────────── */}
      {!loading && (
        <div className="lg:hidden bg-white min-h-screen">

          {/* Report cover — full-width, no card border */}
          <div className="bg-gradient-to-br from-blue-700 via-blue-800 to-blue-950 px-6 pt-8 pb-6">
            {/* Logo row */}
            <div className="flex items-center gap-2.5 mb-6">
              <FinPilotMark size={32} color="rgba(255,255,255,0.9)" />
              <div>
                <div className="text-white/75 text-[10px] font-bold tracking-widest uppercase">BizPlot Agent</div>
                <div className="text-white/50 text-[9.5px]">소상공인 AI CFO Platform</div>
              </div>
            </div>

            {/* Store + title */}
            <div className="text-white text-[22px] font-extrabold leading-tight tracking-tight">{store.name}</div>
            <div className="text-white/60 text-[13px] mt-1.5">
              상담 준비 리포트 · {new Date().toLocaleDateString("ko-KR")}
            </div>

            {/* Key metrics row */}
            {state && (
              <div className="mt-6 pt-5 border-t border-white/15 grid grid-cols-4 gap-0">
                {[
                  { v: `${Math.round(state.health_score ?? 0)}`, l: "사업 건강도" },
                  { v: `${Math.round(state.cash_runway_days ?? 0)}일`, l: "현금 유지" },
                  { v: `${Math.round(state.finance_readiness ?? 0)}%`, l: "금융 준비도" },
                  { v: `${plan?.actions?.length ?? 0}가지`, l: "권장 전략" },
                ].map((m, i) => (
                  <div key={m.l} className={`${i > 0 ? "border-l border-white/15 pl-3" : "pr-3"}`}>
                    <div className="text-white text-[22px] font-black tabular-nums leading-none">{m.v}</div>
                    <div className="text-white/45 text-[9.5px] font-medium mt-1.5">{m.l}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* TOC — flat list */}
          <div className="px-5 pt-3 pb-1">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">목차</div>
          </div>
          {tocItems.map((item, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-100">
              <div className="w-6 h-6 rounded-lg bg-blue-50 text-blue-500 flex items-center justify-center flex-shrink-0 text-[11px] font-bold">{i + 1}</div>
              <span className="flex-1 text-[13.5px] font-semibold text-slate-700">{item.title}</span>
              <span className="text-slate-300">{item.icon}</span>
            </div>
          ))}

          {/* Cause preview */}
          {diagnosis && diagnosis.causes.length > 0 && (
            <>
              <div className="h-2 bg-slate-100 border-y border-slate-100 mt-1" />
              <div className="px-5 pt-4 pb-1">
                <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
                  <span className="w-[3px] h-[14px] bg-red-500 rounded-sm flex-shrink-0" />
                  매출 하락 원인 (미리보기)
                </h3>
              </div>
              {diagnosis.causes.slice(0, 3).map((c, i) => (
                <div key={i} className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-100">
                  <div className="w-28 text-[12px] font-semibold text-slate-600 flex-shrink-0 truncate">{c.factor}</div>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${i === 0 ? "bg-red-500" : i === 1 ? "bg-amber-400" : "bg-blue-400"}`}
                      style={{ width: `${c.contribution}%` }} />
                  </div>
                  <div className="text-[12px] font-bold tabular-nums w-8 text-right">{c.contribution.toFixed(0)}%</div>
                </div>
              ))}
            </>
          )}

          {/* Consultation questions */}
          <div className="h-2 bg-slate-100 border-y border-slate-100 mt-1" />
          <div className="px-5 pt-4 pb-1">
            <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
              <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
              상담 시 확인 질문
            </h3>
          </div>
          {questions.map((q, i) => (
            <div key={i} className="flex items-start gap-2.5 px-5 py-3 border-b border-slate-100 last:border-0">
              <CheckCircle2 size={14} className="text-blue-500 flex-shrink-0 mt-0.5" />
              <span className="text-[12.5px] text-slate-600 leading-relaxed">{q}</span>
            </div>
          ))}

          {/* Finance readiness bar */}
          {state && (
            <>
              <div className="h-2 bg-slate-100 border-y border-slate-100 mt-1" />
              <div className="px-5 py-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[13px] font-bold text-slate-700">금융 준비도</span>
                  <span className="text-[22px] font-extrabold tabular-nums text-blue-700">
                    {Math.round(state.finance_readiness ?? 0)}%
                  </span>
                </div>
                <div className="h-2 bg-blue-50 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                    style={{ width: `${state.finance_readiness ?? 0}%` }} />
                </div>
                <div className="text-[11px] text-slate-400 mt-1.5 font-medium">
                  {(state.finance_readiness ?? 0) >= 70 ? "상담 준비 완료" : "리포트 생성 후 향상"}
                </div>
              </div>
            </>
          )}

          {/* Actions */}
          <div className="h-2 bg-slate-100 border-y border-slate-100" />
          <div className="px-5 py-5 space-y-3">
            {reportStatus === "idle" || reportStatus === "failed" ? (
              <button onClick={handleCreateReport}
                className="flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200">
                <FileText size={17} />PDF 리포트 생성
              </button>
            ) : reportStatus === "creating" || reportStatus === "pending" ? (
              <div className="flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-blue-100 text-blue-600 font-bold text-[15px]">
                <Loader2 size={17} className="animate-spin" />생성 중...
              </div>
            ) : reportStatus === "done" && reportId ? (
              <button onClick={handleDownloadPdf} disabled={downloading}
                className="flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-60">
                {downloading ? <Loader2 size={17} className="animate-spin" /> : <Download size={17} />}
                {downloading ? "다운로드 중..." : "PDF 다운로드"}
              </button>
            ) : null}

            <button onClick={handleDownloadCsv} disabled={downloading}
              className="flex items-center justify-center gap-2 w-full py-3.5 rounded-2xl bg-slate-50 text-slate-700 font-semibold text-[14px] border border-slate-200 disabled:opacity-60">
              {downloading ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />}
              {downloading ? "다운로드 중..." : "데이터 CSV 내보내기"}
            </button>

            {/* JB Connect CTA */}
            <div className="bg-gradient-to-br from-blue-700 to-blue-900 rounded-2xl p-5 text-white mt-1">
              <div className="text-[14px] font-extrabold mb-1">JB금융그룹 상담 연결</div>
              <div className="text-white/70 text-[12px] mb-4 leading-relaxed">
                진단 리포트를 바탕으로 전북은행·광주은행 소상공인 전담 상담을 신청할 수 있습니다.
              </div>
              <button className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-white text-blue-700 font-bold text-[13.5px]">
                상담 신청하기 <ArrowRight size={14} />
              </button>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="flex gap-2 px-5 pb-6">
            <AlertCircle size={13} className="text-slate-300 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-slate-400 leading-relaxed">
              본 리포트는 특정 금융상품 가입을 권유하지 않습니다. 최종 금융 판단은 금융기관 상담·심사를 통해 이루어집니다.
            </p>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────
          DESKTOP LAYOUT  (hidden lg:block)
      ────────────────────────────────────────── */}
      {!loading && (
        <div className="hidden lg:block">
          <div className="bg-white min-h-screen px-10 xl:px-12 2xl:px-16 py-9">

            {/* Page header */}
            <div className="border-b border-slate-100 pb-6">
              <h1 className="text-2xl font-extrabold tracking-tight">상담 준비 리포트</h1>
              <p className="text-sm text-slate-400 mt-0.5">PDF 및 CSV 내보내기 · JB금융그룹 상담 연결</p>
            </div>

            <div className="grid grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-cols-[minmax(0,1fr)_460px] gap-0 divide-x divide-slate-100">
              <div className="pr-8 xl:pr-10 2xl:pr-12">

                {/* Report cover — blue gradient hero, no outer card border */}
                <div className="border-b border-slate-100 py-6">
                  <div className="bg-gradient-to-br from-blue-700 to-blue-900 rounded-xl px-6 py-6">
                    <div className="flex items-center gap-3 mb-4">
                      <FinPilotMark size={36} color="rgba(255,255,255,0.9)" />
                      <div>
                        <div className="text-white/70 text-[10.5px] font-bold tracking-widest">BIZPLOT AGENT</div>
                        <div className="text-white/50 text-[10px]">소상공인 AI CFO Platform</div>
                      </div>
                    </div>
                    <div className="text-white text-[19px] font-extrabold leading-tight">{store.name}</div>
                    <div className="text-white/70 text-[13px] mt-1">상담 준비 리포트 · {new Date().toLocaleDateString("ko-KR")}</div>
                    {state && (
                      <div className="flex gap-0 mt-6 border-t border-white/15">
                        {[
                          { v: `${Math.round(state.health_score ?? 0)}`, l: "사업 건강도" },
                          { v: `${Math.round(state.cash_runway_days ?? 0)}일`, l: "현금 유지" },
                          { v: `${Math.round(state.finance_readiness ?? 0)}%`, l: "금융 준비도" },
                          { v: `${plan?.actions?.length ?? 0}가지`, l: "권장 전략" },
                        ].map((m, i) => (
                          <div key={m.l} className={`flex-1 pt-4 ${i > 0 ? "border-l border-white/15 pl-4" : "pr-4"}`}>
                            <div className="text-white text-2xl font-black tabular-nums">{m.v}</div>
                            <div className="text-white/45 text-[10.5px] font-medium mt-0.5">{m.l}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* TOC — flat list */}
                <div className="border-b border-slate-100 py-6">
                  <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-3">목차</div>
                  <div className="divide-y divide-slate-100">
                    {tocItems.map((item, i) => (
                      <div key={i} className="flex items-center gap-3 py-3">
                        <div className="w-6 h-6 rounded-lg bg-blue-50 text-blue-500 flex items-center justify-center flex-shrink-0 text-[11px] font-bold">{i + 1}</div>
                        <span className="flex-1 text-[13px] font-medium text-slate-700">{item.title}</span>
                        <span className="text-slate-300">{item.icon}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Cause preview — flat list */}
                {diagnosis && diagnosis.causes.length > 0 && (
                  <div className="border-b border-slate-100 py-6">
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-4">
                      <TrendingDown size={13} className="text-red-400" />매출 하락 원인 분석 (미리보기)
                    </div>
                    <div className="divide-y divide-slate-100">
                      {diagnosis.causes.slice(0, 4).map((c, i) => (
                        <div key={i} className="flex items-center gap-3 py-3">
                          <div className="w-32 text-[12px] font-semibold text-slate-600 flex-shrink-0 truncate">{c.factor}</div>
                          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${i === 0 ? "bg-red-500" : i === 1 ? "bg-amber-400" : "bg-blue-400"}`}
                              style={{ width: `${c.contribution}%` }} />
                          </div>
                          <div className="text-[12px] font-bold tabular-nums w-8 text-right">{c.contribution.toFixed(0)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Questions — flat list */}
                <div className="py-6">
                  <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-4">
                    <Shield size={13} className="text-blue-500" />상담 시 확인 질문
                  </div>
                  <div className="divide-y divide-slate-100">
                    {questions.map((q, i) => (
                      <div key={i} className="flex items-start gap-2.5 py-3">
                        <CheckCircle2 size={14} className="text-blue-500 flex-shrink-0 mt-0.5" />
                        <span className="text-[12.5px] text-slate-600 leading-relaxed">{q}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pl-8 xl:pl-10 2xl:pl-12 py-6 space-y-6">

                {/* Finance readiness — plain numbers, no card */}
                {state && (
                  <div className="border-b border-slate-100 pb-6">
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-4">금융 준비도</div>
                    <div className="flex items-center gap-4 mb-4">
                      <HealthGauge score={state.finance_readiness ?? 0} size={72} />
                      <div>
                        <div className="text-3xl font-extrabold tabular-nums text-blue-700">
                          {Math.round(state.finance_readiness ?? 0)}%
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {(state.finance_readiness ?? 0) >= 70 ? "상담 준비 완료" : "리포트 생성 후 향상"}
                        </div>
                      </div>
                    </div>
                    <div className="h-2 bg-blue-50 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                        style={{ width: `${state.finance_readiness ?? 0}%` }} />
                    </div>
                  </div>
                )}

                {/* Download buttons */}
                <div className="border-b border-slate-100 pb-6">
                  <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-4">다운로드</div>
                  {reportStatus === "idle" || reportStatus === "failed" ? (
                    <button onClick={handleCreateReport}
                      className="flex items-center justify-center gap-2 w-full py-3.5 rounded-lg bg-blue-600 text-white font-bold text-[14px] shadow-lg shadow-blue-200 hover:bg-blue-700 mb-3">
                      <FileText size={16} />PDF 리포트 생성
                    </button>
                  ) : reportStatus === "creating" || reportStatus === "pending" ? (
                    <div className="flex items-center justify-center gap-2 w-full py-3.5 rounded-lg bg-blue-100 text-blue-600 font-bold text-[14px] mb-3">
                      <Loader2 size={16} className="animate-spin" />생성 중... ({reportStatus === "pending" ? "처리 중" : "시작 중"})
                    </div>
                  ) : reportStatus === "done" && reportId ? (
                    <button onClick={handleDownloadPdf} disabled={downloading}
                      className="flex items-center justify-center gap-2 w-full py-3.5 rounded-lg bg-blue-600 text-white font-bold text-[14px] shadow-lg shadow-blue-200 hover:bg-blue-700 mb-3 disabled:opacity-60">
                      {downloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                      {downloading ? "다운로드 중..." : "PDF 다운로드"}
                    </button>
                  ) : null}
                  <button onClick={handleDownloadCsv} disabled={downloading}
                    className="flex items-center justify-center gap-2 w-full py-3 rounded-lg bg-slate-50 text-slate-700 font-semibold text-[13.5px] border border-slate-200 hover:bg-slate-100 disabled:opacity-60">
                    {downloading ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />}
                    {downloading ? "다운로드 중..." : "데이터 CSV 내보내기"}
                  </button>
                </div>

                {/* JB Connect — keeps gradient card */}
                <div className="bg-gradient-to-br from-blue-700 to-blue-900 rounded-2xl p-5 text-white">
                  <div className="text-[13px] font-extrabold mb-1">JB금융그룹 상담 연결</div>
                  <div className="text-white/70 text-[11.5px] mb-4 leading-relaxed">
                    진단 리포트를 바탕으로 전북은행·광주은행 소상공인 전담 상담을 신청할 수 있습니다.
                  </div>
                  <button className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-white text-blue-700 font-bold text-[13px] hover:bg-blue-50 transition-colors">
                    상담 신청하기 <ArrowRight size={14} />
                  </button>
                </div>

                {/* Disclaimer */}
                <div className="flex gap-2">
                  <AlertCircle size={13} className="text-slate-400 flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    본 리포트는 특정 금융상품 가입을 권유하지 않습니다. 최종 금융 판단은 금융기관 상담·심사를 통해 이루어집니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
