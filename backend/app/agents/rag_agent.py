"""
RAG Agent
pgvector에서 정책자금·상담 가이드·소상공인 지원사업 문서 검색

검색 전략:
1. 벡터 검색 (pgvector + sentence-transformers) — torch 정상 시 우선
2. 한국어 키워드 기반 검색 — torch 장애 시 fallback (BM25 유사 스코어링)
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.agent import RagDocument

logger = logging.getLogger(__name__)

# 업종(영문 category) → 한국어 검색 키워드 매핑
_CATEGORY_KEYWORDS = {
    "cafe": ["카페", "커피", "음식점", "소상공인", "운전자금", "경영안정"],
    "restaurant": ["음식점", "외식", "소상공인", "운전자금", "경영안정"],
    "bakery": ["제과", "베이커리", "음식점", "소상공인", "운전자금"],
    "beauty": ["미용", "뷰티", "소상공인", "운전자금", "경영안정"],
    "retail": ["소매", "도소매", "소상공인", "운전자금", "경영안정"],
    "laundry": ["세탁", "소상공인", "운전자금"],
}

# 진단 맥락에서 항상 함께 노출하고 싶은 핵심 주제 키워드
_BASE_KEYWORDS = ["소상공인", "정책자금", "운전자금", "경영안정", "현금흐름", "보증"]


def search_policy_docs(category: str, db: Session, top_k: int = 5) -> list[dict]:
    """
    카테고리와 관련된 정책자금·상담 가이드 문서를 검색합니다.
    벡터 검색 실패(torch 장애 등) 시 한국어 키워드 검색으로 자동 폴백합니다.
    """
    # 영문 category를 한국어 질의로 변환
    keywords = _CATEGORY_KEYWORDS.get(category, [category]) + _BASE_KEYWORDS
    query_text = " ".join(dict.fromkeys(keywords))  # 중복 제거, 순서 유지

    try:
        results = _vector_search(query_text, db, top_k)
        if results:
            return results
        logger.info("Vector search returned 0 docs, using keyword fallback")
    except Exception as e:
        logger.warning(f"Vector search unavailable ({type(e).__name__}), using keyword fallback")
    return _keyword_search(keywords, db, top_k)


def _vector_search(query: str, db: Session, top_k: int) -> list[dict]:
    from app.services.embedding import get_embedding
    query_vec = get_embedding(query)
    vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"
    rows = db.execute(
        text(
            f"""
            SELECT id, title, content, source, url,
                   embedding <=> '{vec_str}'::vector AS distance
            FROM rag_documents
            ORDER BY distance
            LIMIT :k
            """
        ),
        {"k": top_k},
    ).fetchall()
    return [
        {"id": str(r.id), "title": r.title, "content": r.content[:300], "source": r.source, "url": r.url}
        for r in rows
    ]


def _keyword_search(keywords: list[str], db: Session, top_k: int) -> list[dict]:
    """
    torch 없이 동작하는 한국어 키워드 검색.
    제목 가중치 3, 본문 키워드 빈도 1로 스코어링하여 상위 문서를 반환한다.
    """
    docs = db.query(RagDocument).all()
    scored = []
    for d in docs:
        title = d.title or ""
        content = d.content or ""
        score = 0.0
        for kw in keywords:
            if kw in title:
                score += 3.0
            score += content.count(kw) * 1.0
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"id": str(d.id), "title": d.title, "content": d.content[:300], "source": d.source, "url": d.url}
        for _, d in scored[:top_k]
    ]


# 하위 호환용 별칭
def _text_search(query: str, db: Session, top_k: int) -> list[dict]:
    return _keyword_search([query], db, top_k)


def get_jb_products(db: Session) -> list[dict]:
    """JB금융그룹 금융 상품 문서를 직접 반환 (RAG 검색 없이 source 필터)."""
    docs = (
        db.query(RagDocument)
        .filter(RagDocument.source.in_(["jb", "jbbank"]))
        .all()
    )
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "content": d.content,
            "source": d.source,
            "url": d.url,
        }
        for d in docs
    ]


def add_document(
    source: str, title: str, content: str, url: str | None, db: Session
) -> RagDocument:
    from app.services.embedding import get_embedding
    embedding = get_embedding(content[:512])

    doc = RagDocument(
        source=source,
        title=title,
        content=content,
        url=url,
        metadata_={"source": source},
    )
    db.add(doc)
    db.flush()

    # Update embedding column directly via SQL
    # Use string formatting for the vector literal (not a parameter) to avoid :: cast conflict
    vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
    doc_id = str(doc.id)
    db.execute(
        text(f"UPDATE rag_documents SET embedding = '{vec_str}'::vector WHERE id = :id"),
        {"id": doc_id},
    )
    db.commit()
    db.refresh(doc)
    return doc
