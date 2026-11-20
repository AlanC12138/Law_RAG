# Law RAG — AI-Powered Legal Document Assistant

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?style=flat&logo=react&logoColor=black)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-DC244C?style=flat)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat&logo=openai&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)

Law RAG lets your legal team ask plain-English questions about case files and get precise, cited answers — backed by the documents themselves, never hallucinated.

- Upload PDFs and Word documents to a **Matter**
- Ask questions in natural language — follow-up questions understand the conversation context
- Every answer links back to the exact page and passage it came from
- Uploaded documents are automatically **summarised** and their **key clauses** (governing law, termination, parties, etc.) extracted and displayed
- Role-based access control and full audit logging built in
- Partners can manage team members and matters through the admin panel
- Citations jump straight to the source document, and passages can be copied in one click
- A matter's full Q&A history exports to a formatted `.docx`
- Drop a file into `data/watch/<matter_id>/` and it is ingested automatically — no manual upload
- Sessions refresh silently in the background instead of logging you out mid-task

---

## Status

**Verified on 2026-11-20** — `master` at `185d9c87`.

| Check | Result |
|---|---|
| Backend tests (`pytest`, SQLite in-memory) | 75 / 75 passing |
| `ruff check` · `black --check` | Clean, 55 files |
| ESLint (`--max-warnings 0`) | Clean |
| `tsc && vite build` | Clean — 263.34 kB (82.41 kB gzipped) |
| Alembic migrations against PostgreSQL 16 | `001` → `002` → `003`, all model tables created |
| `docker compose config` | Valid |

The first five ran locally and in GitHub Actions; the migration check is the CI
job `Migrate (Alembic against Postgres)`. Everything in this README and in
[TECH_STACK.md](TECH_STACK.md) was checked against the source tree on that date.

---

## Requirements

Before you start, you need:

