"""Background worker: 진단 파이프라인 실행"""
import logging
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.store import Store

logger = logging.getLogger(__name__)


def run_diagnosis_task(store_id: str):
    db: Session = SessionLocal()
    try:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            return

        # 1. 공공 데이터 수집
        try:
            from app.services.public_data import collect_external_signals
            collect_external_signals(store, db)
        except Exception as e:
            logger.warning(f"Public data collection failed: {e}")

        # 2. 리뷰 수집 및 감성 분석 (동의된 출처가 있을 때)
        try:
            from app.workers.review_worker import collect_reviews_task
            # 같은 db 세션 내에서 직접 분석 실행
            _run_review_analysis(store, db)
        except Exception as e:
            logger.warning(f"Review analysis failed: {e}")

        # 3. Finance State Agent
        from app.agents.finance_state_agent import compute_business_state
        state = compute_business_state(store, db)

        # 4. Causal Analysis Agent
        from app.agents.causal_analysis_agent import analyze_causes
        diagnosis = analyze_causes(store, state, db)

        # 5. Strategy Planner
        from app.agents.strategy_planner import generate_action_plan
        generate_action_plan(store, state, diagnosis, db)

        logger.info(f"Diagnosis complete for store {store_id}, health={state.health_score}")
    except Exception as e:
        logger.error(f"Diagnosis failed for store {store_id}: {e}")
    finally:
        db.close()


def _run_review_analysis(store: Store, db: Session):
    """리뷰 레코드가 있으면 감성 분석 신호를 갱신한다."""
    from datetime import date, timedelta
    from app.models.review import ReviewSource, ReviewRecord

    period_end = date.today()
    period_start = period_end - timedelta(days=30)

    records = (
        db.query(ReviewRecord)
        .join(ReviewSource)
        .filter(
            ReviewSource.store_id == store.id,
            ReviewRecord.review_date >= period_start,
        )
        .all()
    )

    if not records:
        return

    from app.agents.review_analysis_agent import analyze_reviews
    signal = analyze_reviews(store.id, records, period_start, period_end, db)
    logger.info(f"Review analysis: sentiment={signal.sentiment_score:.2f}, {signal.review_count} reviews")
