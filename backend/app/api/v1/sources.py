"""
Source API 라우터.

엔드포인트:
- POST /sources/youtube  : YouTube URL로 소스 등록 (중복 URL은 기존 소스 반환)
- GET  /sources/{id}     : 소스 상태/메타데이터/진행률 조회
- GET  /sources/{id}/segments : 세그먼트 목록 조회 (디버깅/관리용)
"""

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
    """YouTube URL을 소스로 등록한다.

    1. URL 유효성 검증 → videoId 추출
    2. 동일 videoId로 이미 등록된 소스가 있으면 기존 소스 반환 (중복 방지)
    3. Source + IngestJob 레코드 생성
    4. Celery 워커에 비동기 Ingest 태스크 디스패치
    """
    url_str = str(body.url)
    if not validate_youtube_url(url_str):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    video_id = extract_video_id(url_str)

    # 중복 등록 방지: 동일 videoId의 기존 소스가 있으면 해당 소스 반환
    stmt = select(Source).where(Source.external_id == video_id, Source.type == "youtube")
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return SourceCreateResponse(source_id=existing.id, status=existing.status)

    # 새 소스 레코드 생성
    source = Source(
        type="youtube",
        status="pending",
        original_url=url_str,
        external_id=video_id,
    )
    db.add(source)
    await db.flush()  # ID 생성을 위해 flush (아직 commit 하지 않음)

    # Ingest 작업 추적용 Job 레코드 생성
    job = IngestJob(source_id=source.id, status="pending", step="queued", progress=0)
    db.add(job)
    await db.commit()

    # Celery 워커에 비동기 Ingest 태스크 전달
    ingest_youtube_source.delay(str(source.id), str(job.id))

    return SourceCreateResponse(source_id=source.id, status="pending")


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """소스의 상태, 메타데이터, 처리 진행률을 조회한다.

    프론트엔드에서 processing 상태일 때 2초 간격으로 polling하여
    진행률(step, percent)을 실시간으로 표시한다.
    """
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 가장 최근 IngestJob에서 진행 상황 가져오기
    stmt = (
        select(IngestJob)
        .where(IngestJob.source_id == source_id)
        .order_by(IngestJob.created_at.desc())
        .limit(1)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()

    # 아직 처리 중인 경우에만 progress 정보를 응답에 포함
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
    """소스의 자막 세그먼트 목록을 순서대로 조회한다. (디버깅/관리자 확인용)"""
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
