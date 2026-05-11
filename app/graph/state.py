"""Workflow state definitions."""

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    """Typed dictionary for the research workflow state."""

    task_id: str
    task_status: str
    user_query: str
    requested_competitors: list[str]
    requested_dimensions: list[str]
    competitors: list[dict[str, Any]]
    fetched_pages: list[dict[str, Any]]
    plan: dict[str, Any]
    analysis: dict[str, Any]
    draft_report: str
    final_report: str
    sufficiency: dict[str, Any]
    critic_issues: list[dict[str, Any]]
    current_stage: str
    iteration_count: int
    critic_rounds: int
    max_iterations: int
    sufficiency_threshold: float
    issues: list[str]
    token_usage: dict[str, Any]
    research_todos: list[dict[str, Any]]
    research_strategies: list[dict[str, Any]]
    research_notes: list[dict[str, Any]]
    rag_parent_docs: list[dict[str, Any]]
    rag_chunks: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
    rag_metrics: dict[str, Any]
    agent_metrics: dict[str, Any]
    harness_metrics: dict[str, Any]
