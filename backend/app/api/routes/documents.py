from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import check_matter_access, get_current_active_user
from app.db.models import Document, DocumentStatus, Matter, User
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matters/{matter_id}/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    """Document response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    status: str
    page_count: int
    created_at: str


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    matter_id: str,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DocumentResponse:
    """Upload a document to a matter.

    Args:
        matter_id: Matter ID
        file: Document file to upload
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        Created document

    Raises:
        HTTPException: If matter not found or upload fails
    """
    matter_query = select(Matter).where(Matter.id == matter_id)
    matter_result = await db.execute(matter_query)
    matter = matter_result.scalar_one_or_none()

    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    doc_id = str(uuid.uuid4())
    file_type = file.filename.split(".")[-1].lower() if file.filename else "unknown"
    storage_path = f"data/documents/{matter_id}/{doc_id}.{file_type}"

    document = Document(
        id=doc_id,
        matter_id=matter_id,
        filename=file.filename or "unknown",
        file_type=file_type,
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
        page_count=0,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(f"Document uploaded: {file.filename} to matter {matter_id}")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
        page_count=document.page_count,
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
    query = select(Document).where(
        (Document.id == doc_id) & (Document.matter_id == matter_id)
    )
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
        created_at=document.created_at.isoformat(),
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    matter_id: str,
    doc_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    _: Annotated[str, Depends(check_matter_access)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> None:
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
    query = select(Document).where(
        (Document.id == doc_id) & (Document.matter_id == matter_id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await db.delete(document)
    await db.commit()

    logger.info(f"Document deleted: {doc_id}")
