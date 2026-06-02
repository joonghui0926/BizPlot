"use client"
import { useEffect, useState, useRef } from "react"
import Link from "next/link"
import {
  TrendingDown, TrendingUp, Droplet, Landmark,
  AlertTriangle, ChevronRight, Search, ArrowRight,
  RefreshCw, MessageSquare, BarChart3, Activity, MapPin
} from "lucide-react"
import { getDashboard } from "@/lib/api"
import { useDiagnosis } from "@/components/diagnosis/DiagnosisContext"
import type { Dashboard, Store } from "@/lib/types"
import { HealthGauge } from "@/components/ui/HealthGauge"
import { Badge } from "@/components/ui/Badge"
import { getRiskLevel, getHealthLevel, formatCurrency } from "@/lib/utils"
import { AppShell } from "@/components/layout/AppShell"
import { CashflowSparkline } from "./CashflowSparkline"

interface Props { store: Store }

export function DashboardPage({ store }: Props) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const { diagnosing, progress, start, completedTick } = useDiagnosis()
  const firstTick = useRef(true)

  const load = () => {
    setLoading(true)
    getDashboard(store.id)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [store.id])

  // 진단이 끝나면(다른 탭에서 돌렸어도) 새 결과로 조용히 갱신
  useEffect(() => {
    if (firstTick.current) { firstTick.current = false; return }
    getDashboard(store.id).then(r => setData(r.data)).catch(() => {})
  }, [completedTick])

  const handleDiagnose = () => start(store.id)

  const state = data?.state
  const diagnosis = data?.latest_diagnosis
  const plan = data?.latest_action_plan
  const reviewSummary = data?.review_signal_summary
  const liq = state ? getRiskLevel(state.liquidity_risk ?? 0) : null
  const costRisk = state ? getRiskLevel(state.cost_pressure ?? 0) : null
  const health = state ? getHealthLevel(state.health_score ?? 0) : null
  const topCause = diagnosis?.causes?.[0]
  const today = new Date().toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "long" })

  return (
    <AppShell store={store} unreadCount={state && (state.cash_runway_days ?? 99) < 20 ? 1 : 0}>

      {/* ──────────────────────────────────────────
          LOADING STATE
      ────────────────────────────────────────── */}
      {loading && (
        <div className="p-5 lg:p-7">
          <LoadingSkeleton />
        </div>
      )}

      {/* ──────────────────────────────────────────
          EMPTY STATE
      ────────────────────────────────────────── */}
      {!loading && !state && (
        <EmptyState onDiagnose={handleDiagnose} diagnosing={diagnosing} />
      )}

      {/* ──────────────────────────────────────────
          MOBILE LAYOUT  (lg: hidden)
      ────────────────────────────────────────── */}
      {!loading && state && health && (
        <div className="lg:hidden">
         <div className="bg-white pb-4">

          {/* Greet */}
          <div className="px-5 pt-4 pb-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[11px] text-slate-400 font-medium">{today}</div>
                <h1 className="text-[23px] font-extrabold leading-tight tracking-tight mt-0.5 truncate">{store.name}</h1>
                {store.address && (
                  <div className="flex items-center gap-1.5 mt-1.5 text-[13px] font-semibold text-slate-500">
                    <MapPin size={13} className="text-blue-500 flex-shrink-0" />
                    <span className="truncate">{store.address}</span>
                  </div>
                )}
              </div>
              <button
                onClick={handleDiagnose}
                disabled={diagnosing}
                className="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white text-blue-600 border border-blue-100 font-bold text-[12px] disabled:opacity-50 active:scale-95 transition-transform"
              >
                <RefreshCw size={12} className={diagnosing ? "animate-spin" : ""} />
                {diagnosing ? `${progress}%` : "재진단"}
              </button>
            </div>
          </div>

          {/* Hero: gauge + status */}
          <div className="flex items-center gap-4 px-5 pt-5 pb-5">
            <HealthGauge score={state.health_score ?? 0} size={100} />
            <div className="flex-1 min-w-0">
              <div className={`text-[16px] font-extrabold tracking-tight ${health.color}`}>
                {health.label}
              </div>
              <div className="text-[12px] text-slate-500 mt-1.5 leading-relaxed">
                {topCause
                  ? `최근 매출 흐름에 ‘${topCause.factor}’ 영향이 가장 커요.`
                  : "진단을 실행하면 사업 상태를 확인할 수 있어요."}
              </div>
              <div className="flex items-center gap-1 mt-2.5">
                {(state.revenue_trend ?? 0) >= 0
                  ? <TrendingUp size={12} className="text-green-500" />
                  : <TrendingDown size={12} className="text-red-500" />}
                <span className={`text-[11.5px] font-bold ${(state.revenue_trend ?? 0) >= 0 ? "text-green-600" : "text-red-500"}`}>
                  전월比 {Math.abs((state.revenue_trend ?? 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* 3-col stat tiles — full width */}
          <div className="grid grid-cols-3 gap-px bg-slate-100 border-y border-slate-100">
            <div className="bg-white px-3.5 py-4">
              <div className="text-[10px] text-slate-400 font-semibold mb-2.5 flex items-center gap-1">
                <Droplet size={10} />유동성
              </div>
              <div className={`text-[19px] font-extrabold ${liq?.color ?? "text-slate-600"}`}>
                {liq?.label ?? "–"}
              </div>
            </div>
            <div className="bg-white px-3.5 py-4">
              <div className="text-[10px] text-slate-400 font-semibold mb-2.5 flex items-center gap-1">
                <TrendingDown size={10} />비용 압박
              </div>
              <div className={`text-[19px] font-extrabold ${costRisk?.color ?? "text-slate-600"}`}>
                {costRisk?.label ?? "–"}
              </div>
            </div>
            <div className="bg-white px-3.5 py-4">
              <div className="text-[10px] text-slate-400 font-semibold mb-2.5 flex items-center gap-1">
                <Landmark size={10} />금융 준비
              </div>
              <div className="text-[19px] font-extrabold text-blue-700 tabular-nums">
                {Math.round(state.finance_readiness ?? 0)}%
              </div>
            </div>
          </div>

          {/* Cashflow section */}
          <div className="px-5 pt-5 pb-3">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-[14px] font-extrabold text-slate-800 flex items-center gap-2">
                <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
                현금흐름 전망
              </h3>
              <span className="text-[11px] text-slate-400">
                {state.detail.data_period_days ?? 0}일 데이터 기준
              </span>
            </div>
            <div className="flex items-end justify-between mt-3">
              <div>
                <div className="text-[12px] text-slate-400 font-semibold mb-0.5">현재 구조 유지 시</div>
                <div>
                  <span className={`text-[40px] font-extrabold tabular-nums leading-none ${
                    (state.cash_runway_days ?? 99) < 20 ? "text-red-600" : "text-slate-800"
                  }`}>{Math.round(state.cash_runway_days ?? 0)}</span>
                  <span className="text-[15px] font-bold text-slate-500 ml-1.5">일 후 압박</span>
                </div>
              </div>
              {(state.cash_runway_days ?? 99) < 30 ? (
                <Badge variant="risk" className="text-[10.5px] flex-shrink-0 mb-1">
                  <AlertTriangle size={9} /> 유동성 주의
                </Badge>
              ) : (
                <span className="inline-flex items-center gap-1 text-[10.5px] font-bold text-green-700 bg-green-50 px-2 py-1 rounded-md mb-1">
                  안정 구간
                </span>
              )}
            </div>
            <CashflowSparkline runwayDays={state.cash_runway_days ?? 0} />
          </div>

          {/* Callout — top cause */}
          {topCause && (
            <Link
              href={`/dashboard/${store.id}/diagnosis`}
              className="flex items-center gap-3 mx-5 mt-1 mb-1 px-4 py-3.5 bg-blue-50 rounded-r-xl"
              style={{ borderLeft: "3px solid #2563EB" }}
            >
              <Search size={17} className="text-blue-600 flex-shrink-0" />
              <span className="flex-1 text-[12.5px] font-semibold leading-snug text-slate-700">
                매출 변화가 <b className="font-extrabold text-blue-700">{topCause.factor}</b>에 집중돼 있어요. 원인을 확인해 보세요.
              </span>
              <ChevronRight size={16} className="text-blue-400 flex-shrink-0" />
            </Link>
          )}

          {/* Cause analysis */}
          {diagnosis && diagnosis.causes.length > 0 && (
            <>
              <div className="h-2 bg-slate-50 border-y border-slate-100 mt-4" />
              <div className="flex items-center justify-between px-5 pt-4 pb-1">
                <h3 className="text-[14px] font-extrabold text-slate-800 flex items-center gap-2">
                  <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
                  매출 하락 원인
                </h3>
                <Link
                  href={`/dashboard/${store.id}/diagnosis`}
                  className="text-[12px] text-blue-500 font-semibold flex items-center gap-0.5"
                >
                  전체 보기 <ChevronRight size={13} />
                </Link>
              </div>
              {diagnosis.causes.slice(0, 3).map((cause, i) => (
                <div key={i} className="px-5 py-3.5 border-b border-slate-100 last:border-0">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[13.5px] font-bold text-slate-700">{cause.factor}</span>
                    <span className="text-[15px] font-extrabold tabular-nums">{cause.contribution.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${i === 0 ? "bg-red-500" : i === 1 ? "bg-amber-400" : "bg-blue-400"}`}
                      style={{ width: `${cause.contribution}%`, transition: "width 0.8s ease" }}
                    />
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Strategy preview */}
          {plan && plan.actions.length > 0 && (
            <>
              <div className="h-2 bg-slate-50 border-y border-slate-100 mt-1" />
              <div className="flex items-center justify-between px-5 pt-4 pb-1">
                <h3 className="text-[14px] font-extrabold text-slate-800 flex items-center gap-2">
                  <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
                  추천 전략
                </h3>
                <Link
                  href={`/dashboard/${store.id}/strategy`}
                  className="text-[12px] text-blue-500 font-semibold flex items-center gap-0.5"
                >
                  전체 <ChevronRight size={13} />
                </Link>
              </div>
              {plan.actions.slice(0, 2).map((action, i) => {
                const meta = {
                  operation: { bar: "bg-blue-500", tag: "text-blue-600", label: "운영" },
                  marketing: { bar: "bg-green-500", tag: "text-green-600", label: "마케팅" },
                  finance: { bar: "bg-amber-500", tag: "text-amber-600", label: "금융" },
                }[action.type] ?? { bar: "bg-slate-400", tag: "text-slate-500", label: "기타" }
                return (
                  <div key={i} className="relative flex items-start gap-3 px-5 py-4 border-b border-slate-100 last:border-0">
                    <div className={`absolute left-0 top-4 bottom-4 w-[3px] rounded-r-sm ${meta.bar}`} />
                    <div className="pl-2 flex-1 min-w-0">
                      <div className={`text-[10.5px] font-extrabold mb-0.5 tracking-wide ${meta.tag}`}>{meta.label}</div>
                      <div className="text-[13.5px] font-bold text-slate-800 leading-snug">{action.title}</div>
                      {(action.expected_impact.cash_runway_days_delta || action.expected_impact.revenue_change_pct) && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <TrendingUp size={11} className="text-green-500" />
                          <span className="text-[11px] text-slate-500">
                            {action.expected_impact.cash_runway_days_delta ? (
                              <><span className="font-bold text-green-600">+{action.expected_impact.cash_runway_days_delta}일</span> 현금 유지</>
                            ) : null}
                            {action.expected_impact.revenue_change_pct ? (
                              <><span className="font-bold text-green-600"> +{action.expected_impact.revenue_change_pct}%</span> 매출 기대</>
                            ) : null}
                          </span>
                        </div>
                      )}
                    </div>
                    <ChevronRight size={16} className="text-slate-300 flex-shrink-0 mt-1" />
                  </div>
                )
              })}
            </>
          )}
         </div>{/* /white surface */}

          {/* Report CTA — floats on gradient */}
          <div className="px-5 pt-4">
            <Link
              href={`/dashboard/${store.id}/report`}
              className="flex items-center justify-between w-full px-5 py-4 bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl text-white shadow-[0_18px_36px_-18px_rgba(37,99,235,.6)] active:scale-[.99] transition-transform"
            >
              <div>
                <div className="text-[14px] font-extrabold">상담 준비 리포트</div>
                <div className="text-[11px] text-white/75 mt-0.5">PDF 다운로드 · 금융 상담 자료</div>
              </div>
              <ArrowRight size={18} />
            </Link>
          </div>

          <div className="h-4" />
        </div>
      )}

      {/* ── DESKTOP LAYOUT ── */}
      {!loading && state && (
        <div className="hidden lg:block">
          <div className="bg-white min-h-screen">

            {/* Page header */}
            <div className="flex items-center justify-between px-10 xl:px-12 2xl:px-16 pt-8 pb-6">
              <div>
                <p className="text-xs text-slate-400 font-medium">{today}</p>
                <h1 className="text-2xl font-extrabold tracking-tight mt-0.5 flex items-center gap-3">
                  {store.name}
                  <span className="w-px h-5 bg-slate-200" />
                  <span className="text-base font-medium text-slate-400">
                    {store.address?.split(" ").slice(0, 2).join(" ")}
                  </span>
                </h1>
              </div>
              <button
                onClick={handleDiagnose}
                disabled={diagnosing}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold text-sm rounded-xl shadow-[0_10px_22px_-10px_rgba(37,99,235,.6)] hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <RefreshCw size={14} className={diagnosing ? "animate-spin" : ""} />
                {diagnosing ? `생성 중 ${progress}%` : "재진단"}
              </button>
            </div>

            <div className="band" />

            {/* Metric strip — inset and vertically aligned */}
            <div className="px-10 xl:px-12 2xl:px-16 py-3">
              <div className="grid grid-cols-4 divide-x divide-slate-100">
                <div className="min-h-[164px] flex items-center justify-center px-6 xl:px-8">
                  <div className="flex items-center justify-center gap-6 w-full max-w-[310px]">
                    <HealthGauge score={state.health_score ?? 0} size={88} showLabel={false} />
                    <div className="min-w-0 text-left">
                      <p className="text-[10.5px] text-slate-400 font-semibold uppercase tracking-wide">사업 건강도</p>
                      <p className="text-xl font-extrabold mt-0.5">
                        {(state.health_score ?? 0) >= 75 ? "양호" : (state.health_score ?? 0) >= 50 ? "주의" : "위험"}
                      </p>
                      <div className="flex items-center gap-1 mt-1">
                        {(state.revenue_trend ?? 0) >= 0
                          ? <TrendingUp size={11} className="text-green-500" />
                          : <TrendingDown size={11} className="text-red-500" />}
                        <span className={`text-[11px] font-semibold ${(state.revenue_trend ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                          전월比 {Math.abs((state.revenue_trend ?? 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="min-h-[164px] flex items-center justify-center px-6 xl:px-8">
                  <div className="w-full max-w-[220px] text-center">
                    <p className="text-[10.5px] text-slate-400 font-semibold uppercase tracking-wide flex items-center justify-center gap-1 mb-2">
                      <Droplet size={11} />현금 유지 기간
                    </p>
                    <p className={`text-[48px] leading-none font-extrabold tabular-nums ${
                      (state.cash_runway_days ?? 99) < 20 ? "text-red-600"
                      : (state.cash_runway_days ?? 99) < 40 ? "text-amber-600"
                      : "text-slate-800"}`}>
                      {Math.round(state.cash_runway_days ?? 0)}<span className="text-xl font-bold ml-1.5">일</span>
                    </p>
                    {(state.cash_runway_days ?? 99) < 30 && (
                      <Badge variant="risk" className="mt-2 text-[10px]"><AlertTriangle size={9} />유동성 주의</Badge>
                    )}
                  </div>
                </div>
                <div className="min-h-[164px] flex items-center justify-center px-6 xl:px-8">
                  <div className="w-full max-w-[240px]">
                    <p className="text-[10.5px] text-slate-400 font-semibold uppercase tracking-wide text-center mb-3">위험 지표</p>
                    {[
                      { label: "유동성 위험", value: liq, score: state.liquidity_risk ?? 0 },
                      { label: "비용 압박도", value: costRisk, score: state.cost_pressure ?? 0 },
                    ].map(m => (
                      <div key={m.label} className="mb-2 last:mb-0">
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-500">{m.label}</span>
                          <span className={`font-bold ${m.value?.color}`}>{m.value?.label}</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-500 ${m.score >= 70 ? "bg-red-500" : m.score >= 40 ? "bg-amber-400" : "bg-green-500"}`}
                            style={{ width: `${m.score}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="min-h-[164px] flex items-center justify-center px-6 xl:px-8">
                  <div className="w-full max-w-[260px] text-center">
                    <p className="text-[10.5px] text-slate-400 font-semibold uppercase tracking-wide flex items-center justify-center gap-1 mb-2">
                      <Landmark size={11} />금융 준비도
                    </p>
                    <p className="text-[48px] leading-none font-extrabold tabular-nums text-blue-700">
                      {Math.round(state.finance_readiness ?? 0)}<span className="text-xl font-bold">%</span>
                    </p>
                    <div className="mt-2.5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all duration-700"
                        style={{ width: `${state.finance_readiness ?? 0}%` }} />
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1.5">
                      {(state.finance_readiness ?? 0) >= 70 ? "상담 준비 완료" : "리포트 생성으로 향상 가능"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="band" />

            {/* 2-col content */}
            <div className="grid grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-cols-[minmax(0,1fr)_460px] gap-0">
              {/* Left */}
              <div className="border-r border-slate-100 px-10 xl:px-12 2xl:px-16 py-9 space-y-9">
                {/* Cashflow */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                      <Activity size={13} className="text-blue-500" />현금흐름 예측
                    </h2>
                    <span className="text-[11px] text-slate-400">{state.detail.data_period_days ?? 0}일 데이터 기준</span>
                  </div>
                  <div className="flex items-baseline gap-3 mb-5">
                    <span className={`text-5xl font-extrabold tabular-nums tracking-tight ${(state.cash_runway_days ?? 99) < 20 ? "text-red-600" : "text-slate-800"}`}>
                      {Math.round(state.cash_runway_days ?? 0)}
                    </span>
                    <span className="text-slate-500 font-semibold text-lg">일 후 유동성 압박</span>
                    {(state.detail.recent_revenue_30d ?? 0) > 0 && (
                      <span className="ml-auto text-[12px] text-slate-400 font-medium">
                        최근 30일 {formatCurrency(state.detail.recent_revenue_30d ?? 0)}
                      </span>
                    )}
                  </div>
                  <CashflowSparkline runwayDays={state.cash_runway_days ?? 0} />
                </div>

                {/* Cause analysis */}
                {diagnosis && diagnosis.causes.length > 0 && (
                  <div className="pt-6 border-t border-slate-100">
                    <div className="flex items-center justify-between mb-5">
                      <h2 className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        <Search size={13} className="text-blue-500" />매출 하락 원인
                      </h2>
                      <Link href={`/dashboard/${store.id}/diagnosis`} className="text-[12px] text-blue-500 font-semibold flex items-center gap-1">
                        전체 보기 <ChevronRight size={12} />
                      </Link>
                    </div>
                    <div className="space-y-4">
                      {diagnosis.causes.slice(0, 4).map((cause, i) => (
                        <div key={i}>
                          <div className="flex justify-between text-[13px] mb-1.5">
                            <span className="font-semibold text-slate-700">{cause.factor}</span>
                            <span className="font-extrabold tabular-nums">{cause.contribution.toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${i === 0 ? "bg-red-500" : i === 1 ? "bg-amber-400" : i === 2 ? "bg-blue-400" : "bg-slate-300"}`}
                              style={{ width: `${cause.contribution}%`, transition: "width 0.8s ease" }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right */}
              <div className="px-8 xl:px-10 2xl:px-12 py-9 space-y-6">
                {plan && plan.actions.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest">추천 전략</h2>
                      <Link href={`/dashboard/${store.id}/strategy`} className="text-[12px] text-blue-500 font-semibold flex items-center gap-1">
                        전체 <ChevronRight size={12} />
                      </Link>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {plan.actions.slice(0, 4).map((action, i) => {
                        const meta = {
                          operation: { bar: "bg-blue-500", tag: "text-blue-600", label: "운영" },
                          marketing: { bar: "bg-green-500", tag: "text-green-600", label: "마케팅" },
                          finance: { bar: "bg-amber-500", tag: "text-amber-600", label: "금융" },
                        }[action.type] ?? { bar: "bg-slate-400", tag: "text-slate-500", label: "기타" }
                        return (
                          <div key={i} className="relative py-3 pl-3.5">
                            <div className={`absolute left-0 top-3.5 bottom-3.5 w-[3px] rounded-r ${meta.bar}`} />
                            <p className={`text-[10px] font-extrabold tracking-wide mb-0.5 ${meta.tag}`}>{meta.label}</p>
                            <p className="text-[13px] font-semibold text-slate-800 leading-snug">{action.title}</p>
                            {(action.expected_impact.cash_runway_days_delta || action.expected_impact.revenue_change_pct) && (
                              <p className="text-[11px] text-green-600 font-semibold mt-0.5 flex items-center gap-1">
                                <TrendingUp size={10} />
                                {action.expected_impact.cash_runway_days_delta ? `+${action.expected_impact.cash_runway_days_delta}일 현금` : ""}
                                {action.expected_impact.revenue_change_pct ? ` +${action.expected_impact.revenue_change_pct}% 매출` : ""}
                              </p>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    <Link href={`/dashboard/${store.id}/strategy`}
                      className="flex items-center justify-center gap-1.5 mt-4 w-full py-2.5 rounded-lg bg-blue-600 text-white text-[13px] font-bold">
                      시뮬레이션 실행 <ArrowRight size={13} />
                    </Link>
                  </div>
                )}

                {reviewSummary && (
                  <div className="pt-5 border-t border-slate-100">
                    <h2 className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-1.5 mb-3">
                      <MessageSquare size={12} className="text-amber-500" />리뷰 신호
                    </h2>
                    {reviewSummary.sentiment_score !== null && (
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-3xl font-extrabold tabular-nums">
                          {((reviewSummary.sentiment_score + 1) * 50).toFixed(0)}
                        </span>
                        <div className="flex-1">
                          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-red-400 via-amber-400 to-green-500 rounded-full"
                              style={{ width: `${((reviewSummary.sentiment_score + 1) * 50)}%` }} />
                          </div>
                          <p className="text-[10.5px] text-slate-400 mt-0.5">감성 점수 /100</p>
                        </div>
                      </div>
                    )}
                    {reviewSummary.negative_keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {reviewSummary.negative_keywords.slice(0, 4).map(kw => (
                          <span key={kw} className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-md">{kw}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <Link href={`/dashboard/${store.id}/report`}
                  className="flex items-center justify-between w-full px-5 py-4 bg-gradient-to-br from-blue-700 to-blue-900 rounded-xl text-white mt-2">
                  <div>
                    <p className="text-[13.5px] font-extrabold">상담 준비 리포트</p>
                    <p className="text-[11px] text-white/70 mt-0.5">PDF + CSV 다운로드</p>
                  </div>
                  <ArrowRight size={18} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}

function LoadingSkeleton() {
  return (
    <div className="w-full px-10 xl:px-12 2xl:px-16 py-8 space-y-6">
      <div className="h-8 bg-slate-100 rounded animate-pulse w-64" />
      <div className="grid grid-cols-4 border border-slate-100">
        {[1,2,3,4].map(i => <div key={i} className="h-28 bg-slate-50 animate-pulse border-r border-slate-100 last:border-0" />)}
      </div>
      <div className="grid grid-cols-2 gap-10">
        <div className="space-y-4">
          <div className="h-40 bg-slate-50 animate-pulse" />
          <div className="h-32 bg-slate-50 animate-pulse" />
        </div>
        <div className="h-64 bg-slate-50 animate-pulse" />
      </div>
    </div>
  )
}

function EmptyState({ onDiagnose, diagnosing }: { onDiagnose: () => void; diagnosing: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] gap-5">
      <div className="w-14 h-14 rounded-xl bg-blue-50 flex items-center justify-center">
        <BarChart3 size={26} className="text-blue-500" />
      </div>
      <div className="text-center">
        <p className="text-xl font-extrabold mb-2">아직 진단 데이터가 없어요</p>
        <p className="text-sm text-slate-400 leading-relaxed mb-6">
          매출·비용 데이터를 업로드하고 사업 상태를 진단해 보세요.<br />
          공공 데이터(상권·날씨)와 결합해 원인을 분석합니다.
        </p>
      </div>
      <button onClick={onDiagnose} disabled={diagnosing}
        className="px-8 py-4 rounded-xl bg-blue-600 text-white font-bold text-[15px] disabled:opacity-60">
        {diagnosing ? "진단 중..." : "지금 진단하기"}
      </button>
    </div>
  )
}
