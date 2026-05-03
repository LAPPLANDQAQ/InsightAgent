"""Search aggregation service."""

import asyncio
import hashlib
import json
from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.infra.cache.base import CacheBackend
from app.infra.logger import get_logger
from app.infra.search.base import SearchProvider, SearchResult

logger = get_logger(__name__)


class SearchService:
    """Aggregate search results from configured providers with caching."""

    def __init__(
        self,
        providers: Sequence[SearchProvider],
        cache: CacheBackend | None = None,
        max_concurrency: int = 5,
    ) -> None:
        self.providers = list(providers)
        self.cache = cache
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Run a cached search across providers.

        Args:
            query: Search query text.
            max_results: Maximum results after aggregation and deduplication.

        Returns:
            Deduplicated search results.
        """
        cache_key = self._cache_key(query, max_results)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return self._loads(cached)[:max_results]

        provider_results = await asyncio.gather(
            *(self._search_provider(provider, query, max_results) for provider in self.providers)
        )
        results = self._dedupe([item for group in provider_results for item in group])
        ttl = 21600 if results else 60
        if self.cache:
            await self.cache.set(cache_key, self._dumps(results), ttl=ttl)
        return results[:max_results]

    async def _search_provider(
        self,
        provider: SearchProvider,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        async with self._semaphore:
            try:
                return await provider.search(query, max_results)
            except Exception as exc:
                logger.warning(
                    "search_provider_failed",
                    extra={"provider": provider.name, "query": query, "error": str(exc)},
                )
                return []

    def _cache_key(self, query: str, max_results: int) -> str:
        payload = {
            "providers": [provider.name for provider in self.providers],
            "query": query,
            "max_results": max_results,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "search:v1:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _dumps(results: list[SearchResult]) -> bytes:
        return json.dumps(
            [result.model_dump() for result in results],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _loads(data: bytes) -> list[SearchResult]:
        return [SearchResult.model_validate(item) for item in json.loads(data.decode("utf-8"))]

    @staticmethod
    def _dedupe(results: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        output: list[SearchResult] = []
        for result in results:
            normalized = _normalize_url(result.url)
            if normalized in seen:
                continue
            seen.add(normalized)
            output.append(result)
        return output


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if not key.lower().startswith("utm_") and key.lower() != "ref"
    ]
    query = urlencode(query_items)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))
