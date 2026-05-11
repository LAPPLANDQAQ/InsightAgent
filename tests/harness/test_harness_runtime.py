"""Tests for harness runtime components."""

import pytest

from app.harness.events import create_event
from app.harness.metrics import collect_harness_metrics
from app.harness.policies import PolicyEngine
from app.harness.registry import RegisteredTool, ToolRegistry
from app.harness.replay import create_replay_snapshot
from app.harness.runtime import HarnessRuntime
from app.harness.tracing import InMemoryTraceStore


def test_trace_store_metrics_and_replay_redact_secret():
    store = InMemoryTraceStore()
    event = create_event(
        run_id="run_1",
        task_id="task_1",
        event_type="tool_start",
        name="retrieve",
        payload={"api_key": "secret"},
    )
    store.append(event)

    metrics = collect_harness_metrics(store.list_by_task("task_1"), {"research_todos": []})
    snapshot = create_replay_snapshot({"token": "secret"}, store.list_by_run("run_1"))

    assert metrics["error_count"] == 0
    assert snapshot["state"]["token"] == "[REDACTED]"
    assert event.payload["api_key"] == "[REDACTED]"


def test_policy_engine_blocks_dangerous_and_limits_calls():
    engine = PolicyEngine(max_calls_per_task=1)
    tool = RegisteredTool(name="safe_lookup", handler=lambda: "ok")

    assert engine.check_tool("task_1", tool).allowed
    engine.record_call("task_1")
    assert not engine.check_tool("task_1", tool).allowed
    dangerous = RegisteredTool(name="shell_exec", handler=lambda: None)
    assert not engine.check_tool("task_1", dangerous).allowed


def test_harness_runtime_runs_registered_tool():
    registry = ToolRegistry()
    registry.register(RegisteredTool(name="answer", handler=lambda value: value + 1))
    runtime = HarnessRuntime(registry=registry)

    assert runtime.run_tool("task_1", "answer", value=1) == 2


def test_harness_runtime_blocks_unknown_tool():
    runtime = HarnessRuntime()

    with pytest.raises(PermissionError):
        runtime.run_tool("task_1", "missing")
