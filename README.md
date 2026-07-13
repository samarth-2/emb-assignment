# Northwind Gadgets — Dual-Mode Agentic RAG Chatbot

A chatbot for a fictional e-commerce company, Northwind Gadgets, that answers questions using
two distinct knowledge sources — vector retrieval over policy documents (RAG) and text-to-SQL
over an orders table — deciding per question which to use (or both), via native LLM tool-calling.

**Live URLs:**
- Frontend: https://emb-assignment-frontend.vercel.app
- Backend API: https://emb-assignment-backend.onrender.com (`/health`, `/docs`)

**Login:** `admin` / `admin123` (seeded by `scripts/seed.py`)

## Architecture

```
Browser (Next.js) ──JWT──▶ FastAPI
                              │
                     ┌────────┴─────────┐
                     │  Orchestrator     │  (native Gemini tool-calling; pluggable)
                     └────────┬─────────┘
        ┌─────────────────────┼──────────────────────┐
   search_documents()    execute_sql(question)    (neither → safe fallback)
        │                     │
   pgvector kNN over     NL→SQL (internal LLM call) →
   document_chunks       validate → READ-ONLY tx (least-priv role) → run
        │                     │
        └────────┬────────────┘
                 ▼
     Gemini synthesizes final answer  ──SSE token stream──▶ Browser
                 │
                 ▼
     Persist assistant msg (content, tool_used, generated_sql, citations)
```

One chat turn = a non-streamed routing call (with two tools declared) → 0/1/2 tool
executions → a forced-text-only streamed synthesis call. Bounded at a single round of tool
calls — no open-ended agent loop — which is sufficient for RAG-only, SQL-only, both, and
no-tool questions per the assignment's spec.

## Stack and reasoning

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.x, Alembic | Async-capable, typed, minimal-magic; Alembic gives reviewable, reversible migrations |
| Frontend | Next.js 15, TypeScript, TailwindCSS | App Router + Server/Client components map cleanly onto login-gate + streaming chat |
| LLM | Gemini 3.1 Flash Lite (native tool-calling) | Originally speced as Gemini 2.5 Flash, but that generation (including 2.5-flash-lite) returns a hard 404 "no longer available to new users" for newly created API keys/projects — confirmed directly against Google's API. Gemini 3.5 Flash worked initially but suffered a sustained "model overloaded" 503 outage during deployment verification (5+ failures over an hour, even with 4-attempt exponential backoff), while 3.1 Flash Lite never failed once in the same window — switched for reliability |
| Embeddings | Google `gemini-embedding-001`, truncated to 768 dims | Same provider as the chat model (one API key, one client); 768 dims keeps well under pgvector's 2000-dim index ceiling. Output is renormalized to unit length after MRL truncation per Google's guidance |
| Vector store | pgvector inside Postgres | One database for everything (users, chat history, orders, embeddings) instead of a second system to run/secure; HNSW cosine index scales far beyond this dataset's 22 chunks |
| Database | Supabase Postgres | Managed Postgres with pgvector pre-integrated; free tier is enough for this dataset |
| Auth | Self-rolled bcrypt + JWT (python-jose) | Assignment explicitly disallows Clerk/NextAuth/OAuth; a lightweight custom implementation is the right amount of engineering for one seeded admin user |
| Deployment | Docker + Render (backend), Vercel (frontend) | Render builds directly from the repo's `backend/Dockerfile`; Vercel is the natural fit for Next.js |

## Routing strategy

The LLM is given two function declarations — `search_documents(query)` and
`execute_sql(question)` — and decides per turn whether to call one, both, or neither:

- **Document questions** ("What is the refund window?") → `search_documents` only.
- **Data questions** ("How many orders are pending?") → `execute_sql` only.
- **Mixed questions** ("Our policy allows 30-day returns; did order ORD-1003 qualify?") → both,
  in parallel, in the same turn.
- **Out-of-scope questions** ("Who is the CEO?") → neither; the system prompt instructs the
  model to answer exactly `"I don't have that information."` rather than guess.

`tool_used` (`rag` | `sql` | `both` | `none`) is derived from which tools actually ran, not
predicted in advance — this is what makes the router "decide on its own" rather than following
a keyword heuristic. The decision logic lives entirely behind `services/orchestrator.py`; a
future structured-classifier router could replace it without touching the tool implementations,
streaming layer, or persistence.

