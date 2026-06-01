from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.store import Store
from app.models.agent import BusinessState, Diagnosis, ActionPlan, Simulation, Report
from app.models.review import ReviewSignal
from app.schemas.agent import (
    DashboardOut, BusinessStateOut, DiagnosisOut, ActionPlanOut,
    SimulationRequest, SimulationOut, ReportOut,
)

router = APIRouter(prefix="/stores", tags=["agent"])


@router.post("/{store_id}/diagnose")
def diagnose(
    store_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)
    from app.workers.agent_worker import run_diagnosis_task
    background_tasks.add_task(run_diagnosis_task, str(store.id))
    return {"message": "Diagnosis started", "store_id": str(store.id)}


@router.get("/{store_id}/dashboard", response_model=DashboardOut)
def get_dashboard(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)

    state = db.query(BusinessState).filter(
        BusinessState.store_id == store.id
    ).order_by(BusinessState.computed_at.desc()).first()

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.store_id == store.id
    ).order_by(Diagnosis.created_at.desc()).first()

    plan = db.query(ActionPlan).filter(
        ActionPlan.store_id == store.id
    ).order_by(ActionPlan.created_at.desc()).first()

    review_signal = db.query(ReviewSignal).filter(
        ReviewSignal.store_id == store.id
    ).order_by(ReviewSignal.period_end.desc()).first()

    review_summary = None
    if review_signal:
        review_summary = {
            "sentiment_score": review_signal.sentiment_score,
            "avg_rating": review_signal.avg_rating,
            "positive_keywords": review_signal.positive_keywords[:5],
            "negative_keywords": review_signal.negative_keywords[:5],
            "business_signal": review_signal.business_signal,
        }

    return DashboardOut(
        store_id=store.id,
        state=state,
        latest_diagnosis=diagnosis,
        latest_action_plan=plan,
        review_signal_summary=review_summary,
    )


@router.post("/{store_id}/strategy", response_model=ActionPlanOut)
def generate_strategy(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)

    state = db.query(BusinessState).filter(
        BusinessState.store_id == store.id
    ).order_by(BusinessState.computed_at.desc()).first()
    if not state:
        raise HTTPException(status_code=400, detail="Run /diagnose first")

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.store_id == store.id
    ).order_by(Diagnosis.created_at.desc()).first()
    if not diagnosis:
        raise HTTPException(status_code=400, detail="Diagnosis not found")

    from app.agents.strategy_planner import generate_action_plan
    plan = generate_action_plan(store, state, diagnosis, db)
    return plan


@router.post("/{store_id}/simulate", response_model=SimulationOut)
def simulate(
    store_id: str,
    req: SimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)

    plan = db.query(ActionPlan).filter(ActionPlan.id == req.action_plan_id).first()
    if not plan or str(plan.store_id) != store_id:
        raise HTTPException(status_code=404, detail="Action plan not found")

    state = db.query(BusinessState).filter(
        BusinessState.store_id == store.id
    ).order_by(BusinessState.computed_at.desc()).first()
    if not state:
        raise HTTPException(status_code=400, detail="Business state not found")

    from app.services.simulation import simulate_actions
    sim = simulate_actions(store, state, plan, req.selected_action_ids, db)
    return sim


@router.post("/{store_id}/reports", response_model=ReportOut, status_code=202)
def create_report(
    store_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.store_id == store.id
    ).order_by(Diagnosis.created_at.desc()).first()
    plan = db.query(ActionPlan).filter(
        ActionPlan.store_id == store.id
    ).order_by(ActionPlan.created_at.desc()).first()

    report = Report(
        store_id=store.id,
        diagnosis_id=diagnosis.id if diagnosis else None,
        action_plan_id=plan.id if plan else None,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    from app.workers.report_worker import generate_report_task
    background_tasks.add_task(generate_report_task, str(report.id))
    return report


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    store = _get_store(str(report.store_id), current_user.id, db)
    return report


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.status != "done":
        raise HTTPException(status_code=404, detail="Report not ready")
    _get_store(str(report.store_id), current_user.id, db)
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(report.file_path, media_type="application/pdf", filename="bizplot_report.pdf")


@router.get("/{store_id}/reviews/signals")
def get_review_signals(
    store_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)
    signals = db.query(ReviewSignal).filter(
        ReviewSignal.store_id == store.id
    ).order_by(ReviewSignal.period_end.desc()).limit(6).all()
    return [
        {
            "platform": s.platform,
            "period_start": s.period_start.isoformat() if s.period_start else None,
            "period_end": s.period_end.isoformat() if s.period_end else None,
            "sentiment_score": s.sentiment_score,
            "avg_rating": s.avg_rating,
            "positive_keywords": s.positive_keywords,
            "negative_keywords": s.negative_keywords,
            "issue_categories": s.issue_categories,
            "business_signal": s.business_signal,
        }
        for s in signals
    ]


def _get_store(store_id: str, user_id, db: Session) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.user_id == user_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store
