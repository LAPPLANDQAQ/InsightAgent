"""Tests for MCP read-only tool adapter."""

from app.mcp_server.tools import ReadOnlyToolAdapter
from app.schemas.mcp import MCPToolRequest


def test_mcp_tool_adapter_exposes_only_safe_tools():
    """MCP adapter returns structured errors for unknown tools."""
    adapter = ReadOnlyToolAdapter({"task_id": "task", "final_report": "# Report"})

    assert adapter.call(MCPToolRequest(tool_name="list_tasks")).result["tasks"] == ["task"]
    assert not adapter.call(MCPToolRequest(tool_name="arbitrary_sql")).ok
