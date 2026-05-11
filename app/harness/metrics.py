"""Harness and agent metrics."""

from typing import Any

from app.schemas.harness import HarnessEvent


def collect_harness_metrics(
    events: list[HarnessEvent],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute basic success and TODO completion metrics."""
    tool_starts = [event for event in events if event.event_type == "tool_start"]
    tool_errors = [event for event in events if event.event_type == "error"]
    agent_starts = [event for event in events if event.event_type == "agent_start"]
    todos = list((state or {}).get("research_todos", []))
    completed = [todo for todo in todos if todo.get("status") == "completed"]
    return {
        "tool_call_success_rate": _rate(len(tool_starts) - len(tool_errors), len(tool_starts)),
        "agent_success_rate": _rate(len(agent_starts) - len(tool_errors), len(agent_starts)),
        "error_count": len(tool_errors),
        "todo_completion_rate": _rate(len(completed), len(todos)),
    }


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else max(numerator, 0) / denominator
