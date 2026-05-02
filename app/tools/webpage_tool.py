"""Web page fetch tool."""

from pydantic import BaseModel

from app.infra.fetch.base import FetchClient, FetchResult


class WebpageToolResult(BaseModel):
    """Validated web page tool output."""

    page: FetchResult
    ok: bool


class WebpageTool:
    """Tool wrapper for page fetching."""

    def __init__(self, fetch_client: FetchClient) -> None:
        self.fetch_client = fetch_client

    async def run(self, url: str, timeout: float = 10.0) -> WebpageToolResult:
        """Fetch a page and return a validated result.

        Args:
            url: Page URL.
            timeout: Fetch timeout in seconds.

        Returns:
            Validated web page tool result.
        """
        page = await self.fetch_client.fetch(url, timeout=timeout)
        return WebpageToolResult(page=page, ok=page.error is None)
