from __future__ import annotations

import logging

from app.embeddings.base import BaseEmbeddingProvider
from app.retrieval.bm25 import BM25Index
from app.retrieval.reranker import CrossEncoderReranker, RankedResult
from app.retrieval.vector_store import QdrantVectorStore, SearchResult

logger = logging.getLogger(__name__)

# RRF constant — dampens the impact of rank position.
# k=60 is the standard value from the original RRF paper (Cormack et al., 2009).
_RRF_K = 60


class HybridRetriever:
    """Full retrieval pipeline: semantic + BM25 → RRF fusion → reranking.

    Pipeline overview
    ─────────────────
    1. Embed the query with the same model used at ingestion time.
    2. Run semantic (vector) search in Qdrant, scoped to the matter.
    3. Load all matter chunks from Qdrant and run BM25 keyword search.
    4. Merge both ranked lists with Reciprocal Rank Fusion.
    5. Rerank the top-N fused candidates with a cross-encoder.
    6. Return the final top-K results, ready to be used as LLM context.

    Access control
    ──────────────
    The ``matter_id`` parameter is passed to every search step so results
    are always restricted to a single matter. The caller (the query route)
    is responsible for verifying that the requesting user has access to
    that matter before calling this class.
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedder: BaseEmbeddingProvider,
        reranker: CrossEncoderReranker,
        semantic_top_k: int = 20,
        bm25_top_k: int = 20,
        rerank_top_k: int = 5,
    ) -> None:
        """Initialise the retriever with its three sub-components.

        Args:
            vector_store:    Qdrant wrapper for semantic search.
            embedder:        Embedding provider (must match ingestion model).
            reranker:        Cross-encoder for final scoring.
            semantic_top_k:  Candidates retrieved from vector search.
            bm25_top_k:      Candidates retrieved from BM25 search.
            rerank_top_k:    Final results returned after reranking.
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker
        self.semantic_top_k = semantic_top_k
        self.bm25_top_k = bm25_top_k
        self.rerank_top_k = rerank_top_k

    async def search(self, query: str, matter_id: str) -> list[RankedResult]:
        """Run the full hybrid retrieval pipeline.

        Args:
            query:      Natural-language question from the user.
            matter_id:  Restrict all results to this matter.

        Returns:
            Reranked list of up to ``rerank_top_k`` results.
        """
        # ── Step 1: Embed the query ──────────────────────────────────────
        query_vector = await self.embedder.embed_text(query)

        # ── Step 2: Semantic search ──────────────────────────────────────
        semantic_results = self.vector_store.search(
            query_vector=query_vector,
            matter_id=matter_id,
            top_k=self.semantic_top_k,
        )
        logger.debug(f"Semantic search returned {len(semantic_results)} results")

        # ── Step 3: BM25 keyword search ──────────────────────────────────
        matter_chunks = self.vector_store.scroll_by_matter(matter_id)
        bm25_results = []
        if matter_chunks:
            index = BM25Index.build(matter_chunks)
            bm25_results = index.search(query, top_k=self.bm25_top_k)
            logger.debug(f"BM25 search returned {len(bm25_results)} results")

        # ── Step 4: Reciprocal Rank Fusion ───────────────────────────────
        fused = _reciprocal_rank_fusion(semantic_results, bm25_results)
        logger.debug(f"RRF produced {len(fused)} fused candidates")

        if not fused:
            return []

        # ── Step 5: Rerank ───────────────────────────────────────────────
        reranked = self.reranker.rerank(query, fused, top_k=self.rerank_top_k)
        logger.debug(f"Reranker returned {len(reranked)} final results")

        return reranked


# ---------------------------------------------------------------------------
# RRF implementation
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    semantic: list[SearchResult],
    bm25: list,             # list[BM25Result] — avoid circular import with Any
    k: int = _RRF_K,
) -> list[SearchResult]:
    """Merge two ranked lists using Reciprocal Rank Fusion.

    Each result receives a score of 1 / (rank + k) from each list it
    appears in. Scores are summed across lists, giving a single unified
    ranking that balances keyword precision and semantic relevance.

    Args:
        semantic:  Ranked results from vector search (SearchResult).
        bm25:      Ranked results from BM25 (BM25Result).
        k:         RRF damping constant (default 60).

    Returns:
        Deduplicated list of SearchResult ordered by descending RRF score.
        BM25-only hits are included as SearchResult with score=0 for the
        semantic field, using the BM25 payload data.
    """
    rrf_scores: dict[str, float] = {}

    # Accumulate scores from semantic ranking
    for rank, result in enumerate(semantic):
        key = result.chunk_id
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rank + k)

    # Accumulate scores from BM25 ranking
    for rank, result in enumerate(bm25):
        key = result.chunk_id
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rank + k)

    # Build a lookup of all results by chunk_id
    all_results: dict[str, SearchResult] = {r.chunk_id: r for r in semantic}

    # Add BM25-only hits as SearchResult objects (score field holds RRF score)
    for result in bm25:
        if result.chunk_id not in all_results:
            all_results[result.chunk_id] = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                matter_id=result.matter_id,
                filename=result.filename,
                text=result.text,
                page_number=result.page_number,
                section_title=result.section_title,
                score=0.0,
            )

    # Sort by combined RRF score, attach it as the result's score field
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    fused: list[SearchResult] = []
    for cid in sorted_ids:
        result = all_results[cid]
        # Return a new SearchResult with the RRF score in the score field
        fused.append(
            SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                matter_id=result.matter_id,
                filename=result.filename,
                text=result.text,
                page_number=result.page_number,
                section_title=result.section_title,
                score=rrf_scores[cid],
            )
        )

    return fused
