"""Replay snapshot utilities."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.harness.events import redact_payload
from app.schemas.harness import HarnessEvent


class ReplaySnapshot(BaseModel):
    """Serializable snapshot for replay and debugging."""

    state: dict[str, Any]
    event_ids: list[str]
    events: list[dict[str, Any]]
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


def create_replay_snapshot(
    state: dict[str, Any],
    events: list[HarnessEvent],
) -> dict[str, Any]:
    """Create a JSON-serializable replay snapshot without secrets."""
    snapshot = ReplaySnapshot(
        state=redact_payload(state),
        event_ids=[event.event_id for event in events],
        events=[event.model_dump() for event in events],
    )
    return snapshot.model_dump()
