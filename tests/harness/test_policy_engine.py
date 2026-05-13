"""Tests for PolicyEngine."""

from app.harness.policies import PolicyEngine
from app.harness.registry import RegisteredTool


def test_policy_engine_requires_approval_for_high_risk_and_blocks_names():
    """PolicyEngine controls high-risk and dangerous tools."""
    engine = PolicyEngine()

    high = engine.check_tool(
        "task",
        RegisteredTool(name="high", handler=lambda: None, risk_level="high"),
    )
    blocked = engine.check_tool("task", RegisteredTool(name="delete_file", handler=lambda: None))

    assert high.requires_approval
    assert not blocked.allowed


def test_policy_engine_counts_calls_and_preserves_denials():
    """PolicyEngine counts repeated calls without changing denial semantics."""
    engine = PolicyEngine(max_calls_per_task=2)
    tool = RegisteredTool(name="read_source", handler=lambda: None)

    assert engine.check_tool("task", tool).allowed
    engine.record_call("task")
    assert engine.check_tool("task", tool).allowed
    engine.record_call("task")

    assert not engine.check_tool("task", tool).allowed
    assert engine.check_tool("task", tool).reason == "max_calls_exceeded"
    dangerous = RegisteredTool(name="rm_data", handler=lambda: None)
    assert engine.check_tool("task", dangerous).reason == "dangerous_tool_name"


def test_policy_engine_acquire_slot_checks_and_records_atomically():
    """PolicyEngine can reserve the call slot in one critical section."""
    engine = PolicyEngine(max_calls_per_task=1)
    tool = RegisteredTool(name="read_source", handler=lambda: None)

    first = engine.acquire_slot("task", tool)
    second = engine.acquire_slot("task", tool)

    assert first.allowed
    assert not second.allowed
    assert second.reason == "max_calls_exceeded"
