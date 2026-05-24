from __future__ import annotations

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.llm.base import BaseLLMProvider
from app.llm.prompt import (
    CLAUSE_EXTRACTION_SYSTEM_PROMPT,
    MAX_ENRICHMENT_CHARS,
    SUMMARIZE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    parse_llm_json,
)

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

    async def complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:
        """Generate a non-streaming completion via Ollama.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block.
            history: Optional prior conversation turns.

        Returns:
            Full model response text.
        """
        from app.llm.prompt import build_user_message

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in (history or []):
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": build_user_message(prompt, context)})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )

        answer: str = response.choices[0].message.content or ""
        logger.debug(f"Ollama completion: {len(answer)} chars")
        return answer

    async def stream_complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion via Ollama.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block.
            history: Optional prior conversation turns.

        Yields:
            Text delta chunks from the model.
        """
        from app.llm.prompt import build_user_message

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in (history or []):
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": build_user_message(prompt, context)})

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def summarize(self, text: str) -> str:
        """Generate a concise summary of a legal document via Ollama.

        Args:
            text: Raw document text (truncated to ``MAX_ENRICHMENT_CHARS``).

        Returns:
            3-5 sentence plain-prose summary.
        """
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Document text:\n\n{text[:MAX_ENRICHMENT_CHARS]}"},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    async def extract_clauses(self, text: str) -> dict:
        """Extract structured key clauses from a legal document via Ollama.

        Note: Ollama models may not reliably return JSON; ``parse_llm_json``
        strips markdown fences and falls back to ``{}`` on failure.

        Args:
            text: Raw document text (truncated to ``MAX_ENRICHMENT_CHARS``).

        Returns:
            Dict of extracted clause fields.
        """
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CLAUSE_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Document text:\n\n{text[:MAX_ENRICHMENT_CHARS]}"},
            ],
            temperature=0,
        )
        return parse_llm_json(response.choices[0].message.content or "{}")
