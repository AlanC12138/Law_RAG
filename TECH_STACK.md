# Law RAG — Tech Stack

> All technology choices for the project. Each entry includes the rationale and any key constraints or alternatives considered.

> **Verified on 2026-11-20** against the code on `main` (`185d9c87`). Every row
> below was checked against `backend/pyproject.toml`, `backend/poetry.lock`,
> `frontend/package.json`, `docker-compose.yml` and the source tree.

---

## Backend

| Concern | Choice | Version | Notes |
|---|---|---|---|
| Language | Python | 3.11+ | Best RAG/ML ecosystem |
| Web framework | FastAPI | 0.110+ | Async, auto-generated OpenAPI docs, excellent for streaming |
| ASGI server | Uvicorn | latest | Development; swap to Gunicorn + Uvicorn workers in production |
| Dependency management | Poetry | latest | Lock file, virtual env, clean packaging |

## AI / ML

| Concern | Choice | Notes |
|---|---|---|
| LLM (MVP) | OpenAI GPT-4o | Configurable via `.env`; provider abstracted behind interface |
| Embeddings | OpenAI `text-embedding-3-small` | Good quality/cost ratio; 1536 dimensions |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Runs locally via `sentence-transformers`; no API cost |
| LLM interface | `BaseLLMProvider` over the `openai` AsyncOpenAI client | Hand-rolled rather than via a framework; Ollama implements the same interface |
| Alternative LLM | Ollama (`llama3.2`, `mistral`) | Implemented — set `LLM_PROVIDER=ollama`; for air-gapped/local deployments |

## Document Processing

| Concern | Choice | Notes |
|---|---|---|
| PDF parsing | `pdfplumber` | Text and tables; `pymupdf` was dropped as unused |
| OCR (scanned PDFs) | `pytesseract` + Tesseract | Open source; runs locally |
| DOCX parsing | `python-docx` | Standard; preserves structure |
| Chunking | Custom (`app/ingestion/chunker.py`) | Custom logic to respect legal section/clause boundaries |
| BM25 keyword search | `rank_bm25` | Lightweight, no server needed |

## Data Storage

| Concern | Choice | Notes |
|---|---|---|
| Vector database | Qdrant `v1.17.1` (server mode) | Its own container in docker-compose on port 6333; image pinned so it cannot drift ahead of the client |
| Relational database | PostgreSQL (default) | Started via docker-compose; schema managed by Alembic migrations. SQLite remains available as a zero-config fallback for running the API without Docker |
| Migrations | Alembic | Schema versioning from day one |
| ORM | SQLAlchemy 2.0 | Async-compatible |

## Auth & Security

| Concern | Choice | Notes |
|---|---|---|
| Password hashing | `passlib` + `bcrypt` | Industry standard |
| Session tokens | JWT (`python-jose`) | Stateless; short-lived access tokens + refresh tokens |
| CORS | FastAPI `CORSMiddleware` | Configured to allow only the local frontend origin |

## Frontend

| Concern | Choice | Notes |
|---|---|---|
| Framework | React 18 | Component model, large ecosystem |
| Build tool | Vite | Fast HMR, simple config |
| Language | TypeScript | Type safety, better DX |
| HTTP client | Axios | Includes a 401 interceptor that silently refreshes the access token once before giving up. React Query was removed as unused |
| Styling | Tailwind CSS | Utility-first, fast to build with |
| Component library | None | Components are hand-written against Tailwind utilities |
| Streaming | `fetch` + `ReadableStream` reader | Backend sends `text/event-stream`; `EventSource` is unusable here because it cannot set an auth header on a POST |

## Dev Tooling

| Concern | Choice | Notes |
|---|---|---|
| Version control | Git | GitHub (or self-hosted) |
| Versioning | Semantic Versioning (`MAJOR.MINOR.PATCH`) | |
| Changelog | `CHANGELOG.md` (Keep a Changelog format) | |
| CI | GitHub Actions | On push to `main` and `dev`: ruff, black, pytest, Alembic against a real Postgres, ESLint, and a TypeScript + Vite build |
| Backend linting | `ruff` | Fast, replaces flake8 + isort + pyupgrade |
| Backend formatting | `black` | |
| Frontend linting | ESLint | `--max-warnings 0`; Prettier is not installed |
| Testing — backend | `pytest` + `pytest-asyncio` | 75 tests; heavy ML deps stubbed in `backend/conftest.py` so no model download or API key is needed |
| Testing — frontend | None yet | No frontend test framework is installed |
| Local dev orchestration | `docker compose` | Spins up Postgres, Qdrant, backend and frontend together |
| Environment config | `python-dotenv` / `.env` files | `.env.example` committed; `.env` gitignored |

## Future / Phase 2

| Concern | Choice | Notes |
|---|---|---|
| Desktop packaging | Electron (frontend) + PyInstaller (backend) | Wraps local web server in a desktop app |
| Auto-update | Electron auto-updater | Built into Electron |

---

## Key Abstractions (Interfaces to Define Early)

These should be abstract base classes in Python, so Phase 2/3 extensions slot in without refactoring:

- `BaseDocumentConnector` — manual upload and folder watch in MVP; DMS connectors in Phase 3
- `BaseLLMProvider` — OpenAI in MVP; Ollama/local in Phase 2
- `BaseEmbeddingProvider` — OpenAI in MVP; local model in Phase 2

---

## Dependency Constraints

- All backend dependencies must be installable via `pip` / `poetry` with no compiled binaries that would break cross-platform packaging (with the exception of Tesseract, which ships as a separate system binary).
- No dependency should require a paid license for self-hosted use.
- All AI/ML dependencies must support offline use (for the reranker, which runs locally).
