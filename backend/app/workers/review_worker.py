"""Review Connector Worker: 리뷰 수집 및 감성 분석"""
import hashlib
import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.store import Store
from app.models.review import ReviewSource, ReviewRecord, ReviewSignal

logger = logging.getLogger(__name__)


def collect_reviews_task(store_id: str):
    db: Session = SessionLocal()
    try:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            return

        sources = db.query(ReviewSource).filter(
            ReviewSource.store_id == store.id,
            ReviewSource.consent_given == True,
            ReviewSource.is_active == True,
        ).all()

        for source in sources:
            try:
                reviews = _collect_from_source(source)
                _save_reviews(reviews, source, db)
                source.last_collected_at = date.today()
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to collect from {source.platform}: {e}")

        # 리뷰 감성 분석
        _analyze_review_signals(store, db)
        logger.info(f"Review collection complete for store {store_id}")
    finally:
        db.close()


def _collect_from_source(source: ReviewSource) -> list[dict]:
    if source.platform == "google" and source.place_id:
        return _collect_google(source.place_id)
    elif source.platform == "naver" and source.source_url:
        return _collect_naver_playwright(source.source_url)
    return []


def _collect_google(place_id: str) -> list[dict]:
    """Google Places API로 리뷰 수집"""
    from app.core.config import settings
    if not settings.GOOGLE_PLACES_API_KEY:
        return []
    import httpx
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    resp = httpx.get(url, params={
        "place_id": place_id,
        "fields": "reviews",
        "key": settings.GOOGLE_PLACES_API_KEY,
        "language": "ko",
    }, timeout=10)
    data = resp.json()
    reviews = []
    for r in data.get("result", {}).get("reviews", []):
        reviews.append({
            "platform": "google",
            "text": r.get("text", ""),
            "rating": r.get("rating"),
            "date": date.today().isoformat(),
        })
    return reviews


def _collect_naver_playwright(url: str) -> list[dict]:
    """Playwright 기반 네이버 플레이스 리뷰 수집 (공개 페이지만)"""
    try:
        from playwright.sync_api import sync_playwright
        reviews = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="ko-KR",
            )
            page = ctx.new_page()
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 리뷰 탭 클릭 시도 (있을 경우)
            for tab_sel in ["a[data-pane='review']", "button:has-text('리뷰')", ".veBoZ"]:
                try:
                    el = page.query_selector(tab_sel)
                    if el:
                        el.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            # 복수 선택자로 리뷰 텍스트 추출
            selectors = [
                ".place_section_content .zPfVT",   # 네이버 플레이스 리뷰 텍스트
                ".place_section .inner_list .text",
                ".ReviewItem .body",
                ".EjjAW",                          # 2024+ 클래스
                "._3Mts2",
                ".yEczP",
                ".pui__vn15t2",
            ]
            seen = set()
            for sel in selectors:
                items = page.query_selector_all(sel)
                for item in items[:30]:
                    try:
                        text = item.inner_text().strip()
                        if len(text) > 5 and text not in seen:
                            seen.add(text)
                            reviews.append({
                                "platform": "naver",
                                "text": text[:500],
                                "rating": None,
                                "date": date.today().isoformat(),
                            })
                    except Exception:
                        pass
                if reviews:
                    break

            # 평점 추출 시도
            rating_items = page.query_selector_all(".orXYY, .Cb_xT, ._3HYFa")
            for i, ri in enumerate(rating_items[:len(reviews)]):
                try:
                    r_text = ri.inner_text().strip()
                    r_val = float(r_text)
                    if 1.0 <= r_val <= 5.0:
                        reviews[i]["rating"] = r_val
                except Exception:
                    pass

            browser.close()
        logger.info(f"Naver: collected {len(reviews)} reviews from {url}")
        return reviews
    except Exception as e:
        logger.warning(f"Playwright collection failed: {e}")
        return []


def _save_reviews(reviews: list[dict], source: ReviewSource, db: Session):
    for r in reviews:
        raw = f"{source.platform}:{r.get('date','')}{r.get('rating','')}{r.get('text','')}"
        content_hash = hashlib.md5(raw.encode()).hexdigest()
        if db.query(ReviewRecord).filter(ReviewRecord.content_hash == content_hash).first():
            continue
        record = ReviewRecord(
            source_id=source.id,
            platform=source.platform,
            review_date=date.today(),
            rating=r.get("rating"),
            text=r.get("text", ""),
            content_hash=content_hash,
        )
        db.add(record)


def _analyze_review_signals(store: Store, db: Session):
    """리뷰 감성 분석 → review_signals 업데이트"""
    period_end = date.today()
    period_start = period_end - timedelta(days=30)

    records = db.query(ReviewRecord).join(ReviewSource).filter(
        ReviewSource.store_id == store.id,
        ReviewRecord.review_date >= period_start,
    ).all()

    if not records:
        return

    from app.agents.review_analysis_agent import analyze_reviews
    signal = analyze_reviews(store.id, records, period_start, period_end, db)
    return signal
