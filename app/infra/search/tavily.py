"""Tavily search provider."""

from typing import Any

import httpx

from app.infra.search.base import SearchResult


class TavilyProvider:
    """Search provider backed by Tavily."""

    name = "tavily"

    def __init__(
        self,
        api_key: str,
        endpoint: str = "https://api.tavily.com/search",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self._transport = transport

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Search Tavily.

        Args:
            query: Search query text.
            max_results: Maximum results to request.

        Returns:
            Tavily search results normalized to SearchResult.
        """
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        async with httpx.AsyncClient(transport=self._transport, timeout=15.0) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
        body = response.json()
        return [self._to_result(item) for item in body.get("results", [])[:max_results]]

    def _to_result(self, item: dict[str, Any]) -> SearchResult:
        return SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            snippet=str(item.get("content") or item.get("snippet") or ""),
            provider=self.name,
        )
