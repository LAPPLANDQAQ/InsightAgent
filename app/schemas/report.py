"""Report response data contracts."""

from typing import Any

from pydantic import BaseModel

from app.schemas.task import TaskStatus


class ReportResponse(BaseModel):
    """Report response returned by the API."""

    task_id: str
    status: TaskStatus
    report_markdown: str
    quality_metrics: dict[str, Any]
