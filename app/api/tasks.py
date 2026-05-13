"""Task API routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.report import ReportResponse
from app.schemas.task import CreateTaskRequest, TaskStatusResponse
from app.services.task_service import TaskLimitError

router = APIRouter(prefix="/api")


def get_task_service(request: Request) -> Any:
    """Return TaskService from application state.

    Args:
        request: FastAPI request.

    Returns:
        TaskService instance.
    """
    return request.app.state.task_service


TaskServiceDep = Annotated[Any, Depends(get_task_service)]


@router.post("/tasks")
async def create_task(req: CreateTaskRequest, svc: TaskServiceDep) -> dict[str, str]:
    """Create a research task.

    Args:
        req: Task creation request.
        svc: Task service dependency.

    Returns:
        Created task identifier and initial status.
    """
    try:
        task_id = await svc.create_task(req.query, req.competitors, req.dimensions)
    except TaskLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return {"task_id": task_id, "status": "PENDING"}


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str, svc: TaskServiceDep) -> TaskStatusResponse:
    """Get task status.

    Args:
        task_id: Task identifier.
        svc: Task service dependency.

    Returns:
        Task status response.
    """
    info = svc.get_status(task_id)
    if info.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(
        task_id=task_id,
        status=info["status"],
        current_stage=info.get("stage"),
        stage_label=info.get("stage_label"),
        progress=float(info.get("progress", 0.0)),
        estimated_remaining_seconds=info.get("estimated_remaining_seconds"),
        issues=[str(item) for item in info.get("issues", [])],
    )


@router.get("/tasks/{task_id}/report", response_model=ReportResponse)
async def get_report(task_id: str, svc: TaskServiceDep) -> ReportResponse:
    """Get task report.

    Args:
        task_id: Task identifier.
        svc: Task service dependency.

    Returns:
        Report response.
    """
    report = svc.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not ready")
    info = svc.get_status(task_id)
    return ReportResponse(
        task_id=task_id,
        status=info["status"],
        report_markdown=report["report_markdown"],
        quality_metrics=report["quality_metrics"],
    )
