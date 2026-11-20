# Law RAG — Project Instructions & Agreed Decisions

> This document captures all architectural decisions, product scope, and guiding principles agreed upon during initial planning. It serves as the single source of truth for the project *direction*. Update it as decisions evolve.

> **Note:** this is a planning document, so the phase scope below describes
> intent rather than what is built today. For what actually ships right now, see
> the Status table in [README.md](README.md) and [CHANGELOG.md](CHANGELOG.md).
> Verified on 2026-11-20.

---

## 1. Product Overview

A **downloadable RAG (Retrieval-Augmented Generation) application** for law firms. The system allows legal professionals to query, research, and analyze their firm's document corpus using natural language — always with precise, verifiable source citations.

The application runs locally on the firm's own infrastructure. It is not a cloud SaaS product.

---

## 2. Deployment Model

### Single-Firm Install
Each law firm receives its own completely isolated deployment:
- Its own database instance
- Its own document corpus
- Its own user accounts and permissions
- No shared infrastructure between firms

This model is non-negotiable for legal confidentiality. It simplifies the security story: client data never leaves the firm's own machines.

### LLM Connectivity — API Mode (MVP)
For the MVP, the system connects to an external LLM API (OpenAI by default, configurable). There is no local/on-device LLM in Phase 1. Local LLM support (via Ollama) is a future phase.

---

## 3. Core Features (All Phases)

### Document Ingestion
- Supported formats: PDF (including scanned), DOCX
- OCR support for scanned documents
- Metadata extraction: case number, parties, jurisdiction, document type, date filed
- Legal-aware chunking: clauses and sections are preserved intact
- Folder watch for automatic ingestion of new files dropped into a monitored directory

### Retrieval & Search
- Hybrid search: semantic (vector) + keyword (BM25)
- Metadata filtering: filter by case, date range, jurisdiction, document type
- Reranking for precision

### Q&A Interface
- Natural language queries
- Multi-document synthesis (e.g., "compare how these three contracts handle termination")
- Every answer includes clickable, precise citations: document name, page number, source passage

### Access Control
- Role-based access: Partner, Associate, Paralegal
- Matter-level permissions (ethical walls / information barriers)
- ABA compliance requirements inform all access control design

### Audit & Transparency
- Full audit log of all queries and retrieved sources
- Attorneys can verify every answer against its source

### Contract Analysis (Phase 2)
- Key clause identification: indemnification, limitation of liability, termination, governing law
- Flag missing standard clauses
- Compare against firm's preferred template
- Risk area summary

---

## 4. What Is Explicitly Out of Scope (MVP)

- Local/on-device LLM (deferred to Phase 2+)
- Document Management System integration — iManage, NetDocuments (deferred to Phase 3; ingestion pipeline is designed to be pluggable for future connectors)
- Multi-tenant / hosted SaaS architecture
- Mobile interface
- Case outcome prediction

---

## 5. Document Management Systems

DMS integration (iManage, NetDocuments) is a **Phase 3** feature. It was deferred because each platform has its own OAuth flow, API quirks, and permissioning model — adding this to the MVP would significantly slow delivery.

The ingestion pipeline must be built with a **pluggable connector interface** from day one so that DMS connectors can be added in Phase 3 without rearchitecting the core system.

In the MVP, document ingestion is handled via manual upload and folder watch.

---

## 6. Update Mechanism

The application ships with an auto-update mechanism:
- Electron auto-updater for the desktop wrapper (Phase 2)
- Backend versioning with migration scripts for database schema changes
- Versioned installers as fallback for firms that disable auto-update

---

## 7. Version Control

Git is used from day one. The repository is structured for long-term maintainability:
- Branching strategy: `main` (stable) → `dev` → feature branches
- Commits are atomic and descriptive
- All breaking changes documented in `CHANGELOG.md`
- Semantic versioning (`MAJOR.MINOR.PATCH`)

---

## 8. Development Phases

### Phase 1 — Foundation (MVP)
Repo scaffold, document ingestion (PDF/DOCX + folder watch), hybrid search, Q&A with citations, API-mode LLM, auth, matter-level access control.

### Phase 2 — Polish & Workflows
Contract analysis workflow, improved UI, audit logging, update mechanism, desktop app packaging (Windows/macOS via Electron + PyInstaller).

### Phase 3 — Integrations
DMS connectors (iManage first, then NetDocuments), advanced analytics, firm-wide usage reporting.

---

## 9. Guiding Principles

- **Verifiability first**: Every answer must be traceable to a source. The system should never present ungrounded output.
- **Steady, incremental delivery**: Ship working software at the end of every phase. No big-bang releases.
- **Pluggable by design**: Core components (LLM provider, embedding model, document connectors) are abstracted behind interfaces so they can be swapped without rearchitecting.
- **Security is not an afterthought**: Access control, audit logging, and data isolation are core features, not bolt-ons.
- **Git discipline**: Every meaningful change is committed. No orphaned work.
