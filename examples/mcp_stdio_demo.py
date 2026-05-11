"""Run the read-only MCP tool adapter with fake state."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mcp_server.tools import ReadOnlyToolAdapter
from app.schemas.mcp import MCPToolRequest


def main() -> None:
    """Print a deterministic MCP tool response."""
    adapter = ReadOnlyToolAdapter({"task_id": "demo_task", "final_report": "# Demo"})
    response = adapter.call(MCPToolRequest(tool_name="get_report"))
    print(response.model_dump_json())


if __name__ == "__main__":
    main()
