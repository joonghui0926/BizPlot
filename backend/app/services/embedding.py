"""임베딩 서비스 — ollama 기반 (torch 비의존)

LLM과 동일하게 ollama(llama.cpp 백엔드)로 임베딩을 생성한다.
bge-m3(1024차원, 한국어 멀티링궐)를 사용하며, torch/sentence-transformers에
의존하지 않으므로 CUDA·nccl 충돌 환경에서도 안정적으로 동작한다.
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_embedding(text: str) -> list[float]:
    """단일 텍스트를 ollama 임베딩 API로 벡터화한다."""
    resp = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": settings.EMBEDDING_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if not embedding:
        raise ValueError(f"ollama embedding 응답에 embedding 없음: {data}")
    return embedding


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """여러 텍스트를 순차 임베딩한다 (ollama는 배치 미지원이므로 루프)."""
    return [get_embedding(t) for t in texts]
