from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.config import get_settings
from app.core.logging import RequestIdMiddleware

settings = get_settings()

app = FastAPI(title="Dual-Mode Agentic RAG Chatbot", version="0.1.0")

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
