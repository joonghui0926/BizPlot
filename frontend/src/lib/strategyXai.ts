/**
 * strategyXai — 전략·시뮬레이션의 "왜 이렇게 변할까"를 설명 가능한(XAI) 문장으로 만든다.
 *
 * 원칙(진단 그래프와 동일):
 *   - 숫자는 결정론: 모두 진단 결과·매출 데이터·기대효과 수치에서 직접 끌어온다(LLM 호출 없음).
 *   - 서술은 근거 기반: 같은 말 반복 없이, 행동이 공략하는 "원인 → 메커니즘 → 기대효과 산출"의
 *     서로 다른 단계를 각 줄에 담는다.
 *
 * 반환은 {label, text} 줄 목록. UI는 회색 박스 없이 평면 리스트로 렌더한다.
 */
import type { Action, BusinessState, Cause, Simulation } from "@/lib/types"
import { formatCurrency } from "@/lib/utils"

export interface XaiLine { label: string; text: string }

// ── 행동 텍스트 → 공략하는 진단 원인(group) 추정 ──────────────────────────────
const GROUP_KEYWORDS: Record<string, string[]> = {
  timeofday:   ["시간대", "오후", "피크", "비피크", "한가한", "점심", "저녁", "배치", "근무"],
  competition: ["경쟁", "차별화", "SNS", "콘텐츠", "노출", "홍보", "신규"],
  review:      ["재방문", "단골", "쿠폰", "스탬프", "포인트", "로열티", "리뷰", "응대", "대기", "고객 경험"],
  price:       ["객단가", "세트", "메뉴", "묶음", "사이드", "가격", "업셀"],
  demand:      ["거래", "방문", "수요", "객수"],
}

function matchCause(action: Action, causes: Cause[]): Cause | undefined {
  const text = `${action.title} ${action.description}`
  for (const [group, kws] of Object.entries(GROUP_KEYWORDS)) {
    if (kws.some(k => text.includes(k))) {
      const hit = causes.find(c => c.group === group)
      if (hit) return hit
    }
  }
  return causes[0] // 못 찾으면 기여도 최상위 원인을 연결
}

// ── 레버(지렛대)별 메커니즘·추정 근거 — 같은 type 전략끼리도 문장이 겹치지 않게 ──
interface Lever {
  test: (s: string) => boolean
  mechanism: string
  realism: string
}

const LEVERS: Lever[] = [
  {
    test: s => /쿠폰|스탬프|포인트|로열티|단골|재방문/.test(s),
    mechanism: "한 번 방문한 고객을 다시 부르는 재방문 유도형입니다. 신규 유치보다 전환 비용이 낮아, 약해진 재방문 신호를 가장 적은 비용으로 되돌립니다.",
    realism: "재방문이 손님당 월 1회만 늘어도 거래건수가 그만큼 직접 증가합니다. 모두가 반응하지는 않으므로 회복폭은 보수적으로 잡았습니다.",
  },
  {
    test: s => /SNS|콘텐츠|차별화|노출|홍보|마케팅 채널/.test(s),
    mechanism: "경쟁 점포 사이에서 검색·피드에 노출되는 빈도를 높여, 줄어든 신규 유입을 다시 끌어옵니다.",
    realism: "노출이 늘어도 실제 방문까지는 시차가 있어, 즉각 효과가 아니라 점진적 회복을 가정한 추정치입니다.",
  },
  {
    test: s => /객단가|세트|메뉴|묶음|사이드|업셀/.test(s),
    mechanism: "손님 수를 늘리지 않고 1인당 결제액(객단가)을 올려, 같은 방문에서 매출을 더 만듭니다.",
    realism: "객단가는 외부 변수에 덜 휘둘려 통제하기 쉬운 지표라, 제시한 상승폭은 무리 없는 범위입니다.",
  },
  {
    test: s => /발주|원재료|재고|변동비|폐기|매입/.test(s),
    mechanism: "판매량에 맞춰 발주·재고를 조정해, 폐기와 과잉 매입으로 새던 변동비를 줄입니다.",
    realism: "절감분은 매출과 무관하게 매달 반복되므로, 현금 유지일에 곧바로 누적 반영됩니다.",
  },
  {
    test: s => /인력|시간대|피크|배치|근무|운영 시간/.test(s),
    mechanism: "한가한 시간대 인력을 줄이고 피크에 집중 배치해, 매출은 지키면서 인건비 효율을 높입니다.",
    realism: "시간대별 매출 분포 데이터가 있어, 배치 조정의 효과를 비교적 정확히 추정할 수 있습니다.",
  },
  {
    test: s => /상담|리포트|자금|대출|정책|준비|운전자금|심사/.test(s),
    mechanism: "지금 매출을 바꾸기보다, 현금이 마르는 구간에 대비해 자금 선택지와 서류를 미리 갖추는 준비형 조치입니다.",
    realism: "효과는 매출이 아니라 '필요할 때 빠르게 자금을 쓸 수 있는가'로 나타나, 현금 유지일·금융 준비도로 측정합니다.",
  },
]

