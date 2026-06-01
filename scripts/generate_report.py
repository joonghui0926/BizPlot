"""
독립 실행 PDF 리포트 생성 스크립트
Usage: conda run -n finpilot-llm python scripts/generate_report.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import date
from app.db.base import SessionLocal
from app.models.store import Store
from app.models.agent import BusinessState, Diagnosis, ActionPlan
from app.models.review import ReviewSignal, ReviewRecord, ReviewSource

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..')

LOGO_SVG = """<svg viewBox="30 100 870 590" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36">
  <path d="M420.5 437.5Q421 435 416 434.5Q411 434 365 440Q319 446 308 448.5Q297 451 271 459.5Q245 468 236 472Q227 476 213.5 484Q200 492 183 506.5Q166 521 105 594Q44 667 44 669Q44 671 109.5 671Q175 671 192.5 668Q210 665 220.5 661.5Q231 658 243.5 652Q256 646 272 634.5Q288 623 303.5 606.5Q319 590 346.5 551.5Q374 513 397 476.5Q420 440 420.5 437.5Z" fill="white"/>
  <path d="M777.5 215Q780 207 779 206Q778 205 765 214Q752 223 735 232.5Q718 242 705.5 247.5Q693 253 673.5 259.5Q654 266 617.5 274Q581 282 506.5 292Q432 302 409 307.5Q386 313 372 318Q358 323 337 334Q316 345 296.5 359.5Q277 374 259.5 391.5Q242 409 231.5 422Q221 435 216.5 442.5Q212 450 214 451Q216 452 239.5 441.5Q263 431 284 425Q305 419 328.5 414.5Q352 410 408 402.5Q464 395 496.5 389.5Q529 384 563.5 376Q598 368 620.5 360Q643 352 656 345.5Q669 339 680.5 331.5Q692 324 709 309.5Q726 295 734 286Q742 277 752.5 262Q763 247 769 235Q775 223 777.5 215Z" fill="white"/>
  <path d="M726.5 341.5Q731 327 728 327Q725 327 715 336Q705 345 686.5 357.5Q668 370 650 379Q632 388 609 397Q586 406 577 410.5Q568 415 559.5 420.5Q551 426 545 431Q539 436 529 446.5Q519 457 511 468Q503 479 455 550.5Q407 622 406.5 624.5Q406 627 420.5 627Q435 627 449.5 625.5Q464 624 483.5 619.5Q503 615 514 611.5Q525 608 546.5 598Q568 588 580.5 579.5Q593 571 601 564Q609 557 620.5 544.5Q632 532 643.5 515Q655 498 665 480.5Q675 463 689.5 432.5Q704 402 713 379Q722 356 726.5 341.5Z" fill="white"/>
  <circle cx="842.39" cy="157.99" r="45.16" fill="white"/>
</svg>"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
@page { size: A4 portrait; margin: 0; }
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:297mm;font-family:'Noto Sans KR',-apple-system,sans-serif;color:#0f172a;font-size:13px;line-height:1.5;}

/* ── 표지: A4 전체 채우기 ── */
.cover{
  background:linear-gradient(160deg,#1e3a8a 0%,#1d4ed8 45%,#2563eb 100%);
  color:white;
  width:210mm; height:297mm;
  page-break-after:always;
  display:flex; flex-direction:column;
  padding:56px 64px 52px;
  overflow:hidden;
}
.cover-logo{display:flex;align-items:center;gap:16px;}
.cover-brand{font-size:22px;font-weight:900;letter-spacing:-0.5px;}
.cover-sub{font-size:11px;opacity:.65;margin-top:3px;}

.cover-center{
  flex:1;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  text-align:center;
}
.cover-eyebrow{font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;opacity:.55;margin-bottom:18px;}
.cover-title{font-size:46px;font-weight:900;line-height:1.15;letter-spacing:-1.5px;margin-bottom:14px;}
.cover-subtitle{font-size:16px;opacity:.8;font-weight:500;}
.cover-meta{font-size:12px;opacity:.6;margin-top:8px;}

.cover-divider{height:1px;background:rgba(255,255,255,.2);margin:36px 0;}
.cover-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:0;text-align:center;}
.cover-metric{padding:22px 0;border-right:1px solid rgba(255,255,255,.15);}
.cover-metric:last-child{border-right:none;}
.cover-metric .v{font-size:36px;font-weight:900;letter-spacing:-1.5px;line-height:1;}
.cover-metric .l{font-size:11px;opacity:.6;margin-top:6px;font-weight:600;letter-spacing:.3px;}

