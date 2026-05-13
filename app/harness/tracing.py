"""In-memory trace store."""

from threading import Lock

from app.schemas.harness import HarnessEvent


class InMemoryTraceStore:
    """Append-only trace store for tests and local demos."""

    def __init__(self) -> None:
        self._events: list[HarnessEvent] = []
        self._lock = Lock()

    def append(self, event: HarnessEvent) -> None:
        """Append one event preserving insertion order."""
        with self._lock:
            self._events.append(event)

    def list_by_run(self, run_id: str) -> list[HarnessEvent]:
        """Return events for a run id."""
        with self._lock:
            return [event for event in self._events if event.run_id == run_id]

    def list_by_task(self, task_id: str) -> list[HarnessEvent]:
        """Return events for a task id."""
        with self._lock:
            return [event for event in self._events if event.task_id == task_id]
