"""Tests for trace store."""

from concurrent.futures import ThreadPoolExecutor

from app.harness.events import create_event
from app.harness.tracing import InMemoryTraceStore


def test_trace_store_lists_by_run_and_task():
    """Trace store preserves event order."""
    store = InMemoryTraceStore()
    event = create_event(run_id="run", task_id="task", event_type="agent_start", name="agent")
    store.append(event)

    assert store.list_by_run("run") == [event]
    assert store.list_by_task("task") == [event]


def test_trace_store_threaded_appends_do_not_drop_events():
    """Trace store protects shared event state during concurrent appends."""
    store = InMemoryTraceStore()
    events = [
        create_event(run_id="run", task_id="task", event_type="tool_end", name=f"tool_{index}")
        for index in range(20)
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(store.append, events))

    assert {event.name for event in store.list_by_task("task")} == {
        f"tool_{index}" for index in range(20)
    }
