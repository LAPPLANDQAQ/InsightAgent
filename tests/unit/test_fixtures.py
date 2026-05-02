"""Tests for shared fake and stub fixtures."""

import pytest
from pydantic import BaseModel

from app.infra.llm.base import LLMOutputError


class DemoSchema(BaseModel):
    """Small schema for fake LLM validation tests."""

    name: str


@pytest.mark.asyncio
async def test_fake_llm_returns_schema(fake_llm):
    fake_llm.set_response(keyword="demo", response={"name": "InsightAgent"})
    result = await fake_llm.invoke(prompt="demo", model_role="light", schema=DemoSchema)
    assert result.name == "InsightAgent"


@pytest.mark.asyncio
async def test_fake_llm_raises_without_match(fake_llm):
    with pytest.raises(LLMOutputError):
        await fake_llm.invoke(prompt="missing", model_role="light")


@pytest.mark.asyncio
async def test_stub_search_returns_results(stub_search):
    results = await stub_search.search("Cursor", max_results=1)
    assert results[0].url == "https://cursor.com/pricing"


@pytest.mark.asyncio
async def test_stub_fetch_returns_page(stub_fetch):
    result = await stub_fetch.fetch("https://example.com")
    assert result.url == "https://example.com"
