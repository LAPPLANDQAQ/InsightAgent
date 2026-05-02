"""DuckDuckGo search provider."""

import asyncio
from typing import Any

from app.infra.search.base import SearchResult


class DuckDuckGoProvider:
    """Search provider backed by duckduckgo_search."""

    name = "duckduckgo"

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Search DuckDuckGo.

        Args:
            query: Search query text.
            max_results: Maximum results to request.

        Returns:
            DuckDuckGo results normalized to SearchResult.
        """
        return await asyncio.to_thread(self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            from duckduckgo_search import DDGS
        except ImportError as exc:
            raise RuntimeError("duckduckgo_search is not installed") from exc

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        return [self._to_result(item) for item in raw_results[:max_results]]

    def _to_result(self, item: dict[str, Any]) -> SearchResult:
        return SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("href") or item.get("url") or ""),
            snippet=str(item.get("body") or item.get("snippet") or ""),
            provider=self.name,
        )
