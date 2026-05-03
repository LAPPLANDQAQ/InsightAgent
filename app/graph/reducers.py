"""Workflow reducer helpers."""

from typing import Any


def merge_state(state: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Merge a node update into workflow state.

    Args:
        state: Existing workflow state.
        update: Node output.

    Returns:
        Merged state.
    """
    merged = {**state, **update}
    if "issues" in state or "issues" in update:
        merged["issues"] = list(state.get("issues", [])) + list(update.get("issues", []))
    return merged


def check_sufficiency(state: dict[str, Any]) -> dict[str, Any]:
    """Record a sufficiency routing checkpoint.

    Args:
        state: Current workflow state.

    Returns:
        State update with the next research iteration count.
    """
    return {
        "current_stage": "sufficiency_check",
        "iteration_count": int(state.get("iteration_count", 0)) + 1,
    }


def route_after_sufficiency(state: dict[str, Any]) -> str:
    """Choose whether to research again or continue to analysis.

    Args:
        state: Current workflow state.

    Returns:
        Next LangGraph node name.
    """
    sufficiency = state.get("sufficiency") or {}
    if sufficiency.get("is_sufficient"):
        return "analyst"
    if int(state.get("iteration_count", 0)) >= int(state.get("max_iterations", 1)):
        return "analyst"
    return "researcher"


def route_after_critic(state: dict[str, Any]) -> str:
    """Route after critic review.

    Args:
        state: Current workflow state.

    Returns:
        Next LangGraph node name.
    """
    issues = state.get("critic_issues") or []
    if not issues:
        return "finalize"
    if int(state.get("critic_rounds", 0)) >= int(state.get("max_iterations", 1)):
        return "finalize"
    first_target = str(issues[0].get("target_stage") or "finalize")
    return first_target if first_target in {"researcher", "analyst", "writer"} else "finalize"


def finalize_report(state: dict[str, Any]) -> dict[str, Any]:
    """Finalize task status and report fields.

    Args:
        state: Current workflow state.

    Returns:
        Final state update.
    """
    status = state.get("task_status")
    if status not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        status = "COMPLETED_WITH_WARNINGS" if state.get("issues") else "COMPLETED"
    return {
        "task_status": status,
        "final_report": state.get("final_report") or state.get("draft_report") or "",
        "current_stage": "finalize",
    }
