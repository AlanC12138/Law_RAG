from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents, matters, query, users
from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialise and tear down shared services."""
    from app import services
    from app.db.init_db import create_tables, seed_admin
    from app.db.session import AsyncSessionLocal

    logger = logging.getLogger(__name__)
    logger.info("Application startup — initialising database")

    # Ensure all tables exist (idempotent — safe to call on every start)
    await create_tables()

    # Seed default admin partner if no users exist yet
    async with AsyncSessionLocal() as db:
        await seed_admin(db)

    logger.info("Initialising AI services")

    # Boot all singletons (vector store, embedder, reranker, LLM).
    # The cross-encoder downloads its weights on first run (~85 MB, then cached).
    services.init(settings)
    logger.info("Services ready — application is up")

    yield

    logger.info("Application shutdown")


app = FastAPI(
    title="Law RAG API",
    description="Legal Document Retrieval-Augmented Generation System",
    version="0.1.0",
    lifespan=lifespan,
)

configure_logging(settings.log_level)

cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(matters.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
