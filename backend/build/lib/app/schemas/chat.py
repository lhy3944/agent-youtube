from uuid import UUID

from pydantic import BaseModel


class Citation(BaseModel):
    segment_id: UUID
    start_sec: float
    end_sec: float
    text: str


class ChatAskRequest(BaseModel):
    source_id: UUID
    session_id: UUID | None = None
    question: str


class ChatAskResponse(BaseModel):
    answer: str
    session_id: UUID
    citations: list[Citation]
