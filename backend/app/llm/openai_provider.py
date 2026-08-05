from __future__ import annotations

import logging
from collections.abc import AsyncIterator

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


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using the OpenAI Chat Completions API directly.

    Uses the async OpenAI client rather than going through LlamaIndex so
    we have full control over the system prompt, message structure, and
    streaming behaviour.
    """

    def __init__(self, model: str, api_key: str) -> None:
        """Initialise the OpenAI provider.

        Args:
            model:   Model identifier, e.g. ``"gpt-4o"``.
            api_key: OpenAI API key.
        """
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)
        logger.info(f"OpenAI provider initialised with model: {model}")

    async def complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:
        """Generate a non-streaming completion.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block from ``build_context_block()``.
            history: Optional prior conversation turns.

        Returns:
            Full LLM response text.
        """
        from app.llm.prompt import build_user_message

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history or []:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": build_user_message(prompt, context)})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )

        answer: str = response.choices[0].message.content or ""
        logger.debug(f"LLM completion: {len(answer)} chars")
        return answer

    async def stream_complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion, yielding tokens as they arrive.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block from ``build_context_block()``.
            history: Optional prior conversation turns.

        Yields:
            Text delta chunks from the model.
        """
        from app.llm.prompt import build_user_message

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history or []:
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
        """Generate a concise summary of a legal document.

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
        """Extract structured key clauses from a legal document.

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
            response_format={"type": "json_object"},
        )
        return parse_llm_json(response.choices[0].message.content or "{}")
