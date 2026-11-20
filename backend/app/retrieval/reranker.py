from __future__ import annotations

import logging
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from app.retrieval.vector_store import SearchResult

logger = logging.getLogger(__name__)

# Default model — small, fast, and strong on passage relevance scoring.
# Runs entirely locally; no API call or licence cost.
DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class RankedResult:
    """A search result after cross-encoder reranking."""

    chunk_id: str
    document_id: str
    matter_id: str
    filename: str
    text: str
    page_number: int
    section_title: str
    rerank_score: float  # Cross-encoder logit (higher = more relevant)
    original_score: float  # Fusion score from the hybrid step


class CrossEncoderReranker:
    """Reranks a candidate set using a local cross-encoder model.

    Why a cross-encoder?
    ────────────────────
    The vector search and BM25 steps both use independent representations
    of the query and each passage. A cross-encoder attends to the query
    and passage *together*, giving much more accurate relevance scores at
    the cost of latency. We only run it over the top-N candidates from
    the hybrid step (typically 20), not the full corpus, so it stays fast.

    The model runs locally via ``sentence-transformers`` — no API call,
    no token cost, and no data leaves the machine.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        """Load the cross-encoder model.

        The first call downloads the model weights (~85 MB) and caches
        them locally. Subsequent calls load from cache instantly.

        Args:
            model_name: HuggingFace model identifier.
        """
        logger.info(f"Loading cross-encoder reranker: {model_name}")
        self._model = CrossEncoder(model_name)
        logger.info("Cross-encoder reranker ready")

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5,
    ) -> list[RankedResult]:
        """Score and rerank a list of candidate results.

        Args:
            query:    The original user query string.
            results:  Candidate passages from the hybrid retriever.
            top_k:    Number of top results to return after reranking.

        Returns:
            List of RankedResult ordered by descending cross-encoder score,
            truncated to top_k.
        """
        if not results:
            return []

        # Build (query, passage) pairs for batch scoring
        pairs = [(query, r.text) for r in results]
        scores: list[float] = self._model.predict(pairs).tolist()

        ranked = sorted(
            zip(scores, results),
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            RankedResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                matter_id=result.matter_id,
                filename=result.filename,
                text=result.text,
                page_number=result.page_number,
                section_title=result.section_title,
                rerank_score=score,
                original_score=result.score,
            )
            for score, result in ranked[:top_k]
        ]
