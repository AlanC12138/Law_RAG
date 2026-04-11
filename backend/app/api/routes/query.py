from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import check_matter_access, get_current_active_user
from app.db.models import Matter, QueryLog, User
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matters/{matter_id}/query", tags=["query"])


class QueryRequest(BaseModel):
    """Query request model."""

    question: str


class SourceReference(BaseModel):
    """Reference to a source document."""

    model_config = ConfigDict(from_attributes=True)

    doc_id: str
    filename: str
    page: int = 0
    passage: str


class QueryResponse(BaseModel):
    """Query response with answer and sources."""

    model_config = ConfigDict(from_attributes=True)

    answer: str
    sources: list[SourceReference] = []


@router.post("", response_model=QueryResponse)
async def query_matter(
    matter_id: str,
    query_req: QueryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QueryResponse:
    """Query a matter with RAG (Retrieval-Augmented Generation).

    Retrieves relevant documents and generates an answer using LLM.

    Args:
        matter_id: Matter ID to query
        query_req: Query request with question
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        QueryResponse with LLM answer and source references

    Raises:
        HTTPException: If matter not found or query fails
    """
    matter_query = select(Matter).where(Matter.id == matter_id)
    matter_result = await db.execute(matter_query)
    matter = matter_result.scalar_one_or_none()

    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    log_entry = QueryLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        matter_id=matter_id,
        query_text=query_req.question,
        answer_text="",
        source_chunk_ids=[],
    )

    db.add(log_entry)
    await db.commit()

    logger.info(f"Query logged for matter {matter_id} by user {current_user.email}")

    placeholder_answer = (
        f"Answer to '{query_req.question}' based on matter '{matter.name}'. "
        "Vector store and LLM integration pending."
    )

    return QueryResponse(
        answer=placeholder_answer,
        sources=[],
    )


@router.get("/logs", response_model=list[dict])
async def get_query_logs(
    matter_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """Get query logs for a matter.

    Args:
        matter_id: Matter ID
        current_user: Current authenticated user
        _: Matter access verification
        db: Database session

    Returns:
        List of query log entries
    """
    query = select(QueryLog).where(QueryLog.matter_id == matter_id)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "query": log.query_text,
            "answer": log.answer_text,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
