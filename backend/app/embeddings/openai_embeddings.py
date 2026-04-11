from __future__ import annotations

import logging

from llama_index.embeddings.openai import OpenAIEmbedding

from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using OpenAI's embedding API via LlamaIndex."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialize OpenAI embedding provider.

        Args:
            model: Model name (e.g., 'text-embedding-3-small')
            api_key: OpenAI API key
        """
        self.model = model
        self.client = OpenAIEmbedding(model=model, api_key=api_key)

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Dense vector representation
        """
        embedding = await self.client.aget_text_embedding(text)
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently using OpenAI.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vector representations
        """
        embeddings = await self.client.aget_text_embedding_batch(texts)
        return embeddings
