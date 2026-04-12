from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.api.dependencies import check_matter_access, get_current_active_user
from app.db.models import Matter, QueryLog, User
from app.db.session import get_db
from app.llm.prompt import build_context_block
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import RankedResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matters/{matter_id}/query", tags=["query"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Incoming query from the user."""

    question: str


class SourceReference(BaseModel):
    """A single cited source returned alongside the answer."""

    model_config = ConfigDict(from_attributes=True)

    doc_id: str
    filename: str
    page: int
    section_title: str
    passage: str            # The exact chunk text shown as evidence


class QueryResponse(BaseModel):
    """Full non-streaming query response."""

    model_config = ConfigDict(from_attributes=True)

    answer: str
    sources: list[SourceReference] = []
    query_log_id: str       # Audit trail — links back to QueryLog row


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _results_to_sources(results: list[RankedResult]) -> list[SourceReference]:
    """Convert reranked results into SourceReference objects for the response."""
    return [
        SourceReference(
            doc_id=r.document_id,
            filename=r.filename,
            page=r.page_number,
            section_title=r.section_title,
            passage=r.text,
        )
        for r in results
    ]


async def _log_query(
    db: AsyncSession,
    user_id: str,
    matter_id: str,
    question: str,
    answer: str,
    results: list[RankedResult],
) -> str:
    """Persist a query and its answer to the audit log.

    Returns:
        The new QueryLog row's UUID.
    """
    log_id = str(uuid.uuid4())
    log_entry = QueryLog(
        id=log_id,
        user_id=user_id,
        matter_id=matter_id,
        query_text=question,
        answer_text=answer,
        source_chunk_ids=[r.chunk_id for r in results],
    )
    db.add(log_entry)
    await db.commit()
    return log_id


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=QueryResponse)
async def query_matter(
    matter_id: str,
    query_req: QueryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    stream: bool = Query(default=False, description="Stream tokens via SSE"),
) -> QueryResponse | StreamingResponse:
    """Query a matter using Retrieval-Augmented Generation.

    Retrieves the most relevant document chunks via hybrid search, feeds them
    to GPT-4o as grounded context, and returns an answer with precise source
    citations.

    Set ``?stream=true`` to receive a Server-Sent Events stream instead of
    waiting for the full response. Useful for long answers in the UI.

    Args:
        matter_id:    The matter to search within.
        query_req:    The user's natural-language question.
        current_user: Authenticated user (injected by dependency).
        _:            Matter access gate — raises 403 if denied.
        db:           Async database session.
        stream:       If True, return an SSE streaming response.

    Returns:
        ``QueryResponse`` (JSON) or ``StreamingResponse`` (SSE).

    Raises:
        HTTPException: 404 if matter not found, 503 if retrieval returns nothing.
    """
    # Verify matter exists
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")

    retriever: HybridRetriever = services.get_hybrid_retriever()
    llm = services.get_llm()

    # Retrieve relevant chunks
    results = await retriever.search(query=query_req.question, matter_id=matter_id)
    logger.info(
        f"Retrieved {len(results)} chunks for query in matter {matter_id} "
        f"by user {current_user.email}"
    )

    if not results:
        empty_answer = (
            "I could not find any relevant documents for your question "
            "in the available matter files."
        )
        await _log_query(db, current_user.id, matter_id, query_req.question, empty_answer, [])
        return QueryResponse(answer=empty_answer, sources=[], query_log_id="")

    context = build_context_block(results)
    sources = _results_to_sources(results)

    # --- Streaming path ---
    if stream:
        return StreamingResponse(
            _stream_sse(
                question=query_req.question,
                context=context,
                sources=sources,
                results=results,
                llm=llm,
                db=db,
                user_id=current_user.id,
                matter_id=matter_id,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # --- Non-streaming path ---
    answer = await llm.complete(prompt=query_req.question, context=context)
    log_id = await _log_query(
        db, current_user.id, matter_id, query_req.question, answer, results
    )

    return QueryResponse(answer=answer, sources=sources, query_log_id=log_id)


async def _stream_sse(
    question: str,
    context: str,
    sources: list[SourceReference],
    results: list[RankedResult],
    llm,
    db: AsyncSession,
    user_id: str,
    matter_id: str,
) -> AsyncIterator[str]:
    """Yield Server-Sent Events for a streaming query response.

    Event format:
        data: {"type": "token",   "content": "<token>"}
        data: {"type": "sources", "content": [<SourceReference>, ...]}
        data: {"type": "done"}

    The frontend accumulates "token" events to build the answer string,
    then renders the sources from the final "sources" event.
    """
    full_answer: list[str] = []

    try:
        async for token in llm.stream_complete(prompt=question, context=context):
            full_answer.append(token)
            payload = json.dumps({"type": "token", "content": token})
            yield f"data: {payload}\n\n"

        # Send sources as a single event at the end
        sources_payload = json.dumps({
            "type": "sources",
            "content": [s.model_dump() for s in sources],
        })
        yield f"data: {sources_payload}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    finally:
        # Always log, even if the client disconnects mid-stream
        answer_text = "".join(full_answer)
        if answer_text:
            await _log_query(db, user_id, matter_id, question, answer_text, results)


# ---------------------------------------------------------------------------
# Audit log endpoint
# ---------------------------------------------------------------------------

@router.get("/logs", response_model=list[dict])
async def get_query_logs(
    matter_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _: Annotated[str, Depends(check_matter_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """Return the query audit log for a matter.

    Only accessible to users with matter access. Partners can see all
    queries; associates and paralegals see only their own.

    Args:
        matter_id:    The matter whose logs to retrieve.
        current_user: Authenticated user.
        _:            Matter access gate.
        db:           Async database session.

    Returns:
        List of query log dicts ordered by most recent first.
    """
    from app.db.models import UserRole

    query = select(QueryLog).where(QueryLog.matter_id == matter_id)

    # Non-partners only see their own queries
    if current_user.role != UserRole.PARTNER:
        query = query.where(QueryLog.user_id == current_user.id)

    query = query.order_by(QueryLog.created_at.desc())
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