1. **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/)
2. **An OpenAI API key** — [get one here](https://platform.openai.com/api-keys)

That's it. No Python, no Node.js, no database setup.

---

## Installation

### Windows

1. Double-click **`setup.bat`**
2. Enter your OpenAI API key when prompted
3. Wait a few minutes for Docker to build the app
4. Your browser opens automatically when it's ready

### Mac / Linux

```bash
chmod +x setup.sh
./setup.sh
```

The script will ask for your OpenAI API key, generate a secure configuration, and open the app in your browser when it's ready.

---

## Logging In

Default credentials (set during setup):

| Field    | Default                  |
|----------|--------------------------|
| Email    | `admin@lawfirm.local`    |
| Password | `changeme`               |

> **Important:** Change the admin password after your first login.

---

## Daily Use

After the first install, Docker starts automatically when your machine boots. You can also manage it manually:

**Windows** — open a terminal in the Law RAG folder and run:

| What you want       | Command                        |
|---------------------|-------------------------------|
| Start the app       | `docker compose up -d`        |
| Stop the app        | `docker compose down`         |
| Restart the app     | `docker compose restart`      |
| Check if it's running | `docker compose ps`         |

**Mac / Linux** — same commands, or use `make`:

| What you want       | Command           |
|---------------------|-------------------|
| Start the app       | `make start`      |
| Stop the app        | `make stop`       |
| Restart            | `make restart`    |
| Rebuild after code changes | `make build` |
| View live logs      | `make logs`       |
| Backend logs only   | `make logs-backend` |
| Check status        | `make status`     |
| Wipe data & reset  | `make reset`      |

---

## How It Works

```
You ask a question about a Matter
        ↓
Law RAG searches your uploaded documents
(hybrid keyword + semantic search)
        ↓
The most relevant passages are ranked
and sent to GPT-4o as grounded context
        ↓
You get a precise answer with
[SOURCE] citations linked to the original document
```

---

## Configuration

All settings live in the `.env` file created during setup. See `.env.example` for available options.

If you ran `setup.bat` / `setup.sh`, everything required is already filled in.

Setting up `.env` by hand instead, three values have no usable default:

| Variable | Why |
|---|---|
| `OPENAI_API_KEY` | Not needed if you set `LLM_PROVIDER=ollama` |
| `SECRET_KEY` | Signs login tokens — generate with `openssl rand -base64 32` |
| `POSTGRES_PASSWORD` | Blank in the template; the setup scripts generate a random one |

Uploads are capped at `MAX_UPLOAD_SIZE_MB` (default 50). Anything larger is
rejected with HTTP 413 rather than being written to disk.

---

## Project Structure

```
Law_RAG/
├── setup.bat          ← Windows one-click setup
├── setup.sh           ← Mac/Linux one-click setup
├── docker-compose.yml ← Defines all four services (postgres, qdrant, backend, frontend)
├── .env               ← Your private config (gitignored)
├── .env.example       ← Config template
├── Makefile           ← Convenience commands (Mac/Linux)
├── CHANGELOG.md       ← Release history
├── TECH_STACK.md      ← Stack choices and rationale
├── INSTRUCTIONS.md    ← Original planning decisions and phase scope
├── backend/           ← FastAPI + Python (AI, search, auth)
│   └── alembic/       ← Database migrations (run automatically on startup)
├── frontend/          ← React + TypeScript (UI)
└── data/watch/        ← Drop files in <matter_id>/ to auto-ingest
```

---

## Troubleshooting

**The app won't start**
- Make sure Docker Desktop is running (look for the Docker icon in your taskbar)
- Run `docker compose logs backend` to see error details

**"Invalid API key" errors**
- Check that `OPENAI_API_KEY` in your `.env` file starts with `sk-` and has no extra spaces

**I forgot my password**
- Run the following command to reset the admin password to `changeme`:
  ```bash
  docker compose exec backend python -c "
  import asyncio
  from app.db.session import AsyncSessionLocal
  from app.db.models import User
  from app.core.security import get_password_hash
  from sqlalchemy import select

  async def main():
      async with AsyncSessionLocal() as db:
          result = await db.execute(select(User).where(User.email == 'admin@lawfirm.local'))
          user = result.scalar_one()
          user.hashed_password = get_password_hash('changeme')
          await db.commit()
          print('Password reset to: changeme')

  asyncio.run(main())
  "
  ```
- Then log in with `admin@lawfirm.local` / `changeme` and change your password immediately

**I want to start over with a clean database**
- Run `docker compose down -v` then `docker compose up -d` (this deletes the Postgres database, Qdrant vectors, and all uploaded documents)

---

## For Developers

### Architecture

Law RAG is a full-stack RAG (Retrieval-Augmented Generation) platform built for production use cases where answer accuracy and source traceability matter.

**Retrieval pipeline** — when a query comes in, the backend runs two searches in parallel: a BM25 lexical search (via `rank-bm25`) over matter-scoped chunks, and a dense vector search (via Qdrant, cosine similarity, 1536-dim embeddings). Results are fused with **Reciprocal Rank Fusion** (RRF, k=60) to get the best of both approaches, then the top candidates are reranked by a **cross-encoder** (`ms-marco-MiniLM-L-6-v2`) for precision. The final top-k passages are injected as grounded context into the LLM prompt.

**LLM layer** — supports OpenAI GPT-4o (default) and a local Ollama fallback (llama3.2, mistral). Answers are streamed token-by-token via **SSE** (Server-Sent Events) so the UI feels responsive on long answers. After document upload, the pipeline runs GPT-4o summarization and clause extraction (governing law, termination, parties, etc.) as background tasks.

**Auth & access control** — JWT-based authentication with bcrypt hashing. Three roles: `partner`, `associate`, `paralegal`. Every query is scoped to a Matter, and Matter membership is enforced at the API layer. Partners see full audit logs; others see only their own query history.

**Database** — PostgreSQL is the default when running via `docker compose up`; schema changes are tracked with Alembic migrations that run automatically on startup. SQLite remains available as a zero-dependency fallback for running the API directly without Docker (`DATABASE_URL=sqlite+aiosqlite:///...`) — see [backend/.env.example](backend/.env.example).

**Stack:** FastAPI · SQLAlchemy (async) · PostgreSQL · Qdrant · sentence-transformers · HuggingFace · OpenAI SDK · React · TypeScript · Vite · Docker Compose

### Running Locally (Developer Mode)

```bash
# Clone and configure
cp .env.example .env   # fill in OPENAI_API_KEY and SECRET_KEY

# Start all services
docker compose up -d

# View auto-generated API docs
open http://localhost:8000/docs
```

### Running the tests

The backend image is built with `poetry install --without dev`, so `pytest` is
**not** present inside the container. Run the suite on the host instead, with the
same environment CI uses:

```bash
cd backend
poetry install --with dev --no-root

OPENAI_API_KEY=sk-test-placeholder SECRET_KEY="test-secret-key-for-ci-at-least-32-chars!!" DATABASE_URL="sqlite+aiosqlite:///:memory:" QDRANT_PATH=/tmp/qdrant_test APP_ENV=test poetry run pytest --asyncio-mode=auto -v
```

75 tests. Qdrant and the ML stack are stubbed in `backend/conftest.py`, so no
vector database, model download or API key is needed. Lint with
`poetry run ruff check .` and `poetry run black --check .`.

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for architecture decisions, branching strategy, and contribution guidelines.
