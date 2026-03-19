"""
Source 모델 - 사용자가 등록한 YouTube 영상 소스.

하나의 Source는 하나의 YouTube 영상에 대응하며,
메타데이터(제목, 채널, 썸네일 등), 처리 상태, 요약 등을 저장한다.

상태 전이: pending → processing → ready / partial_ready / failed
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="youtube")  # 소스 유형 (현재 youtube만 지원, 향후 확장 가능)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # 처리 상태: pending, processing, ready, partial_ready, failed
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)  # 사용자가 입력한 원본 URL
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)  # YouTube videoId (11자리)
    title: Mapped[str | None] = mapped_column(String(500))  # 영상 제목
    channel_title: Mapped[str | None] = mapped_column(String(200))  # 채널명
    description: Mapped[str | None] = mapped_column(Text)  # 영상 설명
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048))  # 썸네일 이미지 URL
    duration_sec: Mapped[int | None] = mapped_column(Integer)  # 영상 길이(초)
    language: Mapped[str | None] = mapped_column(String(10))  # 자막/전사 언어 코드
    transcript_source: Mapped[str | None] = mapped_column(String(20))  # 자막 출처: "caption" 또는 "stt"
    summary: Mapped[str | None] = mapped_column(Text)  # LLM이 생성한 영상 요약
    error_message: Mapped[str | None] = mapped_column(Text)  # 처리 실패 시 에러 메시지
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 관계 설정 - Source 삭제 시 연관 데이터 함께 삭제 (cascade)
    segments = relationship("TranscriptSegment", back_populates="source", cascade="all, delete")
    chat_sessions = relationship("ChatSession", back_populates="source", cascade="all, delete")
    ingest_jobs = relationship("IngestJob", back_populates="source", cascade="all, delete")
