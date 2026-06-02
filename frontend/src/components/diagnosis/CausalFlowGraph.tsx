"use client"
/**
 * CausalFlowGraph — 매출 변화의 "인과 귀속 그래프"를 시각화한다.
 *
 *      증거(evidence)  ─►  요인(factor)  ─►  매출·가게 변화(outcome)
 *
 * 기여도(%)가 LLM의 추측이 아니라 측정된 증거의 합으로 유도된다는 점(가산성·접지)을
 * 한눈에 보여주는 것이 목적. 데스크탑은 측정 기반 SVG 엣지로 실제 DAG를, 모바일은
 * 세로 흐름으로 동일한 인과 사슬을 표현한다. (flat 디자인, rounded box 떡칠 지양)
 */
import { useLayoutEffect, useRef, useState } from "react"
import { Store, Clock, CloudRain, MessageSquare, Coins, Users, TrendingDown, TrendingUp, ArrowRight } from "lucide-react"
import type { Cause } from "@/lib/types"

interface Props {
  causes: Cause[]
  trendPct: number          // 매출 변화율 (%, 음수=감소)
  runwayDays?: number | null // 현금 유지 가능 일수
}

// 그룹별 색상 — SVG(hex) + Tailwind 클래스 모두 필요
const GROUP_STYLE: Record<string, { hex: string; text: string; bar: string; dot: string; icon: React.ReactNode }> = {
  competition: { hex: "#e11d48", text: "text-rose-600",    bar: "bg-rose-500",    dot: "bg-rose-500",    icon: <Store size={14} /> },
  timeofday:   { hex: "#d97706", text: "text-amber-600",   bar: "bg-amber-500",   dot: "bg-amber-500",   icon: <Clock size={14} /> },
  weather:     { hex: "#0284c7", text: "text-sky-600",     bar: "bg-sky-500",     dot: "bg-sky-500",     icon: <CloudRain size={14} /> },
  review:      { hex: "#7c3aed", text: "text-violet-600",  bar: "bg-violet-500",  dot: "bg-violet-500",  icon: <MessageSquare size={14} /> },
  price:       { hex: "#059669", text: "text-emerald-600", bar: "bg-emerald-500", dot: "bg-emerald-500", icon: <Coins size={14} /> },
  demand:      { hex: "#475569", text: "text-slate-600",   bar: "bg-slate-500",   dot: "bg-slate-500",   icon: <Users size={14} /> },
  default:     { hex: "#2563eb", text: "text-blue-600",    bar: "bg-blue-500",    dot: "bg-blue-500",    icon: <Users size={14} /> },
}
const styleOf = (c: Cause) => GROUP_STYLE[c.group ?? "default"] ?? GROUP_STYLE.default
const confLabel = (c: string) => (c === "high" ? "높음" : c === "low" ? "낮음" : "중간")

