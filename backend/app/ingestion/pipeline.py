from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.config import get_settings
from app.db.models import Document, DocumentStatus
from app.ingestion.chunker import LegalChunker
from app.ingestion.ocr import extract_text_from_docx, extract_text_from_pdf

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestionPipeline:
    """Orchestrates the full document ingestion flow.

    Flow:
        1. Extract text (PDF direct or OCR, DOCX paragraph walk)
        2. Chunk with legal-aware boundaries
        3. Embed each chunk via OpenAI
        4. Store chunks + vectors in Qdrant
        5. Update the Document record in the database

    The pipeline is designed to be called as a FastAPI BackgroundTask so
    uploads return immediately and processing happens asynchronously.

    Embedder and vector store are resolved from the shared ``services``
    singletons at run time so the pipeline always uses the same Qdrant
    instance (server mode in Docker) as the query service.
    """

    def __init__(self) -> None:
        self.chunker = LegalChunker(
            max_chunk_size=settings.max_chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    async def run(
        self,
        document_id: str,
        file_bytes: bytes,
        file_type: str,
        matter_id: str,
        filename: str,
        db: AsyncSession,
    ) -> None:
        """Run the full ingestion pipeline for a single document.

        Marks the document as PROCESSING on entry and transitions it to
        READY on success or FAILED if any step raises an exception.

        Args:
            document_id: UUID of the Document row in the database.
            file_bytes:  Raw file bytes as received from the upload.
            file_type:   File extension without dot, e.g. "pdf" or "docx".
            matter_id:   Matter this document belongs to (used for filtering).
            filename:    Original filename (used in citations).
            db:          Async database session (injected from FastAPI).
        """
        logger.info(f"Starting ingestion for document {document_id} ({filename})")

        # Resolve shared singletons — guaranteed initialised by lifespan startup
        embedder = services.embedder
        vector_store = services.vector_store

        await self._set_status(db, document_id, DocumentStatus.PROCESSING)

        try:
            # ── Step 1: Text extraction ──────────────────────────────────
            if file_type == "pdf":
                extracted = extract_text_from_pdf(file_bytes)
            elif file_type in ("docx", "doc"):
                extracted = extract_text_from_docx(file_bytes)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            logger.info(
                f"Extracted {extracted.page_count} pages from {filename}"
                + (" (OCR used)" if extracted.used_ocr else "")
            )

            # ── Step 2: Legal-aware chunking ─────────────────────────────
            chunks = self.chunker.chunk_pages(extracted.pages)
            logger.info(f"Created {len(chunks)} chunks from {filename}")

            if not chunks:
                raise ValueError("Document produced no chunks after extraction")

            # ── Step 3: Embed all chunks ─────────────────────────────────
            texts = [chunk.text for chunk in chunks]
            vectors = await embedder.embed_batch(texts)

            # ── Step 4: Store in Qdrant ──────────────────────────────────
            chunks_with_vectors = [
                {
                    "vector": vectors[i],
                    "document_id": document_id,
                    "matter_id": matter_id,
                    "filename": filename,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                }
                for i, chunk in enumerate(chunks)
            ]
            vector_store.upsert_chunks(chunks_with_vectors)

            # ── Step 5: Update Document record ───────────────────────────
            await self._set_ready(db, document_id, extracted.page_count)

            # ── Steps 6–7: LLM enrichment (summary + clauses) ────────────
            llm = services.llm
            full_text = "\n\n".join(texts)
            try:
                summary = await llm.summarize(full_text)
                await self._set_summary(db, document_id, summary)
                logger.info(f"Summary generated for document {document_id}")
            except Exception as exc:
                logger.warning(f"Summarisation failed for {document_id}: {exc}")

            try:
                clauses = await llm.extract_clauses(full_text)
                if clauses:
                    await self._set_clauses(db, document_id, clauses)
                    logger.info(f"Clauses extracted for document {document_id}")
            except Exception as exc:
                logger.warning(f"Clause extraction failed for {document_id}: {exc}")

            logger.info(f"Ingestion complete for document {document_id}")

        except Exception as exc:
            logger.error(f"Ingestion failed for document {document_id}: {exc}", exc_info=True)
            await self._set_status(db, document_id, DocumentStatus.FAILED)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _set_status(
        db: AsyncSession,
        document_id: str,
        status: DocumentStatus,
    ) -> None:
        doc = await db.get(Document, document_id)
        if doc:
            doc.status = status
            await db.commit()

    @staticmethod
    async def _set_ready(
        db: AsyncSession,
        document_id: str,
        page_count: int,
    ) -> None:
        doc = await db.get(Document, document_id)
        if doc:
            doc.status = DocumentStatus.READY
            doc.page_count = page_count
            doc.ingested_at = datetime.utcnow()
            await db.commit()

    @staticmethod
    async def _set_summary(
        db: AsyncSession,
        document_id: str,
        summary: str,
    ) -> None:
        doc = await db.get(Document, document_id)
        if doc:
            doc.summary = summary
            await db.commit()

    @staticmethod
    async def _set_clauses(
        db: AsyncSession,
        document_id: str,
        clauses: dict,
    ) -> None:
        doc = await db.get(Document, document_id)
        if doc:
            doc.clauses_json = clauses
            await db.commit()
