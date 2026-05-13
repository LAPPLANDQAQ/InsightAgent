"""Search and fetch infrastructure tests."""

import asyncio
import logging
import sys
from types import SimpleNamespace

import httpx
import pytest

import app.infra.fetch.httpx_client as fetch_module
import app.infra.search.service as search_service_module
from app.infra.cache.memory_cache import MemoryCache
from app.infra.fetch.httpx_client import MAX_RESPONSE_BYTES, HttpxFetchClient
from app.infra.search.base import SearchResult
from app.infra.search.service import SearchService
from app.infra.search.tavily import TavilyProvider
from app.tools.search_tool import SearchTool
from tests.fixtures.stub_search import StubSearchProvider


class SlowSearchProvider:
    """Search provider that sleeps longer than the configured timeout."""

    name = "slow"

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        await asyncio.sleep(0.2)
        return []


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
async def test_search_service_times_out_one_provider_and_continues():
    working = StubSearchProvider()
    service = SearchService(
        [SlowSearchProvider(), working],
        MemoryCache(),
        provider_timeout_seconds=0.01,
    )

    results, warnings = await service.search_with_diagnostics("query", max_results=1)

    assert results[0].provider == "stub"
    assert "search provider slow timed out" in warnings


@pytest.mark.asyncio
async def test_search_service_times_out_all_providers():
    service = SearchService(
        [SlowSearchProvider()],
        MemoryCache(),
        provider_timeout_seconds=0.01,
    )

    results, warnings = await service.search_with_diagnostics("query", max_results=1)

    assert results == []
    assert "search provider slow timed out" in warnings
    assert "all search providers failed" in warnings


@pytest.mark.asyncio
async def test_search_service_returns_warning_when_all_providers_fail():
    service = SearchService([StubSearchProvider(fail=True)], MemoryCache())
    results, warnings = await service.search_with_diagnostics("query", max_results=1)
    tool_result = await SearchTool(service).run("query", max_results=1)

    assert results == []
    assert "all search providers failed" in warnings
    assert "all search providers failed" in tool_result.issues


@pytest.mark.asyncio
async def test_search_service_redacts_secret_values_in_warning():
    provider = StubSearchProvider(fail=True)
    provider.name = "tavily"

    async def fail_with_secret(query: str, max_results: int) -> list[SearchResult]:
        raise RuntimeError("request failed with api_key=tvly-secret")

    provider.search = fail_with_secret
    service = SearchService([provider], MemoryCache())

    _, warnings = await service.search_with_diagnostics("query", max_results=1)

    warning_text = " ".join(warnings)
    assert "api_key=[REDACTED]" in warning_text
    assert "tvly-secret" not in warning_text


@pytest.mark.asyncio
async def test_search_service_ignores_corrupted_cache():
    cache = MemoryCache()
    provider = StubSearchProvider()
    service = SearchService([provider], cache)
    await cache.set(service._cache_key("query", 1), b"{not json")

    results = await service.search("query", max_results=1)

    assert results[0].provider == "stub"
    assert len(provider.calls) == 1


def test_search_service_uses_shared_url_normalizer(monkeypatch):
    calls: list[str] = []

    def fake_normalize(url: str) -> str:
        calls.append(url)
        return "same"

    monkeypatch.setattr(search_service_module, "normalize_url", fake_normalize)
    results = SearchService._dedupe(
        [
            SearchResult(title="A", url="https://a.test", snippet="", provider="stub"),
            SearchResult(title="B", url="https://b.test", snippet="", provider="stub"),
        ]
    )

    assert [result.title for result in results] == ["A"]
    assert calls == ["https://a.test", "https://b.test"]


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


def test_httpx_fetch_client_logs_trafilatura_failure(monkeypatch, caplog):
    def fail_extract(raw_html: str) -> str:
        raise RuntimeError("parser exploded with api_key=sk-secret")

    monkeypatch.setitem(sys.modules, "trafilatura", SimpleNamespace(extract=fail_extract))

    with caplog.at_level(logging.WARNING):
        text = HttpxFetchClient._extract_text("<html><body>Hello</body></html>")

    assert "Hello" in text
    assert "trafilatura_extract_failed" in caplog.text
    assert any(
        getattr(record, "error", None) == "parser exploded with api_key=[REDACTED]"
        for record in caplog.records
    )
    assert "sk-secret" not in caplog.text


@pytest.mark.asyncio
async def test_httpx_fetch_client_returns_error_result():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com")
    assert result.error
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_redacts_error_result():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline with token=sk-secret", request=request)

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com")

    assert result.error == "offline with token=[REDACTED]"
    assert "sk-secret" not in result.error


@pytest.mark.asyncio
async def test_httpx_fetch_client_blocks_localhost():
    client = HttpxFetchClient(cache=MemoryCache())
    result = await client.fetch("http://127.0.0.1/admin")
    assert result.error == "blocked private or local host"
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_blocks_private_ip():
    client = HttpxFetchClient(cache=MemoryCache())
    result = await client.fetch("http://10.0.0.5/admin")
    assert result.error == "blocked private or local host"
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_blocks_redirect_to_private_host():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1/admin"},
                request=request,
            )
        return httpx.Response(200, html="<p>blocked</p>", request=request)

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com")

    assert "redirect blocked" in result.error
    assert "blocked private or local host" in result.error
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_rejects_unsupported_content_type():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not an image",
            headers={"content-type": "image/png"},
            request=request,
        )

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com/image.png")
    assert result.error == "unsupported content type: image/png"


@pytest.mark.asyncio
async def test_httpx_fetch_client_rejects_oversized_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1), request=request)

    client = HttpxFetchClient(cache=MemoryCache(), transport=httpx.MockTransport(handler))
    result = await client.fetch("https://example.com")
    assert "maximum size" in result.error
    assert result.status_code == 0


@pytest.mark.asyncio
async def test_httpx_fetch_client_returns_dns_failure(monkeypatch):
    async def fail_resolve(host: str) -> set[str]:
        raise OSError("no dns")

    monkeypatch.setattr(fetch_module, "_resolve_host", fail_resolve)
    client = HttpxFetchClient(cache=MemoryCache())
    result = await client.fetch("https://example.invalid")
    assert result.error == "DNS resolution failed: no dns"


@pytest.mark.asyncio
async def test_httpx_fetch_client_ignores_corrupted_cache():
    cache = MemoryCache()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, html="<title>Fresh</title><p>ok</p>", request=request)

    client = HttpxFetchClient(cache=cache, transport=httpx.MockTransport(handler))
    await cache.set(client._cache_key("https://example.com", 10.0), b"{not json")

    result = await client.fetch("https://example.com")
    assert result.title == "Fresh"
    assert calls == 1
