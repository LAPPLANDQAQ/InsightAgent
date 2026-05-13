"""Web page fetch tool."""

from pydantic import BaseModel

from app.infra.fetch.base import FetchClient, FetchResult
from app.infra.logger import get_logger
from app.infra.security.redaction import redact_secret_like

logger = get_logger(__name__)


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
        try:
            page = await self.fetch_client.fetch(url, timeout=timeout)
        except Exception as exc:
            logger.exception(
                "webpage_tool_failed",
                extra={"url": redact_secret_like(url), "error": redact_secret_like(str(exc))},
            )
            raise
        return WebpageToolResult(page=page, ok=page.error is None)
