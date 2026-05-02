"""Stub fetch client for unit tests."""

from app.infra.fetch.base import FetchResult


class StubFetchClient:
    """Configurable fetch client stub."""

    def __init__(self, result: FetchResult | None = None) -> None:
        self.result = result or FetchResult(
            url="https://cursor.com/pricing",
            title="Cursor pricing",
            text="Cursor Pro costs 20 USD per month.",
            status_code=200,
            fetched_at="2026-01-01T00:00:00Z",
        )
        self.calls: list[dict[str, object]] = []

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """Return configured fetch result."""
        self.calls.append({"url": url, "timeout": timeout})
        return self.result.model_copy(update={"url": url})
