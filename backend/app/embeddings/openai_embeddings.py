from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using OpenAI's embedding API directly."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialize OpenAI embedding provider.

        Args:
            model: Model name (e.g., 'text-embedding-3-small')
            api_key: OpenAI API key
        """
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)
        logger.info(f"OpenAI embedding provider initialised — model: {model}")

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Dense vector representation
        """
        response = await self._client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently using OpenAI.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vector representations, same order as input
        """
        if not texts:
            return []

        response = await self._client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
