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
