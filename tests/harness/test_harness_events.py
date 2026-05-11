"""Tests for harness events."""

from app.harness.events import create_event


def test_create_event_redacts_payload():
    """Harness events redact secrets."""
    event = create_event(
        run_id="run",
        task_id="task",
        event_type="tool_start",
        name="tool",
        payload={"token": "secret"},
    )

    assert event.payload["token"] == "[REDACTED]"
