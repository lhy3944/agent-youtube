"""
Chat 관련 요청/응답 Pydantic 스키마.
"""

from uuid import UUID

from pydantic import BaseModel


class Citation(BaseModel):
    """답변의 근거 구간. 해당 세그먼트의 ID, 시작/종료 타임스탬프, 원문 텍스트를 포함한다."""
    segment_id: UUID
    start_sec: float  # 근거 구간 시작 시간(초)
    end_sec: float  # 근거 구간 종료 시간(초)
    text: str  # 해당 구간의 자막 텍스트


class ChatAskRequest(BaseModel):
    """질문 요청 바디. session_id가 없으면 새 세션이 자동 생성된다."""
    source_id: UUID  # 질문 대상 소스 ID
    session_id: UUID | None = None  # 기존 세션 ID (대화 이어가기용, 없으면 신규 생성)
    question: str  # 사용자 질문 텍스트


class ChatAskResponse(BaseModel):
    """질문 응답. 답변 텍스트, 세션 ID, 근거 Citation 목록을 포함한다."""
    answer: str
    session_id: UUID  # 세션 ID (다음 질문 시 이 값을 전달하면 대화가 이어진다)
    citations: list[Citation]  # 답변 근거 목록 (최소 1개 이상 포함 목표)