/* ── 콘텐츠 ── */
.content{padding:44px 52px;}
h2{font-size:15px;font-weight:900;color:#1e40af;border-bottom:2px solid #dbeafe;padding-bottom:9px;margin:36px 0 18px;display:flex;align-items:center;gap:8px;}
h2::before{content:"";display:inline-block;width:4px;height:16px;background:#2563eb;flex-shrink:0;}

/* ── 지표: 라운드 박스 없이 한 줄 테이블 ── */
.metrics-row{width:100%;border-collapse:collapse;margin:10px 0 16px;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;}
.metrics-row td{padding:14px 16px;text-align:center;border-right:1px solid #e2e8f0;vertical-align:top;}
.metrics-row td:last-child{border-right:none;}
.metrics-row .mv{font-size:22px;font-weight:900;letter-spacing:-.5px;display:block;}
.metrics-row .ml{font-size:10px;color:#64748b;margin-top:4px;font-weight:600;display:block;}

/* ── 요약 텍스트: 박스 없이 ── */
.summary-plain{font-size:13px;line-height:1.65;color:#374151;margin:8px 0 14px;padding-left:8px;border-left:3px solid #2563eb;}

/* ── 데이터 테이블 ── */
table.data{width:100%;border-collapse:collapse;margin:8px 0 4px;}
table.data th{background:#eff6ff;color:#1e40af;font-size:11.5px;font-weight:800;padding:10px 14px;text-align:left;border-bottom:2px solid #dbeafe;}
table.data td{padding:10px 14px;font-size:12px;border-bottom:1px solid #f1f5f9;vertical-align:top;}
table.data tr.alt td{background:#fafbff;}

.prog-bar{height:5px;background:#e2e8f0;margin-top:6px;overflow:hidden;}
.prog-fill{height:100%;}

/* 신뢰도 — 배경 없이 컬러 텍스트만 */
.conf-high{color:#15803d;font-weight:700;font-size:11px;}
.conf-mid{color:#b45309;font-weight:700;font-size:11px;}

/* 전략 유형 — 라운드 박스 없이 컬러 텍스트 */
.type-op{color:#2563eb;font-weight:800;font-size:10.5px;}
.type-mk{color:#15803d;font-weight:800;font-size:10.5px;}
.type-fi{color:#b45309;font-weight:800;font-size:10.5px;}

/* 금융 옵션 뱃지 — 배경 없이 텍스트 */
.fin-fit{color:#1d4ed8;font-weight:700;font-size:11.5px;}
.fin-rec{color:#15803d;font-weight:700;font-size:11.5px;}
.fin-opt{color:#78350f;font-weight:700;font-size:11.5px;}

.question-list{list-style:none;}
.question-list li{display:flex;align-items:flex-start;gap:10px;padding:11px 0;border-bottom:1px solid #f1f5f9;font-size:12.5px;line-height:1.55;}
.question-list li::before{content:"Q";color:#2563eb;font-weight:900;flex-shrink:0;}

.disclaimer{background:#fff7ed;border-left:3px solid #f59e0b;padding:14px 18px;font-size:11px;color:#78350f;line-height:1.6;margin-top:36px;}
.disclaimer strong{color:#92400e;}

.footer{margin-top:40px;padding-top:14px;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;font-size:10.5px;color:#94a3b8;}
"""


def cause_row(c, i):
    pct = c.get("contribution", 0)
    conf = c.get("confidence", "")
    conf_cls = "conf-high" if conf == "high" else "conf-mid"
    conf_label = "신뢰도 높음" if conf == "high" else "신뢰도 중간"
    bar_color = "#dc2626" if pct >= 35 else ("#f59e0b" if pct >= 20 else "#2563eb")
    alt = ' class="alt"' if i % 2 == 0 else ""
    desc = (c.get("description") or "")[:90]
    return (
        f'<tr{alt}>'
        f'<td><strong>{c.get("factor","")}</strong>'
        f'{"<br><small style=color:#64748b>" + desc + "</small>" if desc else ""}</td>'
        f'<td style="text-align:center"><strong style="font-size:16px">{pct:.0f}%</strong>'
        f'<div class="prog-bar"><div class="prog-fill" style="width:{pct}%;background:{bar_color}"></div></div></td>'
        f'<td style="text-align:center"><span class="{conf_cls}">{conf_label}</span></td>'
        f'</tr>'
    )


def action_row(a, i):
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
        f'<td style="font-size:11.5px;color:#475569">{(a.get("description") or "")[:90]}</td>'
        f'<td style="font-size:12px;color:#15803d;font-weight:700">{impact_str}</td>'
        f'</tr>'
    )


def render_html(store, state, diagnosis, plan, review_signals=None):
    today = date.today().strftime("%Y년 %m월 %d일")
    causes = diagnosis.causes if diagnosis else []
    actions = plan.actions if plan else []
    rag_refs = plan.rag_references if plan else []

    # ── Cover metrics ──
    cover_metrics = ""
    if state:
        runway_color = "#dc2626" if (state.cash_runway_days or 0) < 20 else ("#f59e0b" if (state.cash_runway_days or 0) < 40 else "#22c55e")
        fin_color = "#22c55e" if (state.finance_readiness or 0) >= 70 else "#60a5fa"
        for v, l in [
            (f"{state.health_score:.0f}", "사업 건강도"),
            (f"{state.cash_runway_days:.0f}일", "현금 유지 기간"),
            (f"{state.finance_readiness:.0f}%", "금융 준비도"),
            (f"{len(actions)}가지", "권장 전략"),
        ]:
            cover_metrics += (
                '<div class="cover-metric">'
                f'<div class="v">{v}</div>'
                f'<div class="l">{l}</div>'
                '</div>'
            )

    # ── State metrics — 한 줄 테이블, 박스 없음 ──
    metrics_html = ""
    if state:
        runway_color = "#dc2626" if (state.cash_runway_days or 0) < 20 else ("#f59e0b" if (state.cash_runway_days or 0) < 40 else "#15803d")
        fin_color = "#15803d" if (state.finance_readiness or 0) >= 70 else "#2563eb"
        liq_color = "#dc2626" if (state.liquidity_risk or 0) >= 70 else ("#f59e0b" if (state.liquidity_risk or 0) >= 40 else "#15803d")
        liq_label = "높음" if (state.liquidity_risk or 0) >= 70 else ("중간" if (state.liquidity_risk or 0) >= 40 else "낮음")
        rev30 = state.detail.get('recent_revenue_30d', 0) or 0
        cost30 = state.detail.get('total_cost_30d', 0) or 0
        metrics_html = (
            '<table class="metrics-row">'
            f'<tr>'
            f'<td><span class="mv">{state.health_score:.0f}</span><span class="ml">사업 건강도 (/100)</span></td>'
            f'<td><span class="mv" style="color:{runway_color}">{state.cash_runway_days:.0f}일</span><span class="ml">현금 유지 기간</span></td>'
            f'<td><span class="mv" style="color:{fin_color}">{state.finance_readiness:.0f}%</span><span class="ml">금융 준비도</span></td>'
            f'<td><span class="mv" style="color:{liq_color}">{liq_label}</span><span class="ml">유동성 위험도</span></td>'
            f'<td><span class="mv">₩{rev30:,.0f}</span><span class="ml">최근 30일 매출</span></td>'
            f'<td><span class="mv">₩{cost30:,.0f}</span><span class="ml">최근 30일 비용</span></td>'
            f'</tr>'
            '</table>'
        )
    else:
        metrics_html = '<p style="color:#94a3b8">진단 데이터가 없습니다.</p>'

    # ── Cause table ──
    if causes:
        cause_table = (
            '<table class="data">'
            '<tr><th style="width:38%">원인 요인 및 설명</th>'
            '<th style="width:22%">기여도</th>'
            '<th style="width:15%">신뢰도</th></tr>'
            + "".join(cause_row(c, i) for i, c in enumerate(causes[:6]))
            + '</table>'
        )
    else:
        cause_table = '<p style="color:#94a3b8">원인 분석 데이터가 없습니다.</p>'

    # ── 요약: 박스 없이 강조 텍스트 ──
    summary_html = ""
    if diagnosis and diagnosis.summary:
        summary_html = f'<p class="summary-plain">{diagnosis.summary}</p>'

    # ── Action table ──
    if actions:
        action_table = (
            '<table class="data">'
            '<tr><th style="width:9%">유형</th>'
            '<th style="width:22%">전략명</th>'
            '<th style="width:44%">실행 내용</th>'
            '<th style="width:25%">예상 효과</th></tr>'
            + "".join(action_row(a, i) for i, a in enumerate(actions[:5]))
            + '</table>'
        )
    else:
        action_table = '<p style="color:#94a3b8">전략 데이터가 없습니다.</p>'

    # ── Finance readiness row ──
    fin_row = ""
    if state:
        runway_days = state.cash_runway_days or 0
        fit_label = "상황 적합" if runway_days < 30 else "검토 가능"
        fin_row = (
            f'<tr><td><strong>단기 운전자금</strong></td>'
            f'<td><span class="fin-fit">{fit_label}</span></td>'
            f'<td style="font-size:11.5px">{runway_days:.0f}일 현금 공백 구간 대응. 한도·금리는 상담에서 확인.</td></tr>'
        )

    rag_note = ""
    if rag_refs:
        titles = " · ".join(r.get("title", "") for r in rag_refs if r.get("title"))
        if titles:
            rag_note = f'<p style="font-size:11px;color:#64748b;margin-top:8px">※ 참고 정책자금: {titles}</p>'

    # ── Review signals ──
    review_html = '<p style="color:#94a3b8;font-size:12px">수집된 리뷰 데이터가 없습니다.</p>'
    if review_signals:
        latest = review_signals[0]
        score_pct = int((latest.sentiment_score + 1) * 50) if latest.sentiment_score is not None else 50
        score_color = "#15803d" if score_pct >= 65 else ("#f59e0b" if score_pct >= 40 else "#dc2626")
        neg_kws = ", ".join(latest.negative_keywords[:5]) if latest.negative_keywords else "없음"
        pos_kws = ", ".join(latest.positive_keywords[:5]) if latest.positive_keywords else "없음"
        review_html = (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0">'
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;padding:16px">'
            '<div style="font-size:10.5px;font-weight:700;color:#64748b;margin-bottom:6px">최근 감성 점수</div>'
            f'<div style="font-size:28px;font-weight:900;color:{score_color}">{score_pct}</div>'
            f'<div style="font-size:10px;color:#94a3b8">/100 · 리뷰 {latest.review_count or 0}건</div>'
            f'<div class="prog-bar" style="margin-top:10px"><div class="prog-fill" style="width:{score_pct}%;background:{score_color}"></div></div>'
            '</div>'
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;padding:16px">'
            '<div style="font-size:10.5px;font-weight:700;color:#15803d;margin-bottom:4px">긍정 키워드</div>'
            f'<div style="font-size:12px;color:#374151;margin-bottom:10px">{pos_kws}</div>'
            '<div style="font-size:10.5px;font-weight:700;color:#dc2626;margin-bottom:4px">부정 키워드</div>'
            f'<div style="font-size:12px;color:#374151">{neg_kws}</div>'
            '</div>'
            '</div>'
        )
        if latest.business_signal:
            review_html += (
                f'<div style="font-size:12px;color:#475569;background:#fff7ed;border-left:3px solid #f59e0b;'
                f'padding:10px 14px;border-radius:0 6px 6px 0;margin-top:8px">{latest.business_signal}</div>'
            )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>{CSS}</style>
</head>
<body>

<div class="cover">
  <!-- 로고 상단 -->
  <div class="cover-logo">
    {LOGO_SVG}
    <div>
      <div class="cover-brand">BizPlot Agent</div>
      <div class="cover-sub">소상공인 AI CFO Platform · JB금융그룹 Fin:AI Challenge</div>
    </div>
  </div>

  <!-- 가운데 정렬 타이틀 -->
  <div class="cover-center">
    <div class="cover-eyebrow">상담 준비 리포트</div>
    <div class="cover-title">{store.name}</div>
    <div class="cover-subtitle">업종: {store.category} &nbsp;·&nbsp; {store.address or "위치 미입력"}</div>
    <div class="cover-meta">생성일: {today}</div>
  </div>

  <!-- 하단 지표 -->
  <div class="cover-divider"></div>
  <div class="cover-metrics">{cover_metrics}</div>
</div>

<div class="content">

  <h2>1. 사업 상태 요약</h2>
  {metrics_html}

  <h2>2. 매출 하락 원인 분석</h2>
  {summary_html}
  {cause_table}

  <h2>3. 권장 실행 전략</h2>
  {action_table}

  <h2>4. 금융 준비 방향</h2>
  <table class="data">
    <tr><th style="width:24%">금융 옵션</th><th style="width:16%">적합도</th><th>설명</th></tr>
    {fin_row}
    <tr><td><strong>소상공인 정책자금</strong></td>
        <td><span class="fin-rec">검토 권장</span></td>
        <td style="font-size:11.5px">경영안정 정책자금 요건 확인 필요. 중기부 공고 참고.</td></tr>
    <tr class="alt"><td><strong>지역화폐 가맹</strong></td>
        <td><span class="fin-opt">선택 사항</span></td>
        <td style="font-size:11.5px">마케팅 전략과 연계 시 효과적.</td></tr>
  </table>
  {rag_note}

  <h2>5. 고객 리뷰 변화 분석</h2>
  {review_html}

  <h2>6. 상담 시 확인 질문 목록</h2>
  <ul class="question-list">
    <li>단기 운전자금 대출 가능 한도 및 금리 조건은 어떻게 되나요?</li>
    <li>소상공인 경영안정 정책자금 신청 자격 요건은 무엇인가요?</li>
    <li>현금흐름 개선을 위한 분할상환 또는 유예 옵션이 있나요?</li>
    <li>지역화폐 가맹 시 추가 혜택이나 마케팅 지원이 있나요?</li>
    <li>사업 상태 데이터를 기반으로 상담 가능한 전담 담당자를 연결받을 수 있나요?</li>
  </ul>

  <div class="disclaimer">
    <strong>중요 안내</strong><br>
    본 리포트는 AI가 자동 생성한 참고 자료이며 법적 효력이 없습니다.
    특정 금융상품 가입을 권유하거나 보장하지 않습니다.
    최종 금융 판단은 금융기관 담당자와의 상담 및 심사 절차를 통해 이루어집니다.
  </div>

  <div class="footer">
    <span>BizPlot Agent · 소상공인 AI CFO Platform</span>
    <span>생성일: {today} · JB금융그룹 Fin:AI Challenge</span>
  </div>
</div>
</body></html>"""


def main():
    db = SessionLocal()
    try:
        stores = db.query(Store).all()
        if not stores:
            print("저장된 사업장이 없습니다.")
            return

        for store in stores:
            print(f"생성 중: {store.name} ...", end=" ")
            state = db.query(BusinessState).filter(
                BusinessState.store_id == store.id
            ).order_by(BusinessState.computed_at.desc()).first()

            diagnosis = db.query(Diagnosis).filter(
                Diagnosis.store_id == store.id
            ).order_by(Diagnosis.created_at.desc()).first()

            plan = db.query(ActionPlan).filter(
                ActionPlan.store_id == store.id
            ).order_by(ActionPlan.created_at.desc()).first()

            review_signals = db.query(ReviewSignal).filter(
                ReviewSignal.store_id == store.id
            ).order_by(ReviewSignal.period_end.desc()).limit(6).all()

            html = render_html(store, state, diagnosis, plan, review_signals)

            safe_name = store.name.replace(" ", "_").replace("/", "-")
            out_path = os.path.join(OUTPUT_DIR, f"report_{safe_name}.pdf")

            try:
                from weasyprint import HTML
                HTML(string=html, base_url="/").write_pdf(out_path)
                print(f"✓ {out_path}")
            except Exception as e:
                # Fallback: save HTML
                html_path = out_path.replace(".pdf", ".html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                os.rename(html_path, out_path)
                print(f"✓ (HTML fallback) {out_path}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
