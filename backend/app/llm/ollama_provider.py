from __future__ import annotations

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.llm.base import BaseLLMProvider
from app.llm.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """LLM provider backed by a local Ollama instance.

    Uses Ollama's OpenAI-compatible API endpoint so we can reuse the
    same openai library.  Point OLLAMA_BASE_URL at your Ollama server
    (default: http://localhost:11434/v1).

    Recommended models (set LLM_MODEL in .env):
        llama3.2        — fast, 3B, good for most legal Q&A
        llama3.1:8b     — better quality, still runs on CPU
        mistral         — strong instruction following
    """

    def __init__(self, model: str, base_url: str) -> None:
        """Initialise the Ollama provider.

        Args:
            model:    Ollama model tag, e.g. ``"llama3.2"``.
            base_url: Ollama OpenAI-compatible base URL,
                      e.g. ``"http://localhost:11434/v1"``.
        """
        self.model = model
        # Ollama's OpenAI-compatible API doesn't validate the API key —
        # any non-empty string works.
        self._client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        logger.info(f"Ollama provider initialised — model: {model}, url: {base_url}")

    async def complete(self, prompt: str, context: str) -> str:
        """Generate a non-streaming completion via Ollama.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block.

        Returns:
            Full model response text.
        """
        from app.llm.prompt import build_user_message

        user_message = build_user_message(prompt, context)

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )

        answer: str = response.choices[0].message.content or ""
        logger.debug(f"Ollama completion: {len(answer)} chars")
        return answer

    async def stream_complete(self, prompt: str, context: str) -> AsyncIterator[str]:
        """Generate a streaming completion via Ollama.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block.

        Yields:
            Text delta chunks from the model.
        """
        from app.llm.prompt import build_user_message

        user_message = build_user_message(prompt, context)

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
