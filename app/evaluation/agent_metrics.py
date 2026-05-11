"""Agent behavior metrics."""

from typing import Any


def todo_completion_rate(todos: list[dict[str, Any]]) -> float:
    """Return the fraction of completed TODOs."""
    if not todos:
        return 0.0
    completed = [todo for todo in todos if todo.get("status") == "completed"]
    return len(completed) / len(todos)


def agent_success_rate(events: list[dict[str, Any]]) -> float:
    """Return agent success rate from harness-like event dicts."""
    starts = [event for event in events if event.get("event_type") == "agent_start"]
    errors = [event for event in events if event.get("event_type") == "error"]
    if not starts:
        return 0.0
    return max(len(starts) - len(errors), 0) / len(starts)


def tool_call_success_rate(events: list[dict[str, Any]]) -> float:
    """Return tool-call success rate from harness-like event dicts."""
    starts = [event for event in events if event.get("event_type") == "tool_start"]
    errors = [event for event in events if event.get("event_type") == "error"]
    if not starts:
        return 0.0
    return max(len(starts) - len(errors), 0) / len(starts)


def summarize_agent_metrics(state: dict[str, Any]) -> dict[str, Any]:
    """Summarize TODO and harness event metrics from workflow state."""
    events = list(state.get("harness_events") or [])
    return {
        "todo_completion_rate": todo_completion_rate(list(state.get("research_todos") or [])),
        "agent_success_rate": agent_success_rate(events),
        "tool_call_success_rate": tool_call_success_rate(events),
        "error_count": len([event for event in events if event.get("event_type") == "error"]),
    }
