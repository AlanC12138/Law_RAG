# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-11-20

Merged to the default branch in `185d9c87`. Verified on 2026-11-20: 75/75 backend tests,
ruff, black, ESLint and `tsc && vite build` all clean; Alembic migrations applied
against PostgreSQL 16.

### Added
- **Citation jump-to-source** — chat source cards have copy-passage and jump-to-document buttons; jumping switches to the Documents tab and highlights the matching document card
- **Export query history** — download a matter's full Q&A history as a formatted `.docx` from the History tab
- **Folder-watch auto-ingest** — drop a PDF/DOCX into `data/watch/{matter_id}/` and it's automatically ingested, no manual upload needed
- **Matter ID display** — the admin panel now shows each matter's UUID (with a copy button), needed for folder-watch and direct API use
- **Silent token refresh** — a new `POST /auth/refresh` endpoint and a frontend interceptor retry a single 401 via refresh before forcing logout, so a session no longer drops mid-use when the access token expires
- **PostgreSQL as the default database** — `docker compose up` now starts a Postgres 16 service; schema is managed by Alembic migrations that run automatically on backend startup. SQLite remains available as a zero-dependency fallback for running the API without Docker

### Fixed
- **Backend CI had never run.** `backend-ci.yml` was invalid YAML (`DATABASE_URL: sqlite+aiosqlite:///:memory:` — a plain YAML scalar cannot end in `:`), so GitHub could not parse the file or schedule any job from it. Also: both workflows triggered on a `main` branch that does not exist in this repo (it uses `master`); the dependency cache key hashed a `poetry.lock` that was never committed, making the key constant and freezing CI on a stale venv; and `poetry install --with dev` built the root package and failed on a `readme` pointing at a non-existent file
- **Frontend CI build had failed on every run since the lock file was committed** — `package-lock.json` was generated in the `node:18-alpine` (musl) dev container, so it resolved only `@rollup/rollup-linux-x64-musl`; CI runs on glibc and needs the `-gnu` variant. Regenerated on glibc, where npm records all 25 rollup and 23 esbuild platform binaries, making the lock valid everywhere
- `app/services.py` had its module docstring below `from __future__ import annotations`, so Python treated it as a bare expression rather than a docstring (`services.__doc__` was `None`)
- Removed a dangling `readme = "README.md"` from `backend/pyproject.toml` pointing at a file that does not exist, which broke `poetry build`
- `verify_token()` now checks the JWT `type` claim — closes a gap where a refresh token could previously be used directly as an access token
- `backend/conftest.py` stubbed `python-docx` with a fake class that didn't support the methods the new export endpoint needs; removed the stub since python-docx is lightweight enough to run for real in tests

- **Upload size limit** — documents larger than `MAX_UPLOAD_SIZE_MB` (default 50 MB) are rejected with HTTP 413. The upload is read in 1 MB chunks and aborted as soon as the running total crosses the limit, so an oversized upload costs at most the limit in memory instead of its full size and never reaches disk. Note that a file *within* the limit is still buffered in full before it is written, so the ceiling on memory per upload is the limit itself, not a small constant

### Changed
- Removed the unused `@tanstack/react-query` dependency and its `QueryClientProvider` wiring — it was installed and mounted but never used anywhere; the app hand-rolls its data fetching. Drops the production bundle from 292 kB to 263 kB (90.9 kB → 82.4 kB gzipped)
- Frontend dev image moved from `node:18-alpine` to `node:20-slim` to match CI's Node 20 on glibc, so one `package-lock.json` is valid for both (see Fixed)
- Removed the unused `pymupdf` dependency (never imported — all PDF/OCR extraction goes through `pdfplumber`)
- Pinned the Qdrant image to `v1.17.1` instead of `:latest`, which had silently drifted well ahead of the `qdrant-client` version pin
- `setup.sh` / `setup.bat` now generate a random Postgres password alongside the existing `SECRET_KEY` generation

## [0.2.0] - 2026-05-19

### Added
- **Document summarisation** — after ingestion the LLM generates a concise summary of each document, displayed below the document card in the UI
- **Clause extraction** — LLM extracts structured key clauses (governing law, termination, parties, effective date, etc.) and renders them as pills on the document card
- **Multi-turn conversation memory** — chat history is sent with every query so follow-up questions work naturally ("what did you just say about indemnification?")
- **Delete matter** — partners can permanently delete a matter (Team & Settings → Matters → expand card → Delete matter); cascades through Qdrant vectors, documents, query logs, and memberships
- **Delete document purges vectors** — deleting a document now also removes its Qdrant chunks, maintaining the ethical wall

### Fixed
- Document summary and clause pills were not appearing because the UI polling stopped the moment a document hit `ready` status, before the LLM enrichment steps completed; a 5 s grace poll now fires after processing finishes
- Chat input text was lost when switching between Chat / Documents / History tabs; all three panels now stay mounted and are toggled with CSS `hidden` so component state (including unsent input) is preserved
- All buttons and form inputs appeared black in Docker due to Vite's boilerplate dark-mode CSS defaults; replaced with a light-first `@layer base` reset so Tailwind utility classes have full control
- `datetime.utcnow()` deprecated warnings throughout backend — replaced with `datetime.now(timezone.utc)`

### Changed
- Unified nav colour hierarchy: idle = white/near-white, hover = blue-50/100, active = blue-600; applied consistently across sidebar, tabs, and admin panel
- Migration error handling in `init_db.py` now distinguishes expected "duplicate column" errors (debug) from unexpected errors (warning)
- `require_partner` FastAPI dependency used consistently; removed inline role checks in matters router
- Ingestion pipeline consolidated four `_set_*` helpers into a single `_update_document(**fields)` method
- Shared `parse_llm_json()` helper in `prompt.py` used by both OpenAI and Ollama providers (eliminates duplicate markdown fence-stripping code)
- `services.py` updated with typed module-level vars and a guarded `get_embedder()` accessor

## [0.1.0] - 2026-04-11

### Added
- Initial project scaffold with complete backend and frontend structure
- FastAPI backend with async SQLAlchemy ORM
- LlamaIndex integration for RAG pipeline
- Qdrant vector database for semantic search
- JWT authentication with role-based access control (partner/associate/paralegal)
- Document ingestion pipeline with PDF, DOCX, and OCR support
- Query endpoint with hybrid search (BM25 + vector) and reranking
- React 18 frontend with TypeScript and Tailwind CSS
- Docker Compose orchestration for local development
- GitHub Actions CI/CD workflows
- Comprehensive test scaffolding with pytest
- Production-ready logging and error handling
