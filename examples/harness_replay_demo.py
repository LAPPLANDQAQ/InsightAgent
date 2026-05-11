"""Run a local harness replay demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.harness.events import create_event
from app.harness.replay import create_replay_snapshot
from app.harness.tracing import InMemoryTraceStore


def main() -> None:
    """Print a deterministic replay snapshot."""
    store = InMemoryTraceStore()
    event = create_event(
        run_id="run_demo",
        task_id="task_demo",
        event_type="agent_start",
        name="planner",
        payload={"api_key": "secret-value"},
    )
    store.append(event)
    snapshot = create_replay_snapshot({"task_id": "task_demo"}, store.list_by_task("task_demo"))
    print(snapshot)


if __name__ == "__main__":
    main()
