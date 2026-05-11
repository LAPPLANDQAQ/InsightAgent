"""Tests for replay snapshots."""

from app.harness.events import create_event
from app.harness.replay import create_replay_snapshot


def test_replay_snapshot_is_json_serializable_and_redacted():
    """Replay snapshots store event ids and redact secrets."""
    event = create_event(run_id="run", task_id="task", event_type="agent_start", name="agent")
    snapshot = create_replay_snapshot({"api_key": "secret"}, [event])

    assert snapshot["state"]["api_key"] == "[REDACTED]"
    assert snapshot["event_ids"] == [event.event_id]