const TYPE_FALLBACK: Record<string, Lever> = {
  marketing: {
    test: () => true,
    mechanism: "수요가 약해진 구간의 고객을 다시 움직여 거래건수를 회복시키는 매출 견인형 전략입니다.",
    realism: "마케팅 반응은 점포·시점마다 달라, 과거 하락폭의 일부만 되돌리는 보수적 수치로 추정했습니다.",
  },
  operation: {
    test: () => true,
    mechanism: "매출을 늘리기보다 같은 매출에서 새는 비용·시간을 줄이는 구조 개선이라, 효과가 매달 반복됩니다.",
    realism: "절감 효과는 운영 데이터로 추적 가능해, 제시한 폭은 실현 가능한 범위로 잡았습니다.",
  },
  finance: {
    test: () => true,
    mechanism: "당장의 매출이 아니라, 현금 부족 구간을 대비해 선택지를 미리 확보하는 안전장치입니다.",
    realism: "금융 효과는 준비도·현금 유지일로 측정되며, 특정 상품 가입을 단정하지 않는 준비 단계입니다.",
  },
}

function leverFor(action: Action): Lever {
  const text = `${action.title} ${action.description}`
  return LEVERS.find(l => l.test(text)) ?? TYPE_FALLBACK[action.type] ?? TYPE_FALLBACK.operation
}

// ── 전략 1개의 XAI 설명 (≥5줄, 단계별로 서로 다른 내용) ────────────────────────
export function buildActionXai(
  action: Action,
  state: BusinessState | null | undefined,
  causes: Cause[],
): XaiLine[] {
  const lines: XaiLine[] = []
  const impact = action.expected_impact || {}
  const rev = impact.revenue_change_pct ?? 0
  const cost = impact.cost_change_pct ?? 0
  const runway = impact.cash_runway_days_delta ?? 0
  const finance = impact.finance_readiness_delta ?? 0

  const cause = matchCause(action, causes)
  const lever = leverFor(action)
  const recent = state?.detail?.recent_revenue_30d ?? null
  const curRunway = state?.cash_runway_days ?? null
  const costPressure = state?.cost_pressure ?? null

  // 1) 진단 연결 — 어떤 원인을 공략하는가 (원인의 실제 기여도%)
  if (cause) {
    lines.push({
      label: "공략 원인",
      text: `진단에서 매출 변화의 ${cause.contribution.toFixed(0)}%를 차지한 ‘${cause.factor}’을(를) 직접 겨냥합니다. 비중이 큰 원인부터 줄일수록 회복 효과가 큽니다.`,
    })
    // 2) 과거 데이터 근거 — 그 원인의 실측 증거
    const ev = cause.evidence?.[0]
    if (ev) {
      lines.push({
        label: "데이터 근거",
        text: `근거가 된 실측값은 “${ev.label}”(${ev.when})입니다. ${ev.mechanism} — 이 경로가 아직 되돌릴 여지로 남아 있습니다.`,
      })
    } else if (cause.basis?.[0]) {
      lines.push({ label: "데이터 근거", text: cause.basis[0] })
    }
  }

  // 3) 작동 방식 — 이 행동이 지표를 움직이는 메커니즘
  lines.push({ label: "작동 방식", text: lever.mechanism })

  // 4) 기대 효과 산출 — 수치를 베이스라인(₩·일)에 붙여서
  if (rev) {
    const base = recent != null
      ? ` 최근 30일 매출 ${formatCurrency(recent)}을 기준으로 하면 약 ${formatCurrency(Math.abs(recent * rev / 100))}/월의 변화폭입니다.`
      : ""
    lines.push({
      label: "기대 매출",
      text: `매출 ${rev > 0 ? "+" : ""}${rev}%를 기대합니다.${base}`,
    })
  }
  if (cost) {
    const press = costPressure != null ? ` 현재 비용 압박 ${costPressure.toFixed(0)}/100 상황에서` : ""
    lines.push({
      label: "기대 비용",
      text: `변동비를 ${cost}% 조정합니다.${press} 같은 매출에서도 남는 현금이 늘어 현금 유지일이 길어집니다.`,
    })
  }
  if (runway) {
    const after = curRunway != null
      ? `${Math.round(curRunway)}일 → ${Math.round(curRunway + runway)}일`
      : `+${runway}일`
    lines.push({
      label: "현금 효과",
      text: `현금 유지 가능일이 ${after}로 늘어납니다. 매출 회복분과 비용 절감분이 매월 순현금에 쌓이기 때문입니다.`,
    })
  }
  if (finance) {
    lines.push({
      label: "금융 준비",
      text: `금융 준비도가 +${finance}p 올라갑니다. 데이터·서류가 갖춰질수록 상담·심사에서 제시할 근거가 많아집니다.`,
    })
  }

  // 5) 추정 근거 — 왜 이 수치가 합리적인가 (레버별로 다른 근거)
  lines.push({ label: "추정 근거", text: lever.realism })

  // 6) 검증 방법 — 사후 확인 지표 (type별로 다른 지표)
  const metric = action.type === "marketing" ? "거래건수·재방문율"
    : action.type === "finance" ? "금융 준비도·현금 유지일"
    : "변동비율·현금 유지일"
  lines.push({
    label: "검증 방법",
    text: `적용 약 4주 뒤 ${metric}을(를) 다시 측정해, 위 기대치와 실제 변화를 비교 검증합니다.`,
  })

  return lines
}

