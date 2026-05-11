"""Harness event creation helpers."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.schemas.harness import HarnessEvent, HarnessEventType

SECRET_KEYS = ("api_key", "token", "secret", "password", "cookie")


def redact_payload(payload: dict[str, Any], limit: int = 1000) -> dict[str, Any]:
    """Return a secret-redacted and size-limited payload."""
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if any(secret in key.lower() for secret in SECRET_KEYS):
            redacted[key] = "[REDACTED]"
            continue
        text = str(value)
        redacted[key] = text[:limit] if len(text) > limit else value
    return redacted


def create_event(
    *,
    run_id: str,
    task_id: str,
    event_type: HarnessEventType,
    name: str,
    payload: dict[str, Any] | None = None,
    payload_limit: int = 1000,
) -> HarnessEvent:
    """Create one harness event with safe payload handling."""
    return HarnessEvent(
        event_id=f"evt_{uuid4().hex}",
        run_id=run_id,
        task_id=task_id,
        event_type=event_type,
        name=name,
        payload=redact_payload(payload or {}, payload_limit),
        created_at=datetime.now(UTC).isoformat(),
    )
