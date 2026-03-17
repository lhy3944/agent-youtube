from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SegmentResponse(BaseModel):
    id: UUID
    source_id: UUID
    segment_index: int
    start_sec: float
    end_sec: float
    text: str
    token_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
