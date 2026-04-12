from __future__ import annotations

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
    retriever = services.hybrid_retriever   # already initialised
"""

from app.config import Settings
from app.embeddings.openai_embeddings import OpenAIEmbeddingProvider
from app.llm.openai_provider import OpenAIProvider
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import QdrantVectorStore

# Module-level singletons — None until init() is called
vector_store: QdrantVectorStore | None = None
embedder: OpenAIEmbeddingProvider | None = None
reranker: CrossEncoderReranker | None = None
hybrid_retriever: HybridRetriever | None = None
llm: OpenAIProvider | None = None


def init(settings: Settings) -> None:
    """Initialise all singletons from application settings.

    Called once from the FastAPI lifespan startup event.
    Order matters: vector_store and embedder are created before
    hybrid_retriever because it depends on both.

    Args:
        settings: Loaded application settings.
    """
    global vector_store, embedder, reranker, hybrid_retriever, llm

    vector_store = QdrantVectorStore(path=settings.qdrant_path)

    embedder = OpenAIEmbeddingProvider(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    # Cross-encoder loads model weights on first call (~85 MB, cached after)
    reranker = CrossEncoderReranker()

    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        embedder=embedder,
        reranker=reranker,
    )

    llm = OpenAIProvider(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
    )


def get_hybrid_retriever() -> HybridRetriever:
    """FastAPI dependency: return the initialised HybridRetriever.

    Raises:
        RuntimeError: If services.init() has not been called yet.
    """
    if hybrid_retriever is None:
        raise RuntimeError("Services not initialised. Call services.init() on startup.")
    return hybrid_retriever


def get_llm() -> OpenAIProvider:
    """FastAPI dependency: return the initialised LLM provider.

    Raises:
        RuntimeError: If services.init() has not been called yet.
    """
    if llm is None:
        raise RuntimeError("Services not initialised. Call services.init() on startup.")
    return llm
