"""Tests for MCP security validators."""

from app.mcp_server.security import is_safe_url, redact_secrets


def test_mcp_security_validates_url_and_redacts_secrets():
    """MCP security rejects local/private/file URLs."""
    assert is_safe_url("https://example.com")
    assert not is_safe_url("file:///secret")
    assert not is_safe_url("http://localhost:8000")
    assert redact_secrets("token=abc") == "token=[REDACTED]"
