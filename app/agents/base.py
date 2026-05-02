"""Base agent interface."""

from typing import Any


class AgentBase:
    """Base class for all agents."""

    name: str = "base"

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent.

        Args:
            state: Workflow state.

        Returns:
            Partial state update.
        """
        raise NotImplementedError
