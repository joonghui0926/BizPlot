"""
공공 데이터 수집 파이프라인 (완성본)
소상공인 상가정보 API, 기상청 단기예보, KOSIS 지역통계, TourAPI
"""
import logging
from datetime import date, datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.store import Store
from app.models.financial import ExternalSignal

logger = logging.getLogger(__name__)

DATA_GO_URL = "https://apis.data.go.kr"
KOSIS_URL = "https://kosis.kr/openapi"


def collect_external_signals(store: Store, db: Session):
    """사업장의 모든 외부 신호를 수집합니다."""
    if not settings.DATA_GO_KR_KEY:
        logger.warning("DATA_GO_KR_KEY not configured")
        return

    collected = []

    if store.latitude and store.longitude:
        if _collect_commerce_radius(store, db):
            collected.append("상권")

    if store.nx and store.ny:
        if _collect_weather(store, db):
            collected.append("날씨")

    if _collect_tour_events(store, db):
        collected.append("지역행사")

    if settings.KOSIS_API_KEY:
        if _collect_kosis_region(store, db):
            collected.append("지역통계")

    if collected:
        logger.info(f"[{store.name}] 외부 신호 수집 완료: {', '.join(collected)}")


# ────────────────────────────────────────────────────────────────
# 1. 소상공인 상가정보 (반경 내 경쟁점포)
# ────────────────────────────────────────────────────────────────
def _collect_commerce_radius(store: Store, db: Session) -> bool:
    try:
        params = {
            "serviceKey": settings.DATA_GO_KR_KEY,
            "radius": 500,
            "cx": store.longitude,
            "cy": store.latitude,
            "type": "json",
        }
        category_code = _category_to_code(store.category)
        if category_code:
            params["indsLclsCd"] = category_code

        resp = httpx.get(
            f"{DATA_GO_URL}/B553077/api/open/sdsc2/storeListInRadius",
            params=params,
            timeout=15,
        )
        data = resp.json()
        # 응답 구조 파싱 (header/body 구조)
        body = data.get("body", data.get("response", {}).get("body", {}))
        total_count = int(body.get("totalCount", 0))
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            items = []

        # 업종 분포 계산
        cat_counter: dict[str, int] = {}
        for item in items:
            cat = item.get("indsSclsNm") or item.get("indsLclsNm") or ""
            if cat:
                cat_counter[cat] = cat_counter.get(cat, 0) + 1

        top_cats = sorted(cat_counter.items(), key=lambda x: x[1], reverse=True)[:5]

        _upsert_signal(store.id, "commerce_radius", "SBDC_STORE_API", date.today(), {
            "radius_m": 500,
            "same_category_count": total_count,
            "nearby_store_count": total_count,
            "top_categories": [c[0] for c in top_cats],
            "category_distribution": dict(top_cats),
        }, db)
        logger.info(f"상권: 반경 500m 내 동종 {total_count}개 점포")
        return True
    except Exception as e:
        logger.warning(f"상권 수집 실패: {e}")
        return False


