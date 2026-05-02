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
        merged["issues"] = list(update.get("issues", state.get("issues", [])))
    return merged
