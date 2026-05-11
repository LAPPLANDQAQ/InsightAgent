"""Harness runtime wrappers for agents and tools."""

from typing import Any
from uuid import uuid4

from app.harness.events import create_event
from app.harness.policies import PolicyEngine
from app.harness.registry import ToolRegistry
from app.harness.tracing import InMemoryTraceStore


class HarnessRuntime:
    """Record agent and tool execution events around normal calls."""

    def __init__(
        self,
        trace_store: InMemoryTraceStore | None = None,
        registry: ToolRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.trace_store = trace_store or InMemoryTraceStore()
        self.registry = registry or ToolRegistry()
        self.policy_engine = policy_engine or PolicyEngine()

    async def run_agent(self, agent: Any, state: dict[str, Any], run_id: str | None = None) -> Any:
        """Run an agent and record start/end/error events."""
        task_id = str(state.get("task_id") or "task")
        active_run_id = run_id or f"run_{uuid4().hex}"
        self.trace_store.append(
            create_event(
                run_id=active_run_id,
                task_id=task_id,
                event_type="agent_start",
                name=str(getattr(agent, "name", agent.__class__.__name__)),
            )
        )
        try:
            result = await agent.run(state)
        except Exception as exc:
            self.trace_store.append(
                create_event(
                    run_id=active_run_id,
                    task_id=task_id,
                    event_type="error",
                    name=str(getattr(agent, "name", "agent")),
                    payload={"error": str(exc)},
                )
            )
            raise
        self.trace_store.append(
            create_event(
                run_id=active_run_id,
                task_id=task_id,
                event_type="agent_end",
                name=str(getattr(agent, "name", "agent")),
            )
        )
        return result

    def run_tool(self, task_id: str, tool_name: str, **kwargs: Any) -> Any:
        """Run a registered tool after policy checks."""
        tool = self.registry.get(tool_name)
        decision = self.policy_engine.check_tool(task_id, tool)
        if not decision.allowed or decision.requires_approval:
            raise PermissionError(decision.reason or "tool_blocked")
        assert tool is not None
        self.policy_engine.record_call(task_id)
        run_id = f"run_{uuid4().hex}"
        self.trace_store.append(
            create_event(run_id=run_id, task_id=task_id, event_type="tool_start", name=tool_name)
        )
        try:
            result = tool.handler(**kwargs)
        except Exception as exc:
            self.trace_store.append(
                create_event(
                    run_id=run_id,
                    task_id=task_id,
                    event_type="error",
                    name=tool_name,
                    payload={"error": str(exc)},
                )
            )
            raise
        self.trace_store.append(
            create_event(run_id=run_id, task_id=task_id, event_type="tool_end", name=tool_name)
        )
        return result
