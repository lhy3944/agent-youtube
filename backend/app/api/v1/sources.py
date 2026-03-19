"""
Source API 라우터.

엔드포인트:
- POST /sources/youtube  : YouTube URL로 소스 등록 (중복 URL은 기존 소스 반환)
- GET  /sources/{id}     : 소스 상태/메타데이터/진행률 조회
- GET  /sources/{id}/segments : 세그먼트 목록 조회 (디버깅/관리용)
"""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "/youtube",
    response_model=SourceCreateResponse,
    status_code=201,
    summary="YouTube URL로 소스 등록",
    responses={
        201: {"description": "소스 등록 성공. 동일 URL이 이미 등록된 경우 기존 소스 정보를 반환한다."},
        400: {"description": "유효하지 않은 YouTube URL"},
    },
)
async def create_youtube_source(
    body: YouTubeSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """YouTube URL을 소스로 등록하고 비동기 Ingest 파이프라인을 시작한다.

    - URL에서 videoId를 추출하고 유효성을 검증한다
    - 동일 videoId가 이미 등록되어 있으면 기존 소스의 ID와 상태를 반환한다 (중복 방지)
    - 새 소스인 경우 Source + IngestJob 레코드를 생성하고 Celery 워커에 처리를 위임한다
    - 응답은 즉시 반환되며, 실제 처리는 백그라운드에서 비동기로 진행된다
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
    # Redis 연결 실패 시에도 소스 등록 자체는 성공하도록 예외 처리
    try:
        from app.worker.tasks import ingest_youtube_source
        ingest_youtube_source.delay(str(source.id), str(job.id))
    except Exception as e:
        logger.error(f"Failed to dispatch ingest task (Redis may be down): {e}")
        # 태스크 디스패치 실패 시 소스 상태를 failed로 업데이트
        source.status = "failed"
        source.error_message = f"Task dispatch failed: {e}"
        job.status = "failed"
        job.error_message = str(e)
        await db.commit()

    return SourceCreateResponse(source_id=source.id, status=source.status)


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    summary="소스 상태 및 메타데이터 조회",
    responses={
        200: {"description": "소스 상세 정보 (메타데이터, 상태, 진행률, 요약 포함)"},
        404: {"description": "소스를 찾을 수 없음"},
    },
)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """소스의 상태, 메타데이터, 처리 진행률을 조회한다.

    - processing 상태일 때 progress 필드에 현재 단계(step)와 진행률(percent)이 포함된다
    - 프론트엔드에서 2초 간격으로 polling하여 실시간 진행 상황을 표시하는 데 사용된다
    - ready/partial_ready 상태에서는 summary가 포함될 수 있다
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


@router.get(
    "/{source_id}/segments",
    response_model=list[SegmentResponse],
    summary="세그먼트 목록 조회 (디버깅용)",
    responses={
        200: {"description": "세그먼트 목록 (segment_index 순)"},
        404: {"description": "소스를 찾을 수 없음"},
    },
)
async def get_segments(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """소스의 자막 세그먼트 목록을 순서대로 조회한다.

    디버깅 및 관리자 확인용. 각 세그먼트의 텍스트, 타임스탬프, 토큰 수를 반환한다.
    임베딩 벡터는 응답에 포함되지 않는다.
    """
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
