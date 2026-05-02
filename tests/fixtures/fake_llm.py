"""Fake LLM client for unit tests."""

from typing import TypeVar

from pydantic import BaseModel

from app.infra.llm.base import LLMOutputError, ModelRole

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient:
    """Keyword-routed fake LLM client."""

    def __init__(self) -> None:
        self.responses: dict[str, dict | str] = {}
        self.calls: list[dict[str, object]] = []

    def set_response(self, *, keyword: str, response: dict | str) -> None:
        """Set a response matched by keyword in the prompt."""
        self.responses[keyword] = response

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
        """Return a configured response matching the prompt."""
        self.calls.append(
            {
                "prompt": prompt[:200],
                "model_role": model_role,
                "schema": schema.__name__ if schema else None,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": timeout,
            }
        )
        response = self._match_response(prompt)
        if schema is None:
            return response if isinstance(response, str) else str(response)
        if isinstance(response, dict):
            return schema.model_validate(response)
        raise LLMOutputError(f"Fake response for {schema.__name__} must be a dict")

    def _match_response(self, prompt: str) -> dict | str:
        for keyword, response in self.responses.items():
            if keyword in prompt:
                return response
        raise LLMOutputError("No fake LLM response configured for prompt")
