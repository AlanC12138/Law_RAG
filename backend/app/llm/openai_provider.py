from __future__ import annotations

import logging
from typing import AsyncIterator

from llama_index.llms.openai import OpenAI

from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using OpenAI API via LlamaIndex."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialize OpenAI provider.

        Args:
            model: Model name (e.g., 'gpt-4o')
            api_key: OpenAI API key
        """
        self.model = model
        self.client = OpenAI(model=model, api_key=api_key)

    async def complete(self, prompt: str, context: str) -> str:
        """Generate a completion from OpenAI.

        Args:
            prompt: User's question
            context: Retrieved context from documents

        Returns:
            LLM response
        """
        full_prompt = f"{context}\n\nQuestion: {prompt}"
        response = await self.client.acomplete(full_prompt)
        return response.text

    async def stream_complete(self, prompt: str, context: str) -> AsyncIterator[str]:
        """Generate a streaming completion from OpenAI.

        Args:
            prompt: User's question
            context: Retrieved context from documents

        Yields:
            Token chunks from the response
        """
        full_prompt = f"{context}\n\nQuestion: {prompt}"
        response = await self.client.astream_complete(full_prompt)

        async for chunk in response:
            yield chunk.delta
