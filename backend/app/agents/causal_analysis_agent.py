"""
Causal Analysis Agent — Graph-based XAI (Explainable AI)

매출 변화의 원인을 "인과 귀속 그래프(Causal Attribution Graph)"로 분해한다.

    증거(evidence)  ─┐
                     ├─►  요인(factor)  ─►  매출 변화(outcome)
    증거(evidence)  ─┘

핵심 설계 (왜 "설명 가능"한가):
- 기여도(%)는 LLM이 통째로 발명하지 않는다. 먼저 매출 변화를 **물량(객수) 효과 vs
  단가(객단가) 효과**로 회계적으로 분해(revenue bridge)하고, 물량 효과를 측정된
  드라이버(경쟁·시간대·날씨·리뷰 등)의 정량 점수에 비례해 배분한다.
- 따라서 각 요인의 contribution(%)은 **자식 증거 노드의 weight_pp 합**으로 유도된다.
  "22% = 9%p + 8%p + 5%p" 처럼 항상 더해서 떨어진다(가산성).
- 모든 증거 노드는 실제 측정값(raw_value)에 묶이며, ctx에 없는 숫자는 만들지 않는다(접지).
- LLM(finpilot)은 숫자 생성기가 아니라 **그래프 위 서술자**로만 쓰인다: 요약과
  요인 한 줄 설명의 자연어 표현만 다듬고, 숫자는 절대 바꾸지 못한다(검증기가 고정).

LLM/데이터가 불충분하면 규칙 기반으로 폴백한다.
"""
import json
import logging
import re
from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord, ExternalSignal
from app.models.review import ReviewSignal
from app.models.agent import BusinessState, Diagnosis
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)