# ────────────────────────────────────────────────────────────────
# 2. 기상청 단기예보
# ────────────────────────────────────────────────────────────────
def _collect_weather(store: Store, db: Session) -> bool:
    try:
        now = datetime.now()
        # 기상청 단기예보 base_time: 02, 05, 08, 11, 14, 17, 20, 23시
        base_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
        base_hour = now.hour
        base_time = "0500"
        base_date = now.strftime("%Y%m%d")

        for bt in base_times:
            if base_hour >= int(bt[:2]):
                base_time = bt
                break
        else:
            # 자정 전에는 전날 2300 사용
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
            base_time = "2300"

        resp = httpx.get(
            f"{DATA_GO_URL}/1360000/VilageFcstInfoService_2.0/getVilageFcst",
            params={
                "serviceKey": settings.DATA_GO_KR_KEY,
                "pageNo": 1,
                "numOfRows": 300,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": store.nx,
                "ny": store.ny,
            },
            timeout=15,
        )
        data = resp.json()
        result_code = data.get("response", {}).get("header", {}).get("resultCode", "99")

        if result_code != "00":
            logger.warning(f"기상청 응답 오류: code={result_code}")
            return False

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        # 카테고리별 첫 번째 값 추출
        weather: dict[str, str] = {}
        for item in items:
            cat = item.get("category", "")
            val = item.get("fcstValue", "")
            if cat and cat not in weather:
                weather[cat] = val

        # 강수 여부 계산
        pty = weather.get("PTY", "0")
        rainy = pty not in ("0", "")
        pop = int(weather.get("POP", 0) or 0)
        tmp = float(weather.get("TMP", 15) or 15)

        _upsert_signal(store.id, "weather_daily", "KMA_FORECAST", date.today(), {
            "base_date": base_date,
            "base_time": base_time,
            "nx": store.nx,
            "ny": store.ny,
            "rainy_days_recent": 3 if rainy else 1,  # 실시간 강수 여부 기반
            "is_rainy": rainy,
            "precipitation_prob": pop,
            "temperature": tmp,
            "forecast": {k: v for k, v in weather.items() if k in ("TMP", "POP", "PTY", "PCP", "SKY", "REH", "WSD")},
        }, db)
        logger.info(f"날씨: 기온={tmp}°C, 강수확률={pop}%, 강수={'있음' if rainy else '없음'}")
        return True
    except Exception as e:
        logger.warning(f"날씨 수집 실패: {e}")
        return False


# ────────────────────────────────────────────────────────────────
# 3. 한국관광공사 TourAPI (지역 행사)
# ────────────────────────────────────────────────────────────────
def _collect_tour_events(store: Store, db: Session) -> bool:
    if not store.address:
        return False
    try:
        today = date.today()
        resp = httpx.get(
            f"{DATA_GO_URL}/B551011/KorService2/searchFestival2",
            params={
                "serviceKey": settings.DATA_GO_KR_KEY,
                "numOfRows": 10,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "BizPlot",
                "eventStartDate": today.strftime("%Y%m%d"),
                "eventEndDate": (today + timedelta(days=30)).strftime("%Y%m%d"),
                "areaCode": _address_to_area_code(store.address),
                "_type": "json",
            },
            timeout=15,
        )
        data = resp.json()
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
        )
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            items = []

        events = [
            {
                "title": i.get("title", ""),
                "start": i.get("eventstartdate", ""),
                "end": i.get("eventenddate", ""),
                "addr": i.get("addr1", ""),
            }
            for i in items[:5]
        ]

        if events:
            _upsert_signal(store.id, "tour_event", "TOUR_API", today, {
                "events": events,
                "count": len(events),
                "area_code": _address_to_area_code(store.address),
            }, db)
            logger.info(f"지역행사: {len(events)}개 발견")
        return True
    except Exception as e:
        logger.warning(f"TourAPI 수집 실패: {e}")
        return False


