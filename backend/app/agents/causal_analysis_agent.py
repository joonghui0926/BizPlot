"""
Causal Analysis Agent — LLM-first
파인튜닝된 Qwen(finpilot)이 데이터를 직접 읽고 원인을 추론.
LLM 실패 시 규칙 기반으로 폴백.
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

    # ── LLM 분석 (파인튜닝 Qwen) ─────────────────────────────────────────────
    causes, review_causes, summary = [], [], ""
    try:
        result = _llm_analyze(store, state, ctx)
        if result and _validate(result):
            causes = result.get("causes", [])
            review_causes = result.get("review_causes", [])
            summary = result.get("summary", "")
            logger.info(f"LLM analysis OK: {len(causes)} causes for {store.name}")
        else:
            logger.warning("LLM result invalid, falling back to rule-based")
            causes, review_causes, summary = _rule_based(state, ctx, review_sig)
    except Exception as e:
        logger.warning(f"LLM analysis failed ({e}), falling back to rule-based")
        causes, review_causes, summary = _rule_based(state, ctx, review_sig)

    # 원인은 항상 최소 4개 보장 (부족하면 데이터 기반 후보로 보강 + 재정규화)
    causes = _ensure_min_causes(causes, ctx, minimum=4)
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

    # 일 평균 거래건수 변화
    days_r = len(set(s.date for s in sales_r if s.date)) or 1
    days_p = len(set(s.date for s in sales_p if s.date)) or 1
    txn_r = sum(s.transaction_count or 1 for s in sales_r) / days_r
    txn_p = sum(s.transaction_count or 1 for s in sales_p) / days_p if sales_p else txn_r

    return {
        "rev_r": rev_r, "rev_p": rev_p, "trend_pct": trend_pct,
        "morning_pct": seg_pct(range(7, 11)),
        "lunch_pct": seg_pct(range(11, 13)),
        "afternoon_pct": seg_pct(range(13, 17)),
        "evening_pct": seg_pct(range(17, 21)),
        "weekend_pct": weekend_pct,
        "fixed": fixed, "variable": variable, "cost_ratio": cost_ratio,
        "txn_r": txn_r, "txn_p": txn_p,
        "competitors": (commerce.payload or {}).get("same_category_count", 0) if commerce else 0,
        "new_competitors": (commerce.payload or {}).get("new_last_3months", 0) if commerce else 0,
        "rainy_days": (weather.payload or {}).get("rainy_days_recent", 0) if weather else 0,
        "temp_drop": (weather.payload or {}).get("avg_temp_drop_vs_prior", 0) if weather else 0,
        "sentiment": review.sentiment_score if review else None,
        "neg_keywords": (review.negative_keywords or [])[:5] if review else [],
        "review_signal": review.business_signal if review else None,
    }


# ── LLM 프롬프트 + 파싱 ───────────────────────────────────────────────────────

def _llm_analyze(store, state, ctx: dict) -> dict | None:
    trend_dir = "감소" if ctx["trend_pct"] < 0 else "증가"
    runway = state.cash_runway_days or 0

    sentiment_line = ""
    if ctx["sentiment"] is not None:
        score_pct = int((ctx["sentiment"] + 1) * 50)
        kws = ", ".join(ctx["neg_keywords"]) if ctx["neg_keywords"] else "없음"
        sentiment_line = f"- 고객 리뷰 감성 점수: {score_pct}/100 (부정 키워드: {kws})"
    if ctx["review_signal"]:
        sentiment_line += f"\n- 리뷰 신호: {ctx['review_signal']}"

    prompt = f"""{store.category} '{store.name}'의 최근 30일 매출이 {abs(ctx['trend_pct']):.1f}% {trend_dir}했습니다.
현금 유지 가능 기간은 {runway:.0f}일로 예측됩니다.

다음 데이터를 바탕으로 매출 하락 원인을 분해하고 기여도를 분석해주세요:

[매출 데이터]
- 최근 30일 매출: ₩{ctx['rev_r']:,.0f} (전월 대비 {ctx['trend_pct']:+.1f}%)
- 일 평균 거래건수 변화: {ctx['txn_p']:.0f}건 → {ctx['txn_r']:.0f}건

