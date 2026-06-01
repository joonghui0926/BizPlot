import csv
import io
import hashlib
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord
from app.models.review import ReviewSource, ReviewRecord
from app.schemas.store import StoreCreate, StoreOut, SalesUploadResult, CostUploadResult, ReviewSourceCreate, ReviewSourceOut
from app.services.geocoder import geocode_address

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("", response_model=StoreOut, status_code=201)
def create_store(
    data: StoreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lat, lon, nx, ny = None, None, None, None
    if data.address:
        try:
            lat, lon, nx, ny = geocode_address(data.address)
        except Exception:
            pass

    store = Store(
        user_id=current_user.id,
        name=data.name,
        category=data.category,
        address=data.address,
        latitude=lat,
        longitude=lon,
        nx=nx,
        ny=ny,
        open_months=data.open_months,
        monthly_avg_revenue=data.monthly_avg_revenue,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("", response_model=list[StoreOut])
def list_stores(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Store).filter(Store.user_id == current_user.id).all()


@router.get("/{store_id}", response_model=StoreOut)
def get_store(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    return store


@router.post("/{store_id}/sales", response_model=SalesUploadResult)
def upload_sales(
    store_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    inserted, skipped, errors = 0, 0, []
    for i, row in enumerate(reader):
        try:
            record = SalesRecord(
                store_id=store.id,
                date=_parse_date(row.get("date") or row.get("날짜") or row.get("Date")),
                hour=_safe_int(row.get("hour") or row.get("시간") or row.get("Hour")),
                amount=float(row.get("amount") or row.get("매출") or row.get("Amount")),
                transaction_count=_safe_int(row.get("count") or row.get("건수")),
                channel=row.get("channel") or row.get("채널") or None,
            )
            db.add(record)
            inserted += 1
        except Exception as e:
            skipped += 1
            if len(errors) < 5:
                errors.append(f"Row {i+2}: {e}")
    db.commit()
    return SalesUploadResult(inserted=inserted, skipped=skipped, errors=errors)


@router.post("/{store_id}/costs", response_model=CostUploadResult)
def upload_costs(
    store_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    inserted, skipped, errors = 0, 0, []
    for i, row in enumerate(reader):
        try:
            record = CostRecord(
                store_id=store.id,
                date=_parse_date(row.get("date") or row.get("날짜")),
                cost_type=row.get("type") or row.get("유형") or "fixed",
                category=row.get("category") or row.get("항목") or "기타",
                amount=float(row.get("amount") or row.get("금액")),
                description=row.get("description") or row.get("설명") or None,
            )
            db.add(record)
            inserted += 1
        except Exception as e:
            skipped += 1
            if len(errors) < 5:
                errors.append(f"Row {i+2}: {e}")
    db.commit()
    return CostUploadResult(inserted=inserted, skipped=skipped, errors=errors)


@router.post("/{store_id}/reviews/sources", response_model=ReviewSourceOut, status_code=201)
def add_review_source(
    store_id: str,
    data: ReviewSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    source = ReviewSource(
        store_id=store.id,
        platform=data.platform,
        source_url=data.source_url,
        place_id=data.place_id,
        consent_given=data.consent_given,
        collection_method=data.collection_method or _default_method(data.platform),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/{store_id}/reviews/collect")
def collect_reviews(
    store_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    sources = db.query(ReviewSource).filter(
        ReviewSource.store_id == store.id,
        ReviewSource.consent_given == True,
        ReviewSource.is_active == True,
    ).all()
    if not sources:
        raise HTTPException(status_code=400, detail="No consented review sources found")

    from app.workers.review_worker import collect_reviews_task
    background_tasks.add_task(collect_reviews_task, str(store.id))
    return {"message": f"Review collection started for {len(sources)} sources", "store_id": str(store.id)}


@router.post("/{store_id}/reviews/upload")
def upload_review_csv(
    store_id: str,
    platform: str = "manual",
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store_or_404(store_id, current_user.id, db)
    source = db.query(ReviewSource).filter(
        ReviewSource.store_id == store.id,
        ReviewSource.platform == platform,
    ).first()
    if not source:
        source = ReviewSource(store_id=store.id, platform=platform, consent_given=True, collection_method="csv")
        db.add(source)
        db.flush()

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    inserted, skipped = 0, 0
    for row in reader:
        text = row.get("text") or row.get("리뷰") or ""
        raw = f"{platform}:{row.get('date','')}{row.get('rating','')}{text}"
        content_hash = hashlib.md5(raw.encode()).hexdigest()
        if db.query(ReviewRecord).filter(ReviewRecord.content_hash == content_hash).first():
            skipped += 1
            continue
        record = ReviewRecord(
            source_id=source.id,
            platform=platform,
            review_date=_parse_date_safe(row.get("date") or row.get("날짜")),
            rating=_safe_float(row.get("rating") or row.get("평점")),
            text=text,
            content_hash=content_hash,
        )
        db.add(record)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped": skipped}


def _get_store_or_404(store_id: str, user_id, db: Session) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.user_id == user_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


def _parse_date(value: str | None) -> date:
    if not value:
        raise ValueError("date is required")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value}")


def _parse_date_safe(value: str | None) -> date | None:
    try:
        return _parse_date(value)
    except Exception:
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value) if value not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> float | None:
    try:
        return float(value) if value not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _default_method(platform: str) -> str:
    methods = {"google": "api", "naver": "playwright", "baemin": "csv", "coupang": "csv"}
    return methods.get(platform, "csv")
