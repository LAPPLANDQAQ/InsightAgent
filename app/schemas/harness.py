"""Harness runtime data contracts."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

HarnessEventType = Literal["agent_start", "agent_end", "tool_start", "tool_end", "error"]


class HarnessEvent(BaseModel):
    """Single trace event emitted by the harness runtime."""

    event_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    event_type: HarnessEventType
    name: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
