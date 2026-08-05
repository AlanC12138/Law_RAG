from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Common English stop-words excluded from BM25 tokenisation.
# Legal documents re-use these so heavily that they add noise to scoring.
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "not",
    }
)


@dataclass
class BM25Result:
    """A single BM25 keyword search result."""

    chunk_id: str  # Qdrant point ID (_qdrant_id from payload)
    document_id: str
    matter_id: str
    filename: str
    text: str
    page_number: int
    section_title: str
    score: float  # Raw BM25 score (not normalised)


class BM25Index:
    """In-memory BM25 index built from the chunks of a single matter.

    Why build per-query rather than persist?
    ─────────────────────────────────────────
    For a single-firm install, a matter typically holds hundreds of chunks,
    not millions. Rebuilding the index per query is fast enough (<100 ms for
    typical matters) and keeps the code simple — no serialisation, no
    invalidation logic when documents are added or deleted.

    Usage
    ─────
    index = BM25Index.build(chunks)   # chunks from vector_store.scroll_by_matter()
    results = index.search("indemnification clause", top_k=20)
    """

    def __init__(self, tokenised_corpus: list[list[str]], chunks: list[dict]) -> None:
        self._bm25 = BM25Okapi(tokenised_corpus)
        self._chunks = chunks  # parallel list — index i matches corpus[i]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def build(cls, chunks: list[dict]) -> BM25Index:
        """Build an index from a list of chunk payloads.

        Args:
            chunks: List of payload dicts as returned by
                    ``QdrantVectorStore.scroll_by_matter()``.

        Returns:
            Ready-to-query BM25Index.
        """
        tokenised: list[list[str]] = [_tokenise(chunk.get("text", "")) for chunk in chunks]
        logger.debug(f"Built BM25 index over {len(chunks)} chunks")
        return cls(tokenised, chunks)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 20) -> list[BM25Result]:
        """Run a BM25 keyword search.

        Args:
            query:  Natural-language query string.
            top_k:  Maximum number of results to return.

        Returns:
            List of BM25Result ordered by descending score,
            filtered to scores > 0 (i.e. at least one query term matched).
        """
        if not self._chunks:
            return []

        query_tokens = _tokenise(query)
        scores: list[float] = self._bm25.get_scores(query_tokens).tolist()

        # Pair each chunk with its score, keep only positive matches
        scored = [(score, chunk) for score, chunk in zip(scores, self._chunks) if score > 0]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [
            BM25Result(
                chunk_id=chunk.get("_qdrant_id", ""),
                document_id=chunk.get("document_id", ""),
                matter_id=chunk.get("matter_id", ""),
                filename=chunk.get("filename", ""),
                text=chunk.get("text", ""),
                page_number=chunk.get("page_number", 0),
                section_title=chunk.get("section_title", ""),
                score=score,
            )
            for score, chunk in top
        ]


# ---------------------------------------------------------------------------
# Tokenisation helper
# ---------------------------------------------------------------------------


def _tokenise(text: str) -> list[str]:
    """Lowercase, strip punctuation, and remove stop-words.

    Args:
        text: Raw text to tokenise.

    Returns:
        List of meaningful tokens suitable for BM25.
    """
    # Lower-case and split on non-alphanumeric characters
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in tokens if t and t not in _STOP_WORDS]
