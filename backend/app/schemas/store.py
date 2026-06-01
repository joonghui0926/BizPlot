from pydantic import BaseModel
from typing import Any
import uuid


class StoreCreate(BaseModel):
    name: str
    category: str
    address: str | None = None
    open_months: int = 0
    monthly_avg_revenue: float | None = None


class StoreOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    address: str | None
    latitude: float | None
    longitude: float | None
    open_months: int
    monthly_avg_revenue: float | None

    class Config:
        from_attributes = True


class SalesUploadResult(BaseModel):
    inserted: int
    skipped: int
    errors: list[str] = []


class CostUploadResult(BaseModel):
    inserted: int
    skipped: int
    errors: list[str] = []


class ReviewSourceCreate(BaseModel):
    platform: str               # naver | google | baemin | coupang | manual
    source_url: str | None = None
    place_id: str | None = None
    consent_given: bool = False
    collection_method: str | None = None


class ReviewSourceOut(BaseModel):
    id: uuid.UUID
    platform: str
    source_url: str | None
    consent_given: bool
    last_collected_at: Any | None

    class Config:
        from_attributes = True
