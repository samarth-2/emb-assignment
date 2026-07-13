import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import log_event
from app.db.session import SessionLocal, get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.memory import HistoryMessage, build_context
from app.services.orchestrator import run_turn

router = APIRouter(tags=["chat"])

_TITLE_MAX_LEN = 60


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _title_from_message(text: str) -> str:
    title = text.strip().replace("\n", " ")
    if len(title) > _TITLE_MAX_LEN:
        title = title[:_TITLE_MAX_LEN] + "…"
    return title or "New conversation"


def _get_or_create_conversation(
    db: Session, user: User, conversation_id: uuid.UUID | None, first_message: str
) -> Conversation:
    if conversation_id is not None:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        return conversation

    conversation = Conversation(user_id=user.id, title=_title_from_message(first_message))
    db.add(conversation)
    db.flush()
    return conversation


def _stream_turn(
    conversation_id: uuid.UUID, history: list[HistoryMessage], user_text: str
) -> Iterator[str]:
    """Runs the LLM turn and persists the result, using its own DB session.

    Deliberately independent from the request-scoped session (which already committed the
    user's message before streaming starts): StreamingResponse drains this generator in a
    worker thread after the endpoint function returns, so it must not depend on a session
    tied to the request's dependency lifecycle.
    """
    stream_db = SessionLocal()
    assistant_id = uuid.uuid4()
    try:
        full_content = ""
        tool_used = "none"
        generated_sql: str | None = None
        citations: list[dict] = []

        for event in run_turn(stream_db, history, user_text):
            if event["type"] == "meta":
                tool_used = event["tool_used"]
                generated_sql = event["generated_sql"]
                citations = event["citations"]
                yield _sse(
                    "meta",
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": str(assistant_id),
                        "tool_used": tool_used,
                        "generated_sql": generated_sql,
                        "citations": citations,
                    },
                )
            elif event["type"] == "token":
                full_content += event["delta"]
                yield _sse("token", {"delta": event["delta"]})
            elif event["type"] == "done":
                full_content = event["content"]
    except Exception as exc:  # noqa: BLE001 - any failure becomes a safe SSE error event
        log_event("chat_turn_error", conversation_id=str(conversation_id), error=str(exc))
        yield _sse("error", {"detail": "Something went wrong while generating a response."})
        stream_db.close()
        return

    stream_db.add(
        Message(
            id=assistant_id,
            conversation_id=conversation_id,
            role="assistant",
            content=full_content,
            tool_used=tool_used,
            generated_sql=generated_sql,
            citations=citations or None,
        )
    )
    stream_db.execute(
        update(Conversation).where(Conversation.id == conversation_id).values(updated_at=func.now())
    )
    stream_db.commit()
    stream_db.close()

    yield _sse("done", {"message_id": str(assistant_id)})


@router.post("/chat")
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    conversation = _get_or_create_conversation(db, user, payload.conversation_id, payload.message)

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.message))
    db.flush()
    history = build_context(db, conversation)[:-1]  # prior turns; current message passed separately
    conversation_id = conversation.id
    db.commit()

    return StreamingResponse(
        _stream_turn(conversation_id, history, payload.message), media_type="text/event-stream"
    )
