"""Replay snapshot utilities."""

from typing import Any

from app.harness.events import redact_payload
from app.schemas.harness import HarnessEvent


def create_replay_snapshot(
    state: dict[str, Any],
    events: list[HarnessEvent],
) -> dict[str, Any]:
    """Create a JSON-serializable replay snapshot without secrets."""
    return {
        "state": redact_payload(state),
        "event_ids": [event.event_id for event in events],
        "events": [event.model_dump() for event in events],
    }
