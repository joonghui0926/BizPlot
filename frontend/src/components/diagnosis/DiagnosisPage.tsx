"use client"
import { useEffect, useState, useRef } from "react"
import { Clock, Store, Package, CloudRain, MessageSquare, BarChart3, Map, CloudSun, TrendingDown, TrendingUp, ChevronRight } from "lucide-react"
import { getDashboard, getReviewSignals } from "@/lib/api"
import { useDiagnosis } from "@/components/diagnosis/DiagnosisContext"
import type { Dashboard, Store as StoreType, Cause } from "@/lib/types"
import { Badge } from "@/components/ui/Badge"
import { AppShell } from "@/components/layout/AppShell"

interface ReviewSignal {
  period_start: string; period_end: string; platform: string | null
  sentiment_score: number; avg_rating: number | null; review_count: number
  positive_keywords: string[]; negative_keywords: string[]
  issue_categories: Record<string, number>; business_signal: string; confidence: string
}

interface Props { store: StoreType }

const FACTOR_ICONS: [string, React.ReactNode][] = [
  ["평일 오후", <Clock size={15} key="c" />],
  ["시간대", <Clock size={15} key="c2" />],
  ["경쟁", <Store size={15} key="s" />],
  ["점포", <Store size={15} key="s2" />],
  ["비용", <Package size={15} key="p" />],
  ["원재료", <Package size={15} key="p2" />],
  ["날씨", <CloudRain size={15} key="r" />],
  ["강수", <CloudRain size={15} key="r2" />],
  ["리뷰", <MessageSquare size={15} key="m" />],
]

function getIcon(factor: string) {
  return FACTOR_ICONS.find(([k]) => factor.includes(k))?.[1] ?? <BarChart3 size={15} />
}

