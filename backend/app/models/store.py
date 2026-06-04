from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class BusinessCategory(str, enum.Enum):
    cafe = "cafe"
    restaurant = "restaurant"
    retail = "retail"
    bakery = "bakery"
    beauty = "beauty"
    laundry = "laundry"
    other = "other"


class Store(Base):
    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)           # 업종
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    nx = Column(Integer, nullable=True)                 # 기상청 격자 X
    ny = Column(Integer, nullable=True)                 # 기상청 격자 Y
    open_months = Column(Integer, default=0)            # 영업기간(개월)
    monthly_avg_revenue = Column(Float, nullable=True)  # 월평균 매출
    extra = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="stores")
    sales_records = relationship("SalesRecord", back_populates="store", cascade="all, delete-orphan")
    cost_records = relationship("CostRecord", back_populates="store", cascade="all, delete-orphan")
    external_signals = relationship("ExternalSignal", back_populates="store", cascade="all, delete-orphan")
    review_sources = relationship("ReviewSource", back_populates="store", cascade="all, delete-orphan")
    business_states = relationship("BusinessState", back_populates="store", cascade="all, delete-orphan")
    diagnoses = relationship("Diagnosis", back_populates="store", cascade="all, delete-orphan")
    action_plans = relationship("ActionPlan", back_populates="store", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="store", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="store", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="store", cascade="all, delete-orphan")
