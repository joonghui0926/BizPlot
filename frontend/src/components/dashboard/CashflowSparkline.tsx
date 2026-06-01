"use client"

interface Props { runwayDays: number }

/**
 * 현금흐름 전망 스파크라인 — 목업(.spark) 스타일.
 * runway가 길든 짧든 항상 의도된 하강 곡선 + 그라데이션 면 + 엔드포인트 점을 렌더한다.
 */
export function CashflowSparkline({ runwayDays }: Props) {
  const W = 300, H = 72
  const horizon = Math.max(40, Math.round(runwayDays / 10) * 10 + 10) // x축 표시 일수
  const critical = runwayDays <= horizon

  // 하강 곡선: 완만(현금 여유) ~ 가파름(임박)을 runway로 보간
  const steep = Math.max(0.18, Math.min(1, 28 / Math.max(runwayDays, 8)))
  const pts = Array.from({ length: 9 }, (_, i) => {
    const t = i / 8
    const x = t * W
    // ease-in 하강: 뒤로 갈수록 빠르게 떨어짐
    const drop = Math.pow(t, 1.6) * steep
    const y = 12 + drop * (H - 20)
    return [x, y] as const
  })
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ")
  const area = `${line} L${W},${H} L0,${H} Z`

  const [ex, ey] = pts[pts.length - 1]
  const endColor = critical && runwayDays < 30 ? "#C0322B" : "#2563EB"

  return (
    <div className="mt-3">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" className="block">
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2563EB" stopOpacity="0.18" />
            <stop offset="1" stopColor="#2563EB" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* baseline grid */}
        <line x1="0" y1={H * 0.5} x2={W} y2={H * 0.5} stroke="#EEF1F6" strokeWidth="1" />
        <path d={area} fill="url(#sparkGrad)" />
        <path d={line} fill="none" stroke="#2563EB" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={ex} cy={ey} r="4" fill={endColor} />
        {critical && runwayDays < 30 && (
          <circle cx={ex} cy={ey} r="7.5" fill="none" stroke={endColor} strokeOpacity="0.25" strokeWidth="2" />
        )}
      </svg>
      <div className="flex justify-between text-[10.5px] text-slate-400 font-medium mt-1 px-0.5">
        <span>오늘</span>
        <span>{Math.round(horizon / 2)}일 후</span>
        <span>{horizon}일 후</span>
      </div>
    </div>
  )
}
