"""CSV 내보내기 API"""
import csv
import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.store import Store
from app.models.financial import SalesRecord, CostRecord
from app.models.agent import BusinessState, Diagnosis, ActionPlan, Simulation

router = APIRouter(prefix="/stores", tags=["export"])


@router.get("/{store_id}/export")
def export_data(
    store_id: str,
    format: str = Query("csv", enum=["csv"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = _get_store(store_id, current_user.id, db)
    today = date.today()
    cutoff = today - timedelta(days=90)

    sales = db.query(SalesRecord).filter(
        SalesRecord.store_id == store.id,
        SalesRecord.date >= cutoff,
    ).order_by(SalesRecord.date.desc()).all()

    costs = db.query(CostRecord).filter(
        CostRecord.store_id == store.id,
        CostRecord.date >= cutoff,
    ).order_by(CostRecord.date.desc()).all()

    state = db.query(BusinessState).filter(
        BusinessState.store_id == store.id
    ).order_by(BusinessState.computed_at.desc()).first()

    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.store_id == store.id
    ).order_by(Diagnosis.created_at.desc()).first()

    plan = db.query(ActionPlan).filter(
        ActionPlan.store_id == store.id
    ).order_by(ActionPlan.created_at.desc()).first()

    output = io.StringIO()
    writer = csv.writer(output)

    # ── Sheet 1: Summary ──
    writer.writerow(["# BizPlot Agent - 사업 상태 리포트"])
    writer.writerow(["사업장", store.name, "업종", store.category, "주소", store.address or ""])
    writer.writerow(["기준일", today.isoformat()])
    writer.writerow([])

    if state:
        writer.writerow(["# 사업 상태 지표"])
        writer.writerow(["항목", "값"])
        writer.writerow(["사업 건강도", f"{state.health_score:.1f}"])
        writer.writerow(["유동성 위험도", f"{state.liquidity_risk:.1f}"])
        writer.writerow(["비용 압박도", f"{state.cost_pressure:.1f}"])
        writer.writerow(["매출 추세", f"{state.revenue_trend:+.1%}"])
        writer.writerow(["금융 준비도", f"{state.finance_readiness:.1f}%"])
        writer.writerow(["현금 유지 가능 기간", f"{state.cash_runway_days:.0f}일"])
        writer.writerow(["최근 30일 매출", f"₩{state.detail.get('recent_revenue_30d', 0):,.0f}"])
        writer.writerow(["최근 30일 비용", f"₩{state.detail.get('total_cost_30d', 0):,.0f}"])
        writer.writerow([])

    if diagnosis and diagnosis.causes:
        writer.writerow(["# 매출 하락 원인 분석"])
        writer.writerow(["원인 요인", "기여도(%)", "신뢰도", "설명"])
        for cause in diagnosis.causes:
            writer.writerow([
                cause.get("factor", ""),
                cause.get("contribution", 0),
                cause.get("confidence", ""),
                cause.get("description", ""),
            ])
        writer.writerow([])

    if plan and plan.actions:
        writer.writerow(["# 권장 실행 전략"])
        writer.writerow(["유형", "전략명", "내용", "예상 효과"])
        for action in plan.actions:
            impact = action.get("expected_impact", {})
            impact_str = ", ".join(f"{k}={v}" for k, v in impact.items())
            writer.writerow([
                action.get("type", ""),
                action.get("title", ""),
                action.get("description", ""),
                impact_str,
            ])
        writer.writerow([])

    # ── Sheet 2: Sales Data ──
    writer.writerow(["# 매출 데이터 (최근 90일)"])
    writer.writerow(["날짜", "시간대", "금액", "거래건수", "채널"])
    for s in sales:
        writer.writerow([s.date.isoformat(), s.hour or "", s.amount, s.transaction_count or "", s.channel or ""])
    writer.writerow([])

    # ── Sheet 3: Cost Data ──
    writer.writerow(["# 비용 데이터 (최근 90일)"])
    writer.writerow(["날짜", "유형", "항목", "금액", "설명"])
    for c in costs:
        writer.writerow([c.date.isoformat(), c.cost_type, c.category, c.amount, c.description or ""])

    output.seek(0)
    # 한글 파일명은 latin-1로 인코딩 못 하므로 RFC 5987(filename*) + ASCII fallback 사용
    from urllib.parse import quote
    filename = f"bizplot_{store.name}_{today.isoformat()}.csv"
    ascii_fallback = f"bizplot_{today.isoformat()}.csv"
    disposition = (
        f"attachment; filename=\"{ascii_fallback}\"; "
        f"filename*=UTF-8''{quote(filename)}"
    )
    return StreamingResponse(
        io.BytesIO(("﻿" + output.getvalue()).encode("utf-8")),  # BOM for Excel
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )


def _get_store(store_id: str, user_id, db: Session) -> Store:
    store = db.query(Store).filter(Store.id == store_id, Store.user_id == user_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store
