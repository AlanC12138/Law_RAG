from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)

# Name of the single Qdrant collection used by the application.
COLLECTION_NAME = "law_rag_chunks"

# Embedding dimension for OpenAI text-embedding-3-small.
VECTOR_DIM = 1536


@dataclass
class SearchResult:
    """A single result from a vector similarity search."""

    chunk_id: str
    document_id: str
    matter_id: str
    filename: str
    text: str               # The raw chunk text
    page_number: int
    section_title: str
    score: float            # Similarity score (0–1, higher = more relevant)


class QdrantVectorStore:
    """Thin wrapper around Qdrant for storing and searching document chunks.

    Each chunk is stored as a Qdrant point with:
    - A dense vector (the embedding)
    - A payload containing all metadata needed to build a citation

    Matter-level access control is enforced by filtering on the
    ``matter_id`` payload field at query time — queries only ever
    return chunks belonging to the requested matter.
    """

    def __init__(self, path: str) -> None:
        """Initialise the vector store in embedded (local) mode.

        Args:
            path: Directory path for Qdrant's on-disk storage.
        """
        self.client = QdrantClient(path=path)
        self._ensure_collection()

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self.client.get_collections().collections}
        if COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.debug(f"Qdrant collection already exists: {COLLECTION_NAME}")

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        chunks_with_vectors: list[dict],
    ) -> None:
        """Insert or update a batch of chunks in the vector store.

        Each dict in ``chunks_with_vectors`` must contain:
            vector       (list[float])  — the embedding
            document_id  (str)
            matter_id    (str)
            filename     (str)
            text         (str)
            chunk_index  (int)
            page_number  (int)
            section_title (str)

        Args:
            chunks_with_vectors: List of chunk dicts with embeddings attached.
        """
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=c["vector"],
                payload={
                    "document_id": c["document_id"],
                    "matter_id": c["matter_id"],
                    "filename": c["filename"],
                    "text": c["text"],
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"],
                    "section_title": c["section_title"],
                },
            )
            for c in chunks_with_vectors
        ]

        self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.debug(f"Upserted {len(points)} chunks into Qdrant")

    def scroll_by_matter(self, matter_id: str) -> list[dict]:
        """Retrieve the payload of every chunk belonging to a matter.

        Used by the BM25 retriever to build a keyword index scoped to
        the matter being queried. Paginates automatically so large matters
        are handled correctly.

        Args:
            matter_id: The matter whose chunks should be returned.

        Returns:
            List of payload dicts (same fields stored by upsert_chunks).
        """
        matter_filter = Filter(
            must=[
                FieldCondition(
                    key="matter_id",
                    match=MatchValue(value=matter_id),
                )
            ]
        )

        all_payloads: list[dict] = []
        offset = None

        while True:
            results, next_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=matter_filter,
                limit=256,          # fetch in pages of 256
                offset=offset,
                with_payload=True,
                with_vectors=False, # payloads only — no need to load vectors
            )
            for point in results:
                payload = dict(point.payload)
                payload["_qdrant_id"] = str(point.id)
                all_payloads.append(payload)

            if next_offset is None:
                break
            offset = next_offset

        logger.debug(f"Scrolled {len(all_payloads)} chunks for matter {matter_id}")
        return all_payloads

    def delete_document(self, document_id: str) -> None:
        """Remove all chunks belonging to a document.

        Called when a document is deleted so no stale chunks remain.

        Args:
            document_id: The document whose chunks should be removed.
        """
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        logger.info(f"Deleted chunks for document: {document_id}")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        matter_id: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Semantic search restricted to a single matter.

        Args:
            query_vector: Embedded query vector.
            matter_id:    Only return chunks from this matter (access control).
            top_k:        Maximum number of results to return.

        Returns:
            List of SearchResult ordered by descending similarity.
        """
        matter_filter = Filter(
            must=[
                FieldCondition(
                    key="matter_id",
                    match=MatchValue(value=matter_id),
                )
            ]
        )

        hits = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=matter_filter,
            limit=top_k,
            with_payload=True,
        )

        return [
            SearchResult(
                chunk_id=str(hit.id),
                document_id=hit.payload["document_id"],
                matter_id=hit.payload["matter_id"],
                filename=hit.payload["filename"],
                text=hit.payload["text"],
                page_number=hit.payload["page_number"],
                section_title=hit.payload.get("section_title", ""),
                score=hit.score,
            )
            for hit in hits
        ]
