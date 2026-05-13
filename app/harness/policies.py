"""Harness policy engine."""

from dataclasses import dataclass
from threading import Lock

from app.harness.registry import RegisteredTool

DANGEROUS_NAMES = ("shell", "exec", "sql", "write_file", "delete", "rm")


@dataclass(frozen=True)
class PolicyDecision:
    """Policy decision for a proposed tool call."""

    allowed: bool
    requires_approval: bool = False
    reason: str = ""


class PolicyEngine:
    """Evaluate tool safety and call-count limits."""

    def __init__(
        self,
        max_calls_per_task: int = 50,
        require_high_risk_approval: bool = True,
    ) -> None:
        self.max_calls_per_task = max_calls_per_task
        self.require_high_risk_approval = require_high_risk_approval
        self._calls_by_task: dict[str, int] = {}
        self._lock = Lock()

    def check_tool(self, task_id: str, tool: RegisteredTool | None) -> PolicyDecision:
        """Return whether a tool call is allowed."""
        if tool is None:
            return PolicyDecision(False, reason="unknown_tool")
        if any(term in tool.name.lower() for term in DANGEROUS_NAMES):
            return PolicyDecision(False, reason="dangerous_tool_name")
        with self._lock:
            count = self._calls_by_task.get(task_id, 0)
        if count >= self.max_calls_per_task:
            return PolicyDecision(False, reason="max_calls_exceeded")
        if tool.risk_level == "high" and self.require_high_risk_approval:
            return PolicyDecision(True, requires_approval=True, reason="approval_required")
        return PolicyDecision(True)

    def acquire_slot(self, task_id: str, tool: RegisteredTool | None) -> PolicyDecision:
        """Check policy and reserve one call slot atomically when execution is allowed."""
        if tool is None:
            return PolicyDecision(False, reason="unknown_tool")
        if any(term in tool.name.lower() for term in DANGEROUS_NAMES):
            return PolicyDecision(False, reason="dangerous_tool_name")
        with self._lock:
            count = self._calls_by_task.get(task_id, 0)
            if count >= self.max_calls_per_task:
                return PolicyDecision(False, reason="max_calls_exceeded")
            if tool.risk_level == "high" and self.require_high_risk_approval:
                return PolicyDecision(True, requires_approval=True, reason="approval_required")
            self._calls_by_task[task_id] = count + 1
        return PolicyDecision(True)

    def record_call(self, task_id: str) -> None:
        """Increment the tool-call counter for a task."""
        with self._lock:
            self._calls_by_task[task_id] = self._calls_by_task.get(task_id, 0) + 1
