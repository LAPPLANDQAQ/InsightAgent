"""LLM client protocol used by business code."""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
ModelRole = Literal["heavy", "light", "fallback"]


class LLMOutputError(Exception):
    """Raised when LLM output cannot be parsed into the target schema."""


class LLMClient(Protocol):
    """Unified interface for invoking language models."""

    async def invoke(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema: type[T] | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0,
    ) -> T | str:
        """Invoke an LLM and return either parsed schema output or text.

        Args:
            prompt: Prompt sent to the model.
            model_role: Logical model role mapped by the provider.
            schema: Optional Pydantic schema for structured output.
            max_tokens: Maximum output token count.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.

        Returns:
            A Pydantic instance when schema is provided, otherwise plain text.

        Raises:
            LLMOutputError: Raised after structured output parsing fails.
        """
        ...
