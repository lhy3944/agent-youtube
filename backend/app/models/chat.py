"""
Chat 모델 - 대화 세션 및 메시지.

ChatSession: 하나의 소스에 대한 질의응답 세션. 세션 내에서 대화 히스토리가 유지된다.
ChatMessage: 세션 내의 개별 메시지. role(user/assistant)과 content를 저장하며,
             assistant 메시지에는 답변의 근거가 되는 citations(JSON)이 포함된다.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatSession(Base):
    """영상별 대화 세션. 세션 ID를 유지하면 이전 대화 맥락을 참조할 수 있다."""
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source = relationship("Source", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete")


class ChatMessage(Base):
    """개별 채팅 메시지. assistant 역할의 메시지에는 citations(근거 구간 정보)이 JSON으로 저장된다."""
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" 또는 "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 메시지 본문
    citations: Mapped[dict | None] = mapped_column(JSON)  # 답변 근거 세그먼트 정보 [{segment_id, start_sec, end_sec, text}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
