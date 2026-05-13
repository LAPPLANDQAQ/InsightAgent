# MCP Server

The MCP layer is safe and read-only by default.

Available tool adapter calls:

- `list_tasks`
- `get_report`
- `retrieve_research_chunks`
- `get_evidences`

Security rules reject non-http schemes, localhost/private IP access by default, shell execution, arbitrary SQL, arbitrary file writes, and unsafe local file access.

Smoke command:

```bash
python -m app.mcp_server.server --transport stdio
```
