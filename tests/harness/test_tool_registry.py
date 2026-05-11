"""Tests for ToolRegistry."""

from app.harness.registry import RegisteredTool, ToolRegistry


def test_tool_registry_registers_whitelist_tools():
    """ToolRegistry stores only explicitly registered tools."""
    registry = ToolRegistry()
    tool = RegisteredTool(name="safe", handler=lambda: "ok")
    registry.register(tool)

    assert registry.get("safe") == tool
    assert registry.list_names() == ["safe"]
