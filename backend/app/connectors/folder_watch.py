from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.connectors.base import BaseDocumentConnector, DocumentInfo
from datetime import datetime

logger = logging.getLogger(__name__)

# File types accepted by the ingestion pipeline
_ALLOWED_TYPES = {"pdf", "docx", "doc"}


class FileSystemEventListener(FileSystemEventHandler):
    """Watchdog event handler — fires callback only on new file creation."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        self.callback = callback

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self.callback(str(event.src_path))


class FolderWatchConnector(BaseDocumentConnector):
    """Document connector that watches a local folder for new documents."""

    def __init__(self, watch_path: str) -> None:
        self.watch_path = Path(watch_path)
        self.watch_path.mkdir(parents=True, exist_ok=True)
        self.observer: Observer | None = None

    async def list_documents(self) -> list[DocumentInfo]:
        documents = []
        for file_path in self.watch_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                documents.append(
                    DocumentInfo(
                        id=str(file_path.relative_to(self.watch_path)),
                        filename=file_path.name,
                        file_type=file_path.suffix.lower(),
                        size_bytes=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                    )
                )
        return documents

    async def fetch_document(self, doc_id: str) -> bytes:
        file_path = self.watch_path / doc_id
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_id}")
        return file_path.read_bytes()

    async def get_metadata(self, doc_id: str) -> dict[str, str]:
        file_path = self.watch_path / doc_id
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_id}")
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "file_type": file_path.suffix.lower(),
            "size_bytes": str(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def start_watching(self, callback: Callable[[str], None]) -> None:
        if self.observer is not None:
            return
        self.observer = Observer()
        self.observer.schedule(
            FileSystemEventListener(callback),
            str(self.watch_path),
            recursive=True,
        )
        self.observer.start()
        logger.info(f"Folder watch started: {self.watch_path}")

    def stop_watching(self) -> None:
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info(f"Folder watch stopped: {self.watch_path}")


# ---------------------------------------------------------------------------
# Async ingest logic
# ---------------------------------------------------------------------------

async def _ingest_watched_file(file_path: str, watch_root: Path) -> None:
    """Auto-ingest a file dropped into the watch folder.

    Expected directory structure::

        {watch_root}/{matter_id}/filename.pdf

    The sub-directory name must be a valid Matter UUID.  Files dropped
    directly in ``watch_root`` (no subdirectory) are ignored.

    Args:
        file_path:  Absolute path to the newly created file.
        watch_root: Root of the watched directory tree.
    """
    from sqlalchemy import select as sa_select

    from app.config import get_settings as _get_settings
    from app.db.models import Document as DBDocument, DocumentStatus, Matter
    from app.db.session import AsyncSessionLocal
    from app.ingestion.pipeline import IngestionPipeline

    path = Path(file_path)

    # Skip hidden / temporary files
    if path.name.startswith(".") or path.suffix.lower() in {".tmp", ".part", ".swp"}:
        return

    file_type = path.suffix.lstrip(".").lower()
    if file_type not in _ALLOWED_TYPES:
        logger.debug(f"Watch folder: skipping unsupported type '{file_type}': {path.name}")
        return

    # Derive matter_id from the immediate subdirectory name
    try:
        rel = path.relative_to(watch_root)
    except ValueError:
        return

    parts = rel.parts
    if len(parts) < 2:
        logger.debug(f"Watch folder: {path.name} is in root (no matter subdirectory) — skipped")
        return

    matter_id = parts[0]
    filename = path.name

    # Small delay — give the OS time to finish writing the file
    await asyncio.sleep(0.5)

    _settings = _get_settings()

    async with AsyncSessionLocal() as db:
        # Validate matter exists
        matter = await db.get(Matter, matter_id)
        if matter is None:
            logger.warning(
                f"Watch folder: no matter with id={matter_id!r} — "
                f"file {filename!r} not ingested"
            )
            return

        # Skip if already ingested (same filename in same matter)
        existing = await db.execute(
            sa_select(DBDocument).where(
                (DBDocument.matter_id == matter_id) & (DBDocument.filename == filename)
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug(
                f"Watch folder: {filename!r} already ingested in matter '{matter.name}'"
            )
            return

        # Read bytes
        try:
            file_bytes = path.read_bytes()
        except OSError as exc:
            logger.error(f"Watch folder: could not read {file_path!r}: {exc}")
            return

        logger.info(
            f"Watch folder: auto-ingesting {filename!r} → matter '{matter.name}'"
        )

        # Persist file copy next to regular uploads
        doc_id = str(uuid.uuid4())
        storage_dir = Path(_settings.data_dir) / "documents" / matter_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / f"{doc_id}.{file_type}"
        storage_path.write_bytes(file_bytes)

        # Create DB record
        document = DBDocument(
            id=doc_id,
            matter_id=matter_id,
            filename=filename,
            file_type=file_type,
            storage_path=str(storage_path),
            status=DocumentStatus.PENDING,
            page_count=0,
        )
        db.add(document)
        await db.commit()

        # Run ingestion pipeline (same as manual upload)
        pipeline = IngestionPipeline()
        await pipeline.run(
            document_id=doc_id,
            file_bytes=file_bytes,
            file_type=file_type,
            matter_id=matter_id,
            filename=filename,
            db=db,
        )


def make_ingest_callback(
    watch_root: Path,
    loop: asyncio.AbstractEventLoop,
) -> Callable[[str], None]:
    """Return a thread-safe sync callback suitable for ``start_watching``.

    Watchdog fires callbacks from a background thread.  This factory
    bridges that thread back to the FastAPI asyncio event loop so that
    ``_ingest_watched_file`` can safely use ``await``.

    Args:
        watch_root: Root of the watched directory tree.
        loop:       The running asyncio event loop (from ``get_running_loop``).

    Returns:
        A synchronous callable that schedules the async ingest coroutine.
    """

    def _callback(file_path: str) -> None:
        asyncio.run_coroutine_threadsafe(
            _ingest_watched_file(file_path, watch_root), loop
        )

    return _callback
