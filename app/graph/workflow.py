"""Sequential workflow builder."""

from typing import Any, Protocol

from app.graph.reducers import merge_state


class RunnableAgent(Protocol):
    """Protocol for workflow agents."""

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the agent and return state updates."""
        ...


class InsightWorkflow:
    """Workflow object exposing a LangGraph-like ainvoke method."""

    def __init__(self, agents: list[RunnableAgent]) -> None:
        self.agents = agents

    async def ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        """Run the workflow.

        Args:
            initial_state: Initial workflow state.

        Returns:
            Final workflow state.
        """
        state = {
            "task_status": "RUNNING",
            "issues": [],
            "iteration_count": 0,
            **initial_state,
        }
        for agent in self.agents:
            update = await agent.run(state)
            state = merge_state(state, update)
        state.setdefault("task_status", "COMPLETED")
        return state


def build_graph(container: Any) -> InsightWorkflow:
    """Build the workflow from a dependency container.

    Args:
        container: Object exposing planner, researcher, analyst, writer, and critic.

    Returns:
        Configured workflow.
    """
    return InsightWorkflow(
        [
            container.planner,
            container.researcher,
            container.analyst,
            container.writer,
            container.critic,
        ]
    )
