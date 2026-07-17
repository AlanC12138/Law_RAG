# Law RAG — Tech Stack

> All technology choices for the project. Each entry includes the rationale and any key constraints or alternatives considered.

---

## Backend

| Concern | Choice | Version | Notes |
|---|---|---|---|
| Language | Python | 3.11+ | Best RAG/ML ecosystem |
| Web framework | FastAPI | 0.110+ | Async, auto-generated OpenAPI docs, excellent for streaming |
| RAG orchestration | LlamaIndex | 0.10+ | Better than LangChain for document-heavy RAG; strong PDF/DOCX support |
| ASGI server | Uvicorn | latest | Development; swap to Gunicorn + Uvicorn workers in production |
| Dependency management | Poetry | latest | Lock file, virtual env, clean packaging |

## AI / ML

| Concern | Choice | Notes |
|---|---|---|
| LLM (MVP) | OpenAI GPT-4o | Configurable via `.env`; provider abstracted behind interface |
| Embeddings | OpenAI `text-embedding-3-small` | Good quality/cost ratio; 1536 dimensions |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Runs locally via `sentence-transformers`; no API cost |
| LLM interface | LlamaIndex `OpenAI` wrapper | Swap-friendly; same interface works for local models later |
| Future LLM (Phase 2) | Ollama | For air-gapped/local deployments |

## Document Processing

| Concern | Choice | Notes |
|---|---|---|
| PDF parsing | `pdfplumber` + `pymupdf` | `pdfplumber` for text/tables; `pymupdf` for speed on large files |
| OCR (scanned PDFs) | `pytesseract` + Tesseract | Open source; runs locally |
| DOCX parsing | `python-docx` | Standard; preserves structure |
| Chunking | Custom + LlamaIndex `SentenceSplitter` | Custom logic to respect legal section/clause boundaries |
| BM25 keyword search | `rank_bm25` | Lightweight, no server needed |

## Data Storage

| Concern | Choice | Notes |
|---|---|---|
| Vector database | Qdrant (embedded mode) | Runs in-process, no separate server; strong metadata filtering; easy to move to server mode later |
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
| HTTP client | Axios + React Query | React Query for caching and loading states |
| Styling | Tailwind CSS | Utility-first, fast to build with |
| Component library | shadcn/ui | Accessible, unstyled base components; works well with Tailwind |
| Streaming | `fetch` + `EventSource` | Native browser streaming for LLM response |

## Dev Tooling

| Concern | Choice | Notes |
|---|---|---|
| Version control | Git | GitHub (or self-hosted) |
| Versioning | Semantic Versioning (`MAJOR.MINOR.PATCH`) | |
| Changelog | `CHANGELOG.md` (Keep a Changelog format) | |
| CI | GitHub Actions | Lint + test on every push to `dev` and `main` |
| Backend linting | `ruff` | Fast, replaces flake8 + isort + pyupgrade |
| Backend formatting | `black` | |
| Type checking | `mypy` | Strict mode encouraged |
| Frontend linting | ESLint + Prettier | |
| Testing — backend | `pytest` + `pytest-asyncio` | |
| Testing — frontend | Vitest | Same config as Vite |
| Local dev orchestration | `docker-compose` | Spins up backend + frontend + Qdrant together |
| Environment config | `python-dotenv` / `.env` files | `.env.example` committed; `.env` gitignored |

## Future / Phase 2

| Concern | Choice | Notes |
|---|---|---|
| Desktop packaging | Electron (frontend) + PyInstaller (backend) | Wraps local web server in a desktop app |
| Auto-update | Electron auto-updater | Built into Electron |
| Local LLM | Ollama | Drop-in replacement for OpenAI API |

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
