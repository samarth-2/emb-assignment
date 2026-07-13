# Northwind Gadgets — Dual-Mode Agentic RAG Chatbot

A chatbot that answers questions about a fictional company using two knowledge sources —
document retrieval (RAG) and text-to-SQL over an orders table — and decides per question
which to use, via native LLM tool-calling.

> Status: under active development, built in phases. This README will be filled in as
> architecture, model/embedding/vector-store choices, routing behavior, and known
> limitations are finalized (see Phase 8).

## Stack

- **Backend:** FastAPI, Python 3.12, SQLAlchemy 2.x, Alembic
- **Frontend:** Next.js 15, TypeScript, TailwindCSS
- **LLM:** Gemini 2.5 Flash (native tool-calling)
- **Embeddings:** Google `gemini-embedding-001`
- **Database:** PostgreSQL + pgvector (Supabase in production, docker-compose locally)
- **Auth:** Self-rolled username/password (bcrypt) + JWT

## Local development

```bash
docker compose up -d           # Postgres + pgvector
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health`
