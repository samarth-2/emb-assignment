import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    role: str
    content: str
    tool_used: str | None
    generated_sql: str | None
    citations: list[dict] | None
    created_at: datetime
