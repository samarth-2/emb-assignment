import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str
