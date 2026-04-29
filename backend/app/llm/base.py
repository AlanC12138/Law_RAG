from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implementers should provide language model inference capabilities
    for both regular and streaming completion modes.
    """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:
        """Generate a completion from the LLM.

        Args:
            prompt:  User's question or prompt.
            context: Additional context (retrieved document chunks).
            history: Optional list of previous turns as
                     ``[{"role": "user"|"assistant", "content": "..."}]``.

        Returns:
            LLM-generated response text.
        """
        pass

    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Generate a completion with streaming output.

        Args:
            prompt:  User's question or prompt.
            context: Additional context (retrieved document chunks).
            history: Optional list of previous turns.

        Yields:
            Token chunks of the LLM response.
        """
        pass

    @abstractmethod
    async def summarize(self, text: str) -> str:
        """Generate a concise summary of a legal document.

        Args:
            text: Raw document text (will be truncated internally if needed).

        Returns:
            3-5 sentence plain-prose summary.
        """
        pass
