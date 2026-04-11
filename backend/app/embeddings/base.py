from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Implementers should provide text-to-vector embedding functionality
    for semantic search and similarity calculations.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            Dense vector representation of the text
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings efficiently.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vector representations
        """
        pass
