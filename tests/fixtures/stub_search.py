"""Stub search provider for unit tests."""

from app.infra.search.base import SearchResult


class StubSearchProvider:
    """Configurable search provider stub."""

    name = "stub"

    def __init__(self, results: list[SearchResult] | None = None, fail: bool = False) -> None:
        self.results = results or [
            SearchResult(
                title="Cursor pricing",
                url="https://cursor.com/pricing",
                snippet="Cursor pricing page.",
                provider=self.name,
            )
        ]
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        """Return configured search results or raise when fail is set."""
        self.calls.append({"query": query, "max_results": max_results})
        if self.fail:
            raise RuntimeError("stub search failure")
        return self.results[:max_results]
