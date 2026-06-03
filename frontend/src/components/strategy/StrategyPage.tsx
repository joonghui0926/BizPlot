"use client"
import { useEffect, useState, useRef } from "react"
import {
  Package, Ticket, FileText, ShieldCheck,
  TrendingUp, ArrowRight, Check, CircleDollarSign, BarChart2,
  ChevronDown, Sparkles
} from "lucide-react"
import { getDashboard, generateStrategy, runSimulation } from "@/lib/api"
import { useDiagnosis } from "@/components/diagnosis/DiagnosisContext"
import type { Dashboard, Store as StoreType, Action, ActionPlan, Simulation, Cause, BusinessState } from "@/lib/types"
import { AppShell } from "@/components/layout/AppShell"
import { buildActionXai, buildSimulationXai, type XaiLine } from "@/lib/strategyXai"

interface Props { store: StoreType }

const ACTION_META: Record<string, { icon: React.ReactNode; label: string; bar: string; icon_cls: string; tag_cls: string }> = {
  operation: { icon: <Package size={18} />, label: "운영",    bar: "bg-blue-500",  icon_cls: "bg-blue-50 text-blue-600",  tag_cls: "text-blue-600" },
  marketing: { icon: <Ticket size={18} />,  label: "마케팅", bar: "bg-green-500", icon_cls: "bg-green-50 text-green-600", tag_cls: "text-green-600" },
  finance:   { icon: <FileText size={18} />,label: "금융",   bar: "bg-amber-500", icon_cls: "bg-amber-50 text-amber-600", tag_cls: "text-amber-600" },
}

