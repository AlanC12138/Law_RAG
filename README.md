# Law RAG - Legal Document Retrieval and Generation System

A production-grade Retrieval-Augmented Generation (RAG) application designed for legal professionals. Law RAG enables attorneys and paralegals to query large collections of legal documents, matter files, and case law with semantically-aware search, powered by modern LLMs and vector databases.

## Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+
- **Tesseract OCR**: Required for document parsing
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
  - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **Docker & Docker Compose**: For containerized deployment

## Quick Start

### 1. Clone and Setup

```bash
git clone <repo-url>
cd Law_RAG
```

### 2. Configure Environment

```bash
# Copy the example config and customize
cp backend/.env.example backend/.env

# Edit backend/.env and add your OpenAI API key and other secrets
# CRITICAL: SECRET_KEY must be a long random string for production
```

### 3. Run with Docker Compose

```bash
# Start all services (backend, frontend, Qdrant)
docker-compose up -d

# Backend API: http://localhost:8000
# Frontend UI: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head
```

### 5. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
Law_RAG/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routes and dependencies
│   │   │   ├── routes/        # Endpoint modules (auth, documents, matters, query)
│   │   │   └── dependencies.py
│   │   ├── core/              # Cross-cutting concerns
│   │   │   ├── logging.py     # Structured logging
│   │   │   └── security.py    # JWT, password utilities
│   │   ├── db/                # Database layer
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   ├── base.py        # Declarative base
│   │   │   └── session.py     # Session factory
│   │   ├── connectors/        # Document source connectors
│   │   │   ├── base.py        # Abstract interface
│   │   │   └── folder_watch.py
│   │   ├── llm/               # LLM abstraction layer
│   │   │   ├── base.py        # Abstract interface
│   │   │   └── openai_provider.py
│   │   ├── embeddings/        # Embedding abstraction
│   │   │   ├── base.py        # Abstract interface
│   │   │   └── openai_embeddings.py
│   │   └── main.py            # FastAPI application
│   ├── tests/                 # Unit and integration tests
│   ├── alembic/               # Database migrations
│   ├── Dockerfile
│   ├── pyproject.toml         # Poetry configuration
│   └── .env.example           # Configuration template
├── frontend/
│   ├── src/
│   │   ├── api/               # API client and hooks
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable UI components
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── .github/
│   └── workflows/             # CI/CD pipelines
├── docker-compose.yml
├── README.md                  # This file
├── CHANGELOG.md
├── INSTRUCTIONS.md            # Product requirements
├── MVP.md                     # MVP scope
└── TECH_STACK.md              # Technology choices
```

## Development Workflow

### Backend Development

```bash
# Install dependencies
cd backend
poetry install

# Run development server
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest -v

# Run linting
poetry run ruff check .
poetry run black --check .
poetry run mypy .
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Architecture

### Core Concepts

- **Documents**: Legal documents uploaded by users (PDFs, DOCX, etc.)
- **Matters**: Legal cases or projects that organize documents
- **Queries**: User questions about matter documents answered by LLM with retrieved context
- **Vector Store**: Qdrant database for semantic document search
- **Reranking**: MS MARCO cross-encoder for relevance ranking before LLM

### Authentication Flow

1. User logs in with email/password
2. Server validates credentials and issues JWT access/refresh tokens
3. Frontend stores tokens in localStorage
4. Subsequent API calls include JWT in Authorization header
5. Server validates token on each request

### Document Ingestion

1. User uploads document to matter
2. Document file is stored and parsed (PDF, DOCX, images with OCR)
3. Content is chunked with overlap (BM25 + semantic search)
4. Chunks are embedded using OpenAI text-embedding-3-small
5. Embeddings and metadata stored in Qdrant
6. Document status transitions to "ready"

### Query Flow

1. User submits question about a matter
2. Backend embeds the question
3. Hybrid search: BM25 (fast, keyword) + vector search (semantic)
4. Reranker scores results by relevance
5. Top chunks sent as context to GPT-4o with prompt
6. LLM generates answer with citations
7. Results stored in QueryLog for audit trail

## Branching Strategy

- **main**: Production-ready code, tagged releases
- **dev**: Integration branch for feature development
- **feature/**: Individual feature branches, e.g., `feature/reranking-tuning`
- **bugfix/**: Bug fixes, e.g., `bugfix/token-expiry`

## CI/CD

GitHub Actions workflows run on every push and pull request:
- **backend-ci**: Lint (ruff, black), test (pytest), type check (mypy)
- **frontend-ci**: Lint (ESLint), build (Vite)

## API Documentation

Once running, visit http://localhost:8000/docs for interactive Swagger UI.

Key endpoints:
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/matters` - Create matter (partner only)
- `POST /api/v1/matters/{matter_id}/documents` - Upload document
- `POST /api/v1/matters/{matter_id}/query` - Ask question about matter

## Configuration

All configuration is driven by environment variables in `.env` file. See `backend/.env.example` for all available options.

## Support & Documentation

- See `INSTRUCTIONS.md` for product vision and requirements
- See `MVP.md` for MVP scope
- See `TECH_STACK.md` for technology rationale
