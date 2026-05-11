"""MCP security validators."""

import ipaddress
import re
from urllib.parse import urlparse

SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)=([^&\s]+)")


def is_safe_url(url: str, *, allow_localhost: bool = False) -> bool:
    """Return whether a URL is safe for read-only use."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    if not allow_localhost and host in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return allow_localhost or not (ip.is_private or ip.is_loopback or ip.is_link_local)


def redact_secrets(text: str) -> str:
    """Redact secret-looking query parameters from text."""
    return SECRET_RE.sub(r"\1=[REDACTED]", text)
