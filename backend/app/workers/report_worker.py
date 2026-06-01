"""Background worker: PDF 상담 준비 리포트 생성"""
import os
import re
import json
import html as html_lib
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.agent import Report, BusinessState, Diagnosis, ActionPlan
from app.models.financial import CostRecord, ExternalSignal, SalesRecord
from app.models.review import ReviewSignal, ReviewRecord, ReviewSource
from app.models.store import Store
from app.core.config import settings

logger = logging.getLogger(__name__)

REPORT_DIR = os.path.join(settings.UPLOAD_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def generate_report_task(report_id: str):
    db: Session = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return

        report.status = "generating"
        db.commit()

        store = db.query(Store).filter(Store.id == report.store_id).first()
        state = db.query(BusinessState).filter(
            BusinessState.store_id == store.id
        ).order_by(BusinessState.computed_at.desc()).first()
        diagnosis = db.query(Diagnosis).filter(Diagnosis.id == report.diagnosis_id).first()
        plan = db.query(ActionPlan).filter(ActionPlan.id == report.action_plan_id).first()

        # 리뷰 신호 (최근 6개월치 — 트렌드용)
        review_signals = db.query(ReviewSignal).filter(
            ReviewSignal.store_id == store.id
        ).order_by(ReviewSignal.period_end.desc()).limit(6).all()

        # 최근 리뷰 샘플
        review_samples = (
            db.query(ReviewRecord)
            .join(ReviewSource)
            .filter(ReviewSource.store_id == store.id)
            .order_by(ReviewRecord.review_date.desc())
            .limit(10)
            .all()
        )

        from app.agents.rag_agent import get_jb_products
        jb_products = get_jb_products(db)

        context = _build_report_context(db, store, review_samples)
        narratives = _generate_report_narratives(
            store, state, diagnosis, plan, review_signals, jb_products, context
        )
        html = _render_report_html(
            store, state, diagnosis, plan, review_signals, review_samples, jb_products, narratives
        )
        file_path = os.path.join(REPORT_DIR, f"report_{report_id}.pdf")
        _html_to_pdf(html, file_path)

        report.file_path = file_path
        report.status = "done"
        report.content = {
            "store_name": store.name,
            "generated_at": datetime.utcnow().isoformat(),
            "health_score": state.health_score if state else None,
        }
        db.commit()
        logger.info(f"Report generated: {file_path}")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        if report:
            report.status = "failed"
            db.commit()
    finally:
        db.close()


FINPILOT_LOGO_SVG = """<svg viewBox="30 100 870 590" fill="none" xmlns="http://www.w3.org/2000/svg" width="56" height="38">
  <path d="M 420.50 437.50 Q 421.00 435.00 416.00 434.50 Q 411.00 434.00 365.00 440.00 Q 319.00 446.00 308.00 448.50 Q 297.00 451.00 271.00 459.50 Q 245.00 468.00 236.00 472.00 Q 227.00 476.00 213.50 484.00 Q 200.00 492.00 183.00 506.50 Q 166.00 521.00 105.00 594.00 Q 44.00 667.00 44.00 669.00 Q 44.00 671.00 109.50 671.00 Q 175.00 671.00 192.50 668.00 Q 210.00 665.00 220.50 661.50 Q 231.00 658.00 243.50 652.00 Q 256.00 646.00 272.00 634.50 Q 288.00 623.00 303.50 606.50 Q 319.00 590.00 346.50 551.50 Q 374.00 513.00 397.00 476.50 Q 420.00 440.00 420.50 437.50 Z" fill="white"/>
  <path d="M 777.50 215.00 Q 780.00 207.00 779.00 206.00 Q 778.00 205.00 765.00 214.00 Q 752.00 223.00 735.00 232.50 Q 718.00 242.00 705.50 247.50 Q 693.00 253.00 673.50 259.50 Q 654.00 266.00 617.50 274.00 Q 581.00 282.00 506.50 292.00 Q 432.00 302.00 409.00 307.50 Q 386.00 313.00 372.00 318.00 Q 358.00 323.00 337.00 334.00 Q 316.00 345.00 296.50 359.50 Q 277.00 374.00 259.50 391.50 Q 242.00 409.00 231.50 422.00 Q 221.00 435.00 216.50 442.50 Q 212.00 450.00 214.00 451.00 Q 216.00 452.00 239.50 441.50 Q 263.00 431.00 284.00 425.00 Q 305.00 419.00 328.50 414.50 Q 352.00 410.00 408.00 402.50 Q 464.00 395.00 496.50 389.50 Q 529.00 384.00 563.50 376.00 Q 598.00 368.00 620.50 360.00 Q 643.00 352.00 656.00 345.50 Q 669.00 339.00 680.50 331.50 Q 692.00 324.00 709.00 309.50 Q 726.00 295.00 734.00 286.00 Q 742.00 277.00 752.50 262.00 Q 763.00 247.00 769.00 235.00 Q 775.00 223.00 777.50 215.00 Z" fill="white"/>
  <path d="M 726.50 341.50 Q 731.00 327.00 728.00 327.00 Q 725.00 327.00 715.00 336.00 Q 705.00 345.00 686.50 357.50 Q 668.00 370.00 650.00 379.00 Q 632.00 388.00 609.00 397.00 Q 586.00 406.00 577.00 410.50 Q 568.00 415.00 559.50 420.50 Q 551.00 426.00 545.00 431.00 Q 539.00 436.00 529.00 446.50 Q 519.00 457.00 511.00 468.00 Q 503.00 479.00 455.00 550.50 Q 407.00 622.00 406.50 624.50 Q 406.00 627.00 420.50 627.00 Q 435.00 627.00 449.50 625.50 Q 464.00 624.00 483.50 619.50 Q 503.00 615.00 514.00 611.50 Q 525.00 608.00 546.50 598.00 Q 568.00 588.00 580.50 579.50 Q 593.00 571.00 601.00 564.00 Q 609.00 557.00 620.50 544.50 Q 632.00 532.00 643.50 515.00 Q 655.00 498.00 665.00 480.50 Q 675.00 463.00 689.50 432.50 Q 704.00 402.00 713.00 379.00 Q 722.00 356.00 726.50 341.50 Z" fill="white"/>
  <circle cx="842.39" cy="157.99" r="45.16" fill="white"/>
</svg>"""



# ── 공유 CSS (generate_report.py와 동일 원칙) ──────────────────────────────
_REPORT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
@page { size: A4 portrait; margin: 12mm 0 10mm 0; }
@page cover { size: A4 portrait; margin: 0; }
*{box-sizing:border-box;margin:0;padding:0;}
html,body{font-family:'Noto Sans KR',-apple-system,sans-serif;color:#0f172a;font-size:13px;line-height:1.5;background:#fff;}

.cover{
  page:cover;
  background:linear-gradient(160deg,#1e3a8a 0%,#1d4ed8 45%,#2563eb 100%);
  color:white; width:210mm; height:297mm;
  page-break-after:always; display:flex; flex-direction:column;
  padding:56px 64px 52px; overflow:hidden;
}
.cover-logo{display:flex;align-items:center;gap:16px;}
.cover-brand{font-size:22px;font-weight:900;letter-spacing:-0.5px;}
.cover-sub{font-size:11px;opacity:.65;margin-top:3px;}
.cover-center{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;}
.cover-eyebrow{font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;opacity:.55;margin-bottom:18px;}
.cover-title{font-size:46px;font-weight:900;line-height:1.15;letter-spacing:-1.5px;margin-bottom:14px;}
.cover-subtitle{font-size:16px;opacity:.8;font-weight:500;}
.cover-meta{font-size:12px;opacity:.6;margin-top:8px;}
.cover-divider{height:1px;background:rgba(255,255,255,.2);margin:36px 0;}
.cover-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:0;text-align:center;}
.cover-metric{padding:22px 0;border-right:1px solid rgba(255,255,255,.15);}
.cover-metric:last-child{border-right:none;}
.cover-metric .v{font-size:36px;font-weight:900;letter-spacing:-1.5px;line-height:1;}
.cover-metric .l{font-size:11px;opacity:.6;margin-top:6px;font-weight:600;}

.content{padding:18px 52px 28px;}
h2{font-size:15px;font-weight:900;color:#1e40af;border-bottom:2px solid #dbeafe;padding-bottom:9px;margin:30px 0 16px;display:flex;align-items:center;gap:8px;break-after:avoid;page-break-after:avoid;}
h2::before{content:"";display:inline-block;width:4px;height:16px;background:#2563eb;flex-shrink:0;}
.report-section{break-inside:auto;page-break-inside:auto;}

.metrics-row{width:100%;border-collapse:collapse;margin:10px 0 16px;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;}
.metrics-row td{padding:14px 16px;text-align:center;border-right:1px solid #e2e8f0;vertical-align:top;}
.metrics-row td:last-child{border-right:none;}
.metrics-row .mv{font-size:22px;font-weight:900;letter-spacing:-.5px;display:block;}
.metrics-row .ml{font-size:10px;color:#64748b;margin-top:4px;font-weight:600;display:block;}

.summary-plain{font-size:13px;line-height:1.65;color:#374151;margin:8px 0 14px;padding-left:8px;border-left:3px solid #2563eb;}

table.data{width:100%;border-collapse:collapse;margin:8px 0 4px;break-inside:auto;page-break-inside:auto;}
table.data thead{display:table-header-group;}
table.data tbody{display:table-row-group;}
table.data tr{break-inside:avoid;page-break-inside:avoid;}
table.data th,table.data td{break-inside:avoid;page-break-inside:avoid;}
table.data th{background:#eff6ff;color:#1e40af;font-size:11.5px;font-weight:800;padding:10px 14px;text-align:left;border-bottom:2px solid #dbeafe;}
table.data td{padding:10px 14px;font-size:12px;border-bottom:1px solid #f1f5f9;vertical-align:top;}
table.data tr.alt td{background:#fafbff;}

.report-narrative{margin:13px 0 6px;padding:2px 4px 2px 12px;border-left:3px solid #bfdbfe;color:#334155;font-size:12.2px;line-height:1.72;white-space:pre-line;}

.prog-bar{height:5px;background:#e2e8f0;margin-top:6px;overflow:hidden;}
.prog-fill{height:100%;}

.conf-high{color:#15803d;font-weight:700;font-size:11px;}
.conf-mid{color:#b45309;font-weight:700;font-size:11px;}

.type-op{color:#2563eb;font-weight:800;font-size:10.5px;}
.type-mk{color:#15803d;font-weight:800;font-size:10.5px;}
.type-fi{color:#b45309;font-weight:800;font-size:10.5px;}

.fin-fit{color:#1d4ed8;font-weight:700;font-size:11.5px;}
.fin-rec{color:#15803d;font-weight:700;font-size:11.5px;}
.fin-opt{color:#78350f;font-weight:700;font-size:11.5px;}

.question-list{list-style:none;}
.question-list li{display:flex;align-items:flex-start;gap:10px;padding:11px 0;border-bottom:1px solid #f1f5f9;font-size:12.5px;line-height:1.55;}
.question-list li::before{content:"Q";color:#2563eb;font-weight:900;flex-shrink:0;}

.disclaimer{background:#fff;border-left:4px solid #93c5fd;border-top:1px solid #dbeafe;border-bottom:1px solid #dbeafe;padding:12px 16px;font-size:11px;color:#334155;line-height:1.55;margin-top:20px;}
.disclaimer strong{color:#1e40af;}

.review-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0;break-inside:avoid;page-break-inside:avoid;}
.review-panel{background:#fff;border:1px solid #dbeafe;border-left:4px solid #93c5fd;border-radius:4px;padding:14px;}
.review-signal{font-size:11.5px;color:#475569;background:#fff;border-left:4px solid #93c5fd;border-top:1px solid #dbeafe;border-bottom:1px solid #dbeafe;padding:8px 12px;margin-top:8px;}

.footer{margin-top:16px;padding-top:10px;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;font-size:10.5px;color:#94a3b8;break-before:avoid;page-break-before:avoid;}
"""


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


def _parse_narrative_json(text: str) -> dict | None:
    text = _strip_think(text)
    if not text:
        return None
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```", r"(\{.*\})"]:
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            continue
        try:
            result = json.loads(m.group(1))
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            continue
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def _clean_narrative(value: str | None) -> str:
    if not value:
        return ""
    text = _strip_think(str(value))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:1800]


def _narrative_block(text: str | None) -> str:
    text = _clean_narrative(text)
    if not text:
        return ""
    return f'<div class="report-narrative">{html_lib.escape(text)}</div>'


def _guard_report_narratives(narratives: dict, state) -> dict:
    guarded = {}
    liquidity = _as_float(getattr(state, "liquidity_risk", None) if state else None, None)
    readiness = _as_float(getattr(state, "finance_readiness", None) if state else None, None)
    for key, text in narratives.items():
        cleaned = _clean_narrative(text)
        cleaned = re.sub(r"최근\s*\d+\s*주간", "최근 입력 자료에서", cleaned)
        cleaned = re.sub(
            r"최근 입력 자료에서\s*([^.\n]{1,40})의 시간대별 매출 패턴에서",
            r"최근 입력 자료의 \1 시간대별 매출 패턴에서",
            cleaned,
        )
        cleaned = re.sub(
            r"최근\s*\d+\s*(?:주|개월|일)간\s*\d+(?:\.\d+)?%\s*증가",
            "최근 리뷰에서 반복적으로 확인",
            cleaned,
        )
        cleaned = re.sub(
            r"(고객 리뷰에서[^.\n]*?)\s*\d+(?:\.\d+)?%\s*증가",
            r"\1 반복 확인",
            cleaned,
        )
        if liquidity is not None and liquidity <= 20:
            cleaned = re.sub(
                r"현재 유동성 위험도\s*\d+(?:\.\d+)?점으로\s*즉각[^.\n]*(?:입니다|합니다|상태입니다|상태다)\.?",
                f"현재 유동성 위험도 {liquidity:.0f}점으로 단기 금융 조치보다는 운영 개선 효과를 먼저 확인할 수 있는 상태입니다.",
                cleaned,
            )
            cleaned = cleaned.replace(
                "즉각적 조치가 필요한 상태입니다.",
                "단기 금융 조치보다는 운영 개선 효과를 먼저 확인할 수 있는 상태입니다.",
            )
        if readiness is not None:
            cleaned = re.sub(r"금융 준비도\s*\d+(?:\.\d+)?점", f"금융 준비도 {readiness:.0f}%", cleaned)
            cleaned = re.sub(r"금융 준비도\s*\d+(?:\.\d+)?%", f"금융 준비도 {readiness:.0f}%", cleaned)
            cleaned = cleaned.replace(f"{readiness:.0f}%으로", f"{readiness:.0f}%로")
        cleaned = re.sub(r"대기 시간\s*\d+(?:\.\d+)?%\s*감축", "대기 시간 단축", cleaned)
        guarded[key] = cleaned
    return guarded


def _as_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_report_context(db: Session, store, review_samples: list | None = None) -> dict:
    sales = (
        db.query(SalesRecord)
        .filter(SalesRecord.store_id == store.id)
        .order_by(SalesRecord.date.desc(), SalesRecord.hour.desc().nullslast())
        .limit(240)
        .all()
    )
    costs = (
        db.query(CostRecord)
        .filter(CostRecord.store_id == store.id)
        .order_by(CostRecord.date.desc())
        .limit(80)
        .all()
    )
    signals = (
        db.query(ExternalSignal)
        .filter(ExternalSignal.store_id == store.id)
        .order_by(ExternalSignal.created_at.desc())
        .limit(12)
        .all()
    )

    hourly = {}
    channel = {}
    daily = {}
    for sale in sales:
        if sale.hour is not None:
            hourly[sale.hour] = hourly.get(sale.hour, 0) + (sale.amount or 0)
        if sale.channel:
            channel[sale.channel] = channel.get(sale.channel, 0) + (sale.amount or 0)
        if sale.date:
            key = sale.date.isoformat()
            daily[key] = daily.get(key, 0) + (sale.amount or 0)
    cost_by_category = {}
    for cost in costs:
        cost_by_category[cost.category] = cost_by_category.get(cost.category, 0) + (cost.amount or 0)

    external_payload = []
    for sig in signals:
        external_payload.append({
            "type": sig.signal_type,
            "source": sig.source,
            "reference_date": sig.reference_date.isoformat() if sig.reference_date else None,
            "payload": sig.payload,
        })

    reviews = []
    for r in (review_samples or [])[:8]:
        reviews.append({
            "platform": r.platform,
            "date": r.review_date.isoformat() if r.review_date else None,
            "rating": r.rating,
            "text": (r.text or "")[:180],
        })

    return {
        "store_extra": getattr(store, "extra", {}) or {},
        "sales_hourly_top": sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:6],
        "sales_hourly_bottom": sorted(hourly.items(), key=lambda x: x[1])[:6],
        "sales_by_channel": sorted(channel.items(), key=lambda x: x[1], reverse=True),
        "sales_daily_recent": sorted(daily.items(), reverse=True)[:14],
        "cost_by_category": sorted(cost_by_category.items(), key=lambda x: x[1], reverse=True)[:8],
        "external_signals": external_payload,
        "review_samples": reviews,
    }


def _call_report_llm(prompt: str, system: str, max_tokens: int = 1500) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=max_tokens,
        timeout=120,
    )
    return response.choices[0].message.content or ""


def _compact_report_context(context: dict) -> dict:
    external = []
    for sig in (context.get("external_signals") or [])[:6]:
        payload = sig.get("payload") or {}
        compact_payload = {}
        for key in [
            "same_category_count", "new_last_3months", "nearby_stores",
            "rainy_days_recent", "avg_temp_drop_vs_prior", "forecast",
        ]:
            if key in payload:
                compact_payload[key] = payload[key]
        external.append({
            "type": sig.get("type"),
            "source": sig.get("source"),
            "reference_date": sig.get("reference_date"),
            "payload": compact_payload or payload,
        })

    return {
        "store_extra": context.get("store_extra") or {},
        "sales_hourly_top": (context.get("sales_hourly_top") or [])[:4],
        "sales_hourly_bottom": (context.get("sales_hourly_bottom") or [])[:4],
        "sales_by_channel": (context.get("sales_by_channel") or [])[:4],
        "sales_daily_recent": (context.get("sales_daily_recent") or [])[:10],
        "cost_by_category": (context.get("cost_by_category") or [])[:5],
        "external_signals": external,
        "review_samples": (context.get("review_samples") or [])[:6],
    }


def _generate_report_narratives(store, state, diagnosis, plan, review_signals=None, jb_products=None, context=None) -> dict:
    context = context or {}
    fallback = _fallback_report_narratives(store, state, diagnosis, plan, jb_products or [], context)

    causes = (diagnosis.causes if diagnosis else []) or []
    actions = (plan.actions if plan else []) or []
    latest_signal = (review_signals or [None])[0]
    products = []
    for doc in (jb_products or [])[:4]:
        content = (doc.get("content") or "")[:500]
        title = doc.get("title") or doc.get("source") or "JB금융 상품"
        products.append({"title": title, "content": content})

    state_payload = {
        "store_name": getattr(store, "name", ""),
        "category": getattr(store, "category", ""),
        "address": getattr(store, "address", ""),
        "health_score": getattr(state, "health_score", None) if state else None,
        "cash_runway_days": getattr(state, "cash_runway_days", None) if state else None,
        "finance_readiness": getattr(state, "finance_readiness", None) if state else None,
        "revenue_trend_pct": (getattr(state, "revenue_trend", 0) or 0) * 100 if state else None,
        "liquidity_risk": getattr(state, "liquidity_risk", None) if state else None,
        "recent_revenue_30d": (state.detail or {}).get("recent_revenue_30d") if state and state.detail else None,
        "total_cost_30d": (state.detail or {}).get("total_cost_30d") if state and state.detail else None,
    }
    review_payload = {}
    if latest_signal:
        review_payload = {
            "review_count": latest_signal.review_count,
            "sentiment_score": latest_signal.sentiment_score,
            "positive_keywords": latest_signal.positive_keywords,
            "negative_keywords": latest_signal.negative_keywords,
            "issue_categories": latest_signal.issue_categories,
            "business_signal": latest_signal.business_signal,
        }
    prompt = f"""
아래 자료만 사용해 상담 준비 PDF에 들어갈 보고서 문단을 작성하세요.

작성 대상:
1. causes: 2번 '매출 하락 원인 분석' 표 아래에 들어갈 세부 원인 문단
2. actions: 3번 '권장 실행 전략' 표 아래에 들어갈 구체 실행 문단
3. finance: 4번 '금융 준비 방향' 표 아래에 들어갈 상담 준비 문단

문체 규칙:
- 실제 은행 상담 전 내부 보고서처럼 담백하게 쓴다.
- "AI가", "데이터 기반으로", "맞춤형", "시사합니다", "중요합니다", "종합하면" 같은 흔한 표현은 쓰지 않는다.
- 표 내용을 다른 말로 요약하지 않는다. 표 아래에는 표에 없는 세부 해석과 실행 방법을 쓴다.
- 원인 문단은 '어떤 시간대/리뷰 표현/상권 신호/가격 부담/경쟁 밀도 때문에 어떤 고객 행동이 줄었는지'까지 좁혀 쓴다.
- 원인 문단에는 review_samples의 실제 리뷰 표현을 1~2개 짧게 인용한다.
- 실행 문단은 '무엇을, 언제, 어디에, 어떤 순서로, 어떤 지표로 확인할지'가 드러나게 쓴다.
- 금융 문단은 '상담 전에 어떤 증빙을 준비하고, 어떤 상품은 어떤 목적일 때만 검토할지'를 구분해 쓴다.
- 매장명, 수치, 원인명, 실행 전략명, 금융 준비도, 현금 유지 기간을 반드시 반영한다.
- 제공되지 않은 사실, 승인 가능성, 대출 가능 금액 확정, 금리 확정은 만들지 않는다.
- 입력에 없는 증가율, 감소율, 기간별 변화율, 메뉴명, 경쟁 가게명, 가격은 절대 만들지 않는다.
- 유동성 위험도는 낮을수록 안정적이다. 유동성 위험도 10점은 즉각 금융 조치가 필요한 상태가 아니다.
- 리뷰 원문이 있으면 원인 문단에 실제 표현을 짧게 인용해 구체화한다.
- 특정 경쟁 가게명, 특정 메뉴명, 정확한 메뉴 가격은 입력 자료에 있을 때만 쓴다. 없으면 '동종 카페', '가격 부담 키워드', '피크타임 대기'처럼 자료 범위 안에서 구체화한다.
- 각 항목은 최소 6문장, 420~700자 분량으로 작성한다.
- 문장마다 줄바꿈을 넣되 번호나 불릿 기호는 쓰지 않는다.
- JSON 외 텍스트를 출력하지 않는다.

사업 상태:
{json.dumps(state_payload, ensure_ascii=False, default=str)}

원인 분석:
{json.dumps(causes[:6], ensure_ascii=False, default=str)}

권장 전략:
{json.dumps(actions[:6], ensure_ascii=False, default=str)}

리뷰 신호:
{json.dumps(review_payload, ensure_ascii=False, default=str)}

세부 근거:
{json.dumps(_compact_report_context(context), ensure_ascii=False, default=str)}

JB금융/RAG 상품 참고:
{json.dumps(products, ensure_ascii=False, default=str)}

출력 JSON:
{{
  "causes": "표 요약이 아닌 세부 원인 분석 문단",
  "actions": "실행 순서와 확인 지표가 포함된 구체 실행 문단",
  "finance": "증빙 준비와 상품 검토 기준이 포함된 상담 준비 문단"
}}
"""
    system = "너는 소상공인 상담 준비 보고서를 작성하는 실무자다. 제공된 자료 안에서만 구체적으로 쓰고 JSON만 출력한다."
    try:
        result = _parse_narrative_json(_call_report_llm(prompt, system=system, max_tokens=1600)) or {}
    except Exception as e:
        logger.warning(f"Report narrative generation failed: {e}")
        return _guard_report_narratives(fallback, state)

    cleaned = {
        "causes": _clean_narrative(result.get("causes")) or fallback["causes"],
        "actions": _clean_narrative(result.get("actions")) or fallback["actions"],
        "finance": _clean_narrative(result.get("finance")) or fallback["finance"],
    }
    return _guard_report_narratives(cleaned, state)


def _fallback_report_narratives(store, state, diagnosis, plan, jb_products: list, context: dict | None = None) -> dict:
    causes = (diagnosis.causes if diagnosis else []) or []
    actions = (plan.actions if plan else []) or []
    context = context or {}
    top_cause = causes[0] if causes else {}
    second_cause = causes[1] if len(causes) > 1 else {}
    first_action = actions[0] if actions else {}
    second_action = actions[1] if len(actions) > 1 else {}
    name = getattr(store, "name", "해당 사업장")
    trend = (getattr(state, "revenue_trend", 0) or 0) * 100 if state else 0
    runway = _as_float(getattr(state, "cash_runway_days", 0) if state else 0)
    readiness = _as_float(getattr(state, "finance_readiness", 0) if state else 0)
    revenue = ((state.detail or {}).get("recent_revenue_30d", 0) if state and state.detail else 0) or 0
    cost = ((state.detail or {}).get("total_cost_30d", 0) if state and state.detail else 0) or 0
    top_cause_pct = _as_float(top_cause.get("contribution", 0))
    product_names = []
    for doc in jb_products[:4]:
        content = doc.get("content", "")
        m = re.search(r"(JB\s*[^\n]{0,30}(?:대출|상품권|보증)[^\n]*)", content)
        if m:
            product_names.append(m.group(1).strip())
    product_hint = ", ".join(product_names[:2]) or "운전자금·매출채권 담보 등 단기 유동성 상품"
    review_samples = context.get("review_samples") or []
    review_line = ""
    if review_samples:
        quoted = [r.get("text", "") for r in review_samples[:3] if r.get("text")]
        review_line = " 최근 리뷰에서는 " + " / ".join(f"'{q[:42]}'" for q in quoted) + " 같은 표현이 확인된다."
    hourly_bottom = context.get("sales_hourly_bottom") or []
    weak_hour = ""
    if hourly_bottom:
        weak_hour = f" 매출이 낮은 시간대는 {', '.join(f'{h}시' for h, _ in hourly_bottom[:3])}로 잡혀 있어 피크 전후 운영을 나눠 봐야 한다."
    external = context.get("external_signals") or []
    external_line = ""
    for sig in external:
        payload = sig.get("payload") or {}
        if sig.get("type") == "commerce_radius":
            same = payload.get("same_category_count")
            new = payload.get("new_last_3months")
            if same is not None:
                external_line = f" 반경 500m 동종 점포는 {same}개이고 최근 3개월 신규 점포는 {new or 0}개로 기록돼 있다."
                break

    return {
        "causes": (
            f"{name}의 최근 매출 추세는 {trend:+.1f}%로, 회복보다 방어가 먼저 필요한 구간이다.\n"
            f"가장 큰 원인은 {top_cause.get('factor', '주요 위험 요인')}이며 표에서는 {top_cause_pct:.0f}% 비중으로 잡혀 있다.\n"
            f"{top_cause.get('description', '방문 전환과 재방문 흐름을 함께 확인해야 한다.')}{review_line}\n"
            f"다음 원인인 {second_cause.get('factor', '보조 위험 요인')}도 매출 압박을 키우는 항목으로 보인다.{external_line}\n"
            f"최근 30일 매출은 ₩{revenue:,.0f}, 비용은 ₩{cost:,.0f} 수준이어서 원인별 개선 효과를 월 단위로 확인할 필요가 있다.\n"
            f"가격 부담이나 좌석 부족처럼 리뷰에 반복되는 표현은 단순 불만이 아니라 재방문을 미루는 신호로 보는 편이 맞다.{weak_hour}\n"
            "상담 전에는 피크타임 주문 대기, 테이크아웃 비중, 주변 동종 카페의 가격대 차이를 함께 확인해야 한다."
        ),
        "actions": (
            f"우선 실행 항목은 {first_action.get('title', '핵심 운영 개선')}으로 두고, 피크타임 주문 대기부터 줄인다.\n"
            f"{first_action.get('description', '현금 유출을 줄이고 매출 회복 가능성이 큰 항목부터 처리한다.')}\n"
            "오후 2~5시처럼 대기 불만이 나오는 시간에는 모바일 주문 안내 문구를 계산대와 출입구에 같이 노출한다.\n"
            f"두 번째로 {second_action.get('title', '보완 실행 전략')}을 붙여 매장 체류 고객과 테이크아웃 고객을 분리한다.\n"
            f"현재 현금 유지 기간이 {runway:.0f}일이므로 큰 설비 투자보다 쿠폰, 동선, 인력 배치처럼 2주 안에 바꿀 수 있는 항목부터 처리한다.\n"
            "확인 지표는 일매출, 오후 시간대 주문 수, 리뷰 내 '대기', '좌석', '가격' 언급 수로 잡는다.\n"
            "첫 1주일은 대기 시간 감소 여부를 보고, 둘째 주에는 재방문 쿠폰 사용률과 객단가 변화를 같이 비교한다."
        ),
        "finance": (
            f"금융 준비도는 {readiness:.0f}%, 현금 유지 기간은 {runway:.0f}일로 상담 전 기본 자료는 어느 정도 갖춰진 상태다.\n"
            f"매출 추세 {trend:+.1f}% 구간에서는 신규 투자보다 운영자금 완충 목적의 상담이 먼저다.\n"
            f"검토 대상은 {product_hint}처럼 현재 현금흐름과 연결되는 상품군이 적합하다.\n"
            "다만 상품명 노출은 상담 후보 정리의 의미이며, 실제 한도와 금리는 지점 심사와 증빙 자료 확인 뒤 결정된다.\n"
            f"최근 30일 매출 ₩{revenue:,.0f}와 비용 ₩{cost:,.0f}를 기준으로 상환 부담이 커지지 않는 범위를 먼저 계산해야 한다.\n"
            "상담 시에는 최근 3개월 카드 매출, 임대료·인건비·재료비 내역, 기존 차입 여부, 지역화폐 가맹 여부를 함께 준비한다.\n"
            "운전자금은 대기 시간 개선과 리뷰 회복 조치가 진행되는 동안의 현금 완충 목적일 때 우선 검토하고, 확장성 투자는 매출 반등 확인 뒤로 미루는 편이 낫다."
        ),
    }


def _cause_row(c, i):
    pct = c.get("contribution", 0)
    conf = c.get("confidence", "")
    conf_cls = "conf-high" if conf == "high" else "conf-mid"
    conf_label = "신뢰도 높음" if conf == "high" else "신뢰도 중간"
    bar_color = "#dc2626" if pct >= 35 else ("#f59e0b" if pct >= 20 else "#2563eb")
    alt = ' class="alt"' if i % 2 == 0 else ""
    desc = (c.get("description") or "")[:80]
    return (
        f'<tr{alt}>'
        f'<td><strong>{c.get("factor","")}</strong>'
        + (f'<br><small style="color:#64748b">{desc}</small>' if desc else "") +
        f'</td>'
        f'<td style="text-align:center"><strong style="font-size:16px">{pct:.0f}%</strong>'
        f'<div class="prog-bar"><div class="prog-fill" style="width:{pct}%;background:{bar_color}"></div></div></td>'
        f'<td style="text-align:center"><span class="{conf_cls}">{conf_label}</span></td>'
        f'</tr>'
    )


def _action_row(a, i):
    t = a.get("type", "operation")
    labels = {"operation": "운영", "marketing": "마케팅", "finance": "금융"}
    type_cls = {"operation": "type-op", "marketing": "type-mk", "finance": "type-fi"}
    cls = type_cls.get(t, "type-op")
    impact = a.get("expected_impact", {})
    parts = []
    if impact.get("cash_runway_days_delta"):
        parts.append(f'+{impact["cash_runway_days_delta"]}일 현금')
    if impact.get("revenue_change_pct"):
        parts.append(f'+{impact["revenue_change_pct"]}% 매출')
    if impact.get("finance_readiness_delta"):
        parts.append(f'+{impact["finance_readiness_delta"]}% 준비도')
    impact_str = " · ".join(parts)
    alt = ' class="alt"' if i % 2 == 0 else ""
    return (
        f'<tr{alt}>'
        f'<td><span class="{cls}">{labels.get(t,"기타")}</span></td>'
        f'<td><strong>{a.get("title","")}</strong></td>'
        f'<td style="font-size:11px;color:#475569">{(a.get("description") or "")[:80]}</td>'
        f'<td style="font-size:12px;color:#15803d;font-weight:700">{impact_str}</td>'
        f'</tr>'
    )


def _render_report_html(
    store, state, diagnosis, plan, review_signals=None, review_samples=None, jb_products=None, narratives=None
) -> str:
    from datetime import date
    today = date.today().strftime("%Y년 %m월 %d일")
    causes = diagnosis.causes if diagnosis else []
    actions = plan.actions if plan else []
    rag_refs = plan.rag_references if plan else []
    narratives = narratives or {}

    # Cover metrics
    cover_metrics = ""
    if state:
        for v, l in [
            (f"{state.health_score:.0f}", "사업 건강도"),
            (f"{state.cash_runway_days:.0f}일", "현금 유지 기간"),
            (f"{state.finance_readiness:.0f}%", "금융 준비도"),
            (f"{len(actions)}가지", "권장 전략"),
        ]:
            cover_metrics += f'<div class="cover-metric"><div class="v">{v}</div><div class="l">{l}</div></div>'

    # State metrics — flat row, no boxes
    metrics_html = '<p style="color:#94a3b8">진단 데이터가 없습니다.</p>'
    if state:
        runway_color = "#dc2626" if (state.cash_runway_days or 0) < 20 else ("#f59e0b" if (state.cash_runway_days or 0) < 40 else "#15803d")
        fin_color = "#15803d" if (state.finance_readiness or 0) >= 70 else "#2563eb"
        liq_color = "#dc2626" if (state.liquidity_risk or 0) >= 70 else ("#f59e0b" if (state.liquidity_risk or 0) >= 40 else "#15803d")
        liq_label = "높음" if (state.liquidity_risk or 0) >= 70 else ("중간" if (state.liquidity_risk or 0) >= 40 else "낮음")
        rev30 = state.detail.get('recent_revenue_30d', 0) or 0
        cost30 = state.detail.get('total_cost_30d', 0) or 0
        metrics_html = (
            '<table class="metrics-row"><tr>'
            f'<td><span class="mv">{state.health_score:.0f}</span><span class="ml">사업 건강도 (/100)</span></td>'
            f'<td><span class="mv" style="color:{runway_color}">{state.cash_runway_days:.0f}일</span><span class="ml">현금 유지 기간</span></td>'
            f'<td><span class="mv" style="color:{fin_color}">{state.finance_readiness:.0f}%</span><span class="ml">금융 준비도</span></td>'
            f'<td><span class="mv" style="color:{liq_color}">{liq_label}</span><span class="ml">유동성 위험도</span></td>'
            f'<td><span class="mv">₩{rev30:,.0f}</span><span class="ml">최근 30일 매출</span></td>'
            f'<td><span class="mv">₩{cost30:,.0f}</span><span class="ml">최근 30일 비용</span></td>'
            '</tr></table>'
        )

    # Summary — plain text with left border, no box
    summary_html = ""
    if diagnosis and diagnosis.summary:
        summary_html = f'<p class="summary-plain">{diagnosis.summary}</p>'

    # Cause table
    if causes:
        cause_table = (
            '<table class="data">'
            '<thead><tr><th style="width:38%">원인 요인 및 설명</th>'
            '<th style="width:22%">기여도</th>'
            '<th style="width:15%">신뢰도</th></tr></thead><tbody>'
            + "".join(_cause_row(c, i) for i, c in enumerate(causes[:6]))
            + '</tbody></table>'
        )
    else:
        cause_table = '<p style="color:#94a3b8">원인 분석 데이터가 없습니다.</p>'

    # Action table
    if actions:
        action_table = (
            '<table class="data">'
            '<thead><tr><th style="width:9%">유형</th>'
            '<th style="width:22%">전략명</th>'
            '<th style="width:44%">실행 내용</th>'
            '<th style="width:25%">예상 효과</th></tr></thead><tbody>'
            + "".join(_action_row(a, i) for i, a in enumerate(actions[:5]))
            + '</tbody></table>'
        )
    else:
        action_table = '<p style="color:#94a3b8">전략 데이터가 없습니다.</p>'

    finance_html = _render_finance_section(state, jb_products or [], rag_refs)
    review_html = _render_review_section(review_signals or [], review_samples or [])

    return (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
        f'<style>{_REPORT_CSS}</style></head><body>'
        '<div class="cover">'
        f'<div class="cover-logo">{FINPILOT_LOGO_SVG}'
        '<div><div class="cover-brand">BizPlot Agent</div>'
        '<div class="cover-sub">소상공인 AI CFO Platform · JB금융그룹 Fin:AI Challenge</div></div></div>'
        '<div class="cover-center">'
        '<div class="cover-eyebrow">상담 준비 리포트</div>'
        f'<div class="cover-title">{store.name}</div>'
        f'<div class="cover-subtitle">업종: {store.category} &nbsp;·&nbsp; {store.address or "위치 미입력"}</div>'
        f'<div class="cover-meta">생성일: {today}</div>'
        '</div>'
        '<div class="cover-divider"></div>'
        f'<div class="cover-metrics">{cover_metrics}</div>'
        '</div>'
        '<div class="content">'
        '<section class="report-section">'
        '<h2>1. 사업 상태 요약</h2>'
        + metrics_html +
        '</section>'
        '<section class="report-section">'
        '<h2>2. 매출 하락 원인 분석</h2>'
        + summary_html + cause_table + _narrative_block(narratives.get("causes")) +
        '</section>'
        '<section class="report-section">'
        '<h2>3. 권장 실행 전략</h2>'
        + action_table + _narrative_block(narratives.get("actions")) +
        '</section>'
        '<section class="report-section">'
        '<h2>4. 금융 준비 방향</h2>'
        + finance_html + _narrative_block(narratives.get("finance")) +
        '</section>'
        '<section class="report-section">'
        '<h2>5. 고객 리뷰 변화 분석</h2>'
        + review_html +
        '</section>'
        '<section class="report-section">'
        '<h2>6. 상담 시 확인 질문 목록</h2>'
        '<ul class="question-list">'
        '<li>JB(전북은행) 소상공인 운전자금 대출 신청 요건 및 금리를 구체적으로 알고 싶습니다.</li>'
        '<li>매출채권 담보 대출로 빠른 자금 조달이 가능한지 확인하고 싶습니다.</li>'
        '<li>전북사랑상품권 가맹 시 JB금융 우대 금리 0.3%p 적용 방법을 알고 싶습니다.</li>'
        '<li>소상공인 경영안정 정책자금 신청 자격 요건은 무엇인가요?</li>'
        '<li>사업 상태 데이터를 기반으로 상담 가능한 전담 담당자를 연결받을 수 있나요?</li>'
        '</ul>'
        '</section>'
        '<div class="disclaimer"><strong>중요 안내</strong><br>'
        '본 리포트는 AI가 자동 생성한 참고 자료이며 법적 효력이 없습니다. '
        '특정 금융상품 가입을 권유하거나 보장하지 않습니다. '
        '최종 금융 판단은 금융기관 담당자와의 상담 및 심사 절차를 통해 이루어집니다.</div>'
        f'<div class="footer"><span>BizPlot Agent · 소상공인 AI CFO Platform</span>'
        f'<span>생성일: {today} · JB금융그룹 Fin:AI Challenge</span></div>'
        '</div></body></html>'
    )

def _render_finance_section(state, jb_products: list, rag_refs: list) -> str:
    """RAG에서 가져온 JB금융그룹 상품을 카테고리별로 정리해 금융 섹션을 렌더링한다."""
    import re

    runway = (state.cash_runway_days or 0) if state else 0
    readiness = (state.finance_readiness or 0) if state else 0
    trend = (state.revenue_trend or 0) if state else 0
    rev30 = (state.detail.get("recent_revenue_30d", 0) if state and state.detail else 0) or 0

    # ── 카테고리 정의: RAG 키워드 → 정규화된 상품 ──────────────────────────────
    # 같은 상품이 jb/jbbank 두 문서에 중복돼 있으므로 카테고리로 dedup한다.
    CATEGORIES = [
        {
            "key": "운전자금",
            "match": ["운전자금"],
            "name": "JB 소상공인 운전자금 대출",
            "label": ("상담 권장", "fin-rec") if readiness >= 60 else ("요건 확인", "fin-opt"),
            "reason": (
                f"매출 추세 {trend*100:+.1f}% 국면에서 운영자금 완충용으로 검토. "
                f"금융 준비도 {readiness:.0f}%로 신청 서류 준비 가능 수준 — 전북은행 지점 상담 권장."
            ),
        },
        {
            "key": "매출채권담보",
            "match": ["매출채권", "담보"],
            "name": "JB 매출채권 담보 대출",
            "label": ("상황 적합", "fin-fit") if runway < 30 else ("검토 가능", "fin-rec"),
            "reason": (
                f"카드 매출 기반 빠른 유동성 확보 수단. 현재 월 매출 ₩{rev30:,.0f} 기준 "
                f"한도 산정 시 약 ₩{rev30*3:,.0f}(3개월분)을 참고 자료로 제시 가능. 심사·지급 일정은 지점 확인 필요."
            ),
        },
        {
            "key": "지역화폐",
            "match": ["지역화폐", "상품권", "사랑상품권"],
            "name": "전북사랑상품권 가맹 + JB 우대 금리",
            "label": ("마케팅 연계", "fin-opt"),
            "reason": (
                "가맹 등록 시 지역 고객 신규 유입 + JB금융 대출 금리 0.3%p 우대. "
                "권장 전략의 '오후 재방문 쿠폰'과 병행 시 매출 회복 효과 극대화."
            ),
        },
        {
            "key": "보증",
            "match": ["보증"],
            "name": "JB 신용보증 연계 대출",
            "label": ("검토 가능", "fin-rec"),
            "reason": (
                "신용보증재단 보증서 기반으로 담보 부담 없이 자금 조달. "
                "정책자금 한도 소진 시 추가 운영자금 확보 경로로 활용."
            ),
        },
    ]

    # ── RAG 내용에서 카테고리별 실제 한도/금리 라인 추출 ───────────────────────
    def _extract_specs(category_match: list[str]) -> list[str]:
        """해당 카테고리 상품 블록에서 한도/금리/기간/상환 라인을 뽑는다."""
        for doc in jb_products:
            content = doc.get("content", "")
            lines = content.splitlines()
            for idx, line in enumerate(lines):
                stripped = line.strip().strip("[]").lstrip("0123456789. ")
                # 상품명 라인 매칭
                if any(kw in stripped for kw in category_match) and (
                    "대출" in stripped or "우대" in stripped or "상품권" in stripped or "보증" in stripped
                ):
                    specs = []
                    for nxt in lines[idx + 1: idx + 8]:
                        n = nxt.strip().lstrip("- ").strip()
                        if not n or n.startswith("[") or re.match(r"^\d+\.", n):
                            if specs:
                                break
                            continue
                        for prefix in ("한도:", "금리:", "기간:", "상환방식:"):
                            if n.startswith(prefix):
                                specs.append(n)
                                break
                    if specs:
                        return specs[:3]
        return []

    # ── 표 행 생성 ─────────────────────────────────────────────────────────────
    jb_rows = ""
    for i, cat in enumerate(CATEGORIES):
        # 해당 카테고리가 RAG 문서에 실제로 존재할 때만 노출
        present = any(
            any(kw in doc.get("content", "") for kw in cat["match"]) for doc in jb_products
        )
        if not present:
            continue
        specs = _extract_specs(cat["match"])
        spec_html = ""
        if specs:
            spec_html = "<br>" + "<br>".join(
                f'<span style="font-size:10.5px;color:#64748b">{s}</span>' for s in specs
            )
        label, cls = cat["label"]
        alt = ' class="alt"' if i % 2 == 1 else ""
        jb_rows += (
            f'<tr{alt}>'
            f'<td><strong style="font-size:12px">{cat["name"]}</strong>{spec_html}</td>'
            f'<td style="text-align:center"><span class="{cls}">{label}</span></td>'
            f'<td style="font-size:11.5px;color:#374151">{cat["reason"]}</td>'
            f'</tr>'
        )

    if not jb_rows:
        # RAG 미적재 시 폴백
        jb_rows = (
            '<tr><td><strong>JB 소상공인 운전자금 대출</strong></td>'
            '<td style="text-align:center"><span class="fin-rec">검토 권장</span></td>'
            '<td style="font-size:11.5px">한도 최대 5,000만원 · 금리 연 4.5~6.5% · 전북은행 지점 상담</td></tr>'
        )

    # ── 정책자금 참고 (JB 외 RAG) ──────────────────────────────────────────────
    policy_note = ""
    policy_refs = [r for r in rag_refs if r.get("source") not in ("jb", "jbbank") and r.get("title")]
    if policy_refs:
        seen, titles = set(), []
        for r in policy_refs:
            t = r["title"]
            if t not in seen:
                seen.add(t)
                titles.append(t)
        policy_note = (
            '<p style="font-size:11px;color:#64748b;margin-top:10px;padding-left:4px">'
            f'함께 검토할 정책자금: {" · ".join(titles[:3])}</p>'
        )

    return (
        f'<p style="font-size:12px;color:#475569;margin-bottom:10px">'
        f'금융 준비도 <strong style="color:#1d4ed8">{readiness:.0f}%</strong>, '
        f'현금 유지 기간 <strong style="color:#15803d">{runway:.0f}일</strong> 기준으로 '
        f'JB금융그룹(전북은행) 연계 상품을 사업 상태에 맞춰 안내합니다.</p>'
        '<table class="data">'
        '<thead><tr>'
        '<th style="width:32%">JB금융그룹 상품</th>'
        '<th style="width:15%">적합도</th>'
        '<th>활용 방향 (현재 사업 상태 연계)</th>'
        '</tr></thead><tbody>'
        + jb_rows +
        '</tbody></table>'
        + policy_note
    )


def _render_review_section(signals: list, samples: list) -> str:
    if not signals and not samples:
        return '<p style="color:#94a3b8;font-size:12px">수집된 리뷰 데이터가 없습니다. 설정에서 리뷰 출처를 등록하고 수집에 동의해 주세요.</p>'

    latest = signals[0] if signals else None
    issue_labels = {
        "wait_time": "대기 시간", "space": "공간 부족", "price": "가격 부담",
        "service": "서비스", "quality": "품질", "delivery": "배달 품질",
    }

    # 트렌드 차트 (SVG 간이)
    trend_svg = ""
    if len(signals) >= 2:
        pts = list(reversed(signals))
        scores = [(s.sentiment_score or 0) for s in pts]
        w, h = 400, 80
        x_step = w / max(len(pts) - 1, 1)
        def y_pos(v): return h - int((v + 1) / 2 * h)
        coords = " ".join(f"{int(i * x_step)},{y_pos(v)}" for i, v in enumerate(scores))
        labels_html = "".join(
            f'<text x="{int(i*x_step)}" y="{h+14}" font-size="9" text-anchor="middle" fill="#94a3b8">{pts[i].period_end.strftime("%m/%d") if pts[i].period_end else ""}</text>'
            for i in range(len(pts))
        )
        trend_svg = f"""
        <div style="margin:12px 0">
          <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:6px">감성 점수 추이 (최근 {len(pts)}기간)</div>
          <svg width="{w}" height="{h+20}" style="overflow:visible">
            <line x1="0" y1="{y_pos(0)}" x2="{w}" y2="{y_pos(0)}" stroke="#e2e8f0" stroke-dasharray="3"/>
            <polyline points="{coords}" fill="none" stroke="#2563EB" stroke-width="2" stroke-linejoin="round"/>
            {''.join(f'<circle cx="{int(i*x_step)}" cy="{y_pos(v)}" r="3" fill="#2563EB"/>' for i, v in enumerate(scores))}
            {labels_html}
          </svg>
        </div>"""

    # 최신 신호 요약
    sentiment_html = ""
    if latest:
        score_pct = int((latest.sentiment_score + 1) * 50) if latest.sentiment_score is not None else 50
        score_color = "#15803d" if score_pct >= 65 else ("#f59e0b" if score_pct >= 40 else "#dc2626")
        neg_kws = ", ".join(latest.negative_keywords[:5]) if latest.negative_keywords else "없음"
        pos_kws = ", ".join(latest.positive_keywords[:5]) if latest.positive_keywords else "없음"
        issues_html = ""
        if latest.issue_categories:
            sorted_issues = sorted(latest.issue_categories.items(), key=lambda x: x[1], reverse=True)[:3]
            issues_html = "".join(
                f'<div style="margin:4px 0"><span style="font-size:11px;color:#475569">{issue_labels.get(k,k)}</span>'
                f'<div style="height:5px;background:#f1f5f9;margin-top:2px;overflow:hidden">'
                f'<div style="height:100%;width:{min(v*100,100):.0f}%;background:#93c5fd"></div></div></div>'
                for k, v in sorted_issues
            )
        sentiment_html = f"""
        <div class="review-grid">
          <div class="review-panel">
            <div style="font-size:10.5px;font-weight:700;color:#64748b;margin-bottom:6px">최근 감성 점수</div>
            <div style="font-size:26px;font-weight:900;color:{score_color}">{score_pct}</div>
            <div style="font-size:10px;color:#94a3b8">/100 · 리뷰 {latest.review_count or 0}건</div>
            <div style="height:6px;background:#e2e8f0;margin-top:8px;overflow:hidden">
              <div style="height:100%;width:{score_pct}%;background:{score_color}"></div>
            </div>
          </div>
          <div class="review-panel">
            <div style="font-size:10.5px;font-weight:700;color:#64748b;margin-bottom:4px">주요 이슈</div>
            {issues_html if issues_html else '<div style="font-size:11px;color:#94a3b8">이슈 없음</div>'}
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 0">
          <div>
            <div style="font-size:10.5px;font-weight:700;color:#15803d;margin-bottom:4px">긍정 키워드</div>
            <div style="font-size:11.5px;color:#374151">{pos_kws}</div>
          </div>
          <div>
            <div style="font-size:10.5px;font-weight:700;color:#dc2626;margin-bottom:4px">부정 키워드</div>
            <div style="font-size:11.5px;color:#374151">{neg_kws}</div>
          </div>
        </div>
        {f'<div class="review-signal">{latest.business_signal}</div>' if latest.business_signal else ''}
        """

    # 최근 리뷰 샘플
    samples_html = ""
    if samples:
        platform_labels = {"google": "Google", "naver": "네이버", "baemin": "배민", "coupang": "쿠팡이츠", "manual": "수동"}
        samples_html = f"""
        <div style="margin-top:14px">
          <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:6px">최근 리뷰 샘플</div>
          {''.join(
            f'<div style="padding:8px 10px;border-bottom:1px solid #f1f5f9;font-size:11.5px">'
            f'<span style="font-size:10px;background:#eff6ff;color:#1d4ed8;padding:1px 6px;border-radius:4px;margin-right:6px;font-weight:700">{platform_labels.get(r.platform, r.platform)}</span>'
            f'{"⭐"*int(r.rating) if r.rating else ""} '
            f'<span style="color:#374151">{(r.text or "")[:120]}{"..." if len(r.text or "") > 120 else ""}</span>'
            f'</div>'
            for r in samples[:5]
          )}
        </div>"""

    return trend_svg + sentiment_html + samples_html


def _html_to_pdf(html: str, output_path: str):
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)
    except Exception as e:
        # Fallback: save as HTML if WeasyPrint fails
        html_path = output_path.replace(".pdf", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        # Rename to .pdf for compatibility
        os.rename(html_path, output_path)
