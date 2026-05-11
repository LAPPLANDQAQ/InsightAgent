"""Tests for MCP safety and tools."""

from app.mcp_server.security import is_safe_url, redact_secrets
from app.mcp_server.tools import ReadOnlyToolAdapter
from app.schemas.mcp import MCPToolRequest


def test_mcp_security_rejects_unsafe_urls_and_redacts():
    assert is_safe_url("https://example.com")
    assert not is_safe_url("file:///tmp/x")
    assert not is_safe_url("http://127.0.0.1:8000")
    assert "SECRET" not in redact_secrets("x?api_key=SECRET")


def test_read_only_tool_adapter():
    adapter = ReadOnlyToolAdapter({"task_id": "task_1", "final_report": "# Report"})

    response = adapter.call(MCPToolRequest(tool_name="get_report"))
    missing = adapter.call(MCPToolRequest(tool_name="shell_exec"))

    assert response.ok
    assert response.result["final_report"] == "# Report"
    assert not missing.ok
