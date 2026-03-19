"""
IngestJob 모델 - 비동기 처리 작업 추적.

소스 등록 시 생성되며, Celery 워커가 Ingest 파이프라인의 각 단계를
실행하면서 step과 progress를 업데이트한다.
프론트엔드는 이 정보를 polling하여 처리 진행 상황을 표시한다.

단계(step): queued → metadata → captions → stt → normalize → chunk → embed → summary → done
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    step: Mapped[str | None] = mapped_column(String(50))  # 현재 실행 중인 파이프라인 단계
    progress: Mapped[int | None] = mapped_column(Integer, default=0)  # 진행률 (0~100%)
    payload: Mapped[dict | None] = mapped_column(JSON)  # 단계별 추가 데이터 (확장용)
    error_message: Mapped[str | None] = mapped_column(Text)  # 실패 시 에러 메시지
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source = relationship("Source", back_populates="ingest_jobs")
