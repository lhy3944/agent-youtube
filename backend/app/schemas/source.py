from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class YouTubeSourceCreate(BaseModel):
    url: HttpUrl


class SourceProgress(BaseModel):
    step: str | None = None
    percent: int | None = None


class SourceResponse(BaseModel):
    id: UUID
    type: str
    status: str
    original_url: str
    external_id: str
    title: str | None = None
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_sec: int | None = None
    language: str | None = None
    transcript_source: str | None = None
    summary: str | None = None
    error_message: str | None = None
    progress: SourceProgress | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceCreateResponse(BaseModel):
    source_id: UUID
    status: str
