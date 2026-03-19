"""
텍스트 임베딩 생성 서비스.

OpenAI Embeddings API를 사용하여 텍스트를 벡터로 변환한다.
생성된 벡터는 pgvector에 저장되어 코사인 유사도 검색에 사용된다.

싱글턴 패턴으로 AsyncOpenAI 클라이언트를 관리하여
불필요한 클라이언트 재생성을 방지한다.
"""

import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 싱글턴 (최초 호출 시 1회만 생성)
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """OpenAI 클라이언트 싱글턴 인스턴스를 반환한다."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """여러 텍스트에 대한 임베딩 벡터를 일괄 생성한다.

    Ingest 파이프라인에서 청크 텍스트를 배치 처리할 때 사용한다.

    Returns:
        각 텍스트에 대응하는 임베딩 벡터 리스트 (길이: EMBEDDING_DIMENSIONS)
    """
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
    return [item.embedding for item in response.data]


async def embed_query(query: str) -> list[float]:
    """단일 질문 텍스트의 임베딩 벡터를 생성한다.

    사용자 질문을 임베딩하여 벡터 검색에 사용한다.
    """
    results = await embed_texts([query])
    return results[0]
