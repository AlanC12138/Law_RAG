from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider backed by a local Ollama instance.

    Uses Ollama's OpenAI-compatible embeddings endpoint.  The embedding
    dimension depends on the model — make sure EMBEDDING_DIM in .env
    matches your chosen model:

        nomic-embed-text    → 768 dimensions  (default)
        mxbai-embed-large   → 1024 dimensions
        all-minilm          → 384 dimensions

    Pull your model first:
        ollama pull nomic-embed-text
    """

    def __init__(self, model: str, base_url: str) -> None:
        """Initialise the Ollama embedding provider.

        Args:
            model:    Ollama embedding model tag, e.g. ``"nomic-embed-text"``.
            base_url: Ollama OpenAI-compatible base URL,
                      e.g. ``"http://localhost:11434/v1"``.
        """
        self.model = model
        self._client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        logger.info(f"Ollama embedding provider initialised — model: {model}, url: {base_url}")

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Dense embedding vector.
        """
        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, same order as input.
        """
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )

        # Ollama returns embeddings in the same order as the input
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
