"""Search provider protocol."""

from typing import Protocol

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Single search result."""

    title: str
    url: str
    snippet: str
    provider: str


class SearchProvider(Protocol):
    """Search provider interface."""

    name: str

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Run a search query.

        Args:
            query: Search query text.
            max_results: Maximum number of results to return.

        Returns:
            Search results from the provider.

        Raises:
            Exception: Provider implementations may raise; orchestration handles fallback.
        """
        ...
