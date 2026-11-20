"""Application-level singletons.

Heavy objects — the vector store, embedding model, cross-encoder reranker,
and LLM client — are expensive to initialise. This module holds one instance
of each, created once during the FastAPI lifespan startup and reused for
every request.

Usage
─────
From main.py lifespan:

    from app import services
    services.init(settings)

From a FastAPI dependency or route:

    from app import services
    retriever = services.get_hybrid_retriever()   # guarded accessor
    llm       = services.get_llm()
"""

from __future__ import annotations

import logging

from app.config import Settings
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)

# Module-level singletons — None until init() is called
vector_store: QdrantVectorStore | None = None
embedder: BaseEmbeddingProvider | None = None
reranker: CrossEncoderReranker | None = None
hybrid_retriever: HybridRetriever | None = None
llm: BaseLLMProvider | None = None


def init(settings: Settings) -> None:
    """Initialise all singletons from application settings.

    Selects LLM and embedding providers based on ``settings.llm_provider``:
      - ``"openai"``  → OpenAI API (requires OPENAI_API_KEY)
      - ``"ollama"``  → Local Ollama instance (requires Ollama running)

    Args:
        settings: Loaded application settings.
    """
    global vector_store, embedder, reranker, hybrid_retriever, llm

    # ── Vector store ──────────────────────────────────────────────────────────
    vector_store = QdrantVectorStore(
        path=settings.qdrant_path,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        vector_dim=settings.embedding_dim,
    )

    # ── Embedding provider ────────────────────────────────────────────────────
    if settings.llm_provider == "ollama":
        from app.embeddings.ollama_embeddings import OllamaEmbeddingProvider

        embedder = OllamaEmbeddingProvider(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )
    else:
        from app.embeddings.openai_embeddings import OpenAIEmbeddingProvider

        embedder = OpenAIEmbeddingProvider(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    # ── Cross-encoder reranker ────────────────────────────────────────────────
    reranker = CrossEncoderReranker()

    # ── Hybrid retriever ──────────────────────────────────────────────────────
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        embedder=embedder,
        reranker=reranker,
    )

    # ── LLM provider ─────────────────────────────────────────────────────────
    if settings.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        llm = OllamaProvider(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
        )
        logger.info(
            f"Using Ollama provider — LLM: {settings.ollama_llm_model}, "
            f"embeddings: {settings.ollama_embedding_model}"
        )
    else:
        from app.llm.openai_provider import OpenAIProvider

        llm = OpenAIProvider(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
        )
        logger.info(
            f"Using OpenAI provider — LLM: {settings.llm_model}, "
            f"embeddings: {settings.embedding_model}"
        )


def get_hybrid_retriever() -> HybridRetriever:
    """FastAPI dependency: return the initialised HybridRetriever."""
    if hybrid_retriever is None:
        raise RuntimeError("Services not initialised. Call services.init() on startup.")
    return hybrid_retriever


def get_llm() -> BaseLLMProvider:
    """FastAPI dependency: return the initialised LLM provider."""
    if llm is None:
        raise RuntimeError("Services not initialised. Call services.init() on startup.")
    return llm


def get_embedder() -> BaseEmbeddingProvider:
    """FastAPI dependency: return the initialised embedding provider."""
    if embedder is None:
        raise RuntimeError("Services not initialised. Call services.init() on startup.")
    return embedder
