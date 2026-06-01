"""
Cashflow Simulation Engine
행동별 현금흐름 변화 계산 (LLM 불사용, 순수 계산 로직)
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord
from app.models.agent import ActionPlan, BusinessState, Simulation


def simulate_actions(
    store: Store,
    state: BusinessState,
    plan: ActionPlan,
    selected_action_ids: list[str],
    db: Session,
) -> Simulation:
    today = date.today()
    recent_cutoff = today - timedelta(days=30)

    sales = db.query(SalesRecord).filter(
        SalesRecord.store_id == store.id,
        SalesRecord.date >= recent_cutoff,
    ).all()
    costs = db.query(CostRecord).filter(
        CostRecord.store_id == store.id,
        CostRecord.date >= recent_cutoff,
    ).all()

    baseline_revenue = sum(s.amount for s in sales)
    baseline_cost = sum(c.amount for c in costs)
    baseline_net = baseline_revenue - baseline_cost
    baseline_runway = state.cash_runway_days or 0

    actions = plan.actions or []
    if selected_action_ids:
        actions = [a for a in actions if a.get("id") in selected_action_ids]

    scenarios = []
    cumulative_revenue_delta = 0.0
    cumulative_cost_delta = 0.0

    for action in actions:
        impact = action.get("expected_impact", {})
        rev_pct = impact.get("revenue_change_pct", 0) / 100
        cost_pct = impact.get("cost_change_pct", 0) / 100
        runway_delta = impact.get("cash_runway_days_delta", 0)

        revenue_after = baseline_revenue * (1 + rev_pct + cumulative_revenue_delta)
        cost_after = baseline_cost * (1 + cost_pct + cumulative_cost_delta)
        net_after = revenue_after - cost_after

        # Recalculate runway
        if net_after >= 0:
            runway_after = baseline_runway + runway_delta + max(net_after * 30 / max(cost_after, 1), 0)
        else:
            monthly_burn = abs(net_after)
            runway_after = max((baseline_revenue * 0.3) / (monthly_burn / 30), 0)

        scenarios.append({
            "action_id": action.get("id"),
            "action_title": action.get("title"),
            "action_type": action.get("type"),
            "baseline_revenue_30d": round(baseline_revenue, 0),
            "revenue_after_30d": round(revenue_after, 0),
            "baseline_cost_30d": round(baseline_cost, 0),
            "cost_after_30d": round(cost_after, 0),
            "cash_runway_days_before": round(baseline_runway, 1),
            "cash_runway_days_after": round(runway_after, 1),
            "revenue_change_pct": round(rev_pct * 100, 1),
            "cost_change_pct": round(cost_pct * 100, 1),
        })

        cumulative_revenue_delta += rev_pct
        cumulative_cost_delta += cost_pct

    # Combined scenario
    if len(scenarios) > 1:
        final_revenue = baseline_revenue * (1 + cumulative_revenue_delta)
        final_cost = baseline_cost * (1 + cumulative_cost_delta)
        final_net = final_revenue - final_cost
        if final_net >= 0:
            total_runway = baseline_runway + sum(
                a.get("expected_impact", {}).get("cash_runway_days_delta", 0)
                for a in actions
            )
        else:
            total_runway = max((baseline_revenue * 0.3) / (abs(final_net) / 30), 0)

        scenarios.append({
            "action_id": "combined",
            "action_title": "전략 전체 적용",
            "action_type": "combined",
            "baseline_revenue_30d": round(baseline_revenue, 0),
            "revenue_after_30d": round(final_revenue, 0),
            "baseline_cost_30d": round(baseline_cost, 0),
            "cost_after_30d": round(final_cost, 0),
            "cash_runway_days_before": round(baseline_runway, 1),
            "cash_runway_days_after": round(total_runway, 1),
            "revenue_change_pct": round(cumulative_revenue_delta * 100, 1),
            "cost_change_pct": round(cumulative_cost_delta * 100, 1),
        })

    sim = Simulation(
        store_id=store.id,
        action_plan_id=plan.id,
        scenarios=scenarios,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim
