"""
FinPilot QLoRA 파인튜닝 학습 데이터 생성
Qwen3.6-27B 기반 소상공인 AI CFO Agent 전용
총 500+ 고품질 instruction-following 샘플
"""
import json
import random
from pathlib import Path

OUTPUT_PATH = "/SSD/guest/chojoonghui/FinPilot/data/training"
Path(OUTPUT_PATH).mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "너는 소상공인의 금융 운영을 설계하는 AI CFO Agent이다. "
    "사업 데이터(매출·비용·상권·날씨·리뷰)를 분석하여 "
    "현금흐름 위험을 진단하고 금융 및 운영 전략을 제안한다. "
    "수치 계산은 제공된 데이터 기반으로만 수행하며, "
    "금융상품 단정 추천이나 근거 없는 정책 정보는 제공하지 않는다."
)

# ─────────────────────────────────────────────────────────────────
# 1. 사업 상태 진단 데이터 (State JSON 생성)
# ─────────────────────────────────────────────────────────────────
def gen_diagnosis_samples(n=80):
    samples = []
    scenarios = [
        {"category": "카페", "revenue_trend": -0.14, "cost_pressure": 72, "health": 58, "runway": 17, "liquidity": 75, "finance_readiness": 58},
        {"category": "음식점", "revenue_trend": -0.08, "cost_pressure": 65, "health": 65, "runway": 28, "liquidity": 55, "finance_readiness": 62},
        {"category": "제과점", "revenue_trend": 0.05, "cost_pressure": 45, "health": 78, "runway": 65, "liquidity": 20, "finance_readiness": 75},
        {"category": "카페", "revenue_trend": -0.25, "cost_pressure": 82, "health": 42, "runway": 9, "liquidity": 90, "finance_readiness": 40},
        {"category": "음식점", "revenue_trend": 0.12, "cost_pressure": 38, "health": 85, "runway": 90, "liquidity": 10, "finance_readiness": 88},
        {"category": "미용", "revenue_trend": -0.06, "cost_pressure": 55, "health": 70, "runway": 35, "liquidity": 45, "finance_readiness": 68},
        {"category": "소매", "revenue_trend": -0.18, "cost_pressure": 78, "health": 50, "runway": 14, "liquidity": 82, "finance_readiness": 45},
    ]
    for i in range(n):
        s = scenarios[i % len(scenarios)]
        rev = random.uniform(8_000_000, 25_000_000)
        cost = rev * (0.7 + random.uniform(-0.1, 0.15))

        user_msg = f"""다음 사업 데이터를 분석하여 사업 상태를 JSON으로 출력하세요.

업종: {s['category']}
최근 30일 매출: ₩{rev:,.0f}
이전 30일 매출: ₩{rev/(1+s['revenue_trend']):,.0f}
최근 30일 비용: ₩{cost:,.0f}
고정비(임대료·인건비): ₩{cost*0.6:,.0f}
변동비(원재료·기타): ₩{cost*0.4:,.0f}"""

        assistant_msg = json.dumps({
            "health_score": round(s["health"] + random.uniform(-3, 3), 1),
            "liquidity_risk": round(s["liquidity"] + random.uniform(-5, 5), 1),
            "revenue_trend": round(s["revenue_trend"] + random.uniform(-0.02, 0.02), 3),
            "cost_pressure": round(s["cost_pressure"] + random.uniform(-3, 3), 1),
            "finance_readiness": round(s["finance_readiness"] + random.uniform(-3, 3), 1),
            "cash_runway_days": round(s["runway"] + random.uniform(-2, 2), 1),
            "diagnosis": (
                f"매출이 전월 대비 {abs(s['revenue_trend'])*100:.0f}% {'감소' if s['revenue_trend']<0 else '증가'}했습니다. "
                f"현재 비용 압박도 {s['cost_pressure']}점으로 {'높은' if s['cost_pressure']>60 else '보통'} 수준입니다. "
                f"현금 유지 가능 기간은 약 {s['runway']}일로 "
                f"{'즉각적인 조치가 필요합니다.' if s['runway']<20 else '주의가 필요한 수준입니다.' if s['runway']<40 else '안정적입니다.'}"
            )
        }, ensure_ascii=False, indent=2)

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 2. 원인 분석 데이터 (Causal Analysis)
# ─────────────────────────────────────────────────────────────────
def gen_causal_samples(n=80):
    samples = []
    cause_templates = [
        {
            "pattern": "오후 시간대 집중 + 경쟁점포",
            "causes": [
                {"factor": "평일 오후 시간대 수요 감소", "contribution": 42.0, "confidence": "high", "description": "오후 14-17시 매출이 3주간 38% 감소"},
                {"factor": "반경 내 동종 경쟁점포 증가", "contribution": 27.0, "confidence": "high", "description": "반경 500m 내 동종 점포 3개 신규 진입"},
                {"factor": "원재료 비용 상승", "contribution": 19.0, "confidence": "medium", "description": "변동비 8% 상승"},
                {"factor": "강수일 증가", "contribution": 12.0, "confidence": "medium", "description": "최근 강수일 9일"},
            ],
        },
        {
            "pattern": "배달 매출 감소 + 리뷰 악화",
            "causes": [
                {"factor": "배달앱 평점 하락으로 인한 노출 감소", "contribution": 38.0, "confidence": "high", "description": "배달앱 평점 4.3→3.9 하락, 주문 건수 25% 감소"},
                {"factor": "포장 품질 불만 증가", "contribution": 32.0, "confidence": "high", "description": "리뷰에서 '포장', '식음', '배달 지연' 키워드 증가"},
                {"factor": "경쟁 메뉴 가격 경쟁", "contribution": 18.0, "confidence": "medium", "description": "인근 유사 메뉴 가격 10% 저렴"},
                {"factor": "기상 악화", "contribution": 12.0, "confidence": "low", "description": "최근 강수일 증가로 외출 감소"},
            ],
        },
        {
            "pattern": "고정비 증가",
            "causes": [
                {"factor": "임대료 인상으로 인한 고정비 부담 증가", "contribution": 45.0, "confidence": "high", "description": "임대료 15% 인상, 고정비/매출 비율 58%→68%"},
                {"factor": "인건비 상승", "contribution": 30.0, "confidence": "high", "description": "최저임금 인상으로 인건비 12% 증가"},
                {"factor": "매출 정체", "contribution": 15.0, "confidence": "medium", "description": "매출은 유지되나 비용 증가로 수익성 악화"},
                {"factor": "상권 성숙기 진입", "contribution": 10.0, "confidence": "low", "description": "상권 내 신규 유입 고객 감소"},
            ],
        },
    ]

    contexts = [
        {"category": "카페", "trend": -14, "runway": 17, "period": "3주"},
        {"category": "음식점", "trend": -22, "runway": 11, "period": "4주"},
        {"category": "제과점", "trend": -9, "runway": 28, "period": "2주"},
    ]

    for i in range(n):
        template = cause_templates[i % len(cause_templates)]
        ctx = contexts[i % len(contexts)]

        user_msg = f"""{ctx['category']}의 최근 {ctx['period']}간 매출이 {ctx['trend']}% 감소했습니다.
현금 유지 가능 기간은 {ctx['runway']}일로 예측됩니다.

다음 데이터를 바탕으로 매출 하락 원인을 분해하고 기여도를 분석해주세요:
- 시간대별 매출 패턴 변화
- 반경 500m 내 경쟁점포 현황
- 최근 날씨 및 강수 데이터
- 고객 리뷰 감성 변화
- 비용 구조 변화"""

        causes_with_desc = [
            {
                "factor": c["factor"],
                "contribution": round(c["contribution"] + random.uniform(-3, 3), 1),
                "confidence": c["confidence"],
                "description": c["description"],
            }
            for c in template["causes"]
        ]

        summary = (
            f"매출 하락의 주요 원인은 '{causes_with_desc[0]['factor']}'({causes_with_desc[0]['contribution']:.0f}%)입니다. "
            f"{'현금 유지 기간이 ' + str(ctx['runway']) + '일로 즉각적인 조치가 필요합니다.' if ctx['runway'] < 20 else '단기 대응과 함께 중기 개선 전략이 필요합니다.'}"
        )

        assistant_msg = json.dumps({
            "causes": causes_with_desc,
            "review_causes": [
                {
                    "factor": "고객 경험 리스크",
                    "keywords": ["대기", "불친절", "가격"] if "리뷰" in template["pattern"] else ["맛", "친절", "가격"],
                    "confidence": "medium",
                    "description": "최근 리뷰에서 부정 키워드 증가 감지",
                }
            ] if "리뷰" in template["pattern"] else [],
            "summary": summary,
        }, ensure_ascii=False, indent=2)

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 3. 전략 생성 데이터 (Strategy Planning)
# ─────────────────────────────────────────────────────────────────
def gen_strategy_samples(n=80):
    samples = []
    strategy_templates = [
        {
            "situation": "매출 감소 + 유동성 위험",
            "actions": [
                {
                    "type": "operation", "title": "원재료 발주량 10% 감축",
                    "description": "변동비 절감을 통한 현금흐름 개선. 일평균 발주량 기준 10% 축소하여 월 약 30만원 절감 가능.",
                    "expected_impact": {"cash_runway_days_delta": 6, "cost_change_pct": -8},
                },
                {
                    "type": "marketing", "title": "평일 오후 재방문 쿠폰 발행",
                    "description": "매출 하락 시간대(14-17시) 재방문 쿠폰 제공. 기존 고객 이탈 방어 및 시간대별 매출 균형화.",
                    "expected_impact": {"revenue_change_pct": 8},
                },
                {
                    "type": "finance", "title": "금융 상담 준비 리포트 생성",
                    "description": "소상공인 경영안정자금 또는 단기 운전자금 상담을 위한 사전 준비. 매출 추이, 비용 구조, 개선 계획 포함.",
                    "expected_impact": {"finance_readiness_delta": 20},
                },
            ],
        },
        {
            "situation": "리뷰 악화 + 배달 매출 감소",
            "actions": [
                {
                    "type": "operation", "title": "포장 품질 및 배달 동선 개선",
                    "description": "배달 지연과 포장 불만 키워드 증가에 대응. 보온 포장재 교체 및 배달 피크타임 조리 동선 재설계.",
                    "expected_impact": {"revenue_change_pct": 12},
                },
                {
                    "type": "marketing", "title": "배달앱 리뷰 관리 및 쿠폰 집중",
                    "description": "평점 회복을 위한 고객 응대 강화. 재주문 고객 대상 할인 쿠폰으로 재구매율 향상.",
                    "expected_impact": {"revenue_change_pct": 10},
                },
                {
                    "type": "operation", "title": "좌석 회전율 개선",
                    "description": "혼잡 시간대 좌석 배치 최적화 및 테이크아웃 유도.",
                    "expected_impact": {"revenue_change_pct": 5},
                },
            ],
        },
        {
            "situation": "안정적 성장 단계",
            "actions": [
                {
                    "type": "finance", "title": "소상공인 성장촉진자금 상담",
                    "description": "현재 안정적인 현금흐름을 기반으로 시설 투자 또는 사업 확장을 위한 성장촉진자금 활용 검토.",
                    "expected_impact": {"finance_readiness_delta": 15},
                },
                {
                    "type": "marketing", "title": "지역화폐 가맹 등록",
                    "description": "전북사랑상품권 가맹을 통한 신규 고객 유입 및 JB금융 우대 금리 혜택 활용.",
                    "expected_impact": {"revenue_change_pct": 7},
                },
                {
                    "type": "operation", "title": "스마트 POS 도입으로 데이터 고도화",
                    "description": "중기부 스마트상점 기술보급 사업 활용. 시간대별 매출 데이터 자동 집계로 운영 최적화.",
                    "expected_impact": {"cost_change_pct": -5},
                },
            ],
        },
    ]

    for i in range(n):
        template = strategy_templates[i % len(strategy_templates)]
        user_msg = f"""다음 사업 상태를 기반으로 실행 가능한 전략을 생성해주세요.

상황: {template['situation']}
사업 건강도: {random.randint(40, 80)}점
유동성 위험도: {random.randint(30, 85)}점
현금 유지 가능: {random.randint(10, 45)}일
금융 준비도: {random.randint(40, 75)}%

운영, 마케팅, 금융 준비 행동을 JSON 배열로 출력하세요."""

        import uuid
        actions = [
            {
                "id": str(uuid.uuid4()),
                "type": a["type"],
                "title": a["title"],
                "description": a["description"],
                "priority": idx + 1,
                "expected_impact": a["expected_impact"],
            }
            for idx, a in enumerate(template["actions"])
        ]

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": json.dumps(actions, ensure_ascii=False, indent=2)},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 4. 상담 리포트 생성 데이터
# ─────────────────────────────────────────────────────────────────
def gen_report_samples(n=60):
    samples = []
    store_names = ["봄날 카페", "전주 한우정", "달콤 제과점", "미소 미용실", "향기 카페"]
    categories = ["카페", "음식점", "제과점", "미용업", "카페"]

    for i in range(n):
        name = store_names[i % len(store_names)]
        cat = categories[i % len(categories)]
        health = random.randint(45, 80)
        runway = random.randint(12, 55)
        readiness = random.randint(45, 78)

        user_msg = f"""{name}({cat})의 은행 상담 준비 리포트를 작성해주세요.

사업 건강도: {health}점
현금 유지 가능: {runway}일
금융 준비도: {readiness}%
주요 원인: 매출 하락 ({random.randint(8,22)}%), 비용 증가

다음 항목을 포함한 상담 준비 요약을 작성하세요:
1. 사업 현황 요약 (2~3문장)
2. 금융 필요성 설명
3. 상담 시 확인할 질문 3개"""

        report_content = f"""## {name} 상담 준비 리포트

### 1. 사업 현황 요약
최근 3개월간 {name}의 매출이 전년 동기 대비 감소 추세를 보이고 있습니다. 현재 비용 구조를 유지할 경우 약 {runway}일 내에 유동성 압박이 발생할 수 있으며, 사업 건강도 {health}점으로 {'즉각적인 금융 지원이 필요한' if runway < 20 else '선제적 대응이 필요한'} 상황입니다.

### 2. 금융 필요성
{'단기 운전자금 지원을 통해 현금흐름 공백 기간을 안정적으로 관리하고, 매출 회복 전략을 실행할 시간을 확보해야 합니다.' if runway < 30 else '현재 안정적인 기반에서 성장을 위한 시설 투자 또는 디지털 전환 자금을 검토할 수 있는 상황입니다.'}
금융 준비도 {readiness}%로 {'추가 자료 준비가 필요합니다.' if readiness < 60 else '상담 진행이 가능한 상태입니다.'}

### 3. 상담 시 확인 질문
1. 현재 신용도와 매출 자료 기준으로 가능한 단기 운전자금 한도와 금리 조건은?
2. 소상공인 경영안정자금 신청 시 처리 기간과 필요 서류는?
3. {'기존 대출이 있는 경우 리파이낸싱 또는 추가 대출 가능 여부와 조건은?' if random.random() > 0.5 else '정책자금과 은행 대출 연계 시 금리 우대 혜택은?'}

⚠️ 본 리포트는 AI가 생성한 참고 자료입니다. 최종 금융 판단은 금융기관 담당자와의 상담을 통해 이루어집니다."""

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": report_content},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 5. 공공 데이터 해석 (날씨·상권 신호 → 사업 설명)
# ─────────────────────────────────────────────────────────────────
def gen_signal_interpretation_samples(n=60):
    samples = []
    weather_scenarios = [
        {"rainy": True, "pop": 85, "tmp": 8, "impact": "비와 낮은 기온으로 카페 방문 고객이 감소할 수 있습니다. 테이크아웃 프로모션 강화를 권장합니다."},
        {"rainy": False, "pop": 10, "tmp": 22, "impact": "맑고 따뜻한 날씨로 야외 활동 증가가 예상됩니다. 테라스 또는 테이크아웃 수요가 높아질 수 있습니다."},
        {"rainy": True, "pop": 70, "tmp": 15, "impact": "강수 확률이 높아 방문 고객 감소가 예상됩니다. 배달 서비스 강화를 권장합니다."},
    ]
    commerce_scenarios = [
        {"count": 18, "trend": "증가", "impact": "반경 내 동종 점포가 18개로 경쟁이 치열합니다. 차별화된 메뉴 또는 서비스 강화가 필요합니다."},
        {"count": 5, "trend": "안정", "impact": "반경 내 경쟁점포 수준이 적정합니다. 상권 내 점유율 유지 전략에 집중하세요."},
        {"count": 25, "trend": "급증", "impact": "최근 경쟁점포가 급증했습니다. 고객 충성도 강화와 재방문 유도 전략이 시급합니다."},
    ]

    for i in range(n):
        w = weather_scenarios[i % len(weather_scenarios)]
        c = commerce_scenarios[i % len(commerce_scenarios)]
        user_msg = f"""다음 외부 신호를 사업 운영 관점에서 해석해주세요.

[날씨 신호]
- 강수 여부: {'비' if w['rainy'] else '맑음'}
- 강수 확률: {w['pop']}%
- 기온: {w['tmp']}°C

[상권 신호]
- 반경 500m 내 동종 점포: {c['count']}개
- 점포 수 추세: {c['trend']}

사업에 미치는 영향과 권장 행동을 설명해주세요."""

        assistant_msg = f"""## 외부 신호 분석 결과

### 날씨 영향
{w['impact']}

### 상권 영향
{c['impact']}

### 종합 권장 사항
{w['impact'].split('.')[0]}. {'경쟁 심화 환경에서 차별화 전략이 더욱 중요합니다.' if c['count'] > 15 else '현재 상권 경쟁도는 적정 수준으로 서비스 품질 유지에 집중하세요.'}

모든 분석은 실제 매출 데이터와 함께 종합적으로 해석해야 합니다."""

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 6. 리뷰 분석 데이터
# ─────────────────────────────────────────────────────────────────
def gen_review_analysis_samples(n=60):
    samples = []
    review_scenarios = [
        {
            "reviews": ["맛있는데 점심에 자리가 부족해요", "대기가 너무 길어요", "가격이 올랐네요", "커피 맛은 좋음"],
            "expected": {"sentiment_score": 0.2, "negative_keywords": ["대기", "자리 부족", "가격"], "positive_keywords": ["맛있", "커피 맛"], "issue": "wait_time"},
        },
        {
            "reviews": ["배달이 너무 늦어요", "포장이 엉망", "음식은 맛있는데", "재주문하고 싶지 않아요"],
            "expected": {"sentiment_score": -0.3, "negative_keywords": ["배달 지연", "포장", "재주문"], "positive_keywords": ["맛있"], "issue": "delivery"},
        },
        {
            "reviews": ["친절하고 빠르다", "맛있어요", "분위기 좋음", "또 올게요", "가성비 최고"],
            "expected": {"sentiment_score": 0.8, "negative_keywords": [], "positive_keywords": ["친절", "맛있", "분위기", "가성비"], "issue": None},
        },
    ]

    for i in range(n):
        s = review_scenarios[i % len(review_scenarios)]
        period = f"2026-{random.randint(3,5):02d}"
        reviews_text = "\n".join([f"- {r}" for r in s["reviews"]])

        user_msg = f"""{period} 기간 고객 리뷰를 분석하여 JSON 형식으로 출력해주세요.

리뷰 목록:
{reviews_text}

감성 점수(-1~1), 긍정·부정 키워드, 이슈 카테고리, 사업 신호를 포함하세요."""

        expected = s["expected"]
        issue_labels = {"wait_time": "대기 시간 불만", "delivery": "배달 품질 문제", None: None}

        assistant_msg = json.dumps({
            "platform": "mixed",
            "period": period,
            "sentiment_score": round(expected["sentiment_score"] + random.uniform(-0.1, 0.1), 2),
            "avg_rating": round(3.5 + expected["sentiment_score"] * 1.5 + random.uniform(-0.3, 0.3), 1),
            "review_count": len(s["reviews"]) + random.randint(0, 5),
            "positive_keywords": expected["positive_keywords"],
            "negative_keywords": expected["negative_keywords"],
            "issue_categories": {expected["issue"]: round(0.4 + random.uniform(0, 0.3), 2)} if expected["issue"] else {},
            "business_signal": issue_labels[expected["issue"]] + " 관련 부정 리뷰 증가" if expected["issue"] else "고객 경험 지표 양호",
            "confidence": "medium" if len(s["reviews"]) < 10 else "high",
        }, ensure_ascii=False, indent=2)

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# 7. Risk Verifier 데이터 (위험 문구 감지)
# ─────────────────────────────────────────────────────────────────
def gen_risk_verifier_samples(n=40):
    samples = []
    risk_cases = [
        {
            "input": "이 고객에게 JB은행 소상공인 대출에 반드시 가입하세요. 100% 승인 보장됩니다.",
            "output": "해당 표현에서 '반드시 가입', '100% 승인 보장' 등의 위험 표현이 감지되었습니다. 특정 금융상품 가입을 강요하거나 승인을 보장하는 표현은 금융소비자보호법에 위반될 수 있습니다. 승인 여부는 금융기관의 심사에 따라 결정됩니다.",
            "flags": ["반드시 가입", "100% 승인 보장"],
        },
        {
            "input": "정책자금을 즉시 신청하면 무조건 3,000만원 받을 수 있습니다.",
            "output": "해당 표현에서 '즉시', '무조건' 등 확정적 표현이 감지되었습니다. 정책자금 지원 금액과 승인 여부는 신청자의 자격 요건 심사에 따라 결정되며, 금액을 확정적으로 안내하는 것은 적절하지 않습니다.",
            "flags": ["즉시 신청", "무조건"],
        },
        {
            "input": "현재 사업 상태를 분석한 결과, 단기 운전자금 상담을 검토해볼 수 있는 상황입니다. 소상공인시장진흥공단 상담을 권장합니다.",
            "output": "위험 표현이 감지되지 않았습니다. 해당 내용은 적절한 안내 수준으로 판단됩니다.",
            "flags": [],
        },
    ]

    for i in range(len(risk_cases) * (n // len(risk_cases) + 1)):
        if i >= n:
            break
        case = risk_cases[i % len(risk_cases)]
        user_msg = f"""다음 텍스트에서 금융소비자 보호 위험 표현을 검증해주세요:\n\n"{case['input']}"""

        samples.append({"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": case["output"]},
        ]})
    return samples


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    print("FinPilot QLoRA 학습 데이터 생성 중...")
    all_samples = []

    tasks = [
        ("사업 상태 진단", gen_diagnosis_samples, 80),
        ("원인 분석", gen_causal_samples, 80),
        ("전략 생성", gen_strategy_samples, 80),
        ("상담 리포트", gen_report_samples, 60),
        ("외부 신호 해석", gen_signal_interpretation_samples, 60),
        ("리뷰 분석", gen_review_analysis_samples, 60),
        ("위험 표현 검증", gen_risk_verifier_samples, 40),
    ]

    for name, fn, n in tasks:
        samples = fn(n)
        all_samples.extend(samples)
        print(f"  ✅ {name}: {len(samples)}개")

    # 셔플
    random.shuffle(all_samples)

    # 학습/검증 분리 (90/10)
    split = int(len(all_samples) * 0.9)
    train_data = all_samples[:split]
    val_data = all_samples[split:]

    # 저장
    train_path = f"{OUTPUT_PATH}/train.jsonl"
    val_path = f"{OUTPUT_PATH}/val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for s in train_data:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for s in val_data:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\n총 {len(all_samples)}개 샘플 생성")
    print(f"  학습: {len(train_data)}개 → {train_path}")
    print(f"  검증: {len(val_data)}개 → {val_path}")


if __name__ == "__main__":
    main()