// ────────────────────────────────────────────────────────────────────────────
// DESKTOP — 측정 기반 SVG DAG (증거 → 요인 → 결과)
// ────────────────────────────────────────────────────────────────────────────
export function CausalFlowDesktop({ causes, trendPct, runwayDays }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const factorRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const evRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const outRef = useRef<HTMLDivElement>(null)
  const [edges, setEdges] = useState<{ d: string; w: number; color: string; key: string }[]>([])
  const [box, setBox] = useState({ w: 0, h: 0 })

  useLayoutEffect(() => {
    const recompute = () => {
      const wrap = wrapRef.current, out = outRef.current
      if (!wrap || !out) return
      const wb = wrap.getBoundingClientRect()
      const center = (el: Element, side: "l" | "r") => {
        const b = el.getBoundingClientRect()
        return { x: (side === "r" ? b.right : b.left) - wb.left, y: b.top - wb.top + b.height / 2 }
      }
      const curve = (x1: number, y1: number, x2: number, y2: number) => {
        const mx = x1 + (x2 - x1) * 0.5
        return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`
      }
      const next: { d: string; w: number; color: string; key: string }[] = []
      const op = center(out, "l")
      causes.forEach((c, i) => {
        const fEl = factorRefs.current.get(i)
        if (!fEl) return
        const fl = center(fEl, "l"), fr = center(fEl, "r")
        const st = styleOf(c)
        // 증거 → 요인
        for (const e of c.evidence ?? []) {
          const eEl = evRefs.current.get(`${i}:${e.id}`)
          if (!eEl) continue
          const er = center(eEl, "r")
          next.push({ key: `e${i}-${e.id}`, d: curve(er.x, er.y, fl.x, fl.y),
            w: Math.max(1.2, (e.weight_pp / 100) * 11), color: st.hex })
        }
        // 요인 → 결과
        next.push({ key: `f${i}`, d: curve(fr.x, fr.y, op.x, op.y),
          w: Math.max(1.6, (c.contribution / 100) * 16), color: st.hex })
      })
      setBox({ w: wb.width, h: wb.height })
      setEdges(next)
    }
    recompute()
    const ro = new ResizeObserver(recompute)
    if (wrapRef.current) ro.observe(wrapRef.current)
    const t = setTimeout(recompute, 60) // 폰트/레이아웃 안정화 후 한 번 더
    window.addEventListener("resize", recompute)
    return () => { ro.disconnect(); window.removeEventListener("resize", recompute); clearTimeout(t) }
  }, [causes])

  const down = trendPct < 0

  return (
    <div>
      {/* 티어 헤더 */}
      <div className="grid grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)_minmax(150px,200px)] gap-x-10 mb-3">
        {["데이터 증거", "원인(요인)", "매출·가게 변화"].map((t, i) => (
          <div key={t} className={`text-[10.5px] font-extrabold uppercase tracking-widest text-slate-400 ${i === 2 ? "text-right" : ""}`}>{t}</div>
        ))}
      </div>

      <div ref={wrapRef} className="relative">
        {/* SVG 엣지 오버레이 */}
        <svg className="absolute inset-0 pointer-events-none" width={box.w} height={box.h} style={{ overflow: "visible" }}>
          {edges.map(e => (
            <path key={e.key} d={e.d} fill="none" stroke={e.color} strokeWidth={e.w} strokeOpacity={0.32} strokeLinecap="round" />
          ))}
        </svg>

        <div className="flex">
          {/* 증거 + 요인 (좌/중) */}
          <div className="flex-1 min-w-0 flex flex-col gap-5">
            {causes.map((c, i) => {
              const st = styleOf(c)
              return (
                <div key={i} className="grid grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-x-10 items-center">
                  {/* 증거 노드들 */}
                  <div className="flex flex-col gap-2 py-1">
                    {(c.evidence ?? []).map(e => (
                      <div key={e.id} ref={el => { if (el) evRefs.current.set(`${i}:${e.id}`, el) }}
                        className="relative pl-3 border-l-2" style={{ borderColor: st.hex }}>
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-[12px] font-semibold text-slate-700 leading-snug">{e.label}</span>
                          <span className="text-[11px] font-extrabold tabular-nums flex-shrink-0" style={{ color: st.hex }}>{e.weight_pp.toFixed(0)}%p</span>
                        </div>
                        <div className="text-[10.5px] text-slate-400 leading-snug">
                          <span className="font-semibold text-slate-500">{e.when}</span> · {e.mechanism}
                        </div>
                      </div>
                    ))}
                    {(!c.evidence || c.evidence.length === 0) && (
                      <div ref={el => { if (el) evRefs.current.set(`${i}:_`, el) }} className="pl-3 border-l-2 border-slate-200">
                        <span className="text-[12px] text-slate-500">{c.description}</span>
                      </div>
                    )}
                  </div>

                  {/* 요인 노드 */}
                  <div ref={el => { if (el) factorRefs.current.set(i, el) }}
                    className="border border-slate-200 bg-white px-3.5 py-2.5">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="flex items-center gap-1.5 text-[13px] font-bold text-slate-800 leading-tight">
                        <span style={{ color: st.hex }}>{st.icon}</span>{c.factor}
                      </span>
                      <span className="text-[16px] font-extrabold tabular-nums flex-shrink-0" style={{ color: st.hex }}>{c.contribution.toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 overflow-hidden">
                      <div className={`h-full ${st.bar} transition-all duration-700`} style={{ width: `${c.contribution}%` }} />
                    </div>
                    <div className="mt-1.5 text-[10.5px] text-slate-400">신뢰도 {confLabel(c.confidence)}</div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* 결과 노드 (우) */}
          <div className="w-[150px] xl:w-[200px] flex-shrink-0 flex items-center justify-end pl-10">
            <div ref={outRef} className={`w-full border-l-4 ${down ? "border-red-500" : "border-green-500"} pl-4 py-3`}>
              <div className="text-[10.5px] font-extrabold uppercase tracking-widest text-slate-400 mb-1">매출 변화</div>
              <div className={`flex items-center gap-1 text-3xl font-extrabold tabular-nums ${down ? "text-red-600" : "text-green-600"}`}>
                {down ? <TrendingDown size={22} /> : <TrendingUp size={22} />}
                {trendPct > 0 ? "+" : ""}{trendPct.toFixed(1)}%
              </div>
              {runwayDays != null && (
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <div className="text-[10.5px] font-extrabold uppercase tracking-widest text-slate-400 mb-0.5">가게 변화 · 현금</div>
                  <div className="text-[15px] font-extrabold tabular-nums text-slate-700">현금런웨이 {runwayDays.toFixed(0)}일</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-slate-400 mt-4 leading-relaxed">
        각 요인의 기여도(%)는 좌측 <span className="font-semibold text-slate-500">데이터 증거(%p)</span>의 합으로 산정됩니다.
        선의 굵기는 기여 크기에 비례합니다.
      </p>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// MOBILE — 세로 인과 흐름 (요인 → 증거 들여쓰기 → 매출 기여)
// ────────────────────────────────────────────────────────────────────────────
export function CausalFlowMobile({ causes, trendPct, runwayDays }: Props) {
  const down = trendPct < 0
  return (
    <div>
      {/* 결과 헤더 (흐름의 종착점) */}
      <div className={`flex items-center gap-3 px-5 py-3 border-l-4 ${down ? "border-red-500" : "border-green-500"} bg-slate-50/60`}>
        {down ? <TrendingDown size={20} className="text-red-600" /> : <TrendingUp size={20} className="text-green-600" />}
        <div className="flex-1">
          <div className="text-[10.5px] font-extrabold uppercase tracking-widest text-slate-400">매출·가게 변화</div>
          <div className="flex items-baseline gap-2">
            <span className={`text-[22px] font-extrabold tabular-nums ${down ? "text-red-600" : "text-green-600"}`}>
              {trendPct > 0 ? "+" : ""}{trendPct.toFixed(1)}%
            </span>
            {runwayDays != null && <span className="text-[12px] font-bold text-slate-500">현금런웨이 {runwayDays.toFixed(0)}일</span>}
          </div>
        </div>
      </div>

      {/* 요인별 흐름 */}
      <div>
        {causes.map((c, i) => {
          const st = styleOf(c)
          return (
            <div key={i} className="px-5 pt-4 pb-3 border-b border-slate-100">
              {/* 요인 노드 */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="flex items-center gap-1.5 text-[14px] font-bold text-slate-800">
                  <span style={{ color: st.hex }}>{st.icon}</span>{c.factor}
                </span>
                <span className="text-[17px] font-extrabold tabular-nums flex-shrink-0" style={{ color: st.hex }}>{c.contribution.toFixed(0)}%</span>
              </div>
              <div className="h-1.5 bg-slate-100 overflow-hidden mb-3">
                <div className={`h-full ${st.bar} transition-all duration-700`} style={{ width: `${c.contribution}%` }} />
              </div>

              {/* 증거 노드들 (들여쓰기 + 좌측 레일로 요인에 연결) */}
              <div className="pl-3 ml-1 border-l-2 space-y-2.5" style={{ borderColor: `${st.hex}55` }}>
                {(c.evidence ?? []).map(e => (
                  <div key={e.id} className="relative">
                    {/* 레일에서 갈라지는 가지 */}
                    <span className="absolute -left-3 top-2 w-2.5 h-px" style={{ backgroundColor: `${st.hex}55` }} />
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-[12.5px] font-semibold text-slate-700 leading-snug">{e.label}</span>
                      <span className="text-[11.5px] font-extrabold tabular-nums flex-shrink-0" style={{ color: st.hex }}>{e.weight_pp.toFixed(0)}%p</span>
                    </div>
                    <div className="text-[11px] text-slate-400 leading-snug mt-0.5">
                      <span className="font-semibold text-slate-500">{e.when}</span> · {e.mechanism}
                    </div>
                  </div>
                ))}
                {(!c.evidence || c.evidence.length === 0) && (
                  <div className="text-[12px] text-slate-500">{c.description}</div>
                )}
              </div>

              {/* 매출 기여 방향 표시 */}
              <div className="flex items-center gap-1.5 mt-2.5 pl-1 text-[11px] font-semibold" style={{ color: st.hex }}>
                <ArrowRight size={13} />매출 변화에 {c.contribution.toFixed(0)}%p 기여
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-[11px] text-slate-400 px-5 pt-3 leading-relaxed">
        각 요인의 기여도(%)는 그 아래 <span className="font-semibold text-slate-500">데이터 증거(%p)</span>의 합으로 산정됩니다.
      </p>
    </div>
  )
}
