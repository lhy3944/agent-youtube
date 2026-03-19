"""
TranscriptSegment 조회 응답 스키마. (디버깅/관리자용)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SegmentResponse(BaseModel):
    """자막 세그먼트 조회 응답. 임베딩 벡터는 제외하고 텍스트와 타임스탬프만 반환한다."""

    id: UUID = Field(..., description="세그먼트 고유 ID")
    source_id: UUID = Field(..., description="소속 소스 ID")
    segment_index: int = Field(..., description="세그먼트 순서 (0부터)", examples=[0])
    start_sec: float = Field(..., description="시작 시간 (초)", examples=[0.0])
    end_sec: float = Field(..., description="종료 시간 (초)", examples=[15.5])
    text: str = Field(..., description="세그먼트 텍스트")
    token_count: int | None = Field(None, description="텍스트의 토큰 수", examples=[87])
    created_at: datetime = Field(..., description="생성 시각")

    model_config = {"from_attributes": True}
