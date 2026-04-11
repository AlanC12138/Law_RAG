# Law RAG — MVP Scope (Phase 1)

> The MVP delivers a fully usable, local RAG application for a single law firm. It is the smallest complete slice of the product that provides real value to attorneys and paralegals.

---

## MVP Goal

A law firm employee can:
1. Ingest their firm's documents (PDF, DOCX)
2. Ask natural language questions about those documents
3. Receive answers with precise, verifiable citations
4. Have their access automatically restricted to matters they are permitted to see

---

## In Scope

### 1. Repository & Project Foundation
- [ ] Git repository with proper structure (monorepo: `backend/`, `frontend/`, `docs/`)
- [ ] `.gitignore`, `README.md`, `CHANGELOG.md`
- [ ] Environment config (`.env.example`)
- [ ] Basic CI config (GitHub Actions: lint + test on push)

### 2. Backend — FastAPI Application
- [ ] FastAPI app skeleton with health check endpoint
- [ ] Configuration management (API keys, model names, paths loaded from `.env`)
- [ ] Structured logging (JSON logs, request IDs)
- [ ] Error handling middleware

### 3. Document Ingestion Pipeline
- [ ] PDF ingestion (including scanned PDFs via OCR)
- [ ] DOCX ingestion
- [ ] Metadata extraction: document type, date, case/matter ID, parties, jurisdiction
- [ ] Legal-aware chunking strategy (respect section and clause boundaries)
- [ ] Folder watch: monitor a directory and auto-ingest new files
- [ ] Manual upload endpoint
- [ ] Pluggable connector interface (abstract base class) — so DMS connectors slot in later without refactoring

### 4. Vector Store & Embeddings
- [ ] Qdrant running in embedded/local mode (no separate server process)
- [ ] OpenAI `text-embedding-3-small` for generating embeddings
- [ ] Store chunks with full metadata (matter ID, document ID, page, section)
- [ ] Metadata filtering support in all search queries

### 5. Search & Retrieval
- [ ] Semantic search (vector similarity via Qdrant)
- [ ] Keyword search (BM25 via `rank_bm25`)
- [ ] Hybrid search: reciprocal rank fusion of both
- [ ] Reranking with a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- [ ] Configurable top-k retrieval

### 6. LLM Integration (API Mode)
- [ ] OpenAI GPT-4o as default LLM
- [ ] LlamaIndex orchestration for query pipeline
- [ ] System prompt engineered for legal Q&A (grounded answers, citation format)
- [ ] LLM provider abstracted behind an interface (for future swap to local or other providers)
- [ ] Streaming responses to frontend

### 7. Q&A API Endpoints
- [ ] `POST /query` — natural language question, returns answer + sources
- [ ] `GET /documents` — list ingested documents (filtered by matter access)
- [ ] `POST /ingest` — trigger ingestion of a file
- [ ] `GET /matters` — list matters accessible to the current user

### 8. Auth & Access Control
- [ ] Local user accounts (username + hashed password, no external IdP)
- [ ] JWT-based session tokens
- [ ] Roles: `partner`, `associate`, `paralegal`
- [ ] Matter-level permissions: users are assigned to matters; queries automatically scoped
- [ ] Ethical wall enforcement: access to a matter's documents denied unless explicitly granted
- [ ] `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`

### 9. Relational Database (SQLite)
- [ ] Tables: `users`, `roles`, `matters`, `matter_memberships`, `documents`, `query_logs`
- [ ] Alembic migrations from day one
- [ ] Audit log: every query stored with user ID, timestamp, retrieved source IDs

### 10. Frontend — React Web UI
- [ ] Vite + React project
- [ ] Login screen
- [ ] Matter selector (sidebar)
- [ ] Chat interface: send query, receive streamed answer
- [ ] Source panel: each answer shows its cited sources with document name, page, and passage
- [ ] Document list view per matter
- [ ] Basic upload UI (drag-and-drop)

---

## Out of Scope for MVP

- Desktop packaging (Electron / PyInstaller) — Phase 2
- Contract analysis workflow — Phase 2
- Auto-update mechanism — Phase 2
- Local LLM (Ollama) — Phase 2
- DMS integrations (iManage, NetDocuments) — Phase 3
- Multi-matter cross-search — Phase 3
- Analytics / usage dashboards — Phase 3

---

## MVP Definition of Done

The MVP is complete when:

1. A user can log in and see only the matters they are permitted to access.
2. A user can upload a PDF or DOCX to a matter and see it appear in the document list.
3. A user can ask a natural language question and receive an answer with inline citations pointing to the exact source document and page.
4. A partner can create users and assign them to matters.
5. All API endpoints are covered by at least one integration test.
6. The application runs end-to-end from a single `docker-compose up` or `make dev` command.

---

## Suggested Build Order

Building in this order minimizes blocked work and lets you test end-to-end quickly:

1. Repo scaffold + backend skeleton (health check, config, logging)
2. Database models + Alembic migrations
3. Auth endpoints (login/logout/me)
4. Document ingestion pipeline (PDF + DOCX, chunking, embeddings → Qdrant)
5. Search & retrieval (hybrid search + reranking)
6. Q&A endpoint (LlamaIndex pipeline + GPT-4o)
7. Frontend — auth + chat interface
8. Frontend — document management + source panel
9. Matter-level access control wired end-to-end
10. Integration tests + CI
