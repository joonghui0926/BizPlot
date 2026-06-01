"""
메가커피 전주시 완산구점 — 현실적 매출·비용·리뷰 데이터 시뮬레이션 및 DB 적재
· 90일치 시간대별 매출 (오전/점심/오후/저녁 피크 패턴)
· 최근 30일 경쟁점 증가로 오후 매출 하락 반영
· 비용 데이터 (임차료, 인건비, 원재료, 기타 변동비)
· 3개월치 리뷰 데이터 (긍정/부정 신호 포함, ReviewSignal 트렌드)
"""
import sys, os, uuid, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import date, timedelta
from app.db.base import SessionLocal
from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord, ExternalSignal
from app.models.review import ReviewSource, ReviewRecord, ReviewSignal

random.seed(42)

STORE_NAME = "메가커피"
MEGACOFFEE_ID = None  # will be resolved

# ── 메가커피 현실 파라미터 (전주 완산구 기준) ─────────────────────────────────
# 월 매출 약 1,800~2,200만원 (프랜차이즈 카페 실적 기준)
# 시간대별 가중치: 오전(출근) 25%, 점심 20%, 오후(낮) 30%, 저녁 15%, 야간 10%
HOURLY_WEIGHTS = {
    7: 0.08, 8: 0.12, 9: 0.10,           # 출근 피크
    10: 0.06, 11: 0.07,                   # 오전 중반
    12: 0.09, 13: 0.08,                   # 점심
    14: 0.08, 15: 0.09, 16: 0.07,         # 오후 (최근 하락 구간)
    17: 0.06, 18: 0.05,                   # 퇴근
    19: 0.04, 20: 0.03, 21: 0.02,         # 저녁·야간
}

# 요일별 배율: 평일 기준 1.0, 주말 1.15 (프랜차이즈 카페)
WEEKDAY_MULT = {0: 1.0, 1: 0.98, 2: 1.0, 3: 1.02, 4: 1.05, 5: 1.18, 6: 1.12}

# 시간 경과에 따른 추세: 90일 전 → 현재
# 최근 30일: 오후(14-17시) 20% 하락 (경쟁점 증가 효과)
def get_hour_mult(hour, days_ago):
    if days_ago <= 30 and 14 <= hour <= 16:
        return 0.78  # 최근 오후 매출 22% 하락
    if days_ago <= 30:
        return 0.94  # 전반적 소폭 감소
    if days_ago <= 60:
        return 0.98
    return 1.0

BASE_DAILY_REVENUE = 680_000  # 일 평균 기준 (월 약 2,040만원)
AVG_UNIT_PRICE = 4_500         # 메가커피 평균 객단가 (아메리카노 2,000~라떼 3,500 → 세트 포함)

def generate_sales(store_id, today, days=90):
    records = []
    for d in range(days, 0, -1):
        target_date = today - timedelta(days=d)
        days_ago = d
        wd = target_date.weekday()
        day_mult = WEEKDAY_MULT.get(wd, 1.0)
        noise_day = random.gauss(1.0, 0.06)

        for hour, weight in HOURLY_WEIGHTS.items():
            h_mult = get_hour_mult(hour, days_ago)
            base = BASE_DAILY_REVENUE * weight * day_mult * h_mult * noise_day
            noise_h = random.gauss(1.0, 0.10)
            amount = round(base * noise_h / 100) * 100  # 100원 단위
            if amount < 0:
                amount = 0
            txns = max(1, round(amount / AVG_UNIT_PRICE))

            records.append(SalesRecord(
                id=str(uuid.uuid4()),
                store_id=store_id,
                date=target_date,
                hour=hour,
                amount=amount,
                transaction_count=txns,
                channel="offline",
            ))
    return records


