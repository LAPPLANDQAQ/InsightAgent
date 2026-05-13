"""Task request and response data contracts."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskStatus = Literal["PENDING", "RUNNING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED"]
TaskListItem = Annotated[str, Field(min_length=1, max_length=80)]


class CreateTaskRequest(BaseModel):
    """Request body for creating a research task."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=2, max_length=500)
    competitors: list[TaskListItem] = Field(default_factory=list, max_length=10)
    dimensions: list[TaskListItem] = Field(default_factory=list, max_length=12)

    @field_validator("query", mode="before")
    @classmethod
    def _strip_query(cls, value: Any) -> Any:
        """Strip query whitespace before length validation."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("competitors", "dimensions", mode="before")
    @classmethod
    def _strip_list_items(cls, value: Any) -> Any:
        """Strip list item whitespace before item length validation."""
        if not isinstance(value, list):
            return value
        return [item.strip() if isinstance(item, str) else item for item in value]


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    status: TaskStatus
    current_stage: str | None = None
    stage_label: str | None = None
    progress: float = 0.0
    estimated_remaining_seconds: int | None = None
    issues: list[str] = Field(default_factory=list)
