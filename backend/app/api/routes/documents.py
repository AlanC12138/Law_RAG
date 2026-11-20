from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.api.dependencies import check_matter_access, get_current_active_user
from app.config import get_settings
from app.db.models import Document, DocumentStatus, Matter, User
from app.db.session import get_db
from app.ingestion.pipeline import IngestionPipeline

settings = get_settings()
_pipeline = IngestionPipeline()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matters/{matter_id}/documents", tags=["documents"])

# Size of each read when streaming an upload in for the size check
_UPLOAD_CHUNK_BYTES = 1024 * 1024


class DocumentResponse(BaseModel):
    """Document response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    status: str
    page_count: int
    summary: str | None = None
    clauses: dict | None = None
    created_at: str


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    matter_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentResponse:
    """Upload a document to a matter and queue it for ingestion.

    The file is saved to disk immediately and the ingestion pipeline
    (text extraction → chunking → embedding → vector store) runs as a
    background task so this endpoint returns without blocking.

    Args:
        matter_id:        Matter ID the document belongs to.
        background_tasks: FastAPI background task queue.
        file:             Uploaded file (PDF or DOCX).
        current_user:     Current authenticated user.
        _:                Matter access gate (raises 403 if denied).
        db:               Async database session.

    Returns:
        Created Document record (status will be PENDING → PROCESSING → READY).

    Raises:
        HTTPException: 404 if matter not found, 400 for unsupported file
            types, 413 if the file exceeds MAX_UPLOAD_SIZE_MB.
    """
    # Validate file type
    allowed_types = {"pdf", "docx", "doc"}
    file_type = (file.filename or "").rsplit(".", 1)[-1].lower()
    if file_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_type}'. Allowed: {', '.join(allowed_types)}",
        )

    matter_query = select(Matter).where(Matter.id == matter_id)
    matter_result = await db.execute(matter_query)
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    # Read file bytes before the request context closes.
    # Read in chunks and bail out as soon as the size limit is exceeded, so an
    # oversized upload costs at most max_bytes (+1 chunk) rather than its full
    # size. A file within the limit is still buffered whole before it is written.
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total_bytes = 0
    while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            logger.warning(
                f"Rejected oversized upload {file.filename!r} "
                f"(>{settings.max_upload_size_mb} MB) from {current_user.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File exceeds the maximum upload size of {settings.max_upload_size_mb} MB."
                ),
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # Persist file to disk
    doc_id = str(uuid.uuid4())
    storage_dir = Path(settings.data_dir) / "documents" / matter_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{doc_id}.{file_type}"
    storage_path.write_bytes(file_bytes)

    # Create DB record (status = PENDING; pipeline will update it)
    document = Document(
        id=doc_id,
        matter_id=matter_id,
        filename=file.filename or "unknown",
        file_type=file_type,
        storage_path=str(storage_path),
        status=DocumentStatus.PENDING,
        page_count=0,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Queue ingestion — runs after this response is sent
    background_tasks.add_task(
        _pipeline.run,
        document_id=doc_id,
        file_bytes=file_bytes,
        file_type=file_type,
        matter_id=matter_id,
        filename=file.filename or "unknown",
        db=db,
    )

    logger.info(f"Document uploaded and queued for ingestion: {file.filename} → matter {matter_id}")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
        page_count=document.page_count,
        summary=document.summary,
        clauses=document.clauses_json,
        created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    matter_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[DocumentResponse]:
    """List documents in a matter.

    Args:
        matter_id: Matter ID
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        List of documents in matter
    """
    query = select(Document).where(Document.matter_id == matter_id)
    result = await db.execute(query)
    documents = result.scalars().all()

    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            status=doc.status,
            page_count=doc.page_count,
            summary=doc.summary,
            clauses=doc.clauses_json,
            created_at=doc.created_at.isoformat(),
        )
        for doc in documents
    ]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    matter_id: str,
    doc_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentResponse:
    """Get document metadata.

    Args:
        matter_id: Matter ID
        doc_id: Document ID
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        Document metadata

    Raises:
        HTTPException: If document not found
    """
    query = select(Document).where((Document.id == doc_id) & (Document.matter_id == matter_id))
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
        page_count=document.page_count,
        summary=document.summary,
        clauses=document.clauses_json,
        created_at=document.created_at.isoformat(),
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    matter_id: str,
    doc_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> Response:
    """Delete a document from a matter.

    Args:
        matter_id: Matter ID
        doc_id: Document ID
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Raises:
        HTTPException: If document not found
    """
    query = select(Document).where((Document.id == doc_id) & (Document.matter_id == matter_id))
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Remove vector chunks from Qdrant first — this is the ethical-wall guarantee.
    # If the vector store call fails we still delete the DB row so the document
    # is not accessible, but we log the error so orphaned chunks can be cleaned up.
    try:
        if services.vector_store is not None:
            services.vector_store.delete_document(doc_id)
    except Exception as exc:
        logger.error(f"Failed to delete Qdrant chunks for document {doc_id}: {exc}", exc_info=True)

    await db.delete(document)
    await db.commit()

    logger.info(f"Document deleted: {doc_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
