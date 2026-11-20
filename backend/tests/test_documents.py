"""Integration tests for the /api/v1/matters/{id}/documents endpoints.

Document upload tests mock the ingestion pipeline so tests don't require
real ML models or a running Qdrant instance.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pdf_upload(filename: str = "contract.pdf") -> tuple[str, tuple]:
    """Return a (field_name, (filename, bytes, content_type)) tuple for multipart."""
    content = b"%PDF-1.4 fake pdf content for testing"
    return ("file", (filename, io.BytesIO(content), "application/pdf"))


def docx_upload(filename: str = "brief.docx") -> tuple[str, tuple]:
    content = b"PK fake docx content"
    return (
        "file",
        (
            filename,
            io.BytesIO(content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )


# ---------------------------------------------------------------------------
# POST /matters/{id}/documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf(
    async_client: AsyncClient, partner, matter, tmp_path, monkeypatch
) -> None:
    """PDF upload creates a Document record with PENDING status."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))

    with patch("app.api.routes.documents._pipeline.run", new_callable=AsyncMock):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/documents",
            headers=auth_headers(partner),
            files=[pdf_upload()],
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "contract.pdf"
    assert body["file_type"] == "pdf"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_docx(
    async_client: AsyncClient, partner, matter, tmp_path, monkeypatch
) -> None:
    """DOCX upload is also accepted."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))

    with patch("app.api.routes.documents._pipeline.run", new_callable=AsyncMock):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/documents",
            headers=auth_headers(partner),
            files=[docx_upload()],
        )

    assert response.status_code == 201
    assert response.json()["file_type"] == "docx"


@pytest.mark.asyncio
async def test_upload_invalid_type(
    async_client: AsyncClient, partner, matter, tmp_path, monkeypatch
) -> None:
    """Non-PDF/DOCX files are rejected with 400."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))

    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/documents",
        headers=auth_headers(partner),
        files=[("file", ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream"))],
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(
    async_client: AsyncClient, partner, matter, tmp_path, monkeypatch
) -> None:
    """Files larger than MAX_UPLOAD_SIZE_MB are rejected with 413 and nothing
    is persisted to disk."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))
    monkeypatch.setattr("app.api.routes.documents.settings.max_upload_size_mb", 1)

    oversized = b"%PDF-1.4" + b"x" * (2 * 1024 * 1024)  # 2 MB against a 1 MB limit
    with patch("app.api.routes.documents._pipeline.run", new_callable=AsyncMock):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/documents",
            headers=auth_headers(partner),
            files=[("file", ("huge.pdf", io.BytesIO(oversized), "application/pdf"))],
        )

    assert response.status_code == 413
    assert "maximum upload size" in response.json()["detail"].lower()
    # The rejected upload must not have been written to disk
    assert not list(tmp_path.rglob("*.pdf"))


@pytest.mark.asyncio
async def test_upload_accepts_file_under_limit(
    async_client: AsyncClient, partner, matter, tmp_path, monkeypatch
) -> None:
    """A file under the limit still uploads normally — the new size check must
    not reject valid uploads."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))
    monkeypatch.setattr("app.api.routes.documents.settings.max_upload_size_mb", 1)

    content = b"%PDF-1.4" + b"x" * 1024  # ~1 KB
    with patch("app.api.routes.documents._pipeline.run", new_callable=AsyncMock):
        response = await async_client.post(
            f"/api/v1/matters/{matter.id}/documents",
            headers=auth_headers(partner),
            files=[("file", ("small.pdf", io.BytesIO(content), "application/pdf"))],
        )

    assert response.status_code == 201
    assert response.json()["filename"] == "small.pdf"


@pytest.mark.asyncio
async def test_upload_denied_without_matter_access(
    async_client: AsyncClient, associate, matter, tmp_path, monkeypatch
) -> None:
    """Users who are not matter members cannot upload documents."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))

    response = await async_client.post(
        f"/api/v1/matters/{matter.id}/documents",
        headers=auth_headers(associate),
        files=[pdf_upload()],
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_matter_not_found(
    async_client: AsyncClient, partner, tmp_path, monkeypatch
) -> None:
    """Uploading to a non-existent matter ID returns 403 (access gate first)."""
    monkeypatch.setattr("app.api.routes.documents.settings.data_dir", str(tmp_path))

    response = await async_client.post(
        f"/api/v1/matters/{uuid.uuid4()}/documents",
        headers=auth_headers(partner),
        files=[pdf_upload()],
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /matters/{id}/documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents(
    async_client: AsyncClient,
    partner,
    matter,
    test_db: AsyncSession,
    tmp_path,
    monkeypatch,
) -> None:
    """Members can list documents in their matter."""
    # Seed a document directly in the DB
    doc = Document(
        id=str(uuid.uuid4()),
        matter_id=matter.id,
        filename="agreement.pdf",
        file_type="pdf",
        storage_path=str(tmp_path / "agreement.pdf"),
        status=DocumentStatus.READY,
        page_count=5,
    )
    test_db.add(doc)
    await test_db.commit()

    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/documents",
        headers=auth_headers(partner),
    )
    assert response.status_code == 200
    filenames = [d["filename"] for d in response.json()]
    assert "agreement.pdf" in filenames


@pytest.mark.asyncio
async def test_list_documents_non_member_denied(
    async_client: AsyncClient, associate, matter
) -> None:
    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/documents",
        headers=auth_headers(associate),
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /matters/{id}/documents/{doc_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document(
    async_client: AsyncClient,
    partner,
    matter,
    test_db: AsyncSession,
    tmp_path,
) -> None:
    """Member can fetch a single document by ID."""
    doc_id = str(uuid.uuid4())
    test_db.add(
        Document(
            id=doc_id,
            matter_id=matter.id,
            filename="brief.docx",
            file_type="docx",
            storage_path=str(tmp_path / "brief.docx"),
            status=DocumentStatus.PENDING,
            page_count=0,
        )
    )
    await test_db.commit()

    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/documents/{doc_id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 200
    assert response.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_get_document_not_found(async_client: AsyncClient, partner, matter) -> None:
    response = await async_client.get(
        f"/api/v1/matters/{matter.id}/documents/{uuid.uuid4()}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /matters/{id}/documents/{doc_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_document(
    async_client: AsyncClient,
    partner,
    matter,
    test_db: AsyncSession,
    tmp_path,
) -> None:
    """Any matter member can delete a document."""
    doc_id = str(uuid.uuid4())
    test_db.add(
        Document(
            id=doc_id,
            matter_id=matter.id,
            filename="delete_me.pdf",
            file_type="pdf",
            storage_path=str(tmp_path / "delete_me.pdf"),
            status=DocumentStatus.READY,
            page_count=2,
        )
    )
    await test_db.commit()

    response = await async_client.delete(
        f"/api/v1/matters/{matter.id}/documents/{doc_id}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 204

    # Verify it's gone
    get_response = await async_client.get(
        f"/api/v1/matters/{matter.id}/documents/{doc_id}",
        headers=auth_headers(partner),
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(async_client: AsyncClient, partner, matter) -> None:
    response = await async_client.delete(
        f"/api/v1/matters/{matter.id}/documents/{uuid.uuid4()}",
        headers=auth_headers(partner),
    )
    assert response.status_code == 404
