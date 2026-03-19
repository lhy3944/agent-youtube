"""
TranscriptSegment 모델 - 청크화된 자막 세그먼트.

영상의 자막을 토큰 기반으로 분할한 결과를 저장한다.
각 세그먼트는 시작/종료 타임스탬프와 텍스트, 그리고
벡터 검색을 위한 pgvector 임베딩을 포함한다.

검색 시 사용자 질문의 임베딩과 코사인 유사도를 비교하여
가장 관련성 높은 세그먼트를 찾는다.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,  # source_id 기반 조회가 빈번하므로 인덱스 설정
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 세그먼트 순서 (0부터 시작)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)  # 시작 시간(초)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)  # 종료 시간(초)
    text: Mapped[str] = mapped_column(Text, nullable=False)  # 청크 텍스트 내용
    token_count: Mapped[int | None] = mapped_column(Integer)  # 텍스트의 토큰 수
    # pgvector 컬럼: 임베딩 차원은 config에서 설정 (기본 1536)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source = relationship("Source", back_populates="segments")
