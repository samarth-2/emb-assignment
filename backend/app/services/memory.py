from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message

DEFAULT_HISTORY_LIMIT = 10


@dataclass(frozen=True)
class HistoryMessage:
    role: str
    content: str


def build_context(
    db: Session, conversation: Conversation, limit: int = DEFAULT_HISTORY_LIMIT
) -> list[HistoryMessage]:
    """Returns the last `limit` messages of the conversation, oldest first.

    Returns plain, already-materialized data rather than live ORM objects: the chat endpoint
    commits (which expires ORM instances) before this list is consumed by the streaming
    generator, which runs in a separate worker thread after the request session may be gone.

    Also a seam for future summarization: once history grows past `limit`, a summarizing
    implementation can replace this function's body without touching the orchestrator or chat API.
    """
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    ordered = list(reversed(rows))
    return [HistoryMessage(role=m.role, content=m.content) for m in ordered]