**Anti-hallucination guardrails:**
- RAG: chunks past a calibrated cosine-distance threshold are dropped, so an off-topic query
  retrieves nothing (empirically calibrated — on-topic queries measured 0.25–0.35 distance,
  off-topic 0.42–0.51, on this dataset).
- SQL: the model only sees the real `orders` schema/columns/status values in its prompt, and a
  validator rejects anything that isn't a single `SELECT` (see below) before it ever executes.
- The system prompt explicitly instructs a safe fallback over guessing when tool results don't
  cover the question.

## Text-to-SQL safety (defense in depth)

`execute_sql` is self-contained: it generates SQL from the question (an internal Gemini call,
grounded in the exact schema + a **pinned "current date" of 2026-06-15** so time-based questions
never depend on the real clock), then runs it through three independent layers before touching
the database:

1. **Prompt grounding** — the generator only knows about the `orders` table's real columns.
2. **App-level validation** — single statement, `SELECT`-only, no destructive keywords, no SQL
   comments, `LIMIT` capped at 200 rows.
3. **Least-privilege execution** — a dedicated `sql_readonly` Postgres role (created in Alembic
   migration `0002`, `GRANT SELECT` on `orders` only — no access to `users`/`messages`/etc.),
   inside a `READ ONLY` transaction with a 5s statement timeout.

Layer 3 is what actually stops a prompt-injection attempt from reading other tables even if
layers 1–2 were somehow bypassed — verified with a live test asserting `permission denied` on
`SELECT * FROM users` through this role.

## Chat history & memory

Full conversation history is persisted (`users` → `conversations` → `messages`, with
`tool_used`/`generated_sql`/`citations` as first-class columns on `messages`). Each turn sends
the system prompt + the **last 10 messages** (not the full history) + freshly retrieved tool
results. `services/memory.py` is a single seam — swapping in summarization once conversations
grow long only requires changing that one function.

## Database schema

```
users            (id, username, password_hash, created_at)
conversations    (id, user_id → users, title, created_at, updated_at)
messages         (id, conversation_id → conversations, role, content,
                  tool_used, generated_sql, citations jsonb, created_at)
documents        (id, filename, title, created_at)
document_chunks  (id, document_id → documents, chunk_index, content, section,
                  embedding vector(768))
orders           (order_id, customer, product, amount, status, order_date)
```

## Local development

```bash
docker compose up -d --build     # Postgres + pgvector + backend (migrates + seeds on boot)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Or run the backend directly (useful for iterating without a rebuild each time):

```bash
docker compose up -d db
cd backend
cp .env.example .env   # fill in GOOGLE_API_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Backend tests: `cd backend && pip install -r requirements-dev.txt && pytest` (16 offline
guardrail/unit tests; 5 more are live integration tests against a running Postgres + Gemini key).

## Known limitations

- **Free-tier LLM quota.** Gemini's free tier historically capped `gemini-3.5-flash` at
  20 requests/day per project — each chat turn costs 2–3 calls (routing + synthesis, +1 more
  for SQL questions), so a handful of messages could exhaust it. Billing is enabled on the
  deployed project's API key to remove this cap.
- **Gemini model availability varies.** `gemini-3.5-flash` returned a sustained "model
  overloaded" 503 during deployment testing; the deployed app uses `gemini-3.1-flash-lite`
  instead, which was reliable throughout the same window. `call_with_retry` (`services/llm.py`)
  retries transient 503s with exponential backoff (4 attempts, up to ~10s), but a long enough
  outage on Google's side would still surface as a graceful "Something went wrong" message.
- **Render free-tier cold starts.** The backend spins down after ~15 minutes of inactivity;
  the first request after idling can take 30–60s while the container restarts.
- **Single-round tool use.** The orchestrator does one routing call, executes 0–2 tools, then
  synthesizes — it does not loop (e.g. it won't run a second SQL query based on the first
  query's results within the same turn). This matches the assignment's dual-mode spec without
  an open-ended agent loop.
- **Fixed, small dataset.** Retrieval thresholds and the SQL system prompt's product/status
  lists are calibrated against this project's specific 5 policy PDFs and ~200-row orders table;
  a larger or different dataset would need the distance threshold and schema description
  re-tuned.
- **No conversation summarization yet.** History beyond the last 10 messages is dropped rather
  than summarized — `services/memory.py` is structured as a single seam for adding this later.
- **Direct Supabase connection over IPv6.** Supabase's direct DB hostname resolves to IPv6-only;
  Render's network can't reach it. The deployed app uses Supabase's session pooler (IPv4) for
  both migrations and runtime instead.
