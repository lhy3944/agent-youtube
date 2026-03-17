import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using OpenAI API."""
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
    return [item.embedding for item in response.data]


async def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query."""
    results = await embed_texts([query])
    return results[0]