# ── 비용 데이터 (월 단위 고정비 + 주간 변동비) ────────────────────────────────
def generate_costs(store_id, today, days=90):
    records = []
    start = today - timedelta(days=days)

    # 월 고정비
    monthly_fixed = [
        ("fixed", "임차료", 2_800_000, "전주 완산구 상가 월임차료"),
        ("fixed", "인건비", 4_200_000, "정규직 2명 + 파트타임 평균"),
        ("fixed", "관리비", 280_000, "전기·수도·통신 포함"),
        ("fixed", "프랜차이즈 로열티", 550_000, "메가커피 가맹 로열티 (매출 2.5%)"),
    ]

    for m in range(3):
        # 3개월치 고정비
        cost_date = today - timedelta(days=30 * (m + 1))
        if cost_date < start:
            continue
        for cost_type, category, base_amount, desc in monthly_fixed:
            noise = random.gauss(1.0, 0.03)
            records.append(CostRecord(
                id=str(uuid.uuid4()),
                store_id=store_id,
                date=cost_date,
                cost_type=cost_type,
                category=category,
                amount=round(base_amount * noise / 1000) * 1000,
                description=desc,
            ))

    # 주간 변동비 (원재료 발주, 소모품)
    week_variable = [
        ("variable", "원재료_커피원두", 320_000, "주간 원두 발주"),
        ("variable", "원재료_우유기타", 180_000, "우유·시럽·파우더"),
        ("variable", "소모품", 55_000, "컵·빨대·냅킨 등"),
    ]

    d = start
    while d <= today:
        if d.weekday() == 0:  # 매주 월요일 발주
            # 최근 30일: 원재료 단가 상승 8% 반영
            price_up = 1.08 if (today - d).days <= 30 else 1.0
            for cost_type, category, base_amount, desc in week_variable:
                noise = random.gauss(1.0, 0.05)
                records.append(CostRecord(
                    id=str(uuid.uuid4()),
                    store_id=store_id,
                    date=d,
                    cost_type=cost_type,
                    category=category,
                    amount=round(base_amount * noise * price_up / 1000) * 1000,
                    description=desc,
                ))
        d += timedelta(days=1)

    return records


