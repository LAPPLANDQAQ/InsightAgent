"""Read-only MCP tool adapter."""

from typing import Any

from app.schemas.mcp import MCPToolRequest, MCPToolResponse


class ReadOnlyToolAdapter:
    """Expose safe read-only research data as tool calls."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}

    def call(self, request: MCPToolRequest) -> MCPToolResponse:
        """Execute a safe read-only tool call."""
        tools = {
            "list_tasks": self._list_tasks,
            "get_report": self._get_report,
            "retrieve_research_chunks": self._retrieve_chunks,
            "get_evidences": self._get_evidences,
        }
        handler = tools.get(request.tool_name)
        if handler is None:
            return MCPToolResponse(ok=False, error=f"unknown_tool:{request.tool_name}")
        return MCPToolResponse(ok=True, result=handler(request.arguments))

    def _list_tasks(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        if not self.state.get("task_id"):
            return {"tasks": []}
        return {"tasks": [self.state.get("task_id")]}

    def _get_report(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        report = self.state.get("final_report") or self.state.get("draft_report") or ""
        return {"final_report": report}

    def _retrieve_chunks(self, arguments: dict[str, Any]) -> dict[str, Any]:
        top_k = int(arguments.get("top_k") or 5)
        chunks = list(self.state.get("retrieved_chunks") or self.state.get("rag_chunks") or [])
        return {"chunks": chunks[:top_k]}

    def _get_evidences(self, arguments: dict[str, Any]) -> dict[str, Any]:
        evidences = [
            evidence
            for competitor in self.state.get("competitors", [])
            for evidence in competitor.get("evidences", [])
        ]
        return {"evidences": evidences}
