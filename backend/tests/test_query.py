"""Integration tests for the /api/v1/matters/{id}/query endpoint.

The AI services (HybridRetriever and LLM) are mocked so tests run offline
without any OpenAI API keys, Qdrant data, or ML model weights.
"""
from __future__ import annotations

import uuid
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers
from app.db.models import MatterMembership, QueryLog, UserRole
from app.retrieval.reranker import RankedResult


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

def _mock_ranked_result(chunk_id: str = "chunk-1") -> RankedResult:
    """Build a minimal RankedResult for mocking retrieval output."""
    result = MagicMock(spec=RankedResult)
    result.chunk_id = chunk_id
    result.document_id = str(uuid.uuid4())
    result.filename = "contract.pdf"
    result.page_number = 3
    result.section_title = "Section 4 — Indemnification"
    result.text = "The indemnifying party shall hold harmless the other party."
    result.score = 0.95
    return result


# ---------------------------------------------------------------------------
# Non-streaming query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_returns_answer_and_sources(
    async_client: AsyncClient, partner, matter
) -> None:
    """Successful query returns a JSON answer with source citations."""
    mock_results = [_mock_ranked_result()]

    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = mock_results

    mock_llm = AsyncMock()
    mock_llm.complete.return_value = "The indemnification clause is on page 3."

    with (
        patch("app.api.routes.query.services.get_hybrid_retriever", return_value=mock_retriever),
        patch("app.api.routes.query.services.get_llm", return_value=mock_llm),
    ):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/query",
            headers=auth_headers(partner),
            json={"question": "What does the indemnification clause say?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "indemnification" in body["answer"].lower()
    assert len(body["sources"]) == 1
    assert body["sources"][0]["filename"] == "contract.pdf"
    assert body["sources"][0]["page"] == 3
    assert "query_log_id" in body


@pytest.mark.asyncio
async def test_query_no_results_returns_empty_answer(
    async_client: AsyncClient, partner, matter
) -> None:
    """When retrieval returns nothing, a graceful 'not found' message is returned."""
    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = []

    with (
        patch("app.api.routes.query.services.get_hybrid_retriever", return_value=mock_retriever),
        patch("app.api.routes.query.services.get_llm", return_value=AsyncMock()),
    ):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/query",
            headers=auth_headers(partner),
            json={"question": "Does this matter contain a NDA?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "could not find" in body["answer"].lower()


@pytest.mark.asyncio
async def test_query_denied_for_non_member(
    async_client: AsyncClient, associate, matter
) -> None:
    """Users without matter access cannot query it — ethical wall holds."""
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/query",
        headers=auth_headers(associate),
        json={"question": "Confidential question?"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_query_unauthenticated(async_client: AsyncClient, matter) -> None:
    """Unauthenticated query request is rejected (HTTPBearer returns 403)."""
    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/query",
        json={"question": "Hello?"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_query_logs_are_persisted(
    async_client: AsyncClient,
    partner,
    matter,
    test_db: AsyncSession,
) -> None:
    """Each query must create a QueryLog row in the database."""
    from sqlalchemy import select

    mock_results = [_mock_ranked_result()]
    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = mock_results
    mock_llm = AsyncMock()
    mock_llm.complete.return_value = "Answer text."

    with (
        patch("app.api.routes.query.services.get_hybrid_retriever", return_value=mock_retriever),
        patch("app.api.routes.query.services.get_llm", return_value=mock_llm),
    ):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/query",
            headers=auth_headers(partner),
            json={"question": "Audit log test query"},
        )

    assert response.status_code == 200
    log_id = response.json()["query_log_id"]

    result = await test_db.execute(select(QueryLog).where(QueryLog.id == log_id))
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.query_text == "Audit log test query"
    assert log.answer_text == "Answer text."
    assert log.matter_id == matter.id
    assert log.user_id == partner.id


# ---------------------------------------------------------------------------
# Streaming query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_stream_returns_sse_events(
    async_client: AsyncClient, partner, matter
) -> None:
    """Streaming query returns text/event-stream with token, sources, done events."""
    mock_results = [_mock_ranked_result()]

    async def fake_stream(**_) -> AsyncIterator[str]:
        for token in ["The ", "clause ", "applies."]:
            yield token

    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = mock_results

    mock_llm = MagicMock()
    mock_llm.stream_complete = fake_stream

    with (
        patch("app.api.routes.query.services.get_hybrid_retriever", return_value=mock_retriever),
        patch("app.api.routes.query.services.get_llm", return_value=mock_llm),
    ):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/query?stream=true",
            headers=auth_headers(partner),
            json={"question": "Stream this."},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    raw = response.text
    assert 'data:' in raw
    assert '"type": "token"' in raw or '"type":"token"' in raw
    assert '"type": "sources"' in raw or '"type":"sources"' in raw
    assert '"type": "done"' in raw or '"type":"done"' in raw


# ---------------------------------------------------------------------------
# Query audit log endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_query_logs_partner_sees_all(
    async_client: AsyncClient,
    partner,
    associate,
    matter,
    test_db: AsyncSession,
) -> None:
    """Partners see every query in the matter, regardless of who asked it."""
    # Add associate to matter
    test_db.add(
        MatterMembership(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            granted_by=partner.id,
        )
    )
    # Seed two query log rows from different users
    test_db.add(
        QueryLog(
            id=str(uuid.uuid4()),
            user_id=partner.id,
            matter_id=matter.id,
            query_text="Partner query",
            answer_text="Partner answer",
            source_chunk_ids=[],
        )
    )
    test_db.add(
        QueryLog(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            query_text="Associate query",
            answer_text="Associate answer",
            source_chunk_ids=[],
        )
    )
    await test_db.commit()

    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/query/logs",
        headers=auth_headers(partner),
    )
    assert response.status_code == 200
    queries = [log["query"] for log in response.json()]
    assert "Partner query" in queries
    assert "Associate query" in queries


@pytest.mark.asyncio
async def test_get_query_logs_associate_sees_own_only(
    async_client: AsyncClient,
    partner,
    associate,
    matter,
    test_db: AsyncSession,
) -> None:
    """Associates only see their own queries in the audit log."""
    # Add associate to matter
    test_db.add(
        MatterMembership(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            granted_by=partner.id,
        )
    )
    test_db.add(
        QueryLog(
            id=str(uuid.uuid4()),
            user_id=partner.id,
            matter_id=matter.id,
            query_text="Secret partner query",
            answer_text="Secret answer",
            source_chunk_ids=[],
        )
    )
    test_db.add(
        QueryLog(
            id=str(uuid.uuid4()),
            user_id=associate.id,
            matter_id=matter.id,
            query_text="My associate query",
            answer_text="My answer",
            source_chunk_ids=[],
        )
    )
    await test_db.commit()

    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/query/logs",
        headers=auth_headers(associate),
    )
    assert response.status_code == 200
    logs = response.json()
    queries = [log["query"] for log in logs]
    assert "My associate query" in queries
    assert "Secret partner query" not in queries


@pytest.mark.asyncio
async def test_get_query_logs_non_member_denied(
    async_client: AsyncClient, associate, matter
) -> None:
    """Non-members cannot read the query audit log."""
    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/query/logs",
        headers=auth_headers(associate),
    )
    assert response.status_code == 403
