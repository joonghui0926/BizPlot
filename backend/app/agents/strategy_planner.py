"""
Strategy Planner — LLM-first
파인튜닝된 Qwen이 진단 결과를 보고 맞춤 전략을 생성.
LLM 실패 시 규칙 기반으로 폴백.
"""
import json
import re
import uuid
import logging
from sqlalchemy.orm import Session

from app.models.store import Store
from app.models.agent import BusinessState, Diagnosis, ActionPlan
from app.services.llm_client import call_llm
from app.agents.rag_agent import search_policy_docs

logger = logging.getLogger(__name__)

RISK_PHRASES = [
    "반드시 가입", "확실히 승인", "보장된 대출", "무조건 대출",
    "바로 신청", "즉시 지원", "100% 승인", "무조건 지원",
]


def generate_action_plan(
    store: Store, state: BusinessState, diagnosis: Diagnosis, db: Session
) -> ActionPlan:
    rag_refs = search_policy_docs(store.category, db)
    causes = diagnosis.causes or []

    # ── LLM-first ────────────────────────────────────────────────────────────
    actions = []
    try:
        actions = _llm_strategies(store, state, diagnosis, rag_refs)
        if not actions or len(actions) < 3:
            logger.warning("LLM strategy output thin, supplementing with rules")
            actions = _supplement_with_rules(actions, state, diagnosis)
    except Exception as e:
        logger.warning(f"LLM strategy failed ({e}), using rule-based")
        actions = _rule_based_actions(state, diagnosis)

    # 최소 5개 보장
    if len(actions) < 5:
        actions = _supplement_with_rules(actions, state, diagnosis)

    # ID 보장 + 우선순위 정렬 + Risk 검증
    for a in actions:
        if "id" not in a or not a["id"]:
            a["id"] = str(uuid.uuid4())
    actions.sort(key=lambda a: a.get("priority", 9))
    actions, risk_flags = _verify_actions(actions)
    actions = actions[:7]

    # XAI: 각 전략이 "왜 그만큼의 효과를 낼 것으로 기대되는지"를 Qwen이 진단
    # 데이터(원인·증거·매출 금액) 기반으로 직접 서술. 실패해도 프론트가 결정론
    # 설명으로 폴백하므로 전략 생성 자체는 막지 않는다.
    _attach_rationales(store, state, diagnosis, actions)

    plan = ActionPlan(
        store_id=store.id,
        diagnosis_id=diagnosis.id,
        actions=actions,
        rag_references=rag_refs[:3],
        verified="passed" if not risk_flags else "flagged",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _llm_strategies(store, state, diagnosis, rag_refs) -> list:
    causes = diagnosis.causes or []
    top_causes = "\n".join(
        f"  - {c['factor']} ({c['contribution']:.0f}%, {c['confidence']}): {c.get('description','')}"
        for c in causes[:5]
    )
    rag_info = ""
    if rag_refs:
        titles = ", ".join(r.get("title", "") for r in rag_refs[:3] if r.get("title"))
        if titles:
            rag_info = f"\n[활용 가능 정책자금]\n{titles}"

    prompt = f"""{store.category} '{store.name}' 사업 상황:
- 건강도: {state.health_score:.0f}/100
- 매출 추세: {state.revenue_trend*100:+.1f}%
- 현금 유지: {state.cash_runway_days:.0f}일
- 비용 압박: {state.cost_pressure:.0f}/100
- 금융 준비도: {state.finance_readiness:.0f}%

[주요 원인]
{top_causes}
{rag_info}

위 상황에 맞는 실행 전략 5~7개를 JSON으로 출력하세요 (다른 텍스트 없이):
[
  {{
    "type": "operation|marketing|finance",
    "title": "전략명 (20자 이내)",
    "description": "구체적 실행 방법 (40자 이내, 데이터 근거 포함)",
    "priority": 1~5,
    "expected_impact": {{
      "cash_runway_days_delta": 숫자(없으면 생략),
      "revenue_change_pct": 숫자(없으면 생략),
      "cost_change_pct": 숫자(없으면 생략),
      "finance_readiness_delta": 숫자(없으면 생략)
    }}
  }}
]

요구사항:
- operation/marketing/finance 균형 있게 포함
- 금융상품 단정 추천 금지 (상담·검토·준비 표현만)
- expected_impact 수치는 현실적으로"""

    system = "너는 소상공인의 금융 운영을 설계하는 AI CFO Agent이다. 데이터 기반 실행 전략을 JSON으로만 출력한다."
    response = call_llm(prompt, system=system, max_tokens=1000)
    return _parse_action_json(response)


# ── XAI 근거 서술 (Qwen이 진단 데이터 위에서 전략별로 직접 설명) ──────────────────
def _attach_rationales(store, state, diagnosis, actions: list) -> None:
    """각 action dict에 rationale(list[str])를 채운다(in-place). LLM 실패 시 미부착."""
    if not actions:
        return
    try:
        rationales = _llm_strategy_rationales(store, state, diagnosis, actions)
    except Exception as e:
        logger.warning(f"LLM rationale failed ({e}); frontend will fall back to deterministic XAI")
        rationales = {}

    for idx, a in enumerate(actions, start=1):
        raw = rationales.get(str(idx)) or rationales.get(idx) or []
        if isinstance(raw, str):
            raw = [raw]
        clean = [str(l).strip() for l in raw if isinstance(l, str) and len(str(l).strip()) >= 8]
        # 중복 문장 제거(같은 전략 안에서)
        seen, deduped = set(), []
        for l in clean:
            if l not in seen:
                seen.add(l)
                deduped.append(l)
        if len(deduped) >= 3:        # 충분할 때만 부착 (아니면 프론트 폴백)
            a["rationale"] = deduped[:7]


def _llm_strategy_rationales(store, state, diagnosis, actions: list) -> dict:
    causes = diagnosis.causes or []

    cause_lines = []
    for c in causes[:5]:
        ev = c.get("evidence") or []
        ev_txt = "; ".join(
            f"{e.get('label','')}({e.get('when','')} · {e.get('mechanism','')})"
            for e in ev[:3] if e.get("label")
        )
        cause_lines.append(
            f"  - {c.get('factor')} 기여도 {float(c.get('contribution', 0)):.0f}%"
            + (f" | 증거: {ev_txt}" if ev_txt else f" | {c.get('description','')}")
        )
    causes_block = "\n".join(cause_lines) or "  - (원인 데이터 없음)"

    detail = state.detail or {}
    recent = detail.get("recent_revenue_30d")
    prior = detail.get("prior_revenue_30d")
    rev_block = ""
    if recent is not None:
        rev_block = f"- 최근 30일 매출: {recent:,.0f}원"
        if prior is not None:
            rev_block += f" (이전 30일: {prior:,.0f}원)"

    action_lines = []
    for idx, a in enumerate(actions, start=1):
        imp = a.get("expected_impact", {}) or {}
        parts = []
        if imp.get("revenue_change_pct"):
            parts.append(f"매출 {imp['revenue_change_pct']:+g}%")
        if imp.get("cost_change_pct"):
            parts.append(f"비용 {imp['cost_change_pct']:+g}%")
        if imp.get("cash_runway_days_delta"):
            parts.append(f"현금 +{imp['cash_runway_days_delta']:g}일")
        if imp.get("finance_readiness_delta"):
            parts.append(f"금융준비 +{imp['finance_readiness_delta']:g}p")
        imp_txt = ", ".join(parts) or "효과 미지정"
        action_lines.append(f"{idx}. [{a.get('type')}] {a.get('title')} — {a.get('description')} (기대효과: {imp_txt})")
    actions_block = "\n".join(action_lines)

    prompt = f"""{store.category} '{store.name}'의 진단 결과와 추천 전략이다.

[사업 상태]
- 매출 추세: {state.revenue_trend*100:+.1f}%
- 현금 유지: {state.cash_runway_days:.0f}일
- 비용 압박: {state.cost_pressure:.0f}/100
{rev_block}

[진단된 매출 변화 원인 (기여도·증거)]
{causes_block}

[추천 전략]
{actions_block}

각 전략에 대해 '왜 이 전략이 그만큼의 효과를 낼 것으로 기대되는지'를 설명하는 근거를 5~6줄씩 작성하라.
줄마다 서로 다른 관점을 담되 다음을 빠짐없이 반영한다:
1) 이 전략이 위 진단 원인 중 무엇을 공략하는지 + 그 원인의 기여도(%)
2) 과거 데이터/증거에서의 구체적 근거 (위에 제시된 수치를 인용)
3) 그 행동이 매출·비용·현금을 움직이는 메커니즘
4) 기대효과 수치를 위 매출 금액 기준으로 환산한 산출 (예: 매출 +8% ≈ 월 약 OOO원)
5) 그 수치가 현실적이라고 보는 이유
6) 적용 후 무엇을 보고 효과를 검증할지

[엄수]
- 전략끼리 같은 문장·표현을 반복하지 말 것. 전략마다 다른 데이터·이유를 사용하라.
- 위에 주어진 숫자만 사용하고 새로운 수치를 지어내지 말 것.
- 한국어로 작성하고, 각 줄은 한 문장으로 끝낸다.
- 아래 JSON 형식으로만 출력한다(다른 텍스트 없이). 전략 번호 1~{len(actions)}을 모두 포함하라:
{{
  "1": ["근거 문장1", "근거 문장2", "근거 문장3", "근거 문장4", "근거 문장5"],
  "2": ["근거 문장1", "근거 문장2", "근거 문장3", "근거 문장4", "근거 문장5"]
}}"""

    system = "너는 소상공인 AI CFO Agent이다. 데이터에 근거해 전략의 기대효과를 반복 없이 설명하고, 지정된 JSON으로만 출력한다."
    # 전략 수×5~6줄 분량 → JSON 중간 truncation 시 파싱 실패로 전체 폴백되므로 여유있게.
    response = call_llm(prompt, system=system, max_tokens=3000)
    return _parse_rationale_json(response)


def _parse_rationale_json(text: str) -> dict:
    if not text or not text.strip():
        return {}
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```", r"(\{.*\})"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return {}


def _parse_action_json(text: str) -> list:
    if not text or not text.strip():
        return []
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```", r"(\[.*\])"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1))
                if isinstance(result, list):
                    return _normalize_actions(result)
            except json.JSONDecodeError:
                continue
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return _normalize_actions(result)
    except json.JSONDecodeError:
        pass
    return []


def _normalize_actions(actions: list) -> list:
    valid = []
    type_map = {"operation": "operation", "marketing": "marketing", "finance": "finance",
                "운영": "operation", "마케팅": "marketing", "금융": "finance"}
    for a in actions:
        if not isinstance(a, dict):
            continue
        t = type_map.get(a.get("type", ""), "operation")
        title = str(a.get("title", "")).strip()
        desc = str(a.get("description", "")).strip()
        if not title:
            continue
        impact = a.get("expected_impact", {}) or {}
        clean_impact = {}
        for k in ["cash_runway_days_delta", "revenue_change_pct", "cost_change_pct", "finance_readiness_delta"]:
            if k in impact and impact[k] is not None:
                try:
                    clean_impact[k] = float(impact[k])
                except (TypeError, ValueError):
                    pass
        valid.append({
            "id": str(uuid.uuid4()),
            "type": t,
            "title": title[:40],
            "description": desc[:100],
            "priority": int(a.get("priority", 3)),
            "expected_impact": clean_impact,
        })
    return valid


def _supplement_with_rules(existing: list, state: BusinessState, diagnosis: Diagnosis) -> list:
    existing_titles = {a["title"] for a in existing}
    causes_text = " ".join(c.get("factor", "") for c in (diagnosis.causes or []))
    additions = []

    def add(type_, title, desc, priority, **impact):
        if title not in existing_titles:
            additions.append({
                "id": str(uuid.uuid4()),
                "type": type_,
                "title": title,
                "description": desc,
                "priority": priority,
                "expected_impact": {k: v for k, v in impact.items() if v},
            })
            existing_titles.add(title)

    # 운영
    if state.cost_pressure and state.cost_pressure > 45:
        add("operation", "원재료 발주량 최적화",
            "주간 판매량 기반 발주 조정으로 변동비 절감",
            1, cash_runway_days_delta=6, cost_change_pct=-10)
    if "오후" in causes_text or "시간대" in causes_text:
        add("operation", "시간대별 인력 배치 재조정",
            "피크·비피크 시간대 인력 탄력 운영",
            2, cost_change_pct=-8)
    if "객단가" in causes_text or "거래" in causes_text:
        add("operation", "세트 메뉴 구성으로 객단가 향상",
            "추가 사이드 옵션 묶음으로 1인당 구매액 증가",
            3, revenue_change_pct=6)

    # 마케팅
    if state.revenue_trend and state.revenue_trend < -0.03:
        add("marketing", "평일 오후 재방문 쿠폰 발행",
            "14-17시 매출 하락 시간대 재방문 유도",
            1, revenue_change_pct=8)
    if "경쟁" in causes_text:
        add("marketing", "차별화 SNS 콘텐츠 강화",
            "경쟁 점포 대비 강점을 콘텐츠로 제작",
            2, revenue_change_pct=5)
    add("marketing", "단골 스탬프·포인트 프로그램 도입",
        "재방문 빈도 하락 대응 로열티 프로그램",
        3, revenue_change_pct=7)

    # 금융
    if state.finance_readiness and state.finance_readiness < 70:
        add("finance", "상담 준비 리포트 생성",
            "매출·비용·현금흐름 데이터 기반 상담 자료 준비",
            1, finance_readiness_delta=20)
    if state.cash_runway_days and state.cash_runway_days < 45:
        add("finance", "단기 운전자금 상담 준비",
            f"현금 유지 {state.cash_runway_days:.0f}일 기준 운전자금 옵션 사전 검토",
            2, cash_runway_days_delta=30)
    add("finance", "소상공인 정책자금 사전 조회",
        "경영안정자금 신청 요건 확인 (중기부 공고 연계)",
        3, finance_readiness_delta=10)

    return existing + additions


def _rule_based_actions(state: BusinessState, diagnosis: Diagnosis) -> list:
    return _supplement_with_rules([], state, diagnosis)


def _verify_actions(actions: list) -> tuple[list, list]:
    risk_flags = []
    clean = []
    for a in actions:
        text = (a.get("description", "") + a.get("title", ""))
        flags = [p for p in RISK_PHRASES if p in text]
        if flags:
            risk_flags.append({"action_title": a.get("title"), "flags": flags})
            for p in flags:
                a["description"] = a["description"].replace(p, "[전문가 상담 필요]")
        clean.append(a)
    return clean, risk_flags
