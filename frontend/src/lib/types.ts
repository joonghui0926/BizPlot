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

export interface Cause {
  factor: string
  contribution: number
  confidence: "high" | "medium" | "low"
  description: string
  basis?: string[]   // 기여도(%) 산정의 정량적 근거 bullet
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
