# Project Instructions

## Goal

Build the AI Engineer Assessment (EMB Global — Dual-Mode Agentic RAG Chatbot) exactly
according to the assignment specification and the approved architecture plan.

Priorities:

1. Correctness
2. Simplicity
3. Readability
4. Finish by EOD

Do NOT over-engineer.

---

## Tech Stack

Backend
- FastAPI, Python 3.12
- SQLAlchemy 2.x, Alembic

Frontend
- Next.js 15, TypeScript, TailwindCSS

LLM
- Gemini 3.1 Flash Lite (native tool-calling). Originally speced as Gemini 2.5 Flash, but that
  generation (including 2.5-flash-lite) returns 404 "no longer available to new users" for
  newly created API keys/projects — confirmed directly against Google's API during Phase 4.
  3.5 Flash worked initially but suffered a sustained "model overloaded" 503 outage during
  Phase 8 deployment verification (5+ failures over an hour, even with 4-attempt exponential
  backoff) while 3.1 Flash Lite never failed once in the same window — switched for reliability.

Embeddings
- Google `gemini-embedding-001`

Database / Vector Store
- PostgreSQL + pgvector
- Dev: docker-compose (postgres:16 + pgvector)
- Prod: Supabase (same Alembic migrations against both)

Auth
- Self-rolled username/password, bcrypt hashing, JWT (python-jose)

Deployment
- Docker
- Backend: Render
- Frontend: Vercel

---

## Architecture

```
User
  ↓
Orchestrator (native Gemini tool-calling; pluggable interface)
  ├── search_documents(query)   → pgvector kNN over document_chunks + citations
  └── execute_sql(question)     → NL→SQL (internal LLM) → validate → read-only execute
  ↓
Response (streamed via SSE), tool_used / generated_sql / citations persisted
```

Avoid unnecessary abstractions. Do NOT introduce microservices, Redis, Celery, Kubernetes,
or LangGraph/LangChain unless there is a strong engineering justification.

The routing mechanism (native tool-calling) lives behind an `Orchestrator` interface so it
can be swapped for a structured LLM classifier later without touching tool services,
streaming, or persistence.

**Pinned clock:** treat current date as **2026-06-15** for all time-based SQL — never `NOW()`.

---

## Coding Style

- Small functions
- Type hints
- Clear names
- Minimal comments
- Modular code
- Production-quality but simple
- Structured JSON logging (`app/core/logging.py`) for request_id, tool_used, latency, errors

---

## Development Process

Implement in phases. Complete exactly one phase at a time; wait for approval before the next.

- Phase 0 — Scaffold (folder structure, docker-compose, config, logging, health check)
- Phase 1 — DB layer (SQLAlchemy models, Alembic migration 0001)
- Phase 2 — Auth (bcrypt + JWT, admin seed)
- Phase 3 — Ingestion & seed (embeddings, PDF chunking, orders import)
- Phase 4 — Tools (search_documents, execute_sql) + tests
- Phase 5 — Orchestrator & chat API (SSE streaming)
- Phase 6 — Frontend (login, chat, sidebar)
- Phase 7 — Dockerize & end-to-end verification
- Phase 8 — Deploy (Supabase, Render, Vercel) + final README

Never implement everything in one step.

---

## Important

- Always ask before introducing additional dependencies.
- Never regenerate the whole project when only one file needs changing.
- Prefer editing existing files; prefer incremental changes over rewrites.
- Keep token usage efficient.
- Full architecture plan: see the plan approved at project start (folder structure, DB
  schema, API design, RAG/SQL/routing architecture, risks).
