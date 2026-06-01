"""
Finance State Agent
사업 건강도(Bt), 유동성 위험도(Lt), 매출 추세(Mt),
비용 압박도(Ct), 금융 준비도(Ft), 현금 유지 기간 계산
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord
from app.models.review import ReviewSignal
from app.models.agent import BusinessState


def compute_business_state(store: Store, db: Session) -> BusinessState:
    today = date.today()
    period_end = today
    period_start = today - timedelta(days=90)

    sales = db.query(SalesRecord).filter(
        SalesRecord.store_id == store.id,
        SalesRecord.date >= period_start,
        SalesRecord.date <= period_end,
    ).all()

    costs = db.query(CostRecord).filter(
        CostRecord.store_id == store.id,
        CostRecord.date >= period_start,
        CostRecord.date <= period_end,
    ).all()

    # Revenue trend (Mt): compare recent 30d vs prior 30d
    recent_cutoff = today - timedelta(days=30)
    prior_cutoff = today - timedelta(days=60)

    recent_sales = sum(s.amount for s in sales if s.date >= recent_cutoff)
    prior_sales = sum(s.amount for s in sales if prior_cutoff <= s.date < recent_cutoff)

    if prior_sales > 0:
        revenue_trend = (recent_sales - prior_sales) / prior_sales  # -1 ~ +1
    else:
        revenue_trend = 0.0

    # Cost pressure (Ct)
    total_cost_30d = sum(c.amount for c in costs if c.date >= recent_cutoff)
    total_revenue_30d = max(recent_sales, 1)
    cost_ratio = total_cost_30d / total_revenue_30d
    cost_pressure = min(cost_ratio * 100, 100)

    # Cash runway days
    monthly_fixed = sum(c.amount for c in costs if c.cost_type == "fixed" and c.date >= recent_cutoff)
    monthly_variable = sum(c.amount for c in costs if c.cost_type == "variable" and c.date >= recent_cutoff)
    monthly_cost = monthly_fixed + monthly_variable
    monthly_net = recent_sales - monthly_cost
    if monthly_net >= 0:
        cash_runway_days = 90.0   # healthy
    else:
        monthly_burn = abs(monthly_net)
        cash_runway_days = max((recent_sales * 0.3) / (monthly_burn / 30), 0)

    # Liquidity risk (Lt): inverse of runway
    if cash_runway_days >= 60:
        liquidity_risk = 10.0
    elif cash_runway_days >= 30:
        liquidity_risk = 40.0
    elif cash_runway_days >= 14:
        liquidity_risk = 70.0
    else:
        liquidity_risk = 90.0

    # Review signal (Rt)
    latest_signal = db.query(ReviewSignal).filter(
        ReviewSignal.store_id == store.id
    ).order_by(ReviewSignal.period_end.desc()).first()

    if latest_signal and latest_signal.sentiment_score is not None:
        review_signal = (latest_signal.sentiment_score + 1) * 50  # -1~1 → 0~100
    else:
        review_signal = 50.0

    # Health score (Bt): composite
    trend_score = min(max((revenue_trend + 1) * 50, 0), 100)
    health_score = (
        trend_score * 0.35 +
        (100 - liquidity_risk) * 0.30 +
        (100 - cost_pressure) * 0.20 +
        review_signal * 0.15
    )

    # Finance readiness (Ft)
    has_sales_data = len(sales) > 30
    has_cost_data = len(costs) > 10
    has_review = latest_signal is not None
    qt = 80 if has_sales_data and has_cost_data else (40 if has_sales_data else 10)
    dt = max(min(cash_runway_days, 60) / 60 * 100, 10)
    vt = max(100 - cost_pressure, 10)
    pt = 70 if has_review else 40
    finance_readiness = 0.3 * qt + 0.3 * dt + 0.2 * vt + 0.2 * pt

    state = BusinessState(
        store_id=store.id,
        health_score=round(health_score, 1),
        liquidity_risk=round(liquidity_risk, 1),
        revenue_trend=round(revenue_trend, 3),
        cost_pressure=round(min(cost_pressure, 100), 1),
        review_signal=round(review_signal, 1),
        finance_readiness=round(finance_readiness, 1),
        cash_runway_days=round(cash_runway_days, 1),
        detail={
            "recent_revenue_30d": round(recent_sales, 0),
            "prior_revenue_30d": round(prior_sales, 0),
            "total_cost_30d": round(total_cost_30d, 0),
            "monthly_fixed": round(monthly_fixed, 0),
            "data_period_days": len(set(s.date for s in sales)),
        },
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state
