"""Web page fetch protocol."""

from typing import Protocol

from pydantic import BaseModel


class FetchResult(BaseModel):
    """Fetched page result with inline error state."""

    url: str
    title: str
    text: str
    status_code: int
    error: str | None = None
    fetched_at: str


class FetchClient(Protocol):
    """Web page fetch client interface."""

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """Fetch page content without raising for fetch failures.

        Args:
            url: Page URL to fetch.
            timeout: Request timeout in seconds.

        Returns:
            Fetch result. Failures are represented by the error field.
        """
        ...
