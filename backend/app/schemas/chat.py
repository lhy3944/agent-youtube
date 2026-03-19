"""
Chat 관련 요청/응답 Pydantic 스키마.

Swagger UI에서 각 필드의 설명과 예시값이 표시되도록
Field를 사용하여 OpenAPI 메타데이터를 명시한다.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """답변의 근거 구간. 해당 세그먼트의 타임스탬프와 원문 텍스트를 포함한다."""

    segment_id: UUID = Field(..., description="근거 세그먼트 ID")
    start_sec: float = Field(..., description="근거 구간 시작 시간 (초)", examples=[92.5])
    end_sec: float = Field(..., description="근거 구간 종료 시간 (초)", examples=[134.2])
    text: str = Field(..., description="해당 구간의 자막 텍스트")


class ChatAskRequest(BaseModel):
    """영상 기반 질문 요청."""

    source_id: UUID = Field(..., description="질문 대상 소스 ID")
    session_id: UUID | None = Field(
        None,
        description="기존 세션 ID. 없으면 새 세션이 자동 생성되고, 있으면 이전 대화 맥락이 유지된다.",
    )
    question: str = Field(
        ...,
        description="사용자 질문 텍스트",
        min_length=1,
        max_length=2000,
        examples=["이 영상의 핵심 내용이 뭐야?"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_id": "550e8400-e29b-41d4-a716-446655440000",
                    "session_id": None,
                    "question": "이 영상의 핵심 내용이 뭐야?",
                }
            ]
        }
    }


class ChatAskResponse(BaseModel):
    """질문 응답. 답변 텍스트, 세션 ID, 근거 Citation 목록을 포함한다."""

    answer: str = Field(..., description="AI 답변 텍스트 (영상 내용 기반)")
    session_id: UUID = Field(
        ..., description="세션 ID. 다음 질문 시 이 값을 전달하면 대화가 이어진다."
    )
    citations: list[Citation] = Field(
        ..., description="답변 근거 목록. 각 Citation은 영상 내 타임스탬프 구간 정보를 포함한다."
    )
