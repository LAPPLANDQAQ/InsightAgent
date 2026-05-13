"""DeepSeek client tests."""

from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

from app.infra.llm.base import LLMOutputError
from app.infra.llm.deepseek_client import DeepSeekClient


class DemoOutput(BaseModel):
    """Structured response used in DeepSeek client tests."""

    name: str
    age: int


class FakeCompletions:
    """Fake OpenAI-compatible completions endpoint."""

    def __init__(self, contents: list[str | Exception]) -> None:
        self.contents = contents
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        """Return the next configured content."""
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        if isinstance(content, Exception):
            raise content
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    """Fake OpenAI-compatible client."""

    def __init__(self, contents: list[str | Exception]) -> None:
        self.completions = FakeCompletions(contents)
        self.chat = SimpleNamespace(completions=self.completions)


class FakeRateLimitError(RuntimeError):
    """Fake upstream 429 error."""

    status_code = 429


class FakeServerError(RuntimeError):
    """Fake upstream 5xx error."""

    status_code = 503


def _client(fake: FakeOpenAIClient) -> DeepSeekClient:
    return DeepSeekClient(
        api_key="fake",
        base_url="https://api.deepseek.test/v1",
        heavy_model="deepseek-v4-pro",
        light_model="deepseek-v4-flash",
        fallback_model="deepseek-v4-flash",
        client=fake,
    )


@pytest.mark.asyncio
async def test_deepseek_client_uses_model_role_mapping():
    fake = FakeOpenAIClient(["hello"])
    result = await _client(fake).invoke(prompt="Hi", model_role="light")
    assert result == "hello"
    assert fake.completions.calls[0]["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_deepseek_client_parses_response_format_json():
    fake = FakeOpenAIClient(['{"name": "Ada", "age": 36}'])
    result = await _client(fake).invoke(
        prompt="Return a person",
        model_role="heavy",
        schema=DemoOutput,
    )
    assert result.name == "Ada"
    assert fake.completions.calls[0]["response_format"] == {"type": "json_object"}
    assert "json" in fake.completions.calls[0]["messages"][0]["content"].lower()


@pytest.mark.asyncio
async def test_deepseek_client_extracts_fenced_json_on_fallback():
    fake = FakeOpenAIClient(["not json", '```json\n{"name": "Ada", "age": 36}\n```'])
    result = await _client(fake).invoke(
        prompt="JSON",
        model_role="fallback",
        schema=DemoOutput,
    )
    assert result.age == 36
    assert "response_format" not in fake.completions.calls[1]


@pytest.mark.asyncio
async def test_deepseek_client_raises_for_invalid_structured_output():
    fake = FakeOpenAIClient(["not json", "still not json"])
    with pytest.raises(LLMOutputError):
        await _client(fake).invoke(prompt="JSON", model_role="heavy", schema=DemoOutput)


@pytest.mark.asyncio
async def test_deepseek_client_raises_for_empty_content():
    fake = FakeOpenAIClient(["   "])
    with pytest.raises(LLMOutputError, match="empty content"):
        await _client(fake).invoke(prompt="Hi", model_role="light")


@pytest.mark.asyncio
async def test_deepseek_client_retries_transient_errors():
    fake = FakeOpenAIClient([httpx.ConnectError("offline"), "hello"])
    result = await _client(fake).invoke(prompt="Hi", model_role="light")

    assert result == "hello"
    assert len(fake.completions.calls) == 2


@pytest.mark.asyncio
async def test_deepseek_client_uses_fallback_model_after_retries():
    fake = FakeOpenAIClient([FakeRateLimitError("limited"), FakeRateLimitError("limited"), "ok"])
    result = await _client(fake).invoke(prompt="Hi", model_role="heavy")

    assert result == "ok"
    assert [call["model"] for call in fake.completions.calls] == [
        "deepseek-v4-pro",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    ]


@pytest.mark.asyncio
async def test_deepseek_client_5xx_fallback_error_is_sanitized():
    fake = FakeOpenAIClient(
        [
            FakeServerError("server failed sk-secret"),
            FakeServerError("server failed sk-secret"),
            FakeServerError("server failed sk-secret"),
            FakeServerError("server failed sk-secret"),
        ]
    )

    with pytest.raises(LLMOutputError) as exc_info:
        await _client(fake).invoke(prompt="Hi", model_role="heavy")

    assert "FakeServerError(status_code=503)" in str(exc_info.value)
    assert "sk-secret" not in str(exc_info.value)
    assert [call["model"] for call in fake.completions.calls] == [
        "deepseek-v4-pro",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "deepseek-v4-flash",
    ]


@pytest.mark.asyncio
async def test_deepseek_client_generic_error_redacts_secret_like_values():
    fake = FakeOpenAIClient([RuntimeError("failed with api_key=sk-secret token=abc123")])

    with pytest.raises(LLMOutputError) as exc_info:
        await _client(fake).invoke(prompt="Hi", model_role="fallback")

    message = str(exc_info.value)
    assert "api_key=[REDACTED]" in message
    assert "token=[REDACTED]" in message
    assert "sk-secret" not in message
    assert "abc123" not in message
