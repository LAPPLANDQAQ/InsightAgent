"""Task status helper functions."""

from time import monotonic

STAGE_LABELS = {
    "queued": "排队中",
    "planner": "规划调研方案",
    "researcher": "搜索资料并抽取证据",
    "sufficiency_check": "检查证据充分性",
    "analyst": "分析竞品差异",
    "writer": "生成报告",
    "critic": "质量检查",
    "finalize": "整理最终结果",
    "failed": "任务失败",
    "completed": "任务完成",
}
STALE_RUNNING_MESSAGE = "服务重启后任务执行上下文丢失，已标记为失败。"


def status_payload(
    *,
    status: str,
    stage: str | None,
    issues: list,
    progress: float,
    started_at: float | None,
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
        "stage_label": STAGE_LABELS.get(stage or "", stage or "未知阶段"),
        "progress": clamped,
        "estimated_remaining_seconds": eta,
        "issues": issues,
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