# ── 리뷰 데이터 (3개월치 트렌드 반영) ──────────────────────────────────────────
# 실제 메가커피 리뷰 패턴: 최근 30일에 "대기", "좌석 부족" 부정 키워드 증가
REVIEW_SAMPLES = [
    # 3개월 전 리뷰 (긍정 우세)
    {"days_ago": 85, "platform": "google", "rating": 4.5, "text": "메가커피 답게 가성비 최고! 아메리카노 진하고 맛있어요. 직원분들도 친절하고 깔끔해요"},
    {"days_ago": 82, "platform": "naver", "rating": 5.0, "text": "전주에서 제일 좋아하는 카페예요. 맛있고 분위기도 좋아요. 사장님이 항상 친절하게 인사해주세요"},
    {"days_ago": 80, "platform": "google", "rating": 4.0, "text": "커피 맛 좋고 합리적인 가격. 자리도 넉넉하고 음악도 조용해서 공부하기 좋아요"},
    {"days_ago": 77, "platform": "naver", "rating": 5.0, "text": "맛있어요! 직원들이 빠르게 만들어줘서 좋아요. 자리도 많아서 편해요"},
    {"days_ago": 75, "platform": "google", "rating": 4.0, "text": "가성비 굳. 아이스 라떼가 특히 맛있어요. 분위기도 좋고 자주 와요"},
    {"days_ago": 72, "platform": "naver", "rating": 4.5, "text": "커피 맛있고 서비스 친절해요. 오전에 오면 자리 여유있고 좋아요"},
    {"days_ago": 70, "platform": "baemin", "rating": 5.0, "text": "포장 꼼꼼하게 잘 해줬어요. 맛있고 빨리 배달와서 좋았어요"},
    {"days_ago": 68, "platform": "google", "rating": 4.0, "text": "동네 카페 중에 제일 맛있는 것 같아요. 가격도 합리적이고"},

    # 2개월 전 리뷰 (중립~약간 부정 시작)
    {"days_ago": 55, "platform": "naver", "rating": 4.0, "text": "커피는 맛있는데 요즘 오후에 사람이 너무 많아졌어요. 그래도 맛은 좋아요"},
    {"days_ago": 52, "platform": "google", "rating": 3.5, "text": "맛은 괜찮은데 대기 시간이 좀 길어졌어요. 오후엔 특히 줄이 길어요"},
    {"days_ago": 50, "platform": "naver", "rating": 4.5, "text": "아메리카노 진하고 좋아요. 가격 대비 최고. 자리 부족한 게 좀 아쉽네요"},
    {"days_ago": 47, "platform": "google", "rating": 4.0, "text": "맛있어요! 근데 요즘 좌석이 좀 부족한 것 같아요. 서서 마셔야 할 때도"},
    {"days_ago": 45, "platform": "baemin", "rating": 3.0, "text": "배달은 좀 늦게 왔어요. 맛은 괜찮은데 가격이 좀 올랐나요?"},
    {"days_ago": 42, "platform": "naver", "rating": 4.0, "text": "분위기 좋고 커피 맛 좋아요. 오후 시간엔 자리 없어서 가끔 불편"},
    {"days_ago": 40, "platform": "google", "rating": 3.5, "text": "맛은 좋은데 평일 오후에 너무 혼잡해요. 자리 찾기가 힘들어요"},

    # 최근 30일 리뷰 (부정 키워드 증가: 대기, 좌석 부족, 가격)
    {"days_ago": 28, "platform": "naver", "rating": 3.0, "text": "커피는 맛있는데 오후 시간대에 대기 줄이 너무 길어요. 10분 넘게 기다렸어요"},
    {"days_ago": 26, "platform": "google", "rating": 3.5, "text": "맛있긴 한데 요즘 좌석 부족해서 불편해요. 자리 늘려줬으면 좋겠어요"},
    {"days_ago": 24, "platform": "naver", "rating": 2.5, "text": "가격이 좀 오른 것 같아요. 전에는 2,000원이었는데 이제 2,500원 되었어요"},
    {"days_ago": 22, "platform": "baemin", "rating": 3.0, "text": "배달 시간 좀 더 걸렸어요. 양도 예전보다 조금 줄어든 것 같아요"},
    {"days_ago": 20, "platform": "google", "rating": 3.0, "text": "오후에 가면 대기 길고 좌석 없어요. 아침엔 괜찮은데 오후엔 불편"},
    {"days_ago": 18, "platform": "naver", "rating": 4.0, "text": "맛은 여전히 좋아요. 근데 요즘 좀 혼잡한 것 같아요. 좌석이 부족한 느낌"},
    {"days_ago": 16, "platform": "google", "rating": 3.0, "text": "대기 시간이 너무 길어요. 오후 3시에 갔는데 15분 기다렸어요. 가격도 부담스럽"},
    {"days_ago": 14, "platform": "naver", "rating": 3.5, "text": "커피 맛은 좋은데 항상 자리가 없어요. 좌석 부족 문제 해결해줬으면 해요"},
    {"days_ago": 12, "platform": "google", "rating": 2.5, "text": "오후에 대기 엄청 길고 자리도 없고 가격도 올랐어요. 예전이 더 좋았는데"},
    {"days_ago": 10, "platform": "naver", "rating": 4.0, "text": "커피 맛 하나는 정말 좋아요. 다만 오후엔 대기가 있어서 아침에 주로 와요"},
    {"days_ago": 8,  "platform": "google", "rating": 3.5, "text": "맛은 좋은데 오후엔 서비스가 좀 느려요. 바쁜 시간대 인력이 부족한 것 같아요"},
    {"days_ago": 6,  "platform": "naver", "rating": 3.0, "text": "요즘 너무 혼잡해요. 대기도 길고 좌석도 없어요. 가격도 조금 부담"},
    {"days_ago": 4,  "platform": "google", "rating": 3.5, "text": "전에는 자리 넉넉했는데 요즘 오후에 좌석 부족해요. 커피 맛은 여전히 좋아요"},
    {"days_ago": 2,  "platform": "naver", "rating": 3.0, "text": "최근에 줄이 너무 길어요. 오후 2-5시에는 대기 10분 이상 기본이에요. 개선 필요"},
]


