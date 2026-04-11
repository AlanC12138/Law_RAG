from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DocumentInfo:
    """Information about a document from a connector."""

    id: str
    filename: str
    file_type: str
    size_bytes: int
    modified_at: datetime


class BaseDocumentConnector(ABC):
    """Abstract base class for document source connectors.

    Implementers should provide ways to list documents from various sources
    (file systems, cloud storage, content management systems, etc.).
    """

    @abstractmethod
    async def list_documents(self) -> list[DocumentInfo]:
        """List all available documents from the source.

        Returns:
            List of DocumentInfo objects with document metadata
        """
        pass

    @abstractmethod
    async def fetch_document(self, doc_id: str) -> bytes:
        """Fetch a document's raw bytes from the source.

        Args:
            doc_id: Unique document identifier

        Returns:
            Raw file bytes

        Raises:
            FileNotFoundError: If document does not exist
        """
        pass

    @abstractmethod
    async def get_metadata(self, doc_id: str) -> dict[str, str]:
        """Get metadata for a specific document.

        Args:
            doc_id: Unique document identifier

        Returns:
            Dictionary of metadata key-value pairs
        """
        pass
