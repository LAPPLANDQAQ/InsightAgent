"""Search tool."""

from pydantic import BaseModel, Field

from app.infra.logger import get_logger
from app.infra.search.base import SearchResult
from app.infra.security.redaction import redact_secret_like
from app.tools.dedup import dedupe_search_results

logger = get_logger(__name__)


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
        try:
            if hasattr(self.search_service, "search_with_diagnostics"):
                results, issues = await self.search_service.search_with_diagnostics(
                    query,
                    max_results=max_results,
                )
            else:
                results = await self.search_service.search(query, max_results=max_results)
                issues = []
        except Exception as exc:
            logger.exception(
                "search_tool_failed",
                extra={
                    "query": redact_secret_like(query),
                    "error": redact_secret_like(str(exc)),
                },
            )
            raise
        deduped = dedupe_search_results(results)[:max_results]
        return SearchToolResult(query=query, results=deduped, total=len(deduped), issues=issues)