[시간대별 매출 비중]
- 오전(7-11시): {ctx['morning_pct']:.0f}%
- 점심(11-13시): {ctx['lunch_pct']:.0f}%
- 오후(13-17시): {ctx['afternoon_pct']:.0f}%
- 저녁(17-21시): {ctx['evening_pct']:.0f}%
- 주말 매출 비중: {ctx['weekend_pct']:.0f}%

[비용 구조]
- 고정비: ₩{ctx['fixed']:,.0f} / 변동비: ₩{ctx['variable']:,.0f}
- 비용/매출 비율: {ctx['cost_ratio']:.0f}%

[상권 신호]
- 반경 500m 내 동종 점포: {ctx['competitors']}개 (최근 3개월 신규 {ctx['new_competitors']}개)

[날씨 신호]
- 최근 강수일: {ctx['rainy_days']}일
- 기온 변화: {ctx['temp_drop']:+.0f}도

[고객 리뷰]
{sentiment_line if sentiment_line else '- 리뷰 데이터 없음'}

JSON 형식으로만 출력하세요 (다른 텍스트 없이):
{{
  "causes": [
    {{"factor": "원인명", "contribution": 기여도숫자, "confidence": "high|medium|low",
      "description": "한 줄 핵심 설명",
      "basis": ["이 기여도(%)를 그렇게 산정한 정량적 근거 1", "근거 2", "근거 3"]}}
  ],
  "review_causes": [],
  "summary": "한두 문장 요약"
}}

요구사항:
- causes는 반드시 4~6개, contribution 합계는 정확히 100
- 각 원인의 "basis"에는 그 기여도(%)가 왜 그 수치인지 **정량적 근거를 2~3개 bullet**으로 쓴다.
  위에 제공된 실제 수치(매출 변화율, 시간대별 매출 비중, 일평균 거래건수, 반경 내 경쟁 점포 수,
  비용/매출 비율, 강수일, 리뷰 감성·키워드)만 인용한다. 입력에 없는 숫자는 절대 지어내지 않는다.
- basis 예시: "오후(13-17시) 매출 비중 28%로 전체 시간대 중 최저", "일평균 거래 142→118건(-17%)"
- 기여도가 큰 원인일수록 basis 근거가 더 강하고 구체적이어야 한다 (정량적·합리적).
- 금융상품 추천 금지"""

    system = "너는 소상공인의 금융 운영을 설계하는 AI CFO Agent이다. 사업 데이터를 분석하여 현금흐름 위험을 진단한다. JSON만 출력한다."
    response = call_llm(prompt, system=system, max_tokens=800)
    return _parse_json(response)


def _parse_json(text: str) -> dict | None:
    if not text or not text.strip():
        return None
    # <think>...</think> 제거
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # JSON 블록 추출
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


def _validate(result: dict) -> bool:
    if not isinstance(result, dict):
        return False
    causes = result.get("causes", [])
    if not causes or not isinstance(causes, list):
        return False
    if len(causes) < 2 or len(causes) > 8:
        return False
    for c in causes:
        if not isinstance(c, dict):
            return False
        if "factor" not in c or "contribution" not in c:
            return False
        try:
            pct = float(c["contribution"])
            if pct <= 0 or pct > 100:
                return False
        except (TypeError, ValueError):
            return False
    total = sum(float(c.get("contribution", 0)) for c in causes)
    # 합계가 60~140% 범위면 정규화
    return 60 <= total <= 140


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
    # 항상 마지막 보강용 일반 원인
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
            # 비슷한 factor 중복 방지 (앞 4글자 겹치면 스킵)
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
        # basis(정량 근거) 보장: 없으면 description을 근거 한 줄로라도 채운다
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

    # 최소 3개 보장
    if len(causes) < 3:
        causes.append({
            "factor": "신규 고객 유입 둔화",
            "contribution": 12.0,
            "confidence": "medium",
            "description": "일 평균 거래건수 감소, 재방문·신규 유입 채널 점검 필요",
        })

    # 정규화
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
