"""HTTPX page fetch client."""

import hashlib
import html
import json
import re
from datetime import UTC, datetime

import httpx

from app.infra.cache.base import CacheBackend
from app.infra.fetch.base import FetchResult


class HttpxFetchClient:
    """Fetch web pages with HTTPX and cache normalized text results."""

    def __init__(
        self,
        cache: CacheBackend | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.cache = cache
        self._transport = transport

    async def fetch(self, url: str, timeout: float = 10.0) -> FetchResult:
        """Fetch a web page.

        Args:
            url: Page URL.
            timeout: Request timeout in seconds.

        Returns:
            Fetch result. Network and parsing failures are represented by error.
        """
        cache_key = self._cache_key(url, timeout)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return FetchResult.model_validate_json(cached)

        result = await self._fetch_uncached(url, timeout)
        if self.cache:
            await self.cache.set(
                cache_key,
                result.model_dump_json().encode("utf-8"),
                ttl=self._ttl(result),
            )
        return result

    async def _fetch_uncached(self, url: str, timeout: float) -> FetchResult:
        fetched_at = datetime.now(UTC).isoformat()
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(url)
            text = self._extract_text(response.text)
            title = self._extract_title(response.text)
            return FetchResult(
                url=str(response.url),
                title=title,
                text=text,
                status_code=response.status_code,
                error=None if response.is_success else response.reason_phrase,
                fetched_at=fetched_at,
            )
        except Exception as exc:
            return FetchResult(
                url=url,
                title="",
                text="",
                status_code=0,
                error=str(exc),
                fetched_at=fetched_at,
            )

    @staticmethod
    def _cache_key(url: str, timeout: float) -> str:
        payload = json.dumps({"url": url, "timeout": timeout}, sort_keys=True)
        return "fetch:v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _ttl(result: FetchResult) -> int:
        return 300 if result.error else 21600

    @staticmethod
    def _extract_text(raw_html: str) -> str:
        try:
            import trafilatura

            extracted = trafilatura.extract(raw_html)
            if extracted:
                return extracted.strip()
        except ImportError:
            pass
        except Exception:
            pass
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw_html, "html.parser")
            for node in soup(["script", "style"]):
                node.decompose()
            return " ".join(soup.get_text(" ").split())
        except ImportError:
            stripped = re.sub(r"<[^>]+>", " ", raw_html)
            return " ".join(html.unescape(stripped).split())

    @staticmethod
    def _extract_title(raw_html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return " ".join(html.unescape(match.group(1)).split())
