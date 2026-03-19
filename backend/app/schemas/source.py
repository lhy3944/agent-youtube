"""
Source 관련 요청/응답 Pydantic 스키마.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class YouTubeSourceCreate(BaseModel):
    """YouTube 소스 등록 요청 바디. URL은 Pydantic이 자동으로 유효성 검증한다."""
    url: HttpUrl


class SourceProgress(BaseModel):
    """Ingest 파이프라인 진행 상황. 현재 단계(step)와 진행률(percent)을 포함한다."""
    step: str | None = None
    percent: int | None = None


class SourceResponse(BaseModel):
    """소스 상세 조회 응답. 메타데이터, 처리 상태, 요약, 진행률 등 모든 정보를 포함한다."""
    id: UUID
    type: str
    status: str  # pending, processing, ready, partial_ready, failed
    original_url: str
    external_id: str  # YouTube videoId
    title: str | None = None
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_sec: int | None = None
    language: str | None = None
    transcript_source: str | None = None  # "caption" 또는 "stt"
    summary: str | None = None
    error_message: str | None = None
    progress: SourceProgress | None = None  # processing 상태일 때만 포함
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # ORM 모델 → Pydantic 모델 자동 변환 허용


class SourceCreateResponse(BaseModel):
    """소스 등록 응답. 생성된 소스 ID와 초기 상태를 반환한다."""
    source_id: UUID
    status: str
