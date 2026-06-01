"""
LLM 클라이언트
Primary: vLLM (Qwen3.6-27B via SSH tunnel)
Fallback 1: 외부 OpenAI-compatible API
Fallback 2: 규칙 기반 응답
"""
import logging
import re
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── 중국어(한자) 후처리 ────────────────────────────────────────────────────────
# Qwen(중국어권 베이스) 파인튜닝 모델은 한국어 출력 중간에 한자(漢字)나 중국어
# 전각 문장부호를 섞어내는 잔재가 있다. 출력은 한글·영문·숫자·한국어 문장부호로만
# 구성돼야 하므로 한자 계열 코드포인트를 제거한다. (JSON 키/값은 ASCII·한글이라
# 파싱 전에 적용해도 구조가 깨지지 않는다.)
_HANZI_RE = re.compile(
    "["
    "㐀-䶿"          # CJK 확장 A
    "一-鿿"          # CJK 기본 한자
    "豈-﫿"          # CJK 호환 한자
    "\U00020000-\U0002FA1F"  # CJK 확장 B~ (희귀 한자)
    "]"
)
# 중국어 전각 문장부호 → 한국어/ASCII 대응 (그냥 지우면 문장이 붙어버려서 치환)
_CJK_PUNCT = {
    "，": ", ", "、": ", ", "。": ". ", "；": "; ", "：": ": ",
    "？": "? ", "！": "! ", "（": " (", "）": ") ",
    "「": "‘", "」": "’", "『": "“", "』": "”",
    "％": "%", "～": "~", "　": " ", "·": "·",
}


def strip_chinese(text: str) -> str:
    """LLM 출력에서 한자·중국어 전각 문장부호를 제거한다. (한국어 응답 보장용 필수 후처리)"""
    if not text:
        return text
    for zh, ko in _CJK_PUNCT.items():
        text = text.replace(zh, ko)
    text = _HANZI_RE.sub("", text)
    # 한자 단어가 통째로 지워지며 남은 빈 괄호/따옴표쌍 제거
    text = re.sub(r"[(\[‘“]\s*[)\]’”]", "", text)
    # 여는 괄호 뒤 / 닫는 괄호·문장부호 앞의 잉여 공백 정리
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+([)\]”’.,!?;:%])", r"\1", text)
    # 한자 삭제로 생긴 잉여 공백 정리
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    return text.strip()


def call_llm(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    max_tokens = max_tokens or settings.LLM_MAX_TOKENS
    if system is None:
        system = "너는 소상공인의 금융 운영을 설계하는 AI CFO Agent이다. 정확하고 근거 있는 정보만 제공한다."

    # Primary: vLLM
    try:
        return strip_chinese(_call_vllm(prompt, system, max_tokens))
    except Exception as e:
        logger.warning(f"vLLM call failed: {e}")

    # Fallback 1: external API
    if settings.FALLBACK_LLM_API_KEY:
        try:
            return strip_chinese(_call_fallback(prompt, system, max_tokens))
        except Exception as e:
            logger.warning(f"Fallback LLM call failed: {e}")

    # Fallback 2: rule-based
    return _rule_response(prompt)


def _call_vllm(prompt: str, system: str, max_tokens: int) -> str:
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
        timeout=30,
    )
    return response.choices[0].message.content or ""


def _call_fallback(prompt: str, system: str, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.FALLBACK_LLM_API_KEY)
    response = client.chat.completions.create(
        model=settings.FALLBACK_LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def _rule_response(prompt: str) -> str:
    return "[]"  # 빈 JSON 배열 (전략 보강 없음, 규칙 기반만 사용)
