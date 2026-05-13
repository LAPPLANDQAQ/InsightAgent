"""DeepSeek OpenAI-compatible LLM client."""

import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.infra.llm.base import LLMClient, LLMOutputError, ModelRole
from app.infra.security.redaction import redact_secret_like

T = TypeVar("T", bound=BaseModel)
RETRY_ATTEMPTS = 2


class EmptyLLMContentError(RuntimeError):
    """Raised internally when the upstream LLM returns empty content."""


class DeepSeekClient(LLMClient):
    """LLM client for DeepSeek's OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        heavy_model: str,
        light_model: str,
        fallback_model: str,
        client: Any | None = None,
    ) -> None:
        self._models: dict[ModelRole, str] = {
            "heavy": heavy_model,
            "light": light_model,
            "fallback": fallback_model,
        }
        if client is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._client = client

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
        """Invoke DeepSeek by logical model role.

        Args:
            prompt: Prompt text.
            model_role: Logical model role mapped to a configured DeepSeek model.
            schema: Optional Pydantic schema for JSON output.
            max_tokens: Maximum output tokens.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.

        Returns:
            Parsed schema instance or plain text.

        Raises:
            LLMOutputError: Raised when output is empty or schema parsing fails.
        """
        if schema is None:
            content = await self._complete(
                prompt=prompt,
                model_role=model_role,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            if not content.strip():
                raise LLMOutputError("LLM returned empty content")
            return content

        return await self._invoke_schema(
            prompt=prompt,
            model_role=model_role,
            schema=schema,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

    async def _invoke_schema(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        schema: type[T],
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> T:
        errors: list[str] = []
        json_prompt = self._schema_prompt(prompt, schema)
        content = await self._complete(
            prompt=json_prompt,
            model_role=model_role,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
        parsed = self._parse_schema(content, schema=schema, allow_extract=False)
        if parsed is not None:
            return parsed
        errors.append(self._diagnostic(content))

        content = await self._complete(
            prompt=json_prompt,
            model_role=model_role,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        parsed = self._parse_schema(content, schema=schema, allow_extract=True)
        if parsed is not None:
            return parsed
        errors.append(self._diagnostic(content))
        raise LLMOutputError(f"LLM output cannot be parsed as {schema.__name__}: {errors}")

    async def _complete(
        self,
        *,
        prompt: str,
        model_role: ModelRole,
        max_tokens: int,
        temperature: float,
        timeout: float,
        response_format: dict[str, str] | None = None,
    ) -> str:
        roles: list[ModelRole] = [model_role]
        if model_role != "fallback" and self._models["fallback"] != self._models[model_role]:
            roles.append("fallback")

        errors: list[str] = []
        for role in roles:
            model = self._models[role]
            for attempt in range(1, RETRY_ATTEMPTS + 1):
                try:
                    content = await self._complete_once(
                        prompt=prompt,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=timeout,
                        response_format=response_format,
                    )
                    if not content.strip():
                        raise EmptyLLMContentError("LLM returned empty content")
                    return content
                except LLMOutputError:
                    raise
                except Exception as exc:
                    errors.append(f"{model}: {self._safe_error(exc)}")
                    if not self._is_transient_error(exc) or attempt >= RETRY_ATTEMPTS:
                        break
        raise LLMOutputError(
            "DeepSeek request failed after retrying configured model"
            f"{'s' if len(roles) > 1 else ''}: {errors[-3:]}"
        )

    async def _complete_once(
        self,
        *,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
        response_format: dict[str, str] | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        response = await self._client.chat.completions.create(**kwargs)
        return self._message_content(response)

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        if isinstance(exc, EmptyLLMContentError):
            return True
        if isinstance(
            exc,
            (
                TimeoutError,
                ConnectionError,
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int) and (status_code == 429 or status_code >= 500):
            return True
        name = type(exc).__name__.lower()
        return any(
            marker in name
            for marker in (
                "timeout",
                "connection",
                "ratelimit",
                "rate_limit",
                "internalserver",
            )
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return f"{type(exc).__name__}(status_code={status_code})"
        message = redact_secret_like(str(exc).replace("\n", " ").strip())
        if len(message) > 160:
            message = message[:157] + "..."
        return f"{type(exc).__name__}: {message}" if message else type(exc).__name__

    @staticmethod
    def _message_content(response: Any) -> str:
        try:
            return str(response.choices[0].message.content or "")
        except (AttributeError, IndexError) as exc:
            raise LLMOutputError("LLM response does not contain message content") from exc

    @staticmethod
    def _schema_prompt(prompt: str, schema: type[BaseModel]) -> str:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        return (
            f"{prompt}\n\n"
            "Return only a valid json object matching this JSON Schema. "
            "Do not include markdown or commentary.\n"
            f"{schema_json}"
        )

    @classmethod
    def _parse_schema(
        cls,
        content: str,
        *,
        schema: type[T],
        allow_extract: bool,
    ) -> T | None:
        candidates = [content]
        if allow_extract:
            extracted = cls._extract_json(content)
            if extracted:
                candidates.insert(0, extracted)
        for candidate in candidates:
            try:
                return schema.model_validate_json(candidate)
            except (ValidationError, ValueError):
                try:
                    return schema.model_validate(json.loads(candidate))
                except (ValidationError, ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _extract_json(content: str) -> str | None:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        first_object = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if first_object:
            return first_object.group(0).strip()
        return None

    @staticmethod
    def _diagnostic(content: str) -> str:
        preview = redact_secret_like(" ".join(content.split()))[:120]
        return f"len={len(content)} preview={preview!r}"
