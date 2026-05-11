"""Tests for agent behavior metrics."""

from app.evaluation.agent_metrics import summarize_agent_metrics


def test_agent_metrics_from_state():
    """Agent metrics include TODO completion and event success rates."""
    metrics = summarize_agent_metrics(
        {
            "research_todos": [{"status": "completed"}, {"status": "pending"}],
            "harness_events": [
                {"event_type": "agent_start"},
                {"event_type": "tool_start"},
            ],
        }
    )

    assert metrics["todo_completion_rate"] == 0.5
    assert metrics["agent_success_rate"] == 1.0
    assert metrics["tool_call_success_rate"] == 1.0
