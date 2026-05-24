# Law RAG — AI-Powered Legal Document Assistant

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
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
| View live logs      | `make logs`       |
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

The only two values you must set are `OPENAI_API_KEY` and `SECRET_KEY` (generated automatically by the setup script).

---

## Project Structure

```
Law_RAG/
├── setup.bat          ← Windows one-click setup
├── setup.sh           ← Mac/Linux one-click setup
├── docker-compose.yml ← Defines all three services
├── .env               ← Your private config (gitignored)
├── .env.example       ← Config template
├── Makefile           ← Convenience commands (Mac/Linux)
├── backend/           ← FastAPI + Python (AI, search, auth)
└── frontend/          ← React + TypeScript (UI)
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
- Run `docker compose down -v` then `docker compose up -d` (this deletes all documents and users)

---

## For Developers

### Architecture

Law RAG is a full-stack RAG (Retrieval-Augmented Generation) platform built for production use cases where answer accuracy and source traceability matter.

**Retrieval pipeline** — when a query comes in, the backend runs two searches in parallel: a BM25 lexical search (via `rank-bm25`) over matter-scoped chunks, and a dense vector search (via Qdrant, cosine similarity, 1536-dim embeddings). Results are fused with **Reciprocal Rank Fusion** (RRF, k=60) to get the best of both approaches, then the top candidates are reranked by a **cross-encoder** (`ms-marco-MiniLM-L-6-v2`) for precision. The final top-k passages are injected as grounded context into the LLM prompt.

**LLM layer** — supports OpenAI GPT-4o (default) and a local Ollama fallback (llama3.2, mistral). Answers are streamed token-by-token via **SSE** (Server-Sent Events) so the UI feels responsive on long answers. After document upload, the pipeline runs GPT-4o summarization and clause extraction (governing law, termination, parties, etc.) as background tasks.

**Auth & access control** — JWT-based authentication with bcrypt hashing. Three roles: `partner`, `associate`, `paralegal`. Every query is scoped to a Matter, and Matter membership is enforced at the API layer. Partners see full audit logs; others see only their own query history.

**Stack:** FastAPI · SQLAlchemy (async) · SQLite · Qdrant · sentence-transformers · HuggingFace · OpenAI SDK · React · TypeScript · Vite · Docker Compose

### Running Locally (Developer Mode)

```bash
# Clone and configure
cp .env.example .env   # fill in OPENAI_API_KEY and SECRET_KEY

# Start all services
docker compose up -d

# Run the test suite
docker compose exec backend pytest -v

# View auto-generated API docs
open http://localhost:8000/docs
```

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for architecture decisions, branching strategy, and contribution guidelines.
