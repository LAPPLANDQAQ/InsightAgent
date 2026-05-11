"""Tool registry for harness-controlled tools."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RegisteredTool:
    """Registered tool metadata and callable."""

    name: str
    handler: Callable[..., Any]
    risk_level: RiskLevel = "low"
    read_only: bool = True


class ToolRegistry:
    """Whitelist registry for callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        """Register a tool by name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool | None:
        """Return a registered tool by name."""
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        """Return registered tool names."""
        return sorted(self._tools)
