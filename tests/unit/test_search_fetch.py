"""Search and fetch infrastructure tests."""

import httpx
import pytest

from app.infra.cache.memory_cache import MemoryCache
from app.infra.fetch.httpx_client import HttpxFetchClient
from app.infra.search.base import SearchResult
from app.infra.search.service import SearchService
from app.infra.search.tavily import TavilyProvider
from tests.fixtures.stub_search import StubSearchProvider


@pytest.mark.asyncio
async def test_search_service_dedupes_and_caches():
    provider = StubSearchProvider(
        results=[
            SearchResult(title="A", url="https://example.com", snippet="one", provider="stub"),
            SearchResult(title="B", url="https://example.com/", snippet="two", provider="stub"),
        ]
    )
    service = SearchService([provider], MemoryCache())
    first = await service.search("query", max_results=5)
    second = await service.search("query", max_results=5)
    assert len(first) == 1
    assert second[0].url == "https://example.com"
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_search_service_continues_after_provider_failure():
    failing = StubSearchProvider(fail=True)
    working = StubSearchProvider()
    service = SearchService([failing, working], MemoryCache())
    results = await service.search("query", max_results=1)
    assert results[0].provider == "stub"


@pytest.mark.asyncio
async def test_tavily_provider_normalizes_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Cursor",
                        "url": "https://cursor.com",
                        "content": "AI coding assistant.",
                    }
                ]
            },
        )

    provider = TavilyProvider(
        api_key="fake",
        endpoint="https://tavily.test/search",
        transport=httpx.MockTransport(handler),
    )
    results = await provider.search("Cursor", max_results=1)
    assert results[0].provider == "tavily"


@pytest.mark.asyncio
async def test_httpx_fetch_client_extracts_and_caches():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            html="<html><title>Demo</title><body><h1>Hello</h1><script>x</script></body></html>",
            request=request,
        )

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    first = await client.fetch("https://example.com")
    second = await client.fetch("https://example.com")
    assert first.title == "Demo"
    assert "Hello" in second.text
    assert calls == 1


@pytest.mark.asyncio
async def test_httpx_fetch_client_returns_error_result():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com")
    assert result.error
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_blocks_localhost():
    client = HttpxFetchClient(cache=MemoryCache())
    result = await client.fetch("http://127.0.0.1/admin")
    assert result.error == "blocked private or local host"
    assert result.status_code == 0