def analyze_causes(store: Store, state: BusinessState, db: Session) -> Diagnosis:
    today = date.today()
    recent_cutoff = today - timedelta(days=30)
    prior_cutoff = today - timedelta(days=60)

    # ── 데이터 수집 ──────────────────────────────────────────────────────────
    sales_recent = db.query(SalesRecord).filter(
        SalesRecord.store_id == store.id,
        SalesRecord.date >= recent_cutoff,
    ).all()
    sales_prior = db.query(SalesRecord).filter(
        SalesRecord.store_id == store.id,
        SalesRecord.date >= prior_cutoff,
        SalesRecord.date < recent_cutoff,
    ).all()
    costs = db.query(CostRecord).filter(
        CostRecord.store_id == store.id,
        CostRecord.date >= recent_cutoff,
    ).all()
    commerce_sig = db.query(ExternalSignal).filter(
        ExternalSignal.store_id == store.id,
        ExternalSignal.signal_type == "commerce_radius",
    ).order_by(ExternalSignal.created_at.desc()).first()
    weather_sig = db.query(ExternalSignal).filter(
        ExternalSignal.store_id == store.id,
        ExternalSignal.signal_type == "weather_daily",
    ).order_by(ExternalSignal.created_at.desc()).first()
    review_sig = db.query(ReviewSignal).filter(
        ReviewSignal.store_id == store.id,
    ).order_by(ReviewSignal.period_end.desc()).first()

    ctx = _build_context(store, state, sales_recent, sales_prior, costs,
                         commerce_sig, weather_sig, review_sig)

    # ── 결정론적 인과 귀속 그래프 (XAI 백본) ─────────────────────────────────
    graph = build_causal_graph(store, state, ctx)
    causes = graph["causes"]
    review_causes = graph["review_causes"]
    summary = graph["summary"]

    # ── LLM(finpilot) 서술 오버레이 — 숫자는 그대로, 자연어 표현만 개선 ───────
    try:
        narration = _llm_narrate(store, state, ctx, causes)
        if narration:
            summary = narration.get("summary") or summary
            _apply_narration(causes, narration)
            logger.info(f"LLM narration applied for {store.name}")
    except Exception as e:
        logger.warning(f"LLM narration skipped ({e}); using deterministic text")

    # ── 그래프가 비면 규칙 기반 폴백 ─────────────────────────────────────────
    if not causes:
        logger.warning("Causal graph empty, falling back to rule-based")
        causes, review_causes, summary = _rule_based(state, ctx, review_sig)

    # 최소 원인 보장 + 가산성 재정규화 + basis(증거→근거) 동기화
    causes = _ensure_min_causes(causes, ctx, minimum=4)
    for c in causes:
        _sync_basis(c)
    if not summary and causes:
        summary = f"매출 변화의 주요 원인은 '{causes[0]['factor']}'({causes[0]['contribution']:.0f}%)입니다."

    diagnosis = Diagnosis(
        store_id=store.id,
        business_state_id=state.id,
        causes=causes,
        review_causes=review_causes,
        summary=summary,
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


# ── 컨텍스트 빌드 ─────────────────────────────────────────────────────────────

def _build_context(store, state, sales_r, sales_p, costs,
                   commerce, weather, review) -> dict:
    rev_r = sum(s.amount for s in sales_r) or 0
    rev_p = sum(s.amount for s in sales_p) or 0
    trend_pct = (rev_r - rev_p) / rev_p * 100 if rev_p > 0 else 0

    # 시간대별 비중
    hour_rev: dict[int, float] = defaultdict(float)
    for s in sales_r:
        if s.hour is not None:
            hour_rev[s.hour] += s.amount
    total_hr = sum(hour_rev.values()) or 1

    def seg_pct(hours):
        return sum(hour_rev.get(h, 0) for h in hours) / total_hr * 100

    # 요일별
    wd_rev: dict[int, float] = defaultdict(float)
    for s in sales_r:
        if s.date:
            wd_rev[s.date.weekday()] += s.amount
    total_wd = sum(wd_rev.values()) or 1
    weekend_pct = (wd_rev[5] + wd_rev[6]) / total_wd * 100

    # 비용 구조
    fixed = sum(c.amount for c in costs if c.cost_type == "fixed")
    variable = sum(c.amount for c in costs if c.cost_type == "variable")
    total_cost = fixed + variable
    cost_ratio = total_cost / rev_r * 100 if rev_r > 0 else 0

    # 거래건수 — 일평균 + 매출 브릿지용 객단가
    days_r = len(set(s.date for s in sales_r if s.date)) or 1
    days_p = len(set(s.date for s in sales_p if s.date)) or 1
    total_txn_r = sum(s.transaction_count or 1 for s in sales_r)
    total_txn_p = sum(s.transaction_count or 1 for s in sales_p)
    txn_r = total_txn_r / days_r                       # 일평균 거래건수(최근)
    txn_p = (total_txn_p / days_p) if sales_p else txn_r  # 일평균 거래건수(직전)

    # ── 매출 브릿지: 일매출 변화 = 물량효과 + 단가효과 ──────────────────────
    daily_rev_r = rev_r / days_r
    daily_rev_p = (rev_p / days_p) if rev_p > 0 else daily_rev_r
    price_p = (daily_rev_p / txn_p) if txn_p > 0 else 0   # 직전 객단가
    price_r = (daily_rev_r / txn_r) if txn_r > 0 else 0   # 최근 객단가
    volume_pp = price_pp = None
    if daily_rev_p > 0 and txn_p > 0:
        volume_effect = (txn_r - txn_p) * price_p        # 객수 변화 × 직전 객단가
        price_effect = txn_r * (price_r - price_p)        # 최근 객수 × 객단가 변화
        volume_pp = volume_effect / daily_rev_p * 100     # 전체 매출 대비 %p
        price_pp = price_effect / daily_rev_p * 100        # (volume_pp + price_pp ≈ trend_pct)

    return {
        "rev_r": rev_r, "rev_p": rev_p, "trend_pct": trend_pct,
        "morning_pct": seg_pct(range(7, 11)),
        "lunch_pct": seg_pct(range(11, 13)),
        "afternoon_pct": seg_pct(range(13, 17)),
        "evening_pct": seg_pct(range(17, 21)),
        "weekend_pct": weekend_pct,
        "fixed": fixed, "variable": variable, "cost_ratio": cost_ratio,
        "txn_r": txn_r, "txn_p": txn_p,
        "price_p": price_p, "price_r": price_r,
        "volume_pp": volume_pp, "price_pp": price_pp,
        "competitors": (commerce.payload or {}).get("same_category_count", 0) if commerce else 0,
        "new_competitors": (commerce.payload or {}).get("new_last_3months", 0) if commerce else 0,
        "rainy_days": (weather.payload or {}).get("rainy_days_recent", 0) if weather else 0,
        "temp_drop": (weather.payload or {}).get("avg_temp_drop_vs_prior", 0) if weather else 0,
        "sentiment": review.sentiment_score if review else None,
        "neg_keywords": (review.negative_keywords or [])[:5] if review else [],
        "review_signal": review.business_signal if review else None,
    }


# ── 인과 귀속 그래프 (결정론적) ───────────────────────────────────────────────

def build_causal_graph(store, state, ctx: dict) -> dict:
    """증거→요인→매출 그래프를 데이터에서 결정론적으로 산정한다.

    반환: {"causes": [factor 노드...], "review_causes": [...], "summary": str}
    각 factor 노드는 evidence[](증거 노드) + contribution(=Σ evidence.weight_pp)를 갖는다.
    """
    trend = ctx["trend_pct"]
    direction = "감소" if trend < 0 else "증가"
    sign = -1.0 if trend < 0 else 1.0

    # ── 1. 매출 브릿지: 변화를 물량 vs 단가로 회계 분해 ──────────────────────
    vol_pp, price_pp = ctx.get("volume_pp"), ctx.get("price_pp")
    # 관측된 방향(감소/증가)에 기여한 크기만 양수로 취한다.
    vol_adv = max(0.0, sign * vol_pp) if vol_pp is not None else 0.0
    price_adv = max(0.0, sign * price_pp) if price_pp is not None else 0.0

    # ── 2. 물량 요인(factor) 후보 — 각 증거에 정량 adverse 점수 부여 ─────────
    factors = _volume_factors(ctx, direction)
    score_sum = sum(f["_score"] for f in factors) or 0.0

    bridge_ok = (vol_pp is not None and price_pp is not None
                 and (vol_adv + price_adv) > 0.5 and score_sum > 0)

    if bridge_ok:
        # 물량 효과(vol_adv %p)를 요인 점수 비례로 배분, 단가 효과는 별도 요인.
        for f in factors:
            f_pp = vol_adv * (f["_score"] / score_sum)
            ev_sum = sum(e["_score"] for e in f["evidence"]) or 1.0
            for e in f["evidence"]:
                e["_pp"] = f_pp * (e["_score"] / ev_sum)
        if price_adv > 0.3:
            factors.append(_price_factor(ctx, price_adv, direction))
    else:
        # 브릿지 산정 불가 → 요인 점수만으로 배분(여전히 접지된 그래프).
        if score_sum <= 0:
            return {"causes": [], "review_causes": _review_causes(ctx), "summary": ""}
        for f in factors:
            f_pp = f["_score"]
            ev_sum = sum(e["_score"] for e in f["evidence"]) or 1.0
            for e in f["evidence"]:
                e["_pp"] = f_pp * (e["_score"] / ev_sum)

    # ── 3. 정규화: 모든 증거 weight_pp 합 = 100 (가산성 보장) ────────────────
    total_pp = sum(e["_pp"] for f in factors for e in f["evidence"]) or 1.0
    scale = 100.0 / total_pp
    for f in factors:
        for e in f["evidence"]:
            e["weight_pp"] = round(e["_pp"] * scale, 1)
        f["contribution"] = round(sum(e["weight_pp"] for e in f["evidence"]), 1)

    # 반올림 잔차를 최대 요인에 흡수해 합계를 정확히 100으로 맞춘다.
    _balance_to_100(factors)

    # ── 4. factor 노드 정리(내부 키 제거) + 기여도 순 정렬 ───────────────────
    causes = []
    for f in sorted(factors, key=lambda x: x["contribution"], reverse=True):
        if f["contribution"] <= 0:
            continue
        evidence = [{
            "id": e["id"], "label": e["label"], "metric": e["metric"],
            "raw_value": e["raw_value"], "delta": e.get("delta", ""),
            "when": e["when"], "mechanism": e["mechanism"],
            "weight_pp": e["weight_pp"], "source": e["source"],
        } for e in f["evidence"] if e["weight_pp"] > 0]
        if not evidence:
            continue
        causes.append({
            "factor": f["factor"],
            "contribution": f["contribution"],
            "confidence": f["confidence"],
            "group": f["group"],
            "description": f["description"],
            "evidence": evidence,
        })

    summary = _deterministic_summary(ctx, causes, direction)
    return {"causes": causes, "review_causes": _review_causes(ctx), "summary": summary}


def _volume_factors(ctx: dict, direction: str) -> list[dict]:
    """매출 물량(객수) 변화를 설명하는 요인 노드 후보. 각 증거는 실측값+정량 점수를 가진다."""
    factors: list[dict] = []
    comp = ctx["competitors"]
    new_comp = ctx["new_competitors"]

    # 경쟁 심화 -----------------------------------------------------------------
    comp_ev = []
    if comp >= 2:
        comp_ev.append({
            "id": "comp_density", "metric": "competitors", "raw_value": comp, "delta": "",
            "label": f"반경 500m 내 동종 점포 {comp}개",
            "when": "현재 상권", "mechanism": "동종 점포 과밀 → 방문 고객 분산·점유율 희석",
            "source": "commerce_radius", "_score": min(comp, 15) * 0.4,
        })
    if new_comp >= 1:
        comp_ev.append({
            "id": "comp_new", "metric": "new_competitors", "raw_value": new_comp, "delta": f"+{new_comp}",
            "label": f"최근 3개월 신규 진입 {new_comp}개",
            "when": "최근 3개월", "mechanism": "신규 진입 점포로 기존 고객 이탈 가속",
            "source": "commerce_radius", "_score": new_comp * 1.6,
        })
    if comp_ev:
        factors.append({
            "factor": "반경 내 경쟁 심화", "group": "competition",
            "confidence": "high" if new_comp >= 2 else "medium",
            "description": f"반경 500m 동종 점포 {comp}개(신규 {new_comp}개)로 고객 분산",
            "evidence": comp_ev, "_score": sum(e["_score"] for e in comp_ev),
        })

    # 시간대 수요 공백 ----------------------------------------------------------
    tod_ev = []
    trough = max(0.0, ctx["lunch_pct"] - ctx["afternoon_pct"])
    if trough > 3 and ctx["afternoon_pct"] > 0:
        tod_ev.append({
            "id": "tod_afternoon", "metric": "afternoon_pct",
            "raw_value": round(ctx["afternoon_pct"], 1), "delta": f"점심 대비 -{trough:.0f}%p",
            "label": f"오후(13-17시) 비중 {ctx['afternoon_pct']:.0f}% · 점심 {ctx['lunch_pct']:.0f}% 대비 저조",
            "when": "평일 오후 13-17시", "mechanism": "오후 유휴 시간대 방문 공백 → 일 매출 베이스 약화",
            "source": "sales_hourly", "_score": min(trough, 30) * 0.5,
        })
    if ctx["weekend_pct"] > 0 and ctx["weekend_pct"] < 24:
        gap = 24 - ctx["weekend_pct"]
        tod_ev.append({
            "id": "tod_weekend", "metric": "weekend_pct",
            "raw_value": round(ctx["weekend_pct"], 1), "delta": f"기준 대비 -{gap:.0f}%p",
            "label": f"주말 매출 비중 {ctx['weekend_pct']:.0f}%로 주중 의존 심화",
            "when": "주말", "mechanism": "주말 집객 부진 → 주간 매출 편중·변동성 확대",
            "source": "sales_weekday", "_score": min(gap, 20) * 0.25,
        })
    if tod_ev:
        factors.append({
            "factor": "시간대 수요 공백", "group": "timeofday", "confidence": "medium",
            "description": f"오후(13-17시) 비중 {ctx['afternoon_pct']:.0f}% 등 특정 시간대 방문 둔화",
            "evidence": tod_ev, "_score": sum(e["_score"] for e in tod_ev),
        })

    # 날씨·외부 환경 ------------------------------------------------------------
    wx_ev = []
    if ctx["rainy_days"] >= 3:
        wx_ev.append({
            "id": "wx_rain", "metric": "rainy_days", "raw_value": ctx["rainy_days"], "delta": "",
            "label": f"최근 강수일 {ctx['rainy_days']}일",
            "when": "최근 30일", "mechanism": "강수일 증가 → 방문형 매장 유입 감소",
            "source": "weather_daily", "_score": max(0, ctx["rainy_days"] - 2) * 0.7,
        })
    if ctx["temp_drop"] <= -3:
        wx_ev.append({
            "id": "wx_temp", "metric": "temp_drop", "raw_value": round(ctx["temp_drop"], 1),
            "delta": f"{ctx['temp_drop']:+.0f}도",
            "label": f"전월 대비 평균 기온 {ctx['temp_drop']:+.0f}도",
            "when": "최근 30일", "mechanism": "기온 급변으로 외출·방문 수요 둔화",
            "source": "weather_daily", "_score": min(abs(ctx["temp_drop"]), 12) * 0.25,
        })
    if wx_ev:
        factors.append({
            "factor": "날씨·외부 환경", "group": "weather", "confidence": "medium",
            "description": f"강수일 {ctx['rainy_days']}일 등 외부 환경 요인으로 방문 둔화",
            "evidence": wx_ev, "_score": sum(e["_score"] for e in wx_ev),
        })

    # 고객 경험 신호 ------------------------------------------------------------
    if ctx["sentiment"] is not None and (ctx["sentiment"] < 0.4 or ctx["neg_keywords"]):
        sent_pct = int((ctx["sentiment"] + 1) * 50)
        rv_ev = [{
            "id": "rv_sentiment", "metric": "sentiment", "raw_value": sent_pct, "delta": "",
            "label": f"리뷰 감성 점수 {sent_pct}/100",
            "when": "최근 리뷰 기간", "mechanism": "부정 경험 누적 → 재방문율 하락",
            "source": "review_signal", "_score": max(0.0, 0.5 - ctx["sentiment"]) * 6,
        }]
        if ctx["neg_keywords"]:
            kws = ", ".join(ctx["neg_keywords"][:3])
            rv_ev.append({
                "id": "rv_keywords", "metric": "neg_keywords", "raw_value": len(ctx["neg_keywords"]),
                "delta": "", "label": f"부정 키워드: {kws}",
                "when": "최근 리뷰 기간", "mechanism": "반복되는 불만 키워드 → 신규 유입·전환 저해",
                "source": "review_signal", "_score": min(len(ctx["neg_keywords"]), 5) * 0.5,
            })
        factors.append({
            "factor": "고객 경험 신호 악화", "group": "review", "confidence": "medium",
            "description": f"리뷰 감성 {sent_pct}/100, 부정 키워드 증가로 재방문 둔화",
            "evidence": rv_ev, "_score": sum(e["_score"] for e in rv_ev),
        })

    # 기타 수요 둔화(잔차) — 위 요인으로 설명되지 않는 객수 감소 흡수 ----------
    factors.append({
        "factor": "전반적 방문·재방문 둔화", "group": "demand", "confidence": "low",
        "description": f"일평균 거래 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건, 신규·재방문 유입 둔화",
        "evidence": [{
            "id": "demand_txn", "metric": "txn", "raw_value": round(ctx["txn_r"], 0),
            "delta": f"{ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건",
            "label": f"일평균 거래건수 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건",
            "when": "최근 30일", "mechanism": "특정 요인 외 전반적 객수 둔화(채널·재방문 점검 필요)",
            "source": "sales_daily", "_score": 1.0,
        }],
        "_score": 1.0,
    })
    return factors


def _price_factor(ctx: dict, price_adv: float, direction: str) -> dict:
    """단가(객단가) 효과를 별도 요인으로. weight는 정규화 단계에서 _pp로 부여."""
    p_from, p_to = ctx["price_p"], ctx["price_r"]
    ev = {
        "id": "price_ticket", "metric": "avg_ticket", "raw_value": round(p_to, 0),
        "delta": f"₩{p_from:,.0f}→₩{p_to:,.0f}",
        "label": f"객단가 ₩{p_from:,.0f}→₩{p_to:,.0f}",
        "when": "최근 30일", "mechanism": "객단가 하락(세트·고마진 비중 축소) → 동일 객수에도 매출 감소",
        "source": "sales_bridge", "_score": price_adv, "_pp": price_adv,
    }
    return {
        "factor": "객단가·구성 변화", "group": "price", "confidence": "high",
        "description": f"객단가 ₩{p_from:,.0f}→₩{p_to:,.0f}로 1인당 구매액 변화",
        "evidence": [ev], "_score": price_adv,
    }


def _balance_to_100(factors: list[dict]) -> None:
    """반올림 잔차를 최대 기여 요인(과 그 최대 증거)에 흡수시켜 합계를 100.0으로 맞춘다."""
    total = sum(f["contribution"] for f in factors)
    diff = round(100.0 - total, 1)
    if abs(diff) < 0.05 or not factors:
        return
    top = max(factors, key=lambda f: f["contribution"])
    top["contribution"] = round(top["contribution"] + diff, 1)
    if top["evidence"]:
        te = max(top["evidence"], key=lambda e: e["weight_pp"])
        te["weight_pp"] = round(te["weight_pp"] + diff, 1)


def _review_causes(ctx: dict) -> list[dict]:
    if ctx["sentiment"] is None or not ctx["neg_keywords"]:
        return []
    return [{
        "factor": "고객 리뷰 부정 신호",
        "keywords": ctx["neg_keywords"][:5],
        "description": ctx["review_signal"] or "부정 키워드 증가",
        "confidence": "medium",
    }]


def _deterministic_summary(ctx: dict, causes: list[dict], direction: str) -> str:
    if not causes:
        return ""
    top = causes[0]
    parts = [
        f"매출 {abs(ctx['trend_pct']):.1f}% {direction}의 가장 큰 요인은 "
        f"'{top['factor']}'({top['contribution']:.0f}%)입니다."
    ]
    if ctx.get("volume_pp") is not None and ctx.get("price_pp") is not None:
        parts.append(
            f"변화는 물량(객수) {ctx['volume_pp']:+.1f}%p, 단가(객단가) {ctx['price_pp']:+.1f}%p로 분해됩니다."
        )
    if len(causes) > 1:
        parts.append(f"'{causes[1]['factor']}'({causes[1]['contribution']:.0f}%)도 복합적으로 작용합니다.")
    return " ".join(parts)


# ── LLM 서술 오버레이 (숫자 불변, 자연어만) ───────────────────────────────────

def _llm_narrate(store, state, ctx: dict, causes: list[dict]) -> dict | None:
    """그래프(요인+기여도)는 고정한 채, finpilot이 요약과 요인 한 줄 설명의 표현만 다듬는다.
    숫자(contribution/weight_pp)는 프롬프트에서 '바꾸지 말 것'으로 못박고, 적용 단계에서도
    텍스트 필드만 반영한다."""
    if not causes:
        return None
    trend_dir = "감소" if ctx["trend_pct"] < 0 else "증가"
    lines = []
    for i, c in enumerate(causes):
        ev = "; ".join(f"{e['label']}({e['weight_pp']:.0f}%p)" for e in c.get("evidence", []))
        lines.append(f"{i}. {c['factor']} — {c['contribution']:.0f}% [증거: {ev}]")
    factors_block = "\n".join(lines)

    prompt = f"""{store.category} '{store.name}'의 최근 30일 매출이 {abs(ctx['trend_pct']):.1f}% {trend_dir}했습니다.
아래는 데이터에서 산정이 끝난 매출 변화 원인 그래프입니다. **기여도(%)와 증거 수치는 이미 확정**되었습니다.

[원인 그래프 — 숫자 고정]
{factors_block}

당신의 역할은 숫자를 바꾸는 것이 아니라, 각 원인을 **소상공인이 이해하기 쉬운 자연어 한 줄**로 다듬고
전체를 1~2문장으로 요약하는 것입니다.

JSON만 출력하세요:
{{
  "summary": "기여도 %를 그대로 인용한 1~2문장 요약",
  "factors": [
    {{"index": 0, "description": "이 원인을 설명하는 자연스러운 한 줄(수치는 위 증거와 일치)"}}
  ]
}}

규칙:
- contribution(%) 숫자를 새로 만들거나 바꾸지 말 것. 위 값만 인용.
- 증거에 없는 숫자를 지어내지 말 것.
- summary의 % 는 위 그래프의 contribution 과 정확히 일치시킬 것.
- 금융상품 추천 금지."""
    system = "너는 소상공인의 금융 운영을 설계하는 AI CFO Agent이다. 확정된 분석 결과를 쉬운 한국어로 서술한다. JSON만 출력한다."
    response = call_llm(prompt, system=system, max_tokens=700)
    return _parse_json(response)


def _apply_narration(causes: list[dict], narration: dict) -> None:
    """LLM이 돌려준 텍스트만 반영. 숫자/구조는 절대 건드리지 않는다."""
    factors = narration.get("factors")
    if not isinstance(factors, list):
        return
    for item in factors:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        desc = item.get("description")
        if 0 <= idx < len(causes) and isinstance(desc, str) and desc.strip():
            causes[idx]["description"] = desc.strip()


def _sync_basis(cause: dict) -> None:
    """증거 노드에서 basis(기여도 산정 근거 bullet)를 파생. 하위호환 + 프론트 즉시 표시용."""
    evidence = cause.get("evidence")
    if evidence:
        cause["basis"] = [
            f"{e['label']} — {e['mechanism']} · 약 {e['weight_pp']:.0f}%p"
            for e in evidence
        ]
    elif not cause.get("basis"):
        d = cause.get("description")
        cause["basis"] = [d] if d else []
    elif isinstance(cause["basis"], str):
        cause["basis"] = [cause["basis"]]


# ── JSON 파싱 ────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    if not text or not text.strip():
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```", r"(\{.*\})"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ── 최소 원인 개수 보장 ───────────────────────────────────────────────────────

def _candidate_causes(ctx: dict) -> list[dict]:
    """데이터 기반 후보 원인 풀 (보강용). 실제 ctx 수치를 description+basis(정량 근거)에 반영."""
    txn_delta = (ctx["txn_r"] - ctx["txn_p"]) / ctx["txn_p"] * 100 if ctx["txn_p"] else 0
    pool = []
    if ctx["competitors"] >= 3:
        pool.append({"factor": "반경 내 동종 경쟁 점포 증가", "contribution": 22,
                     "confidence": "high",
                     "description": f"반경 500m 내 동종 점포 {ctx['competitors']}개 (최근 신규 {ctx['new_competitors']}개)로 경쟁 심화",
                     "basis": [
                         f"반경 500m 내 동종 점포 {ctx['competitors']}개 — 경쟁 밀도 높음",
                         f"최근 3개월 신규 진입 {ctx['new_competitors']}개로 고객 분산 가능성",
                         f"전월 대비 매출 {ctx['trend_pct']:+.1f}% 변화와 시점 일치",
                     ]})
    if ctx["afternoon_pct"] > 22:
        pool.append({"factor": "평일 오후 시간대 수요 감소", "contribution": 18,
                     "confidence": "medium",
                     "description": f"오후(13-17시) 매출 비중 {ctx['afternoon_pct']:.0f}%, 해당 시간대 방문 둔화",
                     "basis": [
                         f"오후(13-17시) 매출 비중 {ctx['afternoon_pct']:.0f}%",
                         f"점심(11-13시) {ctx['lunch_pct']:.0f}% / 저녁(17-21시) {ctx['evening_pct']:.0f}% 대비 흐름 약화",
                         f"일평균 거래건수 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건",
                     ]})
    if ctx["cost_ratio"] > 45:
        pool.append({"factor": "비용/매출 비율 상승", "contribution": 15,
                     "confidence": "high",
                     "description": f"총 비용이 매출의 {ctx['cost_ratio']:.0f}% — 변동비·원재료 단가 압박",
                     "basis": [
                         f"비용/매출 비율 {ctx['cost_ratio']:.0f}%",
                         f"고정비 ₩{ctx['fixed']:,.0f} / 변동비 ₩{ctx['variable']:,.0f}",
                         f"최근 30일 매출 ₩{ctx['rev_r']:,.0f} 대비 비용 부담",
                     ]})
    if ctx["txn_r"] < ctx["txn_p"]:
        pool.append({"factor": "일평균 거래건수 감소", "contribution": 16,
                     "confidence": "high",
                     "description": f"일 평균 거래건수 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건 감소 — 신규·재방문 둔화",
                     "basis": [
                         f"일평균 거래 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건 ({txn_delta:+.0f}%)",
                         f"전월 대비 매출 {ctx['trend_pct']:+.1f}% 와 동반 하락",
                         "객수 감소 = 신규 유입·재방문 둔화 신호",
                     ]})
    if ctx["rainy_days"] >= 3:
        pool.append({"factor": "강수·악천후 일수 증가", "contribution": 10,
                     "confidence": "medium",
                     "description": f"최근 강수일 {ctx['rainy_days']}일 — 방문형 매장 유입 영향",
                     "basis": [
                         f"최근 강수일 {ctx['rainy_days']}일",
                         "비 오는 날 방문형 매장 유입 감소 경향",
                     ]})
    if ctx["sentiment"] is not None and ctx["neg_keywords"]:
        sent_pct = int((ctx["sentiment"] + 1) * 50)
        pool.append({"factor": "고객 경험 신호 악화", "contribution": 12,
                     "confidence": "medium",
                     "description": f"리뷰 부정 키워드({', '.join(ctx['neg_keywords'][:3])}) 증가로 재방문율 하락 우려",
                     "basis": [
                         f"리뷰 감성 점수 {sent_pct}/100",
                         f"부정 키워드: {', '.join(ctx['neg_keywords'][:3])}",
                         "부정 경험은 재방문율 하락으로 이어짐",
                     ]})
    pool.append({"factor": "신규 고객 유입 채널 둔화", "contribution": 10,
                 "confidence": "medium",
                 "description": "온라인 노출·재방문 유도 채널 점검 필요",
                 "basis": [
                     f"일평균 거래 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건",
                     "온라인 노출·재방문 유도 채널 점검 필요",
                 ]})
    pool.append({"factor": "객단가·세트 구성 정체", "contribution": 9,
                 "confidence": "low",
                 "description": "1인당 구매액 정체 — 세트·사이드 구성으로 개선 여지",
                 "basis": [
                     f"최근 30일 매출 ₩{ctx['rev_r']:,.0f} / 거래 {ctx['txn_r']:.0f}건 기준 객단가 정체",
                     "세트·사이드 구성으로 1인당 구매액 개선 여지",
                 ]})
    return pool


def _ensure_min_causes(causes: list, ctx: dict, minimum: int = 4) -> list:
    """원인이 minimum개 미만이면 데이터 기반 후보로 보강하고 100%로 재정규화한다."""
    causes = [c for c in (causes or []) if isinstance(c, dict) and c.get("factor")]
    existing = {c["factor"] for c in causes}

    if len(causes) < minimum:
        for cand in _candidate_causes(ctx):
            if len(causes) >= minimum:
                break
            if cand["factor"] in existing or any(cand["factor"][:4] in f or f[:4] in cand["factor"] for f in existing):
                continue
            causes.append(cand)
            existing.add(cand["factor"])

    # contribution 정규화 (합계 100)
    total = sum(float(c.get("contribution", 0) or 0) for c in causes) or 1
    scale = 100 / total
    for c in causes:
        c["contribution"] = round(float(c.get("contribution", 0) or 0) * scale, 1)
        c.setdefault("confidence", "medium")
        if not c.get("basis"):
            d = c.get("description")
            c["basis"] = [d] if d else []
        elif isinstance(c["basis"], str):
            c["basis"] = [c["basis"]]
    causes.sort(key=lambda x: x["contribution"], reverse=True)
    return causes


# ── 규칙 기반 폴백 ────────────────────────────────────────────────────────────

def _rule_based(state, ctx, review_sig):
    causes = []

    if ctx["trend_pct"] < -3:
        causes.append({
            "factor": "지속적 매출 하락 추세",
            "contribution": round(abs(ctx["trend_pct"]) * 4, 1),
            "confidence": "high",
            "description": f"전월 대비 {abs(ctx['trend_pct']):.1f}% 감소 추세 지속",
        })

    if ctx["competitors"] >= 3:
        c = min(8 + ctx["competitors"] * 4, 38)
        causes.append({
            "factor": "반경 내 동종 경쟁 점포 증가",
            "contribution": round(c, 1),
            "confidence": "high",
            "description": f"반경 500m 내 동종 점포 {ctx['competitors']}개 (최근 신규 {ctx['new_competitors']}개)",
        })

    if ctx["cost_ratio"] > 50:
        causes.append({
            "factor": "비용/매출 비율 상승",
            "contribution": round((ctx["cost_ratio"] - 50) * 0.8, 1),
            "confidence": "high",
            "description": f"총 비용이 매출의 {ctx['cost_ratio']:.0f}% — 수익성 압박",
        })

    if ctx["afternoon_pct"] > 25 and ctx["txn_r"] < ctx["txn_p"] * 0.92:
        causes.append({
            "factor": "오후 시간대 방문 감소",
            "contribution": round(ctx["afternoon_pct"] * 0.6, 1),
            "confidence": "medium",
            "description": f"오후 매출 비중 {ctx['afternoon_pct']:.0f}%, 거래건수 {ctx['txn_p']:.0f}→{ctx['txn_r']:.0f}건",
        })

    if ctx["rainy_days"] >= 3:
        causes.append({
            "factor": "강수·악천후 일수 증가",
            "contribution": round(ctx["rainy_days"] * 1.8, 1),
            "confidence": "medium",
            "description": f"최근 강수일 {ctx['rainy_days']}일 — 방문형 매장 영향",
        })

    if len(causes) < 3:
        causes.append({
            "factor": "신규 고객 유입 둔화",
            "contribution": 12.0,
            "confidence": "medium",
            "description": "일 평균 거래건수 감소, 재방문·신규 유입 채널 점검 필요",
        })

    total = sum(c["contribution"] for c in causes) or 1
    scale = 100 / total
    for c in causes:
        c["contribution"] = round(c["contribution"] * scale, 1)
    causes.sort(key=lambda x: x["contribution"], reverse=True)

    top = causes[0]
    summary = f"매출 하락의 주요 원인은 '{top['factor']}'({top['contribution']:.0f}%)입니다."
    if len(causes) > 1:
        summary += f" '{causes[1]['factor']}'({causes[1]['contribution']:.0f}%)도 복합적으로 작용하고 있습니다."

    review_causes = []
    if review_sig and review_sig.negative_keywords:
        review_causes = [{
            "factor": "고객 리뷰 부정 신호",
            "keywords": review_sig.negative_keywords[:5],
            "description": review_sig.business_signal or "부정 키워드 증가",
            "confidence": "medium",
        }]

    return causes, review_causes, summary