def generate_reviews(store_id, today):
    """ReviewSource + ReviewRecord 생성, 기간별 ReviewSignal 생성"""
    records_by_platform = {}
    all_records = []

    # ReviewSource 생성 (플랫폼별)
    sources = {}
    for platform in ["google", "naver", "baemin"]:
        src = ReviewSource(
            id=uuid.uuid4(),
            store_id=store_id,
            platform=platform,
            source_url=f"https://{platform}.com/megacoffee-jeonju",
            consent_given=True,
            collection_method="csv" if platform == "baemin" else ("api" if platform == "google" else "playwright"),
            is_active=True,
        )
        sources[platform] = src

    # ReviewRecord 생성
    for sample in REVIEW_SAMPLES:
        days_ago = sample["days_ago"]
        platform = sample["platform"]
        review_date = today - timedelta(days=days_ago)
        text = sample["text"]
        rating = sample.get("rating")

        raw = f"{platform}:{review_date.isoformat()}{rating}{text}"
        content_hash = hashlib.md5(raw.encode()).hexdigest()

        record = ReviewRecord(
            id=uuid.uuid4(),
            source_id=sources[platform].id,
            platform=platform,
            review_date=review_date,
            rating=rating,
            text=text,
            content_hash=content_hash,
        )
        all_records.append(record)

        period_key = review_date.strftime("%Y-%m") if days_ago > 30 else "recent"
        if period_key not in records_by_platform:
            records_by_platform[period_key] = []
        records_by_platform[period_key].append(record)

    return list(sources.values()), all_records, records_by_platform


def generate_review_signals(store_id, today, records_by_period):
    """기간별 ReviewSignal 생성 (3개월 트렌드용)"""
    signals = []

    # 최근 30일 신호
    recent_records = records_by_period.get("recent", [])
    if recent_records:
        neg_keywords = ["대기", "좌석 부족", "가격", "혼잡", "느림"]
        pos_keywords = ["맛있", "친절", "합리적"]
        signals.append(ReviewSignal(
            id=uuid.uuid4(),
            store_id=store_id,
            platform=None,
            period_start=today - timedelta(days=30),
            period_end=today,
            sentiment_score=-0.28,
            avg_rating=3.2,
            review_count=len(recent_records),
            positive_keywords=pos_keywords,
            negative_keywords=neg_keywords,
            issue_categories={"wait_time": 0.42, "space": 0.35, "price": 0.23},
            business_signal="평일 오후 대기·좌석 부족 관련 부정 리뷰 증가. 오후 2~5시 집중 개선 필요",
            confidence="high",
        ))

    # 1~2개월 전 신호 (중립)
    signals.append(ReviewSignal(
        id=uuid.uuid4(),
        store_id=store_id,
        platform=None,
        period_start=today - timedelta(days=60),
        period_end=today - timedelta(days=31),
        sentiment_score=0.12,
        avg_rating=3.8,
        review_count=7,
        positive_keywords=["맛있", "분위기", "합리적"],
        negative_keywords=["자리 없", "혼잡"],
        issue_categories={"space": 0.18, "wait_time": 0.12},
        business_signal="좌석 부족 언급 증가 시작",
        confidence="medium",
    ))

    # 2~3개월 전 신호 (긍정 우세)
    signals.append(ReviewSignal(
        id=uuid.uuid4(),
        store_id=store_id,
        platform=None,
        period_start=today - timedelta(days=90),
        period_end=today - timedelta(days=61),
        sentiment_score=0.55,
        avg_rating=4.4,
        review_count=8,
        positive_keywords=["맛있", "친절", "가성비", "분위기", "깔끔"],
        negative_keywords=[],
        issue_categories={},
        business_signal="고객 경험 지표 양호",
        confidence="medium",
    ))

    return signals


