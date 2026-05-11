"""Smoke-testable stdio MCP-style server."""

import argparse
import json
import sys

from app.mcp_server.tools import ReadOnlyToolAdapter
from app.schemas.mcp import MCPToolRequest


def main() -> int:
    """Run a minimal JSON-line stdio server for safe tools."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio", choices=["stdio"])
    parser.parse_args()
    adapter = ReadOnlyToolAdapter()
    for line in sys.stdin:
        payload = json.loads(line)
        response = adapter.call(MCPToolRequest.model_validate(payload))
        sys.stdout.write(response.model_dump_json() + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