export function StrategyPage({ store }: Props) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [plan, setPlan] = useState<ActionPlan | null>(null)
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const { completedTick } = useDiagnosis()
  const firstTick = useRef(true)

  useEffect(() => {
    getDashboard(store.id).then(r => {
      setData(r.data)
      if (r.data.latest_action_plan) {
        setPlan(r.data.latest_action_plan)
        setSelected(new Set<string>(r.data.latest_action_plan.actions.map((a: Action) => a.id)))
      }
    }).finally(() => setLoading(false))
  }, [store.id])

  // 진단 완료 시(다른 탭에서 돌렸어도) 새 전략으로 갱신
  useEffect(() => {
    if (firstTick.current) { firstTick.current = false; return }
    getDashboard(store.id).then(r => {
      setData(r.data)
      if (r.data.latest_action_plan) {
        setPlan(r.data.latest_action_plan)
        setSelected(new Set<string>(r.data.latest_action_plan.actions.map((a: Action) => a.id)))
      }
    }).catch(() => {})
  }, [completedTick])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const r = await generateStrategy(store.id)
      setPlan(r.data)
      setSelected(new Set<string>(r.data.actions.map((a: Action) => a.id)))
    } finally {
      setGenerating(false)
    }
  }

  const toggle = (id: string) =>
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })

  const toggleExpand = (id: string) =>
    setExpanded(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })

  const handleSimulate = async () => {
    if (!plan) return
    setSimulating(true)
    try {
      const r = await runSimulation(store.id, {
        action_plan_id: plan.id,
        selected_action_ids: Array.from(selected),
      })
      setSimulation(r.data)
    } finally {
      setSimulating(false)
    }
  }

  const actions = plan?.actions ?? []
  const combined = simulation?.scenarios.find(s => s.action_id === "combined")
  const state: BusinessState | null = data?.state ?? null
  const causes: Cause[] = data?.latest_diagnosis?.causes ?? []
  const simXai = simulation ? buildSimulationXai(simulation) : []

  return (
    <AppShell store={store}>

      {loading && (
        <div className="p-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-40 bg-white rounded-2xl animate-pulse border border-slate-100" />)}
        </div>
      )}

      {/* ──────────────────────────────────────────
          MOBILE LAYOUT  (lg:hidden)
      ────────────────────────────────────────── */}
      {!loading && (
        <div className="lg:hidden bg-white min-h-screen pb-4">

          {/* Simulation result (if available) */}
          {combined && (
            <>
              <div className="mx-5 mt-4 mb-0 bg-gradient-to-br from-green-600 to-emerald-700 rounded-2xl p-4 text-white shadow-lg shadow-green-200">
                <div className="text-[11px] font-bold opacity-75 mb-2">전략 적용 시뮬레이션</div>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className="text-white/70 text-[10px]">현재</div>
                    <div className="text-3xl font-extrabold tabular-nums">{Math.round(combined.cash_runway_days_before)}<span className="text-sm ml-0.5">일</span></div>
                  </div>
                  <ArrowRight size={18} className="opacity-60" />
                  <div className="text-center">
                    <div className="text-white/70 text-[10px]">적용 후</div>
                    <div className="text-3xl font-extrabold tabular-nums">{Math.round(combined.cash_runway_days_after)}<span className="text-sm ml-0.5">일</span></div>
                  </div>
                  <div className="ml-auto text-right">
                    <div className="text-white/70 text-[10px]">개선</div>
                    <div className="text-2xl font-extrabold">+{Math.round(combined.cash_runway_days_after - combined.cash_runway_days_before)}일</div>
                  </div>
                </div>
              </div>

              {/* 시뮬레이션 XAI — 왜 이렇게 변하는지 산출 과정 */}
              {simXai.length > 0 && (
                <div className="px-5 pt-4">
                  <div className="text-[11.5px] font-extrabold text-slate-700 flex items-center gap-1.5 mb-2.5">
                    <Sparkles size={13} className="text-green-600" />이렇게 계산했어요
                  </div>
                  <XaiList lines={simXai} variant="green" />
                </div>
              )}

              <div className="h-2 bg-slate-100 border-y border-slate-100 mt-4" />
            </>
          )}

          {/* Strategy actions */}
          {actions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4 px-5">
              <BarChart2 size={32} className="text-slate-300" />
              <div className="text-slate-500 font-semibold">전략을 생성해 주세요</div>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-6 py-3.5 rounded-2xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-50"
              >
                {generating ? "생성 중..." : "전략 생성하기"}
              </button>
            </div>
          ) : (
            <>
              <div className="px-5 pt-5 pb-2">
                <h2 className="text-[19px] font-extrabold tracking-tight leading-snug">지금 실행하면 좋은<br />행동 {actions.length}가지</h2>
                <p className="text-[12.5px] text-slate-500 mt-1.5">선택한 전략으로 현금흐름 변화를 시뮬레이션할 수 있어요.</p>
              </div>

              <div className="px-5 space-y-3 pt-1">
                {actions.map(action => {
                  const meta = ACTION_META[action.type] ?? ACTION_META.operation
                  const impact = action.expected_impact
                  const isSelected = selected.has(action.id)
                  const isOpen = expanded.has(action.id)
                  return (
                    <div
                      key={action.id}
                      className={`relative rounded-2xl border bg-white transition-all ${
                        isSelected
                          ? "border-blue-300 shadow-[0_10px_26px_-14px_rgba(37,99,235,.55)]"
                          : "border-slate-200 shadow-[0_4px_14px_-10px_rgba(20,30,55,.3)]"
                      }`}
                    >
                      <span className={`absolute left-0 top-4 bottom-4 w-1 rounded-r ${meta.bar}`} />
                      <div className="flex items-start gap-3 p-4">
                        <button onClick={() => toggleExpand(action.id)} className="flex items-start gap-3 flex-1 min-w-0 text-left">
                          <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ml-1.5 ${meta.icon_cls}`}>
                            {meta.icon}
                          </span>
                          <span className="flex-1 min-w-0">
                            <span className={`block text-[10.5px] font-extrabold tracking-wide ${meta.tag_cls}`}>{meta.label}</span>
                            <span className="block text-[14.5px] font-bold text-slate-800 leading-snug mt-0.5">{action.title}</span>
                            <span className={`block text-[11.5px] text-slate-400 mt-1 leading-relaxed ${isOpen ? "" : "line-clamp-2"}`}>{action.description}</span>
                            {(impact.cash_runway_days_delta || impact.revenue_change_pct) && (
                              <span className="flex items-center gap-1 mt-1.5">
                                <TrendingUp size={11} className="text-green-500" />
                                <span className="text-[11px] text-slate-500">
                                  {impact.cash_runway_days_delta ? <><b className="font-bold text-green-600">+{impact.cash_runway_days_delta}일</b> 현금 유지</> : null}
                                  {impact.revenue_change_pct ? <><b className="font-bold text-green-600"> +{impact.revenue_change_pct}%</b> 매출 기대</> : null}
                                </span>
                              </span>
                            )}
                            <span className={`inline-flex items-center gap-1 mt-2 text-[11px] font-bold ${isOpen ? "text-slate-400" : "text-blue-600"}`}>
                              <Sparkles size={11} />
                              {isOpen ? "근거 접기" : "왜 이만큼 변할까?"}
                              <ChevronDown size={12} className={`transition-transform ${isOpen ? "rotate-180" : ""}`} />
                            </span>
                          </span>
                        </button>
                        <button
                          onClick={() => toggle(action.id)}
                          aria-label="시뮬레이션 대상으로 선택"
                          className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 self-start transition-colors ${
                            isSelected ? "border-blue-600 bg-blue-600" : "border-slate-200 bg-white"
                          }`}
                        >
                          {isSelected && <Check size={13} className="text-white" />}
                        </button>
                      </div>
                      {isOpen && (
                        <div className="px-4 pb-4">
                          <XaiList lines={buildActionXai(action, state, causes)} />
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Risk notice */}
              <div className="flex items-start gap-2.5 mx-5 mt-3 px-4 py-3 bg-slate-50 rounded-xl">
                <ShieldCheck size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />
                <p className="text-[11.5px] text-slate-400 leading-relaxed">
                  모든 추천은 근거 검증을 거쳤으며, 특정 금융상품 가입을 권유하지 않습니다.
                </p>
              </div>

              {/* Simulate button */}
              <div className="px-5 py-5">
                <button
                  onClick={handleSimulate}
                  disabled={simulating || selected.size === 0}
                  className="flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-40"
                >
                  {simulating ? "시뮬레이션 중..." : <><BarChart2 size={18} />선택 전략 시뮬레이션</>}
                </button>
              </div>

              {/* Scenario breakdown */}
              {simulation && simulation.scenarios.filter(s => s.action_id !== "combined").length > 0 && (
                <>
                  <div className="h-2 bg-slate-100 border-y border-slate-100" />
                  <div className="px-5 pt-4 pb-1">
                    <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
                      <span className="w-[3px] h-[14px] bg-green-500 rounded-sm flex-shrink-0" />
                      전략별 효과
                    </h3>
                  </div>
                  {simulation.scenarios.filter(s => s.action_id !== "combined").map((s, i) => (
                    <div key={i} className="px-5 py-3.5 border-b border-slate-100 last:border-0">
                      <div className="font-semibold text-slate-700 text-[13px] mb-1">{s.action_title}</div>
                      <div className="flex gap-4 text-[11.5px] text-slate-400">
                        <span>현금 {Math.round(s.cash_runway_days_before)}→<span className="text-green-600 font-bold">{Math.round(s.cash_runway_days_after)}일</span></span>
                        {s.revenue_change_pct !== 0 && <span>매출 <span className="text-green-600 font-bold">{s.revenue_change_pct > 0 ? "+" : ""}{s.revenue_change_pct}%</span></span>}
                      </div>
                    </div>
                  ))}
                </>
              )}

              {/* RAG References */}
              {plan && plan.rag_references.length > 0 && (
                <>
                  <div className="h-2 bg-slate-100 border-y border-slate-100" />
                  <div className="px-5 pt-4 pb-1">
                    <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
                      <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
                      <CircleDollarSign size={14} className="text-blue-500" />관련 정책자금 정보
                    </h3>
                  </div>
                  {plan.rag_references.map((ref, i) => (
                    <div key={i} className="px-5 py-3 border-b border-slate-100 last:border-0">
                      <div className="text-[12.5px] text-blue-600 leading-relaxed">
                        {ref.title || ref.content.slice(0, 80)}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </>
          )}

          <div className="h-4" />
        </div>
      )}

      {/* ──────────────────────────────────────────
          DESKTOP LAYOUT  (hidden lg:block)
      ────────────────────────────────────────── */}
      {!loading && (
        <div className="hidden lg:block">
          <div className="bg-white min-h-screen px-10 xl:px-12 2xl:px-16 py-9">

            {/* Page header */}
            <div className="border-b border-slate-100 pb-6 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight">추천 전략</h1>
                <p className="text-sm text-slate-400 mt-0.5">운영·마케팅·금융 준비를 하나의 실행 계획으로 묶었습니다.</p>
              </div>
              {actions.length === 0 && (
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {generating ? "생성 중..." : "전략 생성하기"}
                </button>
              )}
            </div>

            <div className="grid grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-cols-[minmax(0,1fr)_460px] gap-0 divide-x divide-slate-100">
              <div className="pr-8 xl:pr-10 2xl:pr-12">
                {actions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20">
                    <BarChart2 size={32} className="text-slate-300 mb-3" />
                    <div className="text-slate-500 font-semibold">전략을 생성해 주세요</div>
                    <button onClick={handleGenerate} disabled={generating}
                      className="mt-4 px-6 py-3 rounded-lg bg-blue-600 text-white font-bold text-sm disabled:opacity-50">
                      {generating ? "생성 중..." : "전략 생성하기"}
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Action list */}
                    <div className="border-b border-slate-100 py-6">
                      <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-4">추천 전략 {actions.length}가지</div>
                      <div className="divide-y divide-slate-100">
                        {actions.map(action => (
                          <ActionCard
                            key={action.id}
                            action={action}
                            checked={selected.has(action.id)}
                            onToggle={() => toggle(action.id)}
                            open={expanded.has(action.id)}
                            onToggleOpen={() => toggleExpand(action.id)}
                            xai={buildActionXai(action, state, causes)}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Risk notice */}
                    <div className="border-b border-slate-100 py-4 flex items-start gap-2.5">
                      <ShieldCheck size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-slate-400 leading-relaxed">
                        모든 추천은 근거 검증을 거쳤으며, 특정 금융상품 가입을 권유하지 않습니다.
                      </p>
                    </div>

                    {/* Simulate button */}
                    <div className="py-6">
                      <button
                        onClick={handleSimulate}
                        disabled={simulating || selected.size === 0}
                        className="flex items-center justify-center gap-2 w-full py-3.5 rounded-lg bg-blue-600 text-white font-bold text-[15px] shadow-lg shadow-blue-200 disabled:opacity-40 hover:bg-blue-700 transition-colors"
                      >
                        {simulating ? "시뮬레이션 중..." : <><BarChart2 size={18} />선택 전략 시뮬레이션</>}
                      </button>
                    </div>

                    {/* Scenario breakdown */}
                    {simulation && simulation.scenarios.filter(s => s.action_id !== "combined").length > 0 && (
                      <div className="border-t border-slate-100 pt-6">
                        <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-4">전략별 효과</div>
                        <div className="divide-y divide-slate-100">
                          {simulation.scenarios.filter(s => s.action_id !== "combined").map((s, i) => (
                            <div key={i} className="py-3 text-xs">
                              <div className="font-semibold text-slate-700 mb-0.5">{s.action_title}</div>
                              <div className="flex gap-3 text-slate-400">
                                <span>현금 {Math.round(s.cash_runway_days_before)}→<span className="text-green-600 font-bold">{Math.round(s.cash_runway_days_after)}일</span></span>
                                {s.revenue_change_pct !== 0 && <span>매출 <span className="text-green-600 font-bold">{s.revenue_change_pct > 0 ? "+" : ""}{s.revenue_change_pct}%</span></span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="pl-8 xl:pl-10 2xl:pl-12 space-y-6 py-6">
                {/* Simulation result card — keeps green gradient */}
                {combined && (
                  <div className="bg-gradient-to-br from-green-600 to-emerald-700 rounded-2xl p-5 text-white shadow-lg shadow-green-200">
                    <div className="text-[11px] font-bold opacity-75 mb-2">전략 적용 시뮬레이션</div>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="text-center">
                        <div className="text-white/70 text-[10px]">현재</div>
                        <div className="text-3xl font-extrabold tabular-nums">{Math.round(combined.cash_runway_days_before)}<span className="text-sm ml-0.5">일</span></div>
                      </div>
                      <ArrowRight size={18} className="opacity-60" />
                      <div className="text-center">
                        <div className="text-white/70 text-[10px]">적용 후</div>
                        <div className="text-3xl font-extrabold tabular-nums">{Math.round(combined.cash_runway_days_after)}<span className="text-sm ml-0.5">일</span></div>
                      </div>
                      <div className="ml-auto text-right">
                        <div className="text-white/70 text-[10px]">개선</div>
                        <div className="text-2xl font-extrabold">+{Math.round(combined.cash_runway_days_after - combined.cash_runway_days_before)}일</div>
                      </div>
                    </div>
                    <div className="flex gap-4 text-xs pt-3 border-t border-white/20">
                      {combined.revenue_change_pct !== 0 && (
                        <div><span className="opacity-70">매출</span> <span className="font-bold">{combined.revenue_change_pct > 0 ? "+" : ""}{combined.revenue_change_pct.toFixed(1)}%</span></div>
                      )}
                      {combined.cost_change_pct !== 0 && (
                        <div><span className="opacity-70">비용</span> <span className="font-bold">{combined.cost_change_pct > 0 ? "+" : ""}{combined.cost_change_pct.toFixed(1)}%</span></div>
                      )}
                    </div>
                  </div>
                )}

                {/* 시뮬레이션 XAI — 왜 이렇게 변하는지 산출 과정 */}
                {simXai.length > 0 && (
                  <div>
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-3">
                      <Sparkles size={13} className="text-green-600" />이렇게 계산했어요
                    </div>
                    <XaiList lines={simXai} variant="green" />
                  </div>
                )}

                {/* RAG references — flat text */}
                {plan && plan.rag_references.length > 0 && (
                  <div>
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-3">
                      <CircleDollarSign size={13} />관련 정책자금 정보
                    </div>
                    <div className="divide-y divide-slate-100">
                      {plan.rag_references.map((ref, i) => (
                        <div key={i} className="py-2.5 text-[12px] text-blue-600 leading-relaxed">
                          {ref.title || ref.content.slice(0, 60)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}

function ActionCard({ action, checked, onToggle, open, onToggleOpen, xai }: {
  action: Action; checked: boolean; onToggle: () => void
  open: boolean; onToggleOpen: () => void; xai: XaiLine[]
}) {
  const meta = ACTION_META[action.type] ?? ACTION_META.operation
  const impact = action.expected_impact

  return (
    <div className="relative py-4">
      <div className={`absolute left-0 top-4 w-[3px] rounded-r-sm ${meta.bar} ${open ? "bottom-auto h-10" : "bottom-4"}`} />
      <div className="flex items-start gap-3">
        <button onClick={onToggleOpen} className="pl-4 flex-1 min-w-0 text-left">
          <div className={`text-[10.5px] font-extrabold tracking-wide mb-0.5 ${meta.tag_cls}`}>{meta.label}</div>
          <div className="text-[13.5px] font-bold tracking-tight leading-snug">{action.title}</div>
          <div className={`text-[11.5px] text-slate-400 mt-0.5 leading-relaxed ${open ? "" : "line-clamp-2"}`}>{action.description}</div>
          {(impact.cash_runway_days_delta || impact.revenue_change_pct) && (
            <div className="flex items-center gap-1 mt-1.5">
              <TrendingUp size={11} className="text-green-500" />
              <span className="text-[11px] text-slate-500">
                {impact.cash_runway_days_delta ? <><span className="font-bold text-green-600">+{impact.cash_runway_days_delta}일</span> 현금 유지</> : null}
                {impact.revenue_change_pct ? <><span className="font-bold text-green-600"> +{impact.revenue_change_pct}%</span> 매출 기대</> : null}
              </span>
            </div>
          )}
          <span className={`inline-flex items-center gap-1 mt-2 text-[11px] font-bold ${open ? "text-slate-400" : "text-blue-600"}`}>
            <Sparkles size={11} />
            {open ? "근거 접기" : "왜 이만큼 변할까?"}
            <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
          </span>
        </button>
        <button
          onClick={onToggle}
          aria-label="시뮬레이션 대상으로 선택"
          className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 self-start transition-colors ${
            checked ? "border-blue-600 bg-blue-600" : "border-slate-200 bg-white"
          }`}
        >
          {checked && <Check size={13} className="text-white" />}
        </button>
      </div>
      {open && (
        <div className="pl-4 mt-3">
          <XaiList lines={xai} />
        </div>
      )}
    </div>
  )
}

// XAI 설명 줄들을 회색 박스 없이 좌측 레일 + 라벨로 평면 렌더 (진단 증거와 동일 톤)
function XaiList({ lines, variant = "blue" }: { lines: XaiLine[]; variant?: "blue" | "green" }) {
  if (!lines.length) return null
  const rail = variant === "green" ? "border-green-100" : "border-blue-100"
  const label = variant === "green" ? "text-green-600/70" : "text-blue-500/70"
  return (
    <div className={`border-l-2 ${rail} pl-3.5 space-y-2.5`}>
      {lines.map((l, i) => (
        <div key={i}>
          <div className={`text-[9.5px] font-extrabold uppercase tracking-wider ${label} mb-0.5`}>{l.label}</div>
          <div className="text-[12px] text-slate-600 leading-relaxed">{l.text}</div>
        </div>
      ))}
    </div>
  )
}
