"""Integration tests for the folder-watch auto-ingest connector.

The watchdog Observer/thread machinery itself isn't exercised here — these
tests call the async ingest coroutine directly, the same way
``make_ingest_callback`` schedules it onto the event loop. That's where
the actual business logic (matter validation, dedup, file-type filtering)
lives, and where bugs would actually bite.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.connectors.folder_watch import _ingest_watched_file, make_ingest_callback
from app.db.models import Document, DocumentStatus
from tests.conftest import make_matter, make_user


@asynccontextmanager
async def _session_wrapper(session: AsyncSession):
    yield session


def _patched_session_local(session: AsyncSession):
    """A stand-in for AsyncSessionLocal() bound to the given test session."""
    return lambda: _session_wrapper(session)


@pytest.fixture
def watch_root(tmp_path: Path) -> Path:
    root = tmp_path / "watch"
    root.mkdir()
    return root


@pytest.fixture(autouse=True)
def _patch_data_dir(tmp_path: Path):
    """Route document storage writes into a temp directory for every test
    in this module, then restore the real value afterwards."""
    settings = get_settings()
    original = settings.data_dir
    settings.data_dir = str(tmp_path / "data")
    yield
    settings.data_dir = original


def _mock_pipeline():
    instance = MagicMock()
    instance.run = AsyncMock()
    return instance


@pytest.mark.asyncio
async def test_ingest_new_file_creates_document(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """Dropping a supported file into {watch_root}/{matter_id}/ creates a
    Document row and hands off to the ingestion pipeline."""
    partner = await make_user(test_db, email="partner-fw1@firm.com")
    matter = await make_matter(test_db, owner=partner)

    matter_dir = watch_root / matter.id
    matter_dir.mkdir()
    file_path = matter_dir / "contract.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake pdf content")

    pipeline = _mock_pipeline()
    with (
        patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)),
        patch("app.ingestion.pipeline.IngestionPipeline", return_value=pipeline),
    ):
        await _ingest_watched_file(str(file_path), watch_root)

    result = await test_db.execute(select(Document).where(Document.matter_id == matter.id))
    doc = result.scalar_one_or_none()
    assert doc is not None
    assert doc.filename == "contract.pdf"
    assert doc.file_type == "pdf"
    assert doc.status == DocumentStatus.PENDING  # pipeline.run is mocked, never flips it

    pipeline.run.assert_awaited_once()
    call_kwargs = pipeline.run.call_args.kwargs
    assert call_kwargs["matter_id"] == matter.id
    assert call_kwargs["filename"] == "contract.pdf"
    assert call_kwargs["file_type"] == "pdf"


@pytest.mark.asyncio
async def test_ingest_skips_unknown_matter(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """A subdirectory name that isn't a real matter ID is ignored — no
    Document row, no pipeline run."""
    fake_matter_dir = watch_root / str(uuid.uuid4())
    fake_matter_dir.mkdir()
    file_path = fake_matter_dir / "contract.pdf"
    file_path.write_bytes(b"content")

    pipeline = _mock_pipeline()
    with (
        patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)),
        patch("app.ingestion.pipeline.IngestionPipeline", return_value=pipeline),
    ):
        await _ingest_watched_file(str(file_path), watch_root)

    result = await test_db.execute(select(Document))
    assert result.scalar_one_or_none() is None
    pipeline.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_skips_unsupported_file_type(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """Files with an extension outside {pdf, docx, doc} are ignored."""
    partner = await make_user(test_db, email="partner-fw2@firm.com")
    matter = await make_matter(test_db, owner=partner)

    matter_dir = watch_root / matter.id
    matter_dir.mkdir()
    file_path = matter_dir / "notes.txt"
    file_path.write_bytes(b"plain text")

    with patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)):
        await _ingest_watched_file(str(file_path), watch_root)

    result = await test_db.execute(select(Document).where(Document.matter_id == matter.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_ingest_skips_file_without_matter_subdirectory(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """A file dropped directly in the watch root (no matter subdir) is
    ignored — there is nowhere safe to ingest it to."""
    file_path = watch_root / "stray.pdf"
    file_path.write_bytes(b"content")

    with patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)):
        await _ingest_watched_file(str(file_path), watch_root)

    result = await test_db.execute(select(Document))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_ingest_skips_already_ingested_filename(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """A filename already ingested into the matter is not re-ingested —
    this is the guard that makes re-dropping the same file a no-op."""
    partner = await make_user(test_db, email="partner-fw3@firm.com")
    matter = await make_matter(test_db, owner=partner)

    test_db.add(
        Document(
            id=str(uuid.uuid4()),
            matter_id=matter.id,
            filename="contract.pdf",
            file_type="pdf",
            storage_path="/already/ingested/contract.pdf",
            status=DocumentStatus.READY,
            page_count=3,
        )
    )
    await test_db.commit()

    matter_dir = watch_root / matter.id
    matter_dir.mkdir()
    file_path = matter_dir / "contract.pdf"
    file_path.write_bytes(b"content")

    pipeline = _mock_pipeline()
    with (
        patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)),
        patch("app.ingestion.pipeline.IngestionPipeline", return_value=pipeline),
    ):
        await _ingest_watched_file(str(file_path), watch_root)

    result = await test_db.execute(select(Document).where(Document.matter_id == matter.id))
    docs = result.scalars().all()
    assert len(docs) == 1  # only the pre-existing row — no duplicate created
    pipeline.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_skips_hidden_and_temp_files(
    test_db: AsyncSession, watch_root: Path
) -> None:
    """Hidden files and editor/OS temp files (.tmp/.part/.swp) are never
    ingested, even when dropped in a valid matter subdirectory."""
    partner = await make_user(test_db, email="partner-fw4@firm.com")
    matter = await make_matter(test_db, owner=partner)
    matter_dir = watch_root / matter.id
    matter_dir.mkdir()

    for name in [".DS_Store", "contract.pdf.tmp", "contract.pdf.part"]:
        f = matter_dir / name
        f.write_bytes(b"content")
        with patch("app.db.session.AsyncSessionLocal", _patched_session_local(test_db)):
            await _ingest_watched_file(str(f), watch_root)

    result = await test_db.execute(select(Document).where(Document.matter_id == matter.id))
    assert result.scalar_one_or_none() is None


def test_make_ingest_callback_bridges_to_event_loop() -> None:
    """The sync watchdog callback must hand off via
    asyncio.run_coroutine_threadsafe rather than awaiting directly —
    watchdog calls it from a background thread, not the asyncio loop."""
    loop = MagicMock()
    watch_root = Path("/tmp/watch")

    with patch("app.connectors.folder_watch.asyncio.run_coroutine_threadsafe") as mock_run:
        callback = make_ingest_callback(watch_root, loop)
        callback("/tmp/watch/abc/file.pdf")

    mock_run.assert_called_once()
    args = mock_run.call_args.args
    assert args[1] is loop
    args[0].close()  # we intercepted scheduling, never intended to run it —
    # close() avoids a spurious "coroutine was never awaited" warning
