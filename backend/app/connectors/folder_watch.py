from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from app.connectors.base import BaseDocumentConnector, DocumentInfo

logger = logging.getLogger(__name__)


class FileSystemEventListener(FileSystemEventHandler):
    """Watchdog event handler for file system changes."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        """Initialize event listener.

        Args:
            callback: Function to call when files are modified
        """
        self.callback = callback

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events.

        Args:
            event: Watchdog file event
        """
        if not event.is_directory:
            self.callback(event.src_path)


class FolderWatchConnector(BaseDocumentConnector):
    """Document connector that watches a local folder for new documents."""

    def __init__(self, watch_path: str) -> None:
        """Initialize folder watch connector.

        Args:
            watch_path: Path to folder to watch
        """
        self.watch_path = Path(watch_path)
        self.watch_path.mkdir(parents=True, exist_ok=True)
        self.observer: Observer | None = None
        self.callback: Callable[[str], None] | None = None

    async def list_documents(self) -> list[DocumentInfo]:
        """List all documents in the watched folder.

        Returns:
            List of DocumentInfo objects
        """
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
        """Fetch document bytes from the watched folder.

        Args:
            doc_id: Relative path to document

        Returns:
            Raw file bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = self.watch_path / doc_id
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_id}")

        return file_path.read_bytes()

    async def get_metadata(self, doc_id: str) -> dict[str, str]:
        """Get metadata for a document.

        Args:
            doc_id: Relative path to document

        Returns:
            Metadata dictionary
        """
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
        """Start watching folder for file changes.

        Args:
            callback: Function to call when files are added/modified
        """
        if self.observer is not None:
            return

        self.callback = callback
        self.observer = Observer()
        event_handler = FileSystemEventListener(callback)
        self.observer.schedule(event_handler, str(self.watch_path), recursive=True)
        self.observer.start()
        logger.info(f"Started watching folder: {self.watch_path}")

    def stop_watching(self) -> None:
        """Stop watching folder for file changes."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info(f"Stopped watching folder: {self.watch_path}")