// ── 시뮬레이션 결과의 XAI 설명 (왜 이렇게 변하는지 산출 과정) ──────────────────
export function buildSimulationXai(sim: Simulation): XaiLine[] {
  const combined = sim.scenarios.find(s => s.action_id === "combined")
  const parts = sim.scenarios.filter(s => s.action_id !== "combined")
  const result = combined ?? parts[0]
  if (!result) return []

  const lines: XaiLine[] = []
  const baseRev = result.baseline_revenue_30d
  const baseCost = result.baseline_cost_30d
  const baseNet = baseRev - baseCost

  // 1) 출발점 — 현재 30일 실측
  lines.push({
    label: "출발점",
    text: `현재 30일 매출 ${formatCurrency(baseRev)}, 비용 ${formatCurrency(baseCost)} (월 순현금 ${baseNet >= 0 ? "" : "-"}${formatCurrency(Math.abs(baseNet))})에서 계산을 시작합니다.`,
  })

  // 2) 매출 효과 합산 — 어느 전략이 얼마씩 더하는지
  const revParts = parts.filter(p => p.revenue_change_pct)
  if (revParts.length && result.revenue_change_pct) {
    const list = revParts.map(p => `${p.action_title} +${p.revenue_change_pct}%`).join(", ")
    lines.push({
      label: "매출 합산",
      text: `매출을 올리는 전략(${list})을 더하면 +${result.revenue_change_pct.toFixed(1)}% → 매출 ${formatCurrency(baseRev)} → ${formatCurrency(result.revenue_after_30d)}로 바뀝니다.`,
    })
  }

  // 3) 비용 효과 합산
  const costParts = parts.filter(p => p.cost_change_pct)
  if (costParts.length && result.cost_change_pct) {
    const list = costParts.map(p => `${p.action_title} ${p.cost_change_pct}%`).join(", ")
    lines.push({
      label: "비용 합산",
      text: `비용을 조정하는 전략(${list})을 더하면 ${result.cost_change_pct.toFixed(1)}% → 비용 ${formatCurrency(baseCost)} → ${formatCurrency(result.cost_after_30d)}로 바뀝니다.`,
    })
  }

  // 4) 현금 유지일 산출
  const before = Math.round(result.cash_runway_days_before)
  const after = Math.round(result.cash_runway_days_after)
  lines.push({
    label: "현금 유지일",
    text: `늘어난 매출과 줄어든 비용이 월 순현금에 더해져, 현금 유지일이 ${before}일 → ${after}일 (${after - before >= 0 ? "+" : ""}${after - before}일)로 바뀝니다.`,
  })

  // 5) 가정·한계 — 과대평가하지 않았다는 근거
  lines.push({
    label: "계산 가정",
    text: "각 전략 효과는 서로 독립으로 보고 단순 합산했으며, 겹치는 효과는 중복 계산하지 않았습니다. 날씨·경쟁 등 외부 변수는 일정하다고 가정한 보수적 추정입니다.",
  })

  return lines
}
