# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
