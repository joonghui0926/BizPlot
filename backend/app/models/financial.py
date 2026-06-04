from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Date, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class CostType(str, enum.Enum):
    fixed = "fixed"
    variable = "variable"


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=True)           # 시간대 (0-23), None이면 일별
    amount = Column(Float, nullable=False)
    transaction_count = Column(Integer, nullable=True)
    channel = Column(String, nullable=True)         # pos, delivery, online
    extra = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="sales_records")


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    date = Column(Date, nullable=False)
    cost_type = Column(String, nullable=False)       # fixed | variable
    category = Column(String, nullable=False)        # rent, labor, materials, marketing, etc.
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    extra = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="cost_records")


class ExternalSignal(Base):
    __tablename__ = "external_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    signal_type = Column(String, nullable=False, index=True)
    # e.g. commerce_radius, weather_daily, kosis_region, local_license, tour_event
    source = Column(String, nullable=False)
    reference_date = Column(Date, nullable=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="external_signals")
