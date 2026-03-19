"""
Source 관련 요청/응답 Pydantic 스키마.

Swagger UI에서 각 필드의 설명, 예시값, 제약조건이 표시되도록
Field를 사용하여 OpenAPI 메타데이터를 명시한다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class YouTubeSourceCreate(BaseModel):
    """YouTube 소스 등록 요청."""

    url: HttpUrl = Field(
        ...,
        description="등록할 YouTube 영상 URL",
        json_schema_extra={"examples": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}]
        }
    }


class SourceProgress(BaseModel):
    """Ingest 파이프라인 진행 상황."""

    step: str | None = Field(
        None,
        description="현재 처리 단계",
        examples=["metadata", "captions", "chunk", "embed", "summary", "done"],
    )
    percent: int | None = Field(None, description="진행률 (0~100)", ge=0, le=100, examples=[72])


class SourceResponse(BaseModel):
    """소스 상세 조회 응답. 메타데이터, 처리 상태, 요약, 진행률 등 모든 정보를 포함한다."""

    id: UUID = Field(..., description="소스 고유 ID")
    type: str = Field(..., description="소스 유형", examples=["youtube"])
    status: str = Field(
        ...,
        description="처리 상태: pending, processing, ready, partial_ready, failed",
        examples=["ready"],
    )
    original_url: str = Field(..., description="사용자가 입력한 원본 URL")
    external_id: str = Field(..., description="YouTube videoId (11자리)", examples=["dQw4w9WgXcQ"])
    title: str | None = Field(None, description="영상 제목")
    channel_title: str | None = Field(None, description="채널명")
    thumbnail_url: str | None = Field(None, description="썸네일 이미지 URL")
    duration_sec: int | None = Field(None, description="영상 길이 (초)", examples=[1234])
    language: str | None = Field(None, description="자막 언어 코드", examples=["ko", "en"])
    transcript_source: str | None = Field(
        None, description="자막 출처", examples=["caption", "stt"]
    )
    summary: str | None = Field(None, description="LLM이 생성한 영상 요약")
    error_message: str | None = Field(None, description="처리 실패 시 에러 메시지")
    progress: SourceProgress | None = Field(None, description="processing 상태일 때 진행 상황")
    created_at: datetime = Field(..., description="소스 생성 시각")
    updated_at: datetime = Field(..., description="최종 업데이트 시각")

    model_config = {"from_attributes": True}


class SourceCreateResponse(BaseModel):
    """소스 등록 응답."""

    source_id: UUID = Field(..., description="생성된 소스 ID")
    status: str = Field(..., description="초기 상태 (pending)", examples=["pending"])