def main():
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.name == STORE_NAME).first()
        if not store:
            print(f"'{STORE_NAME}' 매장을 찾을 수 없습니다.")
            return

        print(f"Store: {store.name} ({store.id})")

        # 기존 데이터 삭제
        from app.models.review import ReviewSource as RS
        db.query(RS).filter(RS.store_id == store.id).delete(synchronize_session=False)
        db.query(ReviewSignal).filter(ReviewSignal.store_id == store.id).delete(synchronize_session=False)
        deleted_sales = db.query(SalesRecord).filter(SalesRecord.store_id == store.id).delete()
        deleted_costs = db.query(CostRecord).filter(CostRecord.store_id == store.id).delete()
        db.commit()
        print(f"기존 데이터 삭제: 매출 {deleted_sales}건, 비용 {deleted_costs}건")

        today = date.today()

        # 매출 데이터 생성
        sales = generate_sales(store.id, today, days=90)
        db.bulk_save_objects(sales)
        total_sales = sum(s.amount for s in sales)
        print(f"매출 {len(sales)}건 생성 (90일 총합: ₩{total_sales:,.0f})")

        # 비용 데이터 생성
        costs = generate_costs(store.id, today, days=90)
        db.bulk_save_objects(costs)
        total_costs = sum(c.amount for c in costs)
        print(f"비용 {len(costs)}건 생성 (90일 총합: ₩{total_costs:,.0f})")

        # 상권 외부 신호 — 경쟁 점포 데이터
        existing_signal = db.query(ExternalSignal).filter(
            ExternalSignal.store_id == store.id,
            ExternalSignal.signal_type == "commerce_radius",
        ).first()
        if existing_signal:
            existing_signal.payload = {
                "same_category_count": 221,
                "new_last_3months": 8,
                "radius_m": 500,
            }
        else:
            db.add(ExternalSignal(
                id=str(uuid.uuid4()),
                store_id=store.id,
                signal_type="commerce_radius",
                payload={
                    "same_category_count": 221,
                    "new_last_3months": 8,
                    "radius_m": 500,
                },
            ))
        print("상권 신호(경쟁 점포 221개, 최근 3개월 신규 8개) 등록")

        # 날씨 외부 신호
        existing_weather = db.query(ExternalSignal).filter(
            ExternalSignal.store_id == store.id,
            ExternalSignal.signal_type == "weather_daily",
        ).first()
        if existing_weather:
            existing_weather.payload = {"rainy_days_recent": 9, "avg_temp_drop_vs_prior": 2}
        else:
            db.add(ExternalSignal(
                id=str(uuid.uuid4()),
                store_id=store.id,
                signal_type="weather_daily",
                payload={"rainy_days_recent": 9, "avg_temp_drop_vs_prior": 2},
            ))
        print("날씨 신호(최근 강수일 9일) 등록")

        db.commit()

        # 리뷰 데이터 생성
        sources, review_records, records_by_period = generate_reviews(store.id, today)
        for src in sources:
            db.add(src)
        db.flush()
        for rec in review_records:
            db.add(rec)
        db.flush()
        signals = generate_review_signals(store.id, today, records_by_period)
        for sig in signals:
            db.add(sig)
        db.commit()
        print(f"리뷰 {len(review_records)}건, ReviewSignal {len(signals)}개 등록")

        # 검증 출력
        recent_sales = [s for s in sales if (today - s.date).days <= 30]
        prior_sales  = [s for s in sales if 30 < (today - s.date).days <= 60]
        print(f"\n── 검증 ──")
        print(f"최근 30일 매출: ₩{sum(s.amount for s in recent_sales):,.0f}")
        print(f"이전 30일 매출: ₩{sum(s.amount for s in prior_sales):,.0f}")
        trend = (sum(s.amount for s in recent_sales) - sum(s.amount for s in prior_sales)) / sum(s.amount for s in prior_sales)
        print(f"매출 추세: {trend:+.1%}")
        print("\n✅ 데이터 적재 완료. 대시보드에서 '재진단' 버튼을 눌러주세요.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
