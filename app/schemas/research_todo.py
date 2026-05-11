"""Research TODO data contract."""

from typing import Literal

from pydantic import BaseModel, Field

TodoStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class ResearchTodo(BaseModel):
    """Executable research task generated from a plan."""

    todo_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    competitor_name: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)
    intent: str = Field(min_length=1, max_length=500)
    query: str = Field(min_length=1, max_length=300)
    preferred_source_types: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    priority: int = Field(default=3, ge=1, le=5)
    status: TodoStatus = "pending"
    retry_count: int = Field(default=0, ge=0)
    created_at: str
    updated_at: str | None = None
