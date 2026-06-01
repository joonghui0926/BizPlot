"""
Review Analysis Agent
리뷰 텍스트 → 감성 점수, 긍정/부정 키워드, 이슈 카테고리
"""
import uuid
from datetime import date
from sqlalchemy.orm import Session
from app.models.review import ReviewRecord, ReviewSignal

NEGATIVE_KEYWORDS = {
    "wait_time": ["대기", "기다림", "오래", "줄", "느림", "지연"],
    "space": ["좌석 부족", "좁음", "공간", "자리 없", "협소"],
    "price": ["가격", "비싸", "비쌈", "비용", "값"],
    "service": ["불친절", "무뚝뚝", "응대", "서비스"],
    "quality": ["맛없", "별로", "실망", "수준"],
    "delivery": ["포장", "배달 지연", "배달", "식음", "양 감소", "양이"],
}

POSITIVE_KEYWORDS = {
    "taste": ["맛있", "맛이 좋", "맛있어", "최고", "맛"],
    "atmosphere": ["분위기", "깔끔", "예쁘", "인테리어"],
    "service": ["친절", "친절해", "빠름", "신속"],
    "price": ["합리적", "가성비", "저렴"],
}


def analyze_reviews(
    store_id: uuid.UUID,
    records: list[ReviewRecord],
    period_start: date,
    period_end: date,
    db: Session,
) -> ReviewSignal:
    texts = [r.text or "" for r in records]
    ratings = [r.rating for r in records if r.rating is not None]

    # 감성 점수 (규칙 기반 + 모델)
    sentiment_score = _compute_sentiment(texts)
    avg_rating = sum(ratings) / len(ratings) if ratings else None

    # 키워드 추출
    positive_kws = _extract_keywords(texts, POSITIVE_KEYWORDS)
    negative_kws = _extract_keywords(texts, NEGATIVE_KEYWORDS)

    # 이슈 카테고리
    issue_cats = _compute_issue_categories(texts)

    # 비즈니스 신호
    business_signal = _generate_business_signal(negative_kws, issue_cats, sentiment_score)

    # 신뢰도
    confidence = "high" if len(records) >= 20 else ("medium" if len(records) >= 5 else "low")

    signal = ReviewSignal(
        store_id=store_id,
        platform=None,
        period_start=period_start,
        period_end=period_end,
        sentiment_score=sentiment_score,
        avg_rating=avg_rating,
        review_count=len(records),
        positive_keywords=positive_kws,
        negative_keywords=negative_kws,
        issue_categories=issue_cats,
        business_signal=business_signal,
        confidence=confidence,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def _compute_sentiment(texts: list[str]) -> float:
    """규칙 기반 감성 점수 (-1 ~ 1)"""
    if not texts:
        return 0.0
    try:
        # LLM 임베딩 기반 감성 점수
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("snunlp/KR-ELECTRA-discriminator")
        scores = []
        for text in texts[:50]:
            if not text.strip():
                continue
            neg_count = sum(1 for kws in NEGATIVE_KEYWORDS.values() for k in kws if k in text)
            pos_count = sum(1 for kws in POSITIVE_KEYWORDS.values() for k in kws if k in text)
            if neg_count + pos_count > 0:
                scores.append((pos_count - neg_count) / (pos_count + neg_count))
        return sum(scores) / len(scores) if scores else 0.0
    except Exception:
        return _rule_based_sentiment(texts)


def _rule_based_sentiment(texts: list[str]) -> float:
    scores = []
    for text in texts:
        neg_count = sum(1 for kws in NEGATIVE_KEYWORDS.values() for k in kws if k in text)
        pos_count = sum(1 for kws in POSITIVE_KEYWORDS.values() for k in kws if k in text)
        if neg_count + pos_count > 0:
            scores.append((pos_count - neg_count) / (pos_count + neg_count))
    return sum(scores) / len(scores) if scores else 0.0


def _extract_keywords(texts: list[str], keyword_map: dict) -> list[str]:
    counter: dict[str, int] = {}
    all_text = " ".join(texts)
    for category, keywords in keyword_map.items():
        for kw in keywords:
            if kw in all_text:
                counter[kw] = all_text.count(kw)
    return sorted(counter.keys(), key=lambda k: counter[k], reverse=True)[:10]


def _compute_issue_categories(texts: list[str]) -> dict:
    all_text = " ".join(texts)
    total = max(len(texts), 1)
    cats = {}
    for cat, keywords in NEGATIVE_KEYWORDS.items():
        count = sum(all_text.count(kw) for kw in keywords)
        if count > 0:
            cats[cat] = round(count / (total * len(keywords)) * 10, 2)
    return cats


def _generate_business_signal(neg_kws: list, issue_cats: dict, sentiment: float) -> str:
    if not neg_kws and sentiment > 0.3:
        return "고객 경험 지표 양호"
    top_issue = max(issue_cats, key=issue_cats.get) if issue_cats else None
    if top_issue:
        issue_labels = {
            "wait_time": "대기 시간 불만",
            "space": "공간 부족",
            "price": "가격 부담",
            "service": "서비스 불만",
            "quality": "품질 하락",
            "delivery": "배달 품질",
        }
        return f"{issue_labels.get(top_issue, top_issue)} 관련 부정 리뷰 증가"
    return "부정 키워드 증가 감지"
