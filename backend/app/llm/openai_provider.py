from __future__ import annotations

import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.llm.base import BaseLLMProvider
from app.llm.prompt import SYSTEM_PROMPT

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

    async def complete(self, prompt: str, context: str) -> str:
        """Generate a non-streaming completion.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block from ``build_context_block()``.

        Returns:
            Full LLM response text.
        """
        from app.llm.prompt import build_user_message

        user_message = build_user_message(prompt, context)

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,      # Zero temperature for deterministic legal answers
        )

        answer: str = response.choices[0].message.content or ""
        logger.debug(f"LLM completion: {len(answer)} chars")
        return answer

    async def stream_complete(self, prompt: str, context: str) -> AsyncIterator[str]:
        """Generate a streaming completion, yielding tokens as they arrive.

        Args:
            prompt:  The user's question.
            context: Pre-formatted source block from ``build_context_block()``.

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
