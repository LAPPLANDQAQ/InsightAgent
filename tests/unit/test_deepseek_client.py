"""DeepSeek client tests."""

from types import SimpleNamespace

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

    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        """Return the next configured content."""
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    """Fake OpenAI-compatible client."""

    def __init__(self, contents: list[str]) -> None:
        self.completions = FakeCompletions(contents)
        self.chat = SimpleNamespace(completions=self.completions)


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
