from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class BusinessState(Base):
    __tablename__ = "business_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    health_score = Column(Float, nullable=True)         # Bt: 사업 건강도 0-100
    liquidity_risk = Column(Float, nullable=True)       # Lt: 유동성 위험도 0-100
    revenue_trend = Column(Float, nullable=True)        # Mt: 매출 추세 -1~1
    cost_pressure = Column(Float, nullable=True)        # Ct: 비용 압박도 0-100
    review_signal = Column(Float, nullable=True)        # Rt: 고객 반응 지표 0-100
    finance_readiness = Column(Float, nullable=True)    # Ft: 금융 준비도 0-100
    cash_runway_days = Column(Float, nullable=True)     # 현금 유지 가능 일수
    computed_at = Column(DateTime, default=datetime.utcnow)
    detail = Column(JSONB, default={})

    store = relationship("Store", back_populates="business_states")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    business_state_id = Column(UUID(as_uuid=True), ForeignKey("business_states.id"), nullable=True)
    causes = Column(JSONB, default=[])      # [{factor, contribution, confidence, description}]
    review_causes = Column(JSONB, default=[])
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="diagnoses")


class ActionPlan(Base):
    __tablename__ = "action_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("diagnoses.id"), nullable=True)
    actions = Column(JSONB, default=[])
    # [{type: operation|marketing|finance, title, description, priority, expected_impact}]
    rag_references = Column(JSONB, default=[])
    verified = Column(String, nullable=True)   # passed | failed | skipped
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="action_plans")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    action_plan_id = Column(UUID(as_uuid=True), ForeignKey("action_plans.id"), nullable=True)
    scenarios = Column(JSONB, default=[])
    # [{action_id, cash_runway_days_before, cash_runway_days_after, cost_change, revenue_change}]
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="simulations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    diagnosis_id = Column(UUID(as_uuid=True), ForeignKey("diagnoses.id"), nullable=True)
    action_plan_id = Column(UUID(as_uuid=True), ForeignKey("action_plans.id"), nullable=True)
    report_type = Column(String, default="consultation")  # consultation | summary
    file_path = Column(String, nullable=True)
    content = Column(JSONB, default={})
    status = Column(String, default="pending")  # pending | generating | done | failed
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="reports")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    run_type = Column(String, nullable=False)   # diagnose | strategy | report
    status = Column(String, default="running")  # running | completed | failed
    input_summary = Column(JSONB, default={})
    output_summary = Column(JSONB, default={})
    risk_flags = Column(JSONB, default=[])      # Risk Verifier 결과
    duration_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="agent_runs")


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)     # smba | sbdc | etc.
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    chunk_index = Column(Float, default=0)
    content = Column(Text, nullable=False)
    # embedding stored via pgvector - defined in migration
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
