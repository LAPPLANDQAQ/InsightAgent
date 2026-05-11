"""MCP tool data contracts."""

from typing import Any

from pydantic import BaseModel, Field


class MCPToolRequest(BaseModel):
    """Safe MCP tool invocation request."""

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    """Structured MCP tool invocation response."""

    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
