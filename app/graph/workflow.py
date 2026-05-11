"""LangGraph workflow builder."""

from collections.abc import Callable
from inspect import isawaitable
from typing import Any, Protocol, cast

from langgraph.graph import END, StateGraph

from app.graph.reducers import (
    check_sufficiency,
    finalize_report,
    merge_state,
    route_after_critic,
    route_after_sufficiency,
)
from app.graph.state import WorkflowState


class RunnableAgent(Protocol):
    """Protocol for workflow agents."""

    name: str

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the agent and return state updates."""
        ...


class WorkflowRunner:
    """Small wrapper exposing a stable ainvoke interface around LangGraph."""

    def __init__(
        self,
        agents: list[RunnableAgent],
        on_stage: Callable[[dict[str, Any], str, int, int], Any] | None = None,
    ) -> None:
        self.agents = agents
        self.on_stage = on_stage
        self._compiled = self._build()

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
            "critic_rounds": 0,
            **initial_state,
        }
        return cast(dict[str, Any], await self._compiled.ainvoke(state))

    def _build(self) -> Any:
        graph = StateGraph(WorkflowState)
        stage_order = {
            "planner": 0,
            "researcher": 1,
            "sufficiency_check": 2,
            "analyst": 3,
            "writer": 4,
            "critic": 5,
            "finalize": 6,
        }
        total = len(stage_order)
        for agent in self.agents:
            graph.add_node(
                agent.name,
                cast(Any, self._agent_node(agent, stage_order[agent.name], total)),
            )
        graph.add_node(
            "sufficiency_check",
            cast(Any, self._plain_node("sufficiency_check", check_sufficiency, stage_order, total)),
        )
        graph.add_node(
            "finalize",
            cast(Any, self._plain_node("finalize", finalize_report, stage_order, total)),
        )
        graph.set_entry_point("planner")
        graph.add_edge("planner", "researcher")
        graph.add_edge("researcher", "sufficiency_check")
        graph.add_conditional_edges(
            "sufficiency_check",
            route_after_sufficiency,
            {"researcher": "researcher", "analyst": "analyst"},
        )
        graph.add_edge("analyst", "writer")
        graph.add_edge("writer", "critic")
        graph.add_conditional_edges(
            "critic",
            route_after_critic,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "finalize": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    def _agent_node(
        self,
        agent: RunnableAgent,
        index: int,
        total: int,
    ) -> Callable[[dict[str, Any]], Any]:
        async def _node(state: dict[str, Any]) -> dict[str, Any]:
            await self._notify_stage(state, agent.name, index, total)
            update = await agent.run(state)
            return merge_state(state, update)

        return _node

    def _plain_node(
        self,
        name: str,
        fn: Callable[[dict[str, Any]], dict[str, Any]],
        stage_order: dict[str, int],
        total: int,
    ) -> Callable[[dict[str, Any]], Any]:
        async def _node(state: dict[str, Any]) -> dict[str, Any]:
            await self._notify_stage(state, name, stage_order[name], total)
            return merge_state(state, fn(state))

        return _node

    async def _notify_stage(
        self,
        state: dict[str, Any],
        stage: str,
        index: int,
        total: int,
    ) -> None:
        if self.on_stage is not None:
            maybe_result = self.on_stage(state, stage, index, total)
            if isawaitable(maybe_result):
                await maybe_result


def build_graph(
    container: Any,
    on_stage: Callable[[dict[str, Any], str, int, int], Any] | None = None,
) -> WorkflowRunner:
    """Build the workflow from a dependency container.

    Args:
        container: Object exposing planner, researcher, analyst, writer, and critic.
        on_stage: Optional callback invoked before each agent runs.

    Returns:
        Configured workflow runner.
    """
    if getattr(getattr(container, "settings", None), "enable_rag_research", False):
        return FeatureFlaggedRAGWorkflowRunner(
            [
                container.planner,
                container.research_router,
                container.rag_indexer,
                container.rag_researcher,
                container.task_summarizer,
                container.analyst,
                container.writer,
                container.critic,
            ],
            on_stage=on_stage,
        )
    return WorkflowRunner(
        [
            container.planner,
            container.researcher,
            container.analyst,
            container.writer,
            container.critic,
        ],
        on_stage=on_stage,
    )


class FeatureFlaggedRAGWorkflowRunner(WorkflowRunner):
    """Workflow runner for the feature-flagged v4 RAG path."""

    def _build(self) -> Any:
        graph = StateGraph(WorkflowState)
        stage_order = {
            "planner": 0,
            "research_router": 1,
            "rag_indexer": 2,
            "rag_researcher": 3,
            "task_summarizer": 4,
            "analyst": 5,
            "writer": 6,
            "critic": 7,
            "finalize": 8,
        }
        total = len(stage_order)
        for agent in self.agents:
            graph.add_node(
                agent.name,
                cast(Any, self._agent_node(agent, stage_order[agent.name], total)),
            )
        graph.add_node(
            "finalize",
            cast(Any, self._plain_node("finalize", finalize_report, stage_order, total)),
        )
        graph.set_entry_point("planner")
        graph.add_edge("planner", "research_router")
        graph.add_edge("research_router", "rag_indexer")
        graph.add_edge("rag_indexer", "rag_researcher")
        graph.add_edge("rag_researcher", "task_summarizer")
        graph.add_edge("task_summarizer", "analyst")
        graph.add_edge("analyst", "writer")
        graph.add_edge("writer", "critic")
        graph.add_edge("critic", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()
