import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.ingest_job import IngestJob
from app.models.source import Source
from app.models.transcript_segment import TranscriptSegment
from app.services.answer import generate_summary
from app.services.chunking import chunk_segments
from app.services.embedding import embed_texts
from app.services.transcript import fetch_captions, normalize_transcript
from app.services.youtube import fetch_video_metadata
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session_factory():
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_ingest(source_id: str, job_id: str):
    factory = _get_async_session_factory()

    async with factory() as db:
        source = await db.get(Source, uuid.UUID(source_id))
        job = await db.get(IngestJob, uuid.UUID(job_id))
        if not source or not job:
            logger.error(f"Source or job not found: {source_id}, {job_id}")
            return

        try:
            # Step 1: Metadata
            job.step = "metadata"
            job.progress = 10
            source.status = "processing"
            await db.commit()

            metadata = await fetch_video_metadata(source.external_id)
            if metadata:
                source.title = metadata.get("title")
                source.channel_title = metadata.get("channel_title")
                source.description = metadata.get("description")
                source.thumbnail_url = metadata.get("thumbnail_url")
                source.duration_sec = metadata.get("duration_sec")
                await db.commit()

            # Step 2: Captions
            job.step = "captions"
            job.progress = 20
            await db.commit()

            raw_segments = fetch_captions(source.external_id)
            if raw_segments is None:
                # STT fallback would go here
                job.step = "stt"
                job.progress = 25
                await db.commit()
                # For now, mark as failed if no captions
                raise ValueError("No captions available and STT not yet implemented")

            source.transcript_source = "caption"

            # Step 3: Normalize
            job.step = "normalize"
            job.progress = 40
            await db.commit()

            normalized = normalize_transcript(raw_segments)
            if not normalized:
                raise ValueError("Transcript normalization produced no segments")

            # Step 4: Chunk
            job.step = "chunk"
            job.progress = 50
            await db.commit()

            chunks = chunk_segments(normalized)

            # Step 5: Embed
            job.step = "embed"
            job.progress = 60
            await db.commit()

            # Batch embed all chunks
            texts = [c["text"] for c in chunks]
            batch_size = 50
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = await embed_texts(batch)
                all_embeddings.extend(embeddings)
                job.progress = 60 + int(20 * (i + len(batch)) / len(texts))
                await db.commit()

            # Save segments with embeddings
            for idx, (chunk, emb) in enumerate(zip(chunks, all_embeddings)):
                segment = TranscriptSegment(
                    source_id=source.id,
                    segment_index=idx,
                    start_sec=chunk["start_sec"],
                    end_sec=chunk["end_sec"],
                    text=chunk["text"],
                    token_count=chunk["token_count"],
                    embedding=emb,
                )
                db.add(segment)

            await db.commit()

            # Step 6: Summary
            job.step = "summary"
            job.progress = 85
            await db.commit()

            # Retrieve saved segments for summary
            stmt = (
                select(TranscriptSegment)
                .where(TranscriptSegment.source_id == source.id)
                .order_by(TranscriptSegment.segment_index)
            )
            result = await db.execute(stmt)
            all_segments = list(result.scalars().all())

            summary = await generate_summary(all_segments)
            if summary:
                source.summary = summary

            # Done
            job.step = "done"
            job.progress = 100
            job.status = "completed"
            source.status = "ready" if summary else "partial_ready"
            await db.commit()

        except Exception as e:
            logger.exception(f"Ingest failed for source {source_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            source.status = "failed"
            source.error_message = str(e)
            await db.commit()


@celery_app.task(name="ingest_youtube_source")
def ingest_youtube_source(source_id: str, job_id: str):
    """Celery task to run the full ingest pipeline."""
    asyncio.run(_run_ingest(source_id, job_id))
