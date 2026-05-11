"""Tests for MetricsCollector."""

from app.harness.events import create_event
from app.harness.metrics import MetricsCollector


def test_metrics_collector_computes_rates():
    """MetricsCollector returns tool and TODO rates."""
    event = create_event(run_id="run", task_id="task", event_type="tool_start", name="tool")
    metrics = MetricsCollector().collect([event], {"research_todos": [{"status": "completed"}]})

    assert metrics["tool_call_success_rate"] == 1.0
    assert metrics["todo_completion_rate"] == 1.0