# ────────────────────────────────────────────────────────────────
# 4. KOSIS 지역통계 (인구·사업체 수)
# ────────────────────────────────────────────────────────────────
def _collect_kosis_region(store: Store, db: Session) -> bool:
    if not settings.KOSIS_API_KEY or not store.address:
        return False
    try:
        # 시도별 사업체 수 통계 (KOSIS 통계ID: 101/DT_1B04005N)
        resp = httpx.get(
            f"{KOSIS_URL}/statisticsData.do",
            params={
                "method": "getList",
                "apiKey": settings.KOSIS_API_KEY,
                "format": "json",
                "jsonVD": "Y",
                "userStatsId": "101/DT_1B04005N/2/1/1/AAAA/2023",
                "prdSe": "Y",
                "startPrdDe": "2023",
                "endPrdDe": "2023",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        if isinstance(data, list) and data:
            total_businesses = sum(int(d.get("DT", 0) or 0) for d in data[:5])
            _upsert_signal(store.id, "kosis_region", "KOSIS", date.today(), {
                "region": store.address.split()[0] if store.address else "",
                "total_businesses_sample": total_businesses,
                "year": "2023",
            }, db)
            logger.info(f"KOSIS 지역통계 수집 완료")
            return True
    except Exception as e:
        logger.warning(f"KOSIS 수집 실패: {e}")
    return False


# ────────────────────────────────────────────────────────────────
# Google Places 리뷰 수집 (Review Connector)
# ────────────────────────────────────────────────────────────────
def fetch_google_place_reviews(place_id: str) -> list[dict]:
    """Google Places API로 리뷰 수집"""
    if not settings.GOOGLE_PLACES_API_KEY:
        return []
    try:
        resp = httpx.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "name,rating,reviews,user_ratings_total",
                "key": settings.GOOGLE_PLACES_API_KEY,
                "language": "ko",
                "reviews_sort": "newest",
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("status") != "OK":
            logger.warning(f"Google Places 응답 오류: {data.get('status')}")
            return []

        result = data.get("result", {})
        reviews = result.get("reviews", [])
        return [
            {
                "platform": "google",
                "text": r.get("text", ""),
                "rating": r.get("rating"),
                "date": r.get("relative_time_description", ""),
                "author": r.get("author_name", ""),
            }
            for r in reviews
        ]
    except Exception as e:
        logger.warning(f"Google Places 리뷰 수집 실패: {e}")
        return []


def search_google_places(query: str, lat: float, lng: float, radius: int = 500) -> list[dict]:
    """장소명으로 Google Places 검색 (상호명 자동완성용)"""
    if not settings.GOOGLE_PLACES_API_KEY:
        return []
    try:
        resp = httpx.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "keyword": query,
                "location": f"{lat},{lng}",
                "radius": radius,
                "key": settings.GOOGLE_PLACES_API_KEY,
                "language": "ko",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            return []
        return [
            {
                "place_id": r.get("place_id", ""),
                "name": r.get("name", ""),
                "address": r.get("vicinity", ""),
                "rating": r.get("rating"),
                "lat": r.get("geometry", {}).get("location", {}).get("lat"),
                "lng": r.get("geometry", {}).get("location", {}).get("lng"),
            }
            for r in data.get("results", [])[:5]
        ]
    except Exception as e:
        logger.warning(f"Google Places 검색 실패: {e}")
        return []


# ────────────────────────────────────────────────────────────────
# 유틸리티
# ────────────────────────────────────────────────────────────────
def _upsert_signal(store_id, signal_type: str, source: str, ref_date, payload: dict, db: Session):
    """같은 날짜의 신호는 업데이트, 없으면 삽입"""
    existing = db.query(ExternalSignal).filter(
        ExternalSignal.store_id == store_id,
        ExternalSignal.signal_type == signal_type,
        ExternalSignal.reference_date == ref_date,
    ).first()

    if existing:
        existing.payload = payload
        existing.source = source
    else:
        signal = ExternalSignal(
            store_id=store_id,
            signal_type=signal_type,
            source=source,
            reference_date=ref_date,
            payload=payload,
        )
        db.add(signal)
    db.commit()


def _category_to_code(category: str) -> str:
    return {
        "cafe": "I2", "restaurant": "I2", "bakery": "I2",
        "beauty": "Q", "laundry": "Q", "retail": "G",
        "other": "",
    }.get(category, "")


def _address_to_area_code(address: str) -> str:
    mapping = {
        "전주": "37", "전북": "37", "익산": "37", "군산": "37",
        "광주": "29", "서울": "1", "부산": "6", "대구": "4",
        "인천": "2", "대전": "3", "울산": "7", "세종": "8",
    }
    for k, v in mapping.items():
        if k in address:
            return v
    return "37"
