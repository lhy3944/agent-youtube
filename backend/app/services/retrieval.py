"""
벡터 검색(Retrieval) 서비스.

사용자 질문을 임베딩한 후, pgvector의 코사인 유사도 검색을 통해
해당 영상에서 가장 관련성 높은 자막 세그먼트를 찾는다.

검색 흐름:
1. 질문 텍스트 → 임베딩 벡터 변환
2. TranscriptSegment 테이블에서 동일 source_id의 세그먼트 중
   코사인 거리가 가장 작은(= 유사도가 가장 높은) top-k개를 반환
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.transcript_segment import TranscriptSegment
from app.services.embedding import embed_query


async def retrieve_relevant_segments(
    db: AsyncSession,
    source_id: uuid.UUID,
    question: str,
    top_k: int | None = None,
) -> list[TranscriptSegment]:
    """질문과 가장 관련성 높은 자막 세그먼트를 검색한다.

    Args:
        db: 비동기 DB 세션
        source_id: 검색 대상 소스 ID
        question: 사용자 질문 텍스트
        top_k: 반환할 최대 세그먼트 수 (기본: settings.RETRIEVAL_TOP_K)

    Returns:
        코사인 유사도 기준 상위 k개의 TranscriptSegment 목록
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K

    # 질문 텍스트를 벡터로 변환
    query_embedding = await embed_query(question)

    # pgvector의 cosine_distance 연산자로 유사도 순 정렬
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.source_id == source_id)
        .where(TranscriptSegment.embedding.isnot(None))  # 임베딩이 없는 세그먼트는 제외
        .order_by(TranscriptSegment.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
