"""Tests for trace store."""

from app.harness.events import create_event
from app.harness.tracing import InMemoryTraceStore


def test_trace_store_lists_by_run_and_task():
    """Trace store preserves event order."""
    store = InMemoryTraceStore()
    event = create_event(run_id="run", task_id="task", event_type="agent_start", name="agent")
    store.append(event)

    assert store.list_by_run("run") == [event]
    assert store.list_by_task("task") == [event]
