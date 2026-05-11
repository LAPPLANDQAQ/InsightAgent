"""Smoke test for stdio MCP server."""

import json
import subprocess
import sys


def test_mcp_stdio_server_smoke():
    """The stdio server reads JSON tool requests and writes JSON responses."""
    proc = subprocess.run(
        [sys.executable, "-m", "app.mcp_server.server", "--transport", "stdio"],
        input='{"tool_name":"get_report","arguments":{}}\n',
        text=True,
        capture_output=True,
        check=True,
    )

    response = json.loads(proc.stdout.strip())
    assert response["ok"] is True