export function DiagnosisPage({ store }: Props) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [reviewSignals, setReviewSignals] = useState<ReviewSignal[]>([])
  const [loading, setLoading] = useState(true)
  const { completedTick } = useDiagnosis()
  const firstTick = useRef(true)

  useEffect(() => {
    Promise.all([
      getDashboard(store.id).then(r => setData(r.data)),
      getReviewSignals(store.id).then(r => setReviewSignals(r.data)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [store.id])

  // 진단 완료 시(이 탭에 머물러 있어도) 새 결과로 갱신
  useEffect(() => {
    if (firstTick.current) { firstTick.current = false; return }
    getDashboard(store.id).then(r => setData(r.data)).catch(() => {})
    getReviewSignals(store.id).then(r => setReviewSignals(r.data)).catch(() => {})
  }, [completedTick])

  const diagnosis = data?.latest_diagnosis
  const state = data?.state
  const causes = diagnosis?.causes ?? []
  const reviewCauses = diagnosis?.review_causes ?? []

  return (
    <AppShell store={store}>

      {/* ──────────────────────────────────────────
          LOADING
      ────────────────────────────────────────── */}
      {loading && (
        <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-white rounded-2xl animate-pulse border border-slate-100" />)}
        </div>
      )}

      {/* ──────────────────────────────────────────
          EMPTY
      ────────────────────────────────────────── */}
      {!loading && !diagnosis && (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 px-5">
          <BarChart3 size={40} className="text-slate-200" />
          <div className="text-lg font-bold text-slate-500">진단 결과가 없습니다</div>
          <div className="text-sm text-slate-400">대시보드에서 진단을 먼저 실행해 주세요.</div>
        </div>
      )}

      {/* ──────────────────────────────────────────
          MOBILE LAYOUT  (lg:hidden)
      ────────────────────────────────────────── */}
      {!loading && diagnosis && (
        <div className="lg:hidden bg-white min-h-screen">

          {/* Summary headline */}
          <div className="px-5 pt-4 pb-3">
            <div className="text-[19px] font-extrabold leading-tight tracking-tight text-slate-900">
              {diagnosis.summary
                ? <span dangerouslySetInnerHTML={{ __html: diagnosis.summary.replace(/(\d+(\.\d+)?%)/g, '<em class="not-italic text-red-600">$1</em>') }} />
                : "매출 하락 원인을 분석했습니다."
              }
            </div>
          </div>

          {/* Revenue change stat row */}
          {state && (
            <div className="mx-5 mb-1 rounded-2xl bg-slate-50 border border-slate-100 px-4 py-3">
              <div className="flex items-center gap-5">
                <div>
                  <div className="text-[10px] text-slate-400 font-semibold">30일 매출 변화</div>
                  <div className={`text-[22px] font-extrabold tabular-nums mt-0.5 ${(state.revenue_trend ?? 0) < 0 ? "text-red-600" : "text-green-600"}`}>
                    {(state.revenue_trend ?? 0) > 0 ? "+" : ""}{((state.revenue_trend ?? 0) * 100).toFixed(1)}%
                  </div>
                </div>
                {state.detail.recent_revenue_30d != null && (
                  <>
                    <div className="w-px h-8 bg-slate-200" />
                    <div>
                      <div className="text-[10px] text-slate-400">최근 30일</div>
                      <div className="text-[16px] font-extrabold tabular-nums mt-0.5">
                        ₩{((state.detail.recent_revenue_30d ?? 0) / 10000).toFixed(0)}만
                      </div>
                    </div>
                    <div className="w-px h-8 bg-slate-200" />
                    <div>
                      <div className="text-[10px] text-slate-400">이전 30일</div>
                      <div className="text-[16px] font-extrabold text-slate-400 tabular-nums mt-0.5">
                        ₩{((state.detail.prior_revenue_30d ?? 0) / 10000).toFixed(0)}만
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Cause breakdown */}
          {causes.length > 0 && (
            <>
              <div className="flex items-center justify-between px-5 pt-5 pb-1">
                <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
                  <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
                  매출 하락 원인 분해
                </h3>
              </div>
              {causes.map((cause, i) => (
                <div key={i} className="px-5 py-4 border-b border-slate-100">
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-2 text-[13.5px] font-bold text-slate-800">
                      <span className="text-slate-400">{getIcon(cause.factor)}</span>
                      {cause.factor}
                    </div>
                    <span className="text-[17px] font-extrabold tabular-nums">{cause.contribution.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-2.5">
                    <div
                      className={`h-full rounded-full ${
                        i === 0 ? "bg-red-500"
                        : i === 1 ? "bg-amber-400"
                        : "bg-blue-500"
                      } transition-all duration-700`}
                      style={{ width: `${cause.contribution}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11.5px] text-slate-400 flex-1 leading-relaxed">{cause.description}</span>
                    <Badge
                      variant={cause.confidence === "high" ? "ok" : "warn"}
                      className="text-[10.5px] flex-shrink-0"
                    >
                      신뢰도 {cause.confidence === "high" ? "높음" : "중간"}
                    </Badge>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* AI 종합 분석 — 기여도 산정 근거 (mobile) */}
          {(diagnosis.summary || causes.length > 0) && (
            <>
              <div className="h-2 bg-slate-100 border-y border-slate-100 mt-1" />
              <div className="px-5 pt-4 pb-4">
                <CauseBasisSection summary={diagnosis.summary} causes={causes} />
              </div>
            </>
          )}

          {/* Review causes */}
          {reviewCauses.length > 0 && (
            <>
              <div className="h-2 bg-slate-100 border-y border-slate-100" />
              <div className="flex items-center gap-2 px-5 pt-4 pb-1">
                <h3 className="text-[13.5px] font-extrabold text-amber-700 flex items-center gap-2">
                  <span className="w-[3px] h-[14px] bg-amber-400 rounded-sm flex-shrink-0" />
                  <MessageSquare size={14} />고객 리뷰 신호
                </h3>
              </div>
              {reviewCauses.map((rc, i) => (
                <div key={i} className="px-5 py-3.5 border-b border-amber-50 last:border-0">
                  <div className="text-[13px] font-semibold text-slate-700 mb-2">{rc.description}</div>
                  <div className="flex flex-wrap gap-1.5">
                    {rc.keywords.slice(0, 6).map(kw => (
                      <span key={kw} className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-lg">{kw}</span>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Data sources */}
          <div className="h-2 bg-slate-100 border-y border-slate-100 mt-1" />
          <div className="flex items-center justify-between px-5 pt-4 pb-1">
            <h3 className="text-[13.5px] font-extrabold text-slate-800 flex items-center gap-2">
              <span className="w-[3px] h-[14px] bg-blue-600 rounded-sm flex-shrink-0" />
              분석 근거 데이터
            </h3>
          </div>
          {[
            { icon: <BarChart3 size={14} />, label: "매출·비용 데이터", tag: `${state?.detail?.data_period_days ?? 0}일` },
            { icon: <Map size={14} />, label: "소상공인 상가정보 API", tag: "반경 500m" },
            { icon: <CloudSun size={14} />, label: "기상청 단기예보", tag: "30일" },
            { icon: <MessageSquare size={14} />, label: "고객 리뷰 분석", tag: "네이버·구글" },
          ].map((src, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5 border-b border-slate-100 last:border-0">
              <span className="text-blue-500">{src.icon}</span>
              <span className="flex-1 text-[12.5px] text-slate-600 font-medium">{src.label}</span>
              <span className="text-[11px] text-slate-400 font-semibold">{src.tag}</span>
            </div>
          ))}


          <div className="h-4" />
        </div>
      )}

      {/* ──────────────────────────────────────────
          DESKTOP LAYOUT  (hidden lg:block)
      ────────────────────────────────────────── */}
      {!loading && diagnosis && (
        <div className="hidden lg:block">
          <div className="bg-white min-h-screen px-10 xl:px-12 2xl:px-16 py-9">

            {/* Page header */}
            <div className="border-b border-slate-100 pb-6 mb-0">
              <h1 className="text-2xl font-extrabold tracking-tight">원인 분석</h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {diagnosis.summary || "매출 하락 요인을 기여도 순으로 분석했습니다."}
              </p>
            </div>

            {/* Revenue stat row */}
            {state && (
              <div className="border-b border-slate-100 py-6">
                <div className="flex items-center gap-8">
                  <div>
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-1">30일 매출 변화</div>
                    <div className={`text-3xl font-extrabold tabular-nums ${(state.revenue_trend ?? 0) < 0 ? "text-red-600" : "text-green-600"}`}>
                      {(state.revenue_trend ?? 0) > 0 ? "+" : ""}{((state.revenue_trend ?? 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  {state.detail.recent_revenue_30d != null && (
                    <>
                      <div className="w-px h-12 bg-slate-100" />
                      <div>
                        <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-1">최근 30일</div>
                        <div className="text-xl font-extrabold tabular-nums">₩{((state.detail.recent_revenue_30d ?? 0)/10000).toFixed(0)}만</div>
                      </div>
                      <div className="w-px h-12 bg-slate-100" />
                      <div>
                        <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-1">이전 30일</div>
                        <div className="text-xl font-extrabold text-slate-400 tabular-nums">₩{((state.detail.prior_revenue_30d ?? 0)/10000).toFixed(0)}만</div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            <div className="grid grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_420px] 2xl:grid-cols-[minmax(0,1fr)_460px] gap-0 divide-x divide-slate-100">
              <div className="pr-8 xl:pr-10 2xl:pr-12">

                {/* Cause breakdown */}
                {causes.length > 0 && (
                  <div className="border-b border-slate-100 py-6">
                    <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-4">
                      <BarChart3 size={13} />매출 하락 원인 분해
                    </div>
                    <div className="divide-y divide-slate-100">
                      {causes.map((cause, i) => (
                        <div key={i} className="py-4">
                          <div className="flex items-start justify-between gap-2 mb-2.5">
                            <div className="flex items-center gap-2.5 text-[13.5px] font-bold text-slate-800">
                              <span className="text-slate-400">{getIcon(cause.factor)}</span>{cause.factor}
                            </div>
                            <span className="text-[17px] font-extrabold tabular-nums flex-shrink-0">{cause.contribution.toFixed(0)}%</span>
                          </div>
                          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden mb-2">
                            <div className={`h-full rounded-full ${i===0?"bg-red-500":i===1?"bg-amber-400":"bg-blue-500"} transition-all duration-700`}
                              style={{ width: `${cause.contribution}%` }} />
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[11.5px] text-slate-400 flex-1 leading-relaxed">{cause.description}</span>
                            <Badge variant={cause.confidence === "high" ? "ok" : "warn"} className="text-[10.5px] flex-shrink-0">
                              신뢰도 {cause.confidence === "high" ? "높음" : "중간"}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Review signals */}
                {reviewCauses.length > 0 && (
                  <div className="border-b border-slate-100 py-6">
                    <div className="text-[11px] font-extrabold text-amber-700 uppercase tracking-widest flex items-center gap-2 mb-4">
                      <MessageSquare size={13} />고객 리뷰 신호
                    </div>
                    <div className="divide-y divide-slate-100">
                      {reviewCauses.map((rc, i) => (
                        <div key={i} className="py-4">
                          <div className="text-[13px] font-semibold text-slate-700 mb-2">{rc.description}</div>
                          <div className="flex flex-wrap gap-1.5">
                            {rc.keywords.slice(0,6).map(kw => (
                              <span key={kw} className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-lg">{kw}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI 종합 분석 — 기여도 산정 근거 */}
                {(diagnosis.summary || causes.length > 0) && (
                  <div className="border-b border-slate-100 py-6">
                    <CauseBasisSection summary={diagnosis.summary} causes={causes} />
                  </div>
                )}
              </div>

              <div className="pl-8 xl:pl-10 2xl:pl-12">

                {/* Review signals trend */}
                {reviewSignals.length > 0 && (
                  <div className="border-b border-slate-100 py-6">
                    <div className="text-[11px] font-extrabold text-amber-700 uppercase tracking-widest flex items-center gap-2 mb-4">
                      <MessageSquare size={13} />리뷰 변동 추이
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="text-[11px] font-bold text-slate-400 mb-2">기간별 감성 점수 (/100)</div>
                        <div className="space-y-2">
                          {[...reviewSignals].reverse().map((sig, i) => {
                            const pct = Math.round((sig.sentiment_score + 1) * 50)
                            const prev = i > 0 ? Math.round(([...reviewSignals].reverse()[i-1].sentiment_score + 1) * 50) : null
                            const delta = prev !== null ? pct - prev : null
                            return (
                              <div key={i} className="flex items-center gap-3">
                                <div className="text-[10px] text-slate-400 w-12 flex-shrink-0 text-right">{sig.period_end?.slice(5, 10)}</div>
                                <div className="flex-1 h-4 bg-slate-100 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full transition-all ${pct >= 65 ? "bg-green-400" : pct >= 40 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: `${pct}%` }} />
                                </div>
                                <div className="text-[12px] font-extrabold tabular-nums w-8">{pct}</div>
                                {delta !== null && (
                                  <div className={`flex items-center gap-0.5 text-[10.5px] font-bold w-10 ${delta > 0 ? "text-green-600" : delta < 0 ? "text-red-500" : "text-slate-400"}`}>
                                    {delta > 0 ? <TrendingUp size={10}/> : delta < 0 ? <TrendingDown size={10}/> : null}
                                    {delta > 0 ? "+" : ""}{delta}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                      {reviewSignals[0]?.issue_categories && Object.keys(reviewSignals[0].issue_categories).length > 0 && (
                        <div>
                          <div className="text-[11px] font-bold text-slate-400 mb-2">주요 이슈 카테고리</div>
                          <div className="flex flex-wrap gap-1.5">
                            {Object.entries(reviewSignals[0].issue_categories).sort(([,a],[,b]) => b - a).slice(0, 4).map(([cat, score]) => {
                              const labels: Record<string, string> = { wait_time: "대기 시간", space: "공간 부족", price: "가격", service: "서비스", quality: "품질", delivery: "배달" }
                              return (
                                <span key={cat} className="text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-100 px-2 py-1 rounded-lg">
                                  {labels[cat] ?? cat} {(score * 100).toFixed(0)}%
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      )}
                      {reviewSignals[0] && (
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <div className="text-[10.5px] font-bold text-green-600 mb-1.5">긍정 키워드</div>
                            <div className="flex flex-wrap gap-1">
                              {(reviewSignals[0].positive_keywords ?? []).slice(0, 4).map(kw => (
                                <span key={kw} className="text-[10.5px] bg-green-50 text-green-700 border border-green-100 px-1.5 py-0.5 rounded-md font-semibold">{kw}</span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10.5px] font-bold text-red-500 mb-1.5">부정 키워드</div>
                            <div className="flex flex-wrap gap-1">
                              {(reviewSignals[0].negative_keywords ?? []).slice(0, 4).map(kw => (
                                <span key={kw} className="text-[10.5px] bg-red-50 text-red-600 border border-red-100 px-1.5 py-0.5 rounded-md font-semibold">{kw}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      {reviewSignals[0]?.business_signal && (
                        <div className="text-[11.5px] text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2">
                          {reviewSignals[0].business_signal}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Data sources */}
                <div className="py-6">
                  <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-3">
                    <BarChart3 size={13} />분석 근거 데이터
                  </div>
                  <div className="divide-y divide-slate-100">
                    {[
                      { icon: <BarChart3 size={14} />, label: "매출·비용 데이터", tag: `${state?.detail?.data_period_days ?? 0}일` },
                      { icon: <Map size={14} />, label: "소상공인 상가정보 API", tag: "반경 500m" },
                      { icon: <CloudSun size={14} />, label: "기상청 단기예보", tag: "30일" },
                      { icon: <MessageSquare size={14} />, label: "고객 리뷰 분석", tag: "네이버·구글" },
                    ].map((src, i) => (
                      <div key={i} className="flex items-center gap-3 py-3">
                        <span className="text-blue-500">{src.icon}</span>
                        <span className="flex-1 text-[12.5px] text-slate-600 font-medium">{src.label}</span>
                        <span className="text-[11px] text-slate-400 font-semibold">{src.tag}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}

// 기여도(%) 산정 근거를 항목별 정량 bullet으로 표현하는 섹션
function CauseBasisSection({ summary, causes }: { summary: string | null; causes: Cause[] }) {
  return (
    <div>
      <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
        <BarChart3 size={13} className="text-blue-500" />AI 종합 분석 · 기여도 산정 근거
      </div>
      {summary && <p className="text-[12.5px] text-slate-600 leading-relaxed mb-4">{summary}</p>}
      <div className="space-y-2.5">
        {causes.map((c, i) => (
          <div key={i} className="rounded-xl border border-slate-100 bg-slate-50/70 px-3.5 py-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[13px] font-bold text-slate-800">{c.factor}</span>
              <span className={`text-[14px] font-extrabold tabular-nums ${i === 0 ? "text-red-600" : i === 1 ? "text-amber-600" : "text-slate-800"}`}>
                {c.contribution.toFixed(0)}%
              </span>
            </div>
            {c.basis && c.basis.length > 0 ? (
              <ul className="space-y-1">
                {c.basis.map((b, j) => (
                  <li key={j} className="flex gap-1.5 text-[11.5px] text-slate-600 leading-snug">
                    <span className="text-blue-500 font-bold flex-shrink-0">·</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[11.5px] text-slate-500 leading-snug">{c.description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
