"""Search aggregation service."""

import asyncio
import hashlib
import json
from collections.abc import Sequence

from app.infra.cache.base import CacheBackend
from app.infra.logger import get_logger
from app.infra.search.base import SearchProvider, SearchResult
from app.infra.security.redaction import redact_secret_like
from app.tools.dedup import normalize_url

logger = get_logger(__name__)


class SearchService:
    """Aggregate search results from configured providers with caching."""

    def __init__(
        self,
        providers: Sequence[SearchProvider],
        cache: CacheBackend | None = None,
        max_concurrency: int = 5,
        provider_timeout_seconds: float = 10.0,
    ) -> None:
        self.providers = list(providers)
        self.cache = cache
        self.provider_timeout_seconds = provider_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Run a cached search across providers.

        Args:
            query: Search query text.
            max_results: Maximum results after aggregation and deduplication.

        Returns:
            Deduplicated search results.
        """
        results, _ = await self.search_with_diagnostics(query, max_results=max_results)
        return results

    async def search_with_diagnostics(
        self,
        query: str,
        max_results: int = 5,
    ) -> tuple[list[SearchResult], list[str]]:
        """Run search and return user-visible warnings for provider failures."""
        cache_key = self._cache_key(query, max_results)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                try:
                    return self._loads(cached)[:max_results], []
                except Exception as exc:
                    logger.warning(
                        "search_cache_corrupted",
                        extra={"cache_key": cache_key, "error": str(exc)},
                    )
                    await self.cache.delete(cache_key)

        provider_results = await asyncio.gather(
            *(self._search_provider(provider, query, max_results) for provider in self.providers)
        )
        warnings = [warning for _, warning in provider_results if warning]
        results = self._dedupe([item for group, _ in provider_results for item in group])
        if not results and warnings:
            warnings.append("all search providers failed")
        ttl = 21600 if results else 60
        if self.cache and (results or not warnings):
            await self.cache.set(cache_key, self._dumps(results), ttl=ttl)
        return results[:max_results], warnings

    async def _search_provider(
        self,
        provider: SearchProvider,
        query: str,
        max_results: int,
    ) -> tuple[list[SearchResult], str | None]:
        async with self._semaphore:
            try:
                return (
                    await asyncio.wait_for(
                        provider.search(query, max_results),
                        timeout=self.provider_timeout_seconds,
                    ),
                    None,
                )
            except TimeoutError:
                warning = f"search provider {provider.name} timed out"
                logger.warning(
                    "search_provider_timed_out",
                    extra={"provider": provider.name, "query": query},
                )
                return [], warning
            except Exception as exc:
                error = redact_secret_like(str(exc))
                warning = f"search provider {provider.name} failed: {error}"
                logger.warning(
                    "search_provider_failed",
                    extra={"provider": provider.name, "query": query, "error": error},
                )
                return [], warning

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
            normalized = normalize_url(result.url)
            if normalized in seen:
                continue
            seen.add(normalized)
            output.append(result)
        return output
