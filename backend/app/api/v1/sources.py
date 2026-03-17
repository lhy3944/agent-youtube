import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ingest_job import IngestJob
from app.models.source import Source
from app.models.transcript_segment import TranscriptSegment
from app.schemas.segment import SegmentResponse
from app.schemas.source import (
    SourceCreateResponse,
    SourceProgress,
    SourceResponse,
    YouTubeSourceCreate,
)
from app.services.youtube import extract_video_id, validate_youtube_url
from app.worker.tasks import ingest_youtube_source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/youtube", response_model=SourceCreateResponse, status_code=201)
async def create_youtube_source(
    body: YouTubeSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    url_str = str(body.url)
    if not validate_youtube_url(url_str):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    video_id = extract_video_id(url_str)

    # Check for duplicate
    stmt = select(Source).where(Source.external_id == video_id, Source.type == "youtube")
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return SourceCreateResponse(source_id=existing.id, status=existing.status)

    source = Source(
        type="youtube",
        status="pending",
        original_url=url_str,
        external_id=video_id,
    )
    db.add(source)
    await db.flush()

    job = IngestJob(source_id=source.id, status="pending", step="queued", progress=0)
    db.add(job)
    await db.commit()

    # Dispatch async ingest task
    ingest_youtube_source.delay(str(source.id), str(job.id))

    return SourceCreateResponse(source_id=source.id, status="pending")


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Get latest ingest job progress
    stmt = (
        select(IngestJob)
        .where(IngestJob.source_id == source_id)
        .order_by(IngestJob.created_at.desc())
        .limit(1)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()

    progress = None
    if job and job.status != "completed":
        progress = SourceProgress(step=job.step, percent=job.progress)

    response = SourceResponse.model_validate(source)
    response.progress = progress
    return response


@router.get("/{source_id}/segments", response_model=list[SegmentResponse])
async def get_segments(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.source_id == source_id)
        .order_by(TranscriptSegment.segment_index)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
