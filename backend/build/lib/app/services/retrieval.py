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
    """Retrieve the top-k most relevant transcript segments for a question."""
    top_k = top_k or settings.RETRIEVAL_TOP_K

    query_embedding = await embed_query(question)

    # Use pgvector cosine distance operator
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.source_id == source_id)
        .where(TranscriptSegment.embedding.isnot(None))
        .order_by(TranscriptSegment.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
