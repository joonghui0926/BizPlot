from pydantic import BaseModel
from typing import Any
import uuid


class BusinessStateOut(BaseModel):
    id: uuid.UUID
    health_score: float | None
    liquidity_risk: float | None
    revenue_trend: float | None
    cost_pressure: float | None
    review_signal: float | None
    finance_readiness: float | None
    cash_runway_days: float | None
    computed_at: Any
    detail: dict

    class Config:
        from_attributes = True


class DiagnosisOut(BaseModel):
    id: uuid.UUID
    causes: list
    review_causes: list
    summary: str | None
    created_at: Any

    class Config:
        from_attributes = True


class ActionPlanOut(BaseModel):
    id: uuid.UUID
    actions: list
    rag_references: list
    verified: str | None
    created_at: Any

    class Config:
        from_attributes = True


class SimulationRequest(BaseModel):
    action_plan_id: uuid.UUID
    selected_action_ids: list[str] = []


class SimulationOut(BaseModel):
    id: uuid.UUID
    scenarios: list
    created_at: Any

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    store_id: uuid.UUID
    state: BusinessStateOut | None
    latest_diagnosis: DiagnosisOut | None
    latest_action_plan: ActionPlanOut | None
    review_signal_summary: dict | None


class ReportOut(BaseModel):
    id: uuid.UUID
    report_type: str
    status: str
    file_path: str | None
    created_at: Any

    class Config:
        from_attributes = True
