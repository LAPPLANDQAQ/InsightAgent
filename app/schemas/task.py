"""Task request and response data contracts."""

from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["PENDING", "RUNNING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"]


class CreateTaskRequest(BaseModel):
    """Request body for creating a research task."""

    query: str = Field(min_length=2)
    competitors: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    status: TaskStatus
    current_stage: str | None = None
    stage_label: str | None = None
    progress: float = 0.0
    estimated_remaining_seconds: int | None = None
    issues: list[str] = Field(default_factory=list)
