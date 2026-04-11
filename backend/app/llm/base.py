from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implementers should provide language model inference capabilities
    for both regular and streaming completion modes.
    """

    @abstractmethod
    async def complete(self, prompt: str, context: str) -> str:
        """Generate a completion from the LLM.

        Args:
            prompt: User's question or prompt
            context: Additional context to include in the request

        Returns:
            LLM-generated response text
        """
        pass

    @abstractmethod
    async def stream_complete(self, prompt: str, context: str) -> AsyncIterator[str]:
        """Generate a completion with streaming output.

        Args:
            prompt: User's question or prompt
            context: Additional context to include in the request

        Yields:
            Token chunks of the LLM response
        """
        pass
