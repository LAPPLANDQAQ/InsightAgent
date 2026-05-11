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
