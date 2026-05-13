"""Search tool."""

from pydantic import BaseModel, Field

from app.infra.search.base import SearchResult
from app.tools.dedup import dedupe_search_results


class SearchToolResult(BaseModel):
    """Validated search tool output."""

    query: str
    results: list[SearchResult]
    total: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)


class SearchTool:
    """Tool wrapper for search service."""

    def __init__(self, search_service) -> None:
        self.search_service = search_service

    async def run(self, query: str, max_results: int = 5) -> SearchToolResult:
        """Run search and return validated results.

        Args:
            query: Search query.
            max_results: Maximum result count.

        Returns:
            Validated search tool result.
        """
        if hasattr(self.search_service, "search_with_diagnostics"):
            results, issues = await self.search_service.search_with_diagnostics(
                query,
                max_results=max_results,
            )
        else:
            results = await self.search_service.search(query, max_results=max_results)
            issues = []
        deduped = dedupe_search_results(results)[:max_results]
        return SearchToolResult(query=query, results=deduped, total=len(deduped), issues=issues)
