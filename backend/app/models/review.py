from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class ReviewSource(Base):
    __tablename__ = "review_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    platform = Column(String, nullable=False)   # naver | google | baemin | coupang | manual
    source_url = Column(String, nullable=True)
    place_id = Column(String, nullable=True)    # Google place_id
    consent_given = Column(Boolean, default=False)
    collection_method = Column(String, nullable=True)  # api | playwright | csv
    last_collected_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="review_sources")
    review_records = relationship("ReviewRecord", back_populates="source", cascade="all, delete-orphan")


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("review_sources.id"), nullable=False)
    platform = Column(String, nullable=False)
    review_date = Column(Date, nullable=True)
    rating = Column(Float, nullable=True)
    text = Column(String, nullable=True)
    content_hash = Column(String, unique=True, nullable=False, index=True)  # 중복 제거
    collected_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("ReviewSource", back_populates="review_records")


class ReviewSignal(Base):
    __tablename__ = "review_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    platform = Column(String, nullable=True)    # None = 전체 통합
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    sentiment_score = Column(Float, nullable=True)
    avg_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    positive_keywords = Column(JSONB, default=[])
    negative_keywords = Column(JSONB, default=[])
    issue_categories = Column(JSONB, default={})
    business_signal = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # high | medium | low
    created_at = Column(DateTime, default=datetime.utcnow)
