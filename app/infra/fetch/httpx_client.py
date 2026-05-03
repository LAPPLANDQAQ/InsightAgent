"""HTTPX page fetch client."""

import hashlib
import html
import ipaddress
import json
import re
import socket
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.infra.cache.base import CacheBackend
from app.infra.fetch.base import FetchResult

MAX_RESPONSE_BYTES = 2_000_000
ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/xhtml+xml", "application/xml")
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


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
        blocked = await self._blocked_reason(url)
        if blocked:
            return FetchResult(
                url=url,
                title="",
                text="",
                status_code=0,
                error=blocked,
                fetched_at=datetime.now(UTC).isoformat(),
            )
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
            response, raw_text = await self._request_once(url, timeout)
            content_type = response.headers.get("content-type", "").split(";")[0].lower()
            if content_type and content_type not in ALLOWED_CONTENT_TYPES:
                return FetchResult(
                    url=str(response.url),
                    title="",
                    text="",
                    status_code=response.status_code,
                    error=f"unsupported content type: {content_type}",
                    fetched_at=fetched_at,
                )
            text = self._extract_text(raw_text)
            title = self._extract_title(raw_text)
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

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _request_once(self, url: str, timeout: float) -> tuple[httpx.Response, str]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            transport=self._transport,
        ) as client:
            async with client.stream("GET", url) as response:
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise httpx.HTTPError("response exceeds maximum size")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                encoding = response.encoding or "utf-8"
                return response, raw.decode(encoding, errors="replace")

    async def _blocked_reason(self, url: str) -> str | None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            return "blocked URL scheme"
        host = parsed.hostname
        if not host:
            return "missing URL host"
        if self._is_blocked_host(host):
            return "blocked private or local host"
        if self._transport is None:
            return await self._blocked_dns_reason(host)
        return None

    @staticmethod
    def _is_blocked_host(host: str) -> bool:
        normalized = host.strip().lower().rstrip(".")
        if normalized in BLOCKED_HOSTS or normalized.endswith(".localhost"):
            return True
        try:
            ip = ipaddress.ip_address(normalized)
        except ValueError:
            return False
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )

    @staticmethod
    async def _blocked_dns_reason(host: str) -> str | None:
        try:
            resolved = await _resolve_host(host)
        except OSError as exc:
            return f"DNS resolution failed: {exc}"
        for ip_text in resolved:
            if HttpxFetchClient._is_blocked_host(ip_text):
                return "blocked private or local resolved address"
        return None


async def _resolve_host(host: str) -> set[str]:
    """Resolve a host to IP strings.

    Args:
        host: DNS host name.

    Returns:
        Resolved IP addresses.
    """
    import asyncio

    infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    return {str(item[4][0]) for item in infos}
