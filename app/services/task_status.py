"""Task status helper functions."""

from time import monotonic

STAGE_LABELS = {
    "queued": "Queued",
    "planner": "Planning",
    "researcher": "Researching",
    "sufficiency_check": "Checking Evidence Sufficiency",
    "analyst": "Analyzing",
    "writer": "Writing Report",
    "critic": "Reviewing",
    "finalize": "Finalizing",
    "research_router": "Routing Research",
    "rag_indexer": "Indexing Evidence",
    "rag_researcher": "Retrieving Evidence",
    "task_summarizer": "Summarizing Research",
    "failed": "Failed",
    "completed": "Completed",
}
STALE_RUNNING_MESSAGE = (
    "Task execution context was lost after service restart; "
    "last known stage: {stage}; marked as failed."
)


def status_payload(
    *,
    status: str,
    stage: str | None,
    issues: list,
    progress: float,
    started_at: float | None,
    structured_issues: list[dict] | None = None,
) -> dict:
    """Build a normalized status payload.

    Args:
        status: Current task status.
        stage: Current workflow stage.
        issues: User-visible issues.
        progress: Progress ratio.
        started_at: Monotonic start timestamp.

    Returns:
        Status payload used by API and frontend.
    """
    clamped = max(0.0, min(1.0, progress))
    eta = estimate_remaining_seconds(clamped, started_at, status)
    return {
        "status": status,
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage or "", stage or "Unknown Stage"),
        "progress": clamped,
        "estimated_remaining_seconds": eta,
        "issues": issues,
        "structured_issues": structured_issues or [],
        "started_monotonic": started_at,
    }


def estimate_remaining_seconds(
    progress: float,
    started_at: float | None,
    status: str,
) -> int:
    """Estimate remaining seconds for an active task.

    Args:
        progress: Current progress ratio.
        started_at: Monotonic start timestamp.
        status: Current task status.

    Returns:
        Estimated remaining seconds.
    """
    if status in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"}:
        return 0
    if started_at is None or progress <= 0.05:
        return 120
    elapsed = max(0.0, monotonic() - started_at)
    total_estimate = elapsed / max(progress, 0.05)
    return int(max(5.0, total_estimate - elapsed))
