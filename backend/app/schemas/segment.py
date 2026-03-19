"""
TranscriptSegment 조회 응답 스키마. (디버깅/관리자용)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SegmentResponse(BaseModel):
    """자막 세그먼트 조회 응답. 임베딩 벡터는 제외하고 텍스트와 타임스탬프만 반환한다."""
    id: UUID
    source_id: UUID
    segment_index: int  # 세그먼트 순서 (0부터)
    start_sec: float  # 시작 시간(초)
    end_sec: float  # 종료 시간(초)
    text: str  # 세그먼트 텍스트
    token_count: int | None = None  # 토큰 수
    created_at: datetime

    model_config = {"from_attributes": True}
