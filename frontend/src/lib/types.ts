export interface Store {
  id: string
  name: string
  category: string
  address: string | null
  latitude: number | null
  longitude: number | null
  open_months: number
  monthly_avg_revenue: number | null
}

export interface BusinessState {
  id: string
  health_score: number | null
  liquidity_risk: number | null
  revenue_trend: number | null
  cost_pressure: number | null
  review_signal: number | null
  finance_readiness: number | null
  cash_runway_days: number | null
  computed_at: string
  detail: {
    recent_revenue_30d?: number
    prior_revenue_30d?: number
    total_cost_30d?: number
    monthly_fixed?: number
    data_period_days?: number
  }
}

// 인과 귀속 그래프의 증거 노드(leaf). 기여도(%)의 정량적 근거 단위.
export interface EvidenceNode {
  id: string
  label: string          // 실측값 기반 한 줄 (예: "반경 500m 동종 점포 12개")
  metric: string         // 어느 지표에서 왔는지
  raw_value: number | string
  delta?: string         // 변화량 표기 (예: "120→95건")
  when: string           // 언제 (예: "평일 오후 13-17시")
  mechanism: string      // 어떻게 매출에 작용했는지
  weight_pp: number      // 이 증거가 설명하는 기여도(%p)
  source: string         // 데이터 출처
}

export interface Cause {
  factor: string
  contribution: number   // = Σ evidence.weight_pp (가산성 보장)
  confidence: "high" | "medium" | "low"
  description: string
  group?: string         // competition|timeofday|weather|review|price|demand
  evidence?: EvidenceNode[]  // 증거→요인 그래프의 자식 노드들
  basis?: string[]       // 기여도(%) 산정의 정량적 근거 bullet (evidence에서 파생)
  detail?: Record<string, unknown>
}

export interface Diagnosis {
  id: string
  causes: Cause[]
  review_causes: ReviewCause[]
  summary: string | null
  created_at: string
}

export interface ReviewCause {
  factor: string
  keywords: string[]
  sentiment_score: number | null
  confidence: string
  description: string
}

export interface Action {
  id: string
  type: "operation" | "marketing" | "finance"
  title: string
  description: string
  priority: number
  expected_impact: {
    cash_runway_days_delta?: number
    revenue_change_pct?: number
    cost_change_pct?: number
    finance_readiness_delta?: number
  }
}

export interface ActionPlan {
  id: string
  actions: Action[]
  rag_references: RagRef[]
  verified: string | null
  created_at: string
}

export interface RagRef {
  id: string
  title: string | null
  content: string
  source: string
  url: string | null
}

export interface SimulationScenario {
  action_id: string
  action_title: string
  action_type: string
  baseline_revenue_30d: number
  revenue_after_30d: number
  baseline_cost_30d: number
  cost_after_30d: number
  cash_runway_days_before: number
  cash_runway_days_after: number
  revenue_change_pct: number
  cost_change_pct: number
}

export interface Simulation {
  id: string
  scenarios: SimulationScenario[]
  created_at: string
}

export interface ReviewSignalSummary {
  sentiment_score: number | null
  avg_rating: number | null
  positive_keywords: string[]
  negative_keywords: string[]
  business_signal: string | null
}

export interface Dashboard {
  store_id: string
  state: BusinessState | null
  latest_diagnosis: Diagnosis | null
  latest_action_plan: ActionPlan | null
  review_signal_summary: ReviewSignalSummary | null
}
