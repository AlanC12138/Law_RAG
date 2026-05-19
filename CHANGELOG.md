# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
